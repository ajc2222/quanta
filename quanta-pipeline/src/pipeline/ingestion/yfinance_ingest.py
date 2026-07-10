"""Ingest SPX/NDX options chains via yfinance and compute GEX.

Gamma is not returned by yfinance, so we compute it from the Black-Scholes
model using the data yfinance *does* return: strike, spot, implied volatility,
and days-to-expiry.

Runs intraday (09:00-16:30 ET) at configurable intervals.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
import pytz
import yfinance as yf

from ..config import Config
from ..db import insert_options_snapshot, insert_gex_levels, upsert_gex_summary
from ._retry import http_retry

log = logging.getLogger("pipeline.ingestion.yfinance")

ET = pytz.timezone("America/New_York")

# Multiplier for SPX/NDX standard options
CONTRACT_MULTIPLIER = 100

# Risk-free rate proxy (current 2yr Treasury yield ~ 4.75%)
RISK_FREE_RATE = 0.0475  # ponytail: hardcoded; pull from FRED if rates move >100bp


# ---------------------------------------------------------------------------
# Black-Scholes gamma
# ---------------------------------------------------------------------------


def _norm_pdf(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x ** 2) / np.sqrt(2 * np.pi)


def compute_gamma(
    S: float,
    K: np.ndarray,
    T: np.ndarray,
    sigma: np.ndarray,
    r: float = RISK_FREE_RATE,
) -> np.ndarray:
    """Compute Black-Scholes gamma for an array of options.

    Parameters
    ----------
    S : float — spot price
    K : ndarray — strike prices
    T : ndarray — time to expiry in years
    sigma : ndarray — implied volatilities (decimals, e.g. 0.20 for 20%)

    Returns
    -------
    ndarray — gamma per option
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * np.sqrt(T))


# ---------------------------------------------------------------------------
# Fetch chain
# ---------------------------------------------------------------------------


@http_retry("yfinance")
def _fetch_chain(underlying: str) -> tuple[pd.DataFrame, float]:
    """Fetch ALL option expirations for *underlying*.

    Returns (DataFrame with columns: strike, expiry, type, OI, IV, last_price,
    spot) and the spot price.
    """
    ticker = yf.Ticker(underlying)

    # Get current price
    hist = ticker.history(period="1d", interval="1m")
    if hist.empty:
        raise ValueError(f"No price data for {underlying}")
    spot = float(hist["Close"].iloc[-1])

    expiry_dates = ticker.options
    if not expiry_dates:
        raise ValueError(f"No options for {underlying}")

    rows: list[dict] = []
    for expiry_str in expiry_dates:
        chain = ticker.option_chain(expiry_str)
        expiry_date = pd.Timestamp(expiry_str).date()
        dte = max((pd.Timestamp(expiry_str) - pd.Timestamp.now()).days, 1)

        for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
            if df.empty:
                continue
            for _, opt in df.iterrows():
                rows.append({
                    "strike": float(opt["strike"]),
                    "expiry": expiry_date,
                    "option_type": opt_type,
                    "open_interest": min(int(opt.get("openInterest", 0) or 0), 10_000_000),
                    "volume": int(opt.get("volume", 0) or 0),
                    "implied_volatility": min(float(opt.get("impliedVolatility", np.nan) or np.nan), 10.0),
                    "last_price": float(opt.get("lastPrice", np.nan) or np.nan),
                })

    result = pd.DataFrame(rows)
    result["dte"] = dte
    return result, spot


# ---------------------------------------------------------------------------
# GEX computation
# ---------------------------------------------------------------------------


