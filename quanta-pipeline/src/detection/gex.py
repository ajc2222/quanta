"""Intraday GEX computation from options chain snapshots.

GEX = gamma x open_interest x contract_multiplier x spot_price (per strike)
Per-strike GEX summed by call/put to derive walls, flip, zero gamma, max pain.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

import numpy as np

from src.detection.models import GEXLevelDaily


MULTIPLIER = {"SPX": 100, "NDX": 100}


def compute_gex(snapshot: list[dict], underlying: str, snap_date: date) -> GEXLevelDaily:
    """Compute GEX levels from an options chain snapshot.

    Args:
        snapshot: list of dicts from options_chain_snapshots.
                  Each has: strike, call_gamma, put_gamma, call_oi, put_oi
        underlying: "SPX" or "NDX"
        snap_date: date of snapshot

    Returns GEXLevelDaily with computed levels.
    """
    mult = MULTIPLIER.get(underlying, 100)
    spot_price = None
    per_strike: list[dict] = []

    total_call_gex = 0.0
    total_put_gex = 0.0

    for row in snapshot:
        strike = Decimal(str(row["strike"]))
        call_g = float(row.get("call_gamma", 0) or 0) * mult
        put_g = float(row.get("put_gamma", 0) or 0) * mult
        call_oi = float(row.get("call_oi", 0) or 0)
        put_oi = float(row.get("put_oi", 0) or 0)
        call_gex = call_g * call_oi * float(strike)
        put_gex = put_g * put_oi * float(strike)

        total_call_gex += call_gex
        total_put_gex += put_gex

        per_strike.append({
            "strike": strike,
            "call_gex": call_gex,
            "put_gex": put_gex,
            "net_gex": call_gex - put_gex,
            "call_oi": call_oi,
            "put_oi": put_oi,
        })

        if "spot" in row:
            spot_price = Decimal(str(row["spot"]))

    if not per_strike:
        return GEXLevelDaily(
            date=snap_date, underlying=underlying,
            spot_price=Decimal("0"),
            call_wall_strike=Decimal("0"), put_wall_strike=Decimal("0"),
            max_pain_strike=Decimal("0"),
        )

    call_wall = max(per_strike, key=lambda r: r["call_gex"])
    put_wall = max(per_strike, key=lambda r: r["put_gex"])

    sorted_strikes = sorted(per_strike, key=lambda r: r["strike"])

    gex_flip = None
    for i in range(len(sorted_strikes) - 1):
        curr_net = sorted_strikes[i]["net_gex"]
        next_net = sorted_strikes[i + 1]["net_gex"]
        if (curr_net >= 0 and next_net < 0) or (curr_net < 0 and next_net >= 0):
            gex_flip = sorted_strikes[i]["strike"]
            break

    zero_gamma_strike = min(sorted_strikes, key=lambda r: abs(r["net_gex"]))["strike"]

    if spot_price is not None and sorted_strikes:
        strikes = np.array([float(r["strike"]) for r in sorted_strikes])
        oi = np.array([float(r.get("call_oi", 0) + r.get("put_oi", 0)) for r in sorted_strikes])
        total_oix = np.sum(oi * strikes)
        total_oi = np.sum(oi)
        max_pain_approx = total_oix / total_oi if total_oi > 0 else 0.0
        max_pain = min(sorted_strikes, key=lambda r: abs(float(r["strike"]) - max_pain_approx))["strike"]
    else:
        max_pain = Decimal("0")

    net_gex = total_call_gex - total_put_gex

    return GEXLevelDaily(
        date=snap_date, underlying=underlying,
        spot_price=spot_price or Decimal("0"),
        call_wall_strike=call_wall["strike"],
        put_wall_strike=put_wall["strike"],
        gex_flip_strike=gex_flip,
        zero_gamma_strike=zero_gamma_strike,
        max_pain_strike=max_pain,
        total_call_gex=total_call_gex,
        total_put_gex=total_put_gex,
        net_gex=net_gex,
    )