def _compute_gex_snapshot(
    chain: pd.DataFrame,
    spot: float,
    underlying: str,
    now: pd.Timestamp,
) -> tuple[list[dict], dict]:
    """Compute per-strike GEX and summary metrics from a raw chain DataFrame.

    Returns (per_strike_rows, summary_dict).
    """
    chain = chain.dropna(subset=["implied_volatility"]).copy()
    if chain.empty:
        return [], {}

    chain["T"] = chain["dte"] / 365.0
    chain["gamma"] = compute_gamma(
        S=spot,
        K=chain["strike"].values,
        T=chain["T"].values,
        sigma=chain["implied_volatility"].values,
    )

    # GEX per option = gamma * OI * multiplier * S
    # Puts have negative gamma by convention
    chain["gex"] = chain["gamma"] * chain["open_interest"] * CONTRACT_MULTIPLIER * spot
    chain.loc[chain["option_type"] == "put", "gex"] *= -1.0

    today = now.date()
    date_param = today if isinstance(today, date) else today.date()

    per_strike = []
    for strike, grp in chain.groupby("strike"):
        call_gex = grp.loc[grp["option_type"] == "call", "gex"].sum()
        put_gex = grp.loc[grp["option_type"] == "put", "gex"].sum()
        per_strike.append({
            "snapshot_timestamp": now,
            "date": date_param,
            "underlying": underlying,
            "strike": strike,
            "call_gex": round(call_gex, 2),
            "put_gex": round(put_gex, 2),
            "net_gex": round(call_gex + put_gex, 2),
        })

    # Summary
    gex_df = pd.DataFrame(per_strike)
    if gex_df.empty:
        return [], {}

    total_call_gex = gex_df["call_gex"].sum()
    total_put_gex = gex_df["put_gex"].sum()
    net_gex = total_call_gex + total_put_gex

    call_wall_row = gex_df.loc[gex_df["call_gex"].idxmax()] if not gex_df[gex_df["call_gex"] > 0].empty else None
    # Put wall = strike with largest absolute put GEX (most negative)
    put_wall_row = gex_df.loc[gex_df["put_gex"].abs().idxmax()] if not gex_df[gex_df["put_gex"] < 0].empty else None

    gex_flip = None
    sorted_by_strike = gex_df.sort_values("strike")
    for i in range(len(sorted_by_strike) - 1):
        if sorted_by_strike.iloc[i]["net_gex"] <= 0 <= sorted_by_strike.iloc[i + 1]["net_gex"]:
            gex_flip = sorted_by_strike.iloc[i]["strike"]
            break

    zero_gamma = gex_df.iloc[(gex_df["net_gex"].abs()).idxmin()]["strike"] if not gex_df.empty else None

    # Max pain: the strike where total dollar loss for option buyers is minimized
    # Approximate by finding strike where sum of put + call OI * |S - K| is minimized
    # This is a simplification; an accurate max pain requires all strikes simultaneously
    strikes = chain["strike"].unique()
    best_strike = strikes[0]
    best_pain = float("inf")
    for sk in strikes:
        call_pain = chain.loc[(chain["strike"] == sk) & (chain["option_type"] == "call"), "open_interest"].sum() * max(spot - sk, 0)
        put_pain = chain.loc[(chain["strike"] == sk) & (chain["option_type"] == "put"), "open_interest"].sum() * max(sk - spot, 0)
        total_pain = call_pain + put_pain
        if total_pain < best_pain:
            best_pain = total_pain
            best_strike = sk
    max_pain = best_strike

    summary = {
        "snapshot_timestamp": now,
        "date": date_param,
        "underlying": underlying,
        "total_call_gex": round(total_call_gex, 2),
        "total_put_gex": round(total_put_gex, 2),
        "net_gex": round(net_gex, 2),
        "call_wall_strike": round(call_wall_row["strike"], 2) if call_wall_row is not None else None,
        "put_wall_strike": round(put_wall_row["strike"], 2) if put_wall_row is not None else None,
        "gex_flip_strike": round(gex_flip, 2) if gex_flip is not None else None,
        "zero_gamma_strike": round(zero_gamma, 2) if zero_gamma is not None else None,
        "max_pain_strike": round(max_pain, 2) if max_pain is not None else None,
        "spot_price": round(spot, 2),
    }

    return per_strike, summary


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_snapshot(per_strike: list, summary: dict, underlying: str) -> None:
    """Basic sanity checks on the ingested data."""
    if not per_strike:
        log.warning("yfinance: %s GEX per-strike list is empty", underlying)
        return
    if summary["total_call_gex"] == 0 and summary["total_put_gex"] == 0:
        log.warning("yfinance: %s both call and put GEX are 0 — check data", underlying)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_snapshot(cfg: Config, underlying: str) -> dict[str, Any] | None:
    """Fetch options chain for *underlying*, compute GEX, persist.

    Returns summary dict or None on failure.
    """
    log.info("yfinance: fetching %s options chain", underlying)
    try:
        chain, spot = _fetch_chain(underlying)
    except Exception:
        log.exception("yfinance: failed to fetch chain for %s", underlying)
        return None

    if chain.empty:
        log.warning("yfinance: empty chain for %s", underlying)
        return None

    now = pd.Timestamp.now(tz=ET)

    # 1. Store raw chain (pivot to call/put per-strike format)
    raw_rows = chain.to_dict("records")
    strike_map: dict[float, dict] = {}
    for r in raw_rows:
        sk = r["strike"]
        if sk not in strike_map:
            strike_map[sk] = {
                "snapshot_timestamp": now,
                "underlying": underlying,
                "strike": sk,
                "expiry": r["expiry"],
                "call_oi": 0, "put_oi": 0,
                "call_volume": 0, "put_volume": 0,
                "call_iv": None, "put_iv": None,
                "call_delta": None, "put_delta": None,
                "call_gamma": None, "put_gamma": None,
                "spot_price": round(spot, 2),
            }
        prefix = "call" if r["option_type"] == "call" else "put"
        strike_map[sk][f"{prefix}_oi"] = int(r.get("open_interest", 0) or 0)
        strike_map[sk][f"{prefix}_volume"] = int(r.get("volume", 0) or 0)
        strike_map[sk][f"{prefix}_iv"] = float(r.get("implied_volatility", 0) or 0)
    insert_options_snapshot(list(strike_map.values()))

    # 2. Compute + store GEX
    per_strike, summary = _compute_gex_snapshot(chain, spot, underlying.replace("^", ""), now)

    _validate_snapshot(per_strike, summary, underlying)

    if per_strike:
        insert_gex_levels(per_strike)
    if summary:
        upsert_gex_summary(summary)

    log.info(
        "yfinance: %s done — spot=%.2f, GEX net=%.0f, call_wall=%s, put_wall=%s",
        underlying, spot, summary.get("net_gex", 0),
        summary.get("call_wall_strike"), summary.get("put_wall_strike"),
    )

    return summary


def run_all(cfg: Config) -> dict[str, dict | None]:
    """Run options + GEX snapshot for all configured underlyings."""
    results: dict[str, dict | None] = {}
    for sym in cfg.options_underlyings:
        try:
            results[sym] = run_snapshot(cfg, sym)
        except Exception:
            log.exception("yfinance snapshot failed for %s", sym)
            results[sym] = None
    return results
