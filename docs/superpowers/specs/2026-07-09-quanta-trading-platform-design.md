# Quanta — Trading Statistics Platform: Design Spec
**Date:** 2026-07-09
**Version:** v1.1
**Status:** Approved for implementation planning

---

## 1. Product Overview

Quanta is a web-based trading statistics platform built exclusively for advanced and professional futures traders who trade using ICT (Inner Circle Trader) methodology and Quarterly Theory. It is not an education platform — users are assumed to have full fluency in all ICT/QT terminology and concepts. The platform's value is providing deep, data-backed probability statistics on ICT-specific setups and structures that no other tool currently offers at this level of specificity.

**Core differentiators from Edgeful:**
- ICT and QT frameworks as first-class citizens (not generic OHLCV stats)
- Power of 3 reports across 7 specific time windows with fractal phase-awareness
- PD array correlation at HOD/LOD (which FVG or OB held the extreme)
- Options & GEX module integrated with ICT stat engine (historical respect rates at GEX levels)
- Zero onboarding — built for professionals, dense information layout

---

## 2. Target Audience

- **Primary:** Advanced to professional ICT futures day traders
- **Secondary:** Prop-firm traders using ICT methodology
- **Explicitly excluded:** Beginners, options-only traders, long-term investors, discretionary non-ICT traders

Users know what NWOG, NDOG, AMD cycles, PD arrays, FVGs, OBs, BSL/SSL, killzones, and PO3 mean. No tooltips, no explainers, no onboarding videos.

---

## 3. Asset Classes (v1)

**Futures only:** ES, NQ, GC, CL, MES, MNQ (CME via Databento)

For Options & GEX module: SPX and NDX options chains (via yfinance, applied to ES/NQ analysis)

---

## 4. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 14 (App Router) | UI, report rendering, routing |
| Hosting | Vercel | Frontend deployment, serverless API routes |
| Auth | Clerk | User accounts, session management |
| Database | Supabase (Postgres) | Precomputed stats, PD array labels, PO3 phase classifications |
| Cache | Upstash Redis | Sub-100ms report queries, TTL-invalidated after each pipeline run |
| Data Pipeline | Python service on Railway | Nightly + intraday data ingestion and stat computation |
| Futures Data | Databento (GLBX.MDP3) | CME futures OHLCV 1-min bars, 7+ years historical |
| Options Data | yfinance (Yahoo Finance) | SPX/NDX options chains, free, 15-20 min delayed |
| News Data | ForexFactory scrape | Daily news events for PO3 news-day correlation |
| Payments | Stripe | Added when monetization is introduced |

**Architecture principle:** The Python pipeline is fully decoupled from the Next.js app. Pipeline writes to Postgres; app only reads. Rebuild either side independently.

---

## 5. Navigation Structure

```
Quanta
├── ICT Reports
│   ├── Fair Value Gaps
│   ├── Order Blocks
│   ├── Killzones & Sessions
│   ├── Liquidity Sweeps
│   ├── Power of 3
│   └── Key Opens
├── Options & GEX
│   ├── GEX Levels
│   ├── Historical GEX Stats
│   ├── Put/Call Ratio
│   └── Open Interest by Strike
├── QT Reports          ← locked, "coming soon"
└── Account / Settings
```

ICT and QT are top-level sections with separate report libraries. They never share a screen.

Updated ICT navigation:
```
ICT Reports
├── Fair Value Gaps
├── Order Blocks
├── Killzones & Sessions
├── Liquidity Sweeps
├── Power of 3
├── Key Opens (18:00 / 00:00 / 10:00)
├── Opening Gaps (NDOG / NWOG)
├── News Data Highs & Lows
└── Macros
    ├── 9:50–10:10
    ├── 10:50–11:10
    ├── 1:10–1:40
    ├── 2:10–2:40
    └── 3:15–4:00
```

---

## 6. ICT Reports Module

### 6.1 Standard Report Page Layout

Every report page follows this structure:

```
[Instrument Selector] [Lookback: 3mo / 6mo / 1yr / Custom] [Session Filter]
────────────────────────────────────────────────────────────────────────────
[Primary Stat Cards]
────────────────────────────────────────────────────────────────────────────
[Subreport Tabs: By Weekday | By Size | By Session | By News Day | By HTF Phase]
────────────────────────────────────────────────────────────────────────────
[Data Table + Chart]
[Sample size indicator — red warning badge if n < 30]
```

All filters are URL-persistent. Traders can bookmark and share exact report views.

---

### 6.2 Fair Value Gaps (FVG)

**What it tracks:** Every FVG detected on 1m/5m/15m/1H/4H/Daily bars per instrument.

**Stats:**
- Fill rate (full fill to 100%, partial fill to 50%)
- Avg fill time (minutes/hours from creation to fill)
- Partial fill % (how often price enters but does not fully close the gap)
- Distribution by timeframe (1H FVGs fill faster than Daily FVGs)

**Subreports:**
- By weekday
- By session (London / NY AM / NY PM / Overnight)
- By size (small / medium / large relative to ATR)
- By HTF bias alignment (FVG in direction of Daily PO3 phase vs counter-trend)
- By news day vs non-news day

**Database table:** `fvg_instances`, aggregated into `report_fvg_stats`

---

### 6.3 Order Blocks (OB)

**What it tracks:** Every detected OB per instrument and timeframe.

**Stats:**
- Respect rate (price returns to OB and reverses)
- Break rate (price returns to OB and continues through)
- Mitigation time (avg time from OB creation to first test)
- Avg reversal magnitude after respect (in points and % of OB range)

**Subreports:**
- By timeframe
- By session
- By weekday
- By HTF bias alignment (OB in PO3 distribution direction vs counter)
- Breaker block conversion rate (OBs that break and become breakers)

**Database table:** `order_block_instances`, aggregated into `report_ob_stats`

---

### 6.4 Killzones & Sessions

**What it tracks:** Session performance stats for London Open, NY AM, NY PM, and the Asian range.

**Stats:**
- Direction bias by session (bullish / bearish % by weekday)
- Judas swing: direction of initial move and reversal rate
- Judas swing magnitude (avg points before reversal)
- Session range (avg high-low range by weekday)
- Session overlap behavior (London-NY overlap directional stats)

**Subreports:**
- By weekday
- By news day (8:30 news present vs not)
- By preceding session bias (London bullish → NY AM bullish rate)
- By instrument

**Database table:** `sessions`, aggregated into `report_killzone_stats`

---

### 6.5 Liquidity Sweeps

**What it tracks:** BSL (buy-side liquidity) and SSL (sell-side liquidity) sweep events per session.

**Stats:**
- Sweep rate (how often a BSL/SSL level is swept during the session)
- Reversal rate after sweep (sweep + reversal vs sweep + continuation)
- Avg reversal magnitude after confirmed sweep
- Time distribution of sweeps within session
- Double sweep rate (both BSL and SSL swept same session)

**Subreports:**
- By session
- By weekday
- By sweep size relative to prior range
- By news day
- By HTF bias (sweeping SSL in uptrend vs downtrend)

**Database table:** `liquidity_levels`, aggregated into `report_liquidity_stats`

---

### 6.6 Key Opens

**What it tracks:** Price behavior at three specific open times: 18:00 ET (Globex open), 00:00 ET (Midnight open), 10:00 ET (Late morning open).

**Stats per open time:**
- Respect rate (price returns to open level and reverses)
- Rejection rate (price opens and immediately moves away, never returns)
- Avg deviation before respect (how many points price moves before returning)
- Reversal magnitude after respect
- Time to first test of open level

**Subreports:**
- By weekday
- By instrument
- By session context (what session is active at each open)
- By news day

**Database table:** `key_opens`, aggregated into `report_keyopen_stats`

---

### 6.7 Power of 3 (PO3) — Flagship Report

#### Overview

PO3 is the most complex and differentiated report in Quanta. It tracks the Open-Manipulation-Distribution (AMD) sequence across 7 specific time windows. The system is fractal-aware: higher timeframe PO3 phase is used as a filter variable for lower timeframe PO3 stats.

#### 7 PO3 Windows

| Window | Timeframe | Hours (ET) | Notes |
|---|---|---|---|
| Daily | Daily candle | 18:00 – 17:00 next day | Full trading day |
| 4H Morning | 4H candle | 06:00 – 10:00 | London into NY open |
| 4H Midday | 4H candle | 10:00 – 14:00 | NY AM session |
| 30m Open | 30m candle | 09:30 – 10:00 | NY open candle |
| 30m Late | 30m candle | 10:00 – 10:30 | Post-open candle |
| NY Session (custom) | Custom | 09:30 – 11:00 (08:30 on news days) | Extended to 8:30 when 8:30 news present |
| 15m (custom) | 15m candle | 09:45 – 10:00 | Specific 15m window |

#### Stats Per Window

**Timing stats:**
- HOD time distribution (histogram: when within the window is the high made)
- LOD time distribution (histogram: when within the window is the low made)
- HOD made before LOD rate (manipulation low first → distribution high)
- LOD made before HOD rate (manipulation high first → distribution low)

**Size stats:**
- Avg candle range (points) by weekday
- Avg candle range on news days vs non-news days
- Range distribution (small / medium / large buckets)

**Phase stats:**
- Bullish phase rate (manipulation below open → close above open)
- Bearish phase rate (manipulation above open → close below open)
- Ambiguous / no-clear-phase rate
- Avg manipulation depth (% below open on bullish days before reversal)
- Avg manipulation depth by weekday

**PD Array correlation:**
- What held the HOD: FVG / OB / Key Open level / Round number / None identified
- What held the LOD: same breakdown
- Distribution by PD array timeframe (e.g., "1H FVG held LOD 34% of the time on bullish Daily PO3 days")

**News correlation:**
- Stats split by: news present / no news / 8:30 news / 10:00 news / 14:00 news
- ForexFactory impact filter: high-impact only, medium+high, all

**HTF fractal filters (the key differentiator):**
- Filter any lower-TF window by the phase of a higher-TF window
- Example: "Show 30m Open PO3 stats only on days where the Daily PO3 is bullish AND the 4H Morning PO3 is bullish"
- Example: "Avg NY Session PO3 range when London expanded >40 points"

#### PO3 Phase Auto-Classification Rules

```
BULLISH (Manipulation Low → Distribution High):
  - Price trades below open by ≥ threshold within first 40% of window duration
  - Price subsequently closes above the open
  - Close is in upper 40% of candle range
  → Classified: BULLISH

BEARISH (Manipulation High → Distribution Low):
  - Price trades above open by ≥ threshold within first 40% of window duration
  - Price subsequently closes below the open
  - Close is in lower 40% of candle range
  → Classified: BEARISH

AMBIGUOUS:
  - Neither condition met clearly
  → Classified: UNCONFIRMED, surfaced in admin queue for manual label
```

**Manual override:** Admin `/admin` page lists all UNCONFIRMED instances. Admin selects: Bullish / Bearish / Exclude. Confirmed label stored in `po3_phase_labels` table. Pipeline uses confirmed labels on next aggregation run.

#### PO3 Report Page Layout

```
[Instrument] [Window Selector: Daily | 4H-6AM | 4H-10AM | 30m-9:30 | 30m-10 | NY Session | 15m-9:45]
[Lookback] [Phase Filter: All | Bullish | Bearish | Ambiguous]
[HTF Context Builder: Daily Phase = ? → 4H Phase = ? → (applies to selected window)]
────────────────────────────────────────────────────────────────────────────
[HOD Time Distribution chart]    [LOD Time Distribution chart]
────────────────────────────────────────────────────────────────────────────
[Avg range by weekday bar chart] [News day vs non-news breakdown]
────────────────────────────────────────────────────────────────────────────
[PD Array held HOD breakdown]    [PD Array held LOD breakdown]
[FVG X% | OB X% | Key Open X% | Round # X% | None X%]
────────────────────────────────────────────────────────────────────────────
[Manipulation depth distribution] [Phase rates by weekday]
────────────────────────────────────────────────────────────────────────────
[Sample size badge — red if n < 30 for any active filter combination]
```

**Database tables:** `po3_instances`, `po3_phase_labels`, aggregated into `report_po3_stats`

---

### 6.8 Opening Gaps (NDOG / NWOG)

**What it tracks:** The gap between one session's close and the next session's open — two distinct gap types.

**NDOG (New Day Opening Gap):**
- Gap between prior day's 17:00 close and current day's 18:00 globex open
- Stats: full fill rate that day, partial fill rate, avg fill time, by weekday, by gap size (small/medium/large), by session where fill occurs, by instrument

**NWOG (New Week Opening Gap):**
- Gap between Friday's 17:00 close and Sunday's globex open
- Stats: full fill rate that week, mitigation rate (price enters gap but doesn't fully close), partial fill %, avg fill time (hours/days), by instrument, by gap direction (bullish/bearish)

**Subreports (both):**
- By weekday (NDOG only)
- By gap size relative to prior ATR
- By news week (high-impact news present that week)
- By HTF PO3 phase alignment

**Database tables:** `opening_gap_instances`, aggregated into `report_opening_gap_stats`

---

### 6.9 News Data Highs & Lows

**What it tracks:** The 1-minute candle that prints at the exact moment a high-impact news event releases. This candle's high and low are treated as significant levels.

**Stats:**
- High taken that session rate (how often the news candle high is swept during the same session)
- Low taken that session rate
- Which side is taken first (high first vs low first %)
- Time from release to level being taken (avg minutes)
- Both sides taken rate (full sweep of news candle)
- Magnitude of move after the level is taken

**Subreports:**
- By news event type (CPI / NFP / FOMC / PPI / Jobless Claims / ISM / GDP)
- By news impact (high only vs medium+high)
- By release time (8:30 / 10:00 / 14:00 / other)
- By instrument
- By weekday
- By whether HOD/LOD of day was made at the news candle

**Database table:** `news_candle_instances`, aggregated into `report_news_candle_stats`

---

### 6.10 Macros

**What it tracks:** Price behavior during each of the 5 ICT macro windows. Stats are context-aware — filtered by what price did before the macro opened.

**The 5 Macro Windows:**
| Macro | Window (ET) | Session Context |
|---|---|---|
| NY AM Macro 1 | 9:50–10:10 | Post NY open |
| NY AM Macro 2 | 10:50–11:10 | Late NY AM |
| Lunch Macro | 1:10–1:40 | NY lunch |
| NY PM Macro | 2:10–2:40 | NY PM |
| Close Macro | 3:15–4:00 | NY close |

**Stats per macro window:**
- Directional bias (bullish / bearish / choppy %)
- Avg move magnitude during window (points, by instrument)
- HOD of window: made at open / mid / close of window (time distribution)
- LOD of window: same
- Reversal rate (price reverses the pre-macro move during the macro)
- Continuation rate (price extends the pre-macro move during the macro)

**Situational (prior context) filters — the key differentiator:**
- HOD/LOD of day already made before macro opens
- What phase the preceding PO3 window was in (e.g., 30m 9:30 PO3 = bullish)
- Was price approaching/inside a PD array (FVG or OB) when macro opened
- 8:30 or 10:00 news present that day
- NY open 30m candle direction (9:30–10:00 bullish vs bearish)
- London session direction (bullish vs bearish day)
- Distance from a key GEX level (call wall / put wall) at macro open

**Database table:** `macro_instances`, aggregated into `report_macro_stats`

---

## 7. Options & GEX Module

### Data Source
- **yfinance** Python library — pulls SPX and NDX options chains (free, 15-20 min delayed)
- Pipeline pulls options chains every 30 minutes during market hours (09:00–16:30 ET)
- GEX computed in-house: `GEX = gamma × open_interest × contract_multiplier × spot_price` per strike, summed by call/put

### GEX Levels Page

Displays for ES (SPX proxy) and NQ (NDX proxy):
- **Call Wall** — strike with highest call-side GEX concentration
- **Put Wall** — strike with highest put-side GEX concentration
- **GEX Flip** — strike where net GEX crosses from positive to negative
- **Zero Gamma** — level where total GEX = 0
- **Max Pain** — strike where total options losses are minimized

Updated every 30 minutes during market hours. Historical levels stored daily for backtesting.

### Historical GEX Stats Page

Same probability engine as ICT reports applied to GEX levels:
- How often does ES/NQ respect the call wall when approaching from below
- Avg reversal magnitude from GEX flip point
- Put wall respect rate by session
- Stats filterable by: session, weekday, lookback period, distance from level

### Put/Call Ratio Page
- Daily P/C ratio chart (historical + current)
- Rolling 5-day and 20-day averages
- Filterable by lookback

### Open Interest by Strike Page
- Visual OI distribution across strikes (bar chart)
- Call OI vs Put OI per strike
- Updated every 30 minutes during market hours

### v2 Addition (not in v1)
- Options flow (large prints, sweeps, unusual activity) — requires paid source when revenue justifies

---

## 8. Python Data Pipeline

### Schedule
- **Nightly run:** 18:30 ET — after futures close, ingests the full trading day
- **Intraday run (options only):** every 30 minutes 09:00–16:30 ET on trading days

### Stage 1 — Ingest
```
Databento API
  → Pull 1-min OHLCV for all instruments (ES, NQ, GC, CL, MES, MNQ)
  → Append to ohlcv_1m (never overwrite)

ForexFactory scrape
  → Pull today's + next trading day's economic events
  → Store to news_events (time, currency, impact, event name)

yfinance
  → Pull SPX + NDX options chains (all strikes, OI, gamma, delta)
  → Store raw chain snapshot to options_chain_snapshots
```

### Stage 2 — Detect & Classify
```
For each new trading day:

FVG detection:
  → Scan 1m/5m/15m/1H/4H/Daily bars for 3-candle gap patterns
  → Record: instrument, TF, high bound, low bound, creation time
  → Check if subsequently filled: fill time, fill %, partial/full
  → Write to fvg_instances

OB detection:
  → Identify last down-close candle before bullish impulse (bullish OB)
  → Identify last up-close candle before bearish impulse (bearish OB)
  → Track: respected / broken / mitigated, first test time
  → Write to order_block_instances

BSL/SSL detection:
  → Identify swing highs (BSL) and swing lows (SSL) per session
  → Track: swept / not swept, sweep time, post-sweep direction, magnitude
  → Write to liquidity_levels

PO3 classification (per window):
  → Extract OHLCV for each of the 7 defined time windows
  → Apply phase rules (bullish / bearish / unconfirmed)
  → Record HOD time, LOD time within window
  → Match HOD/LOD price to nearest PD array (within 2-tick tolerance)
  → Flag news events present that day (FK to news_events)
  → Write to po3_instances

Key open classification:
  → Extract 18:00, 00:00, 10:00 open prices
  → Check if price returned to each level within session
  → Record: respected / rejected, time to test, deviation before test
  → Write to key_opens

Opening gap detection:
  → Compute NDOG: prior day 17:00 close vs current 18:00 open
  → Compute NWOG: Friday 17:00 close vs Sunday globex open
  → Track fill status throughout session/week
  → Write to opening_gap_instances

News candle detection:
  → For each high-impact news event in news_events:
  → Extract the 1m candle at exact release time per instrument
  → Record high, low, open, close of that candle
  → Track whether high/low is subsequently taken that session
  → Record which side taken first, time to take, magnitude after
  → Write to news_candle_instances

Macro classification (per window):
  → Extract OHLCV for each of 5 macro windows
  → Record HOD/LOD time within window, direction, magnitude
  → Snapshot prior context: HOD/LOD status, preceding PO3 phase,
    nearest PD array at window open, news flag, London direction,
    NY open 30m direction, GEX level proximity
  → Write to macro_instances

GEX computation (intraday):
  → For each options chain snapshot:
  → Compute per-strike GEX (calls + puts separately)
  → Identify call wall, put wall, GEX flip, zero gamma, max pain
  → Write to gex_levels_daily
```

### Stage 3 — Aggregate
```
For each report type × instrument × session × lookback:
  → Query instance tables
  → Compute stats (rates, averages, distributions, sample sizes)
  → Write to report_*_stats tables
  → Invalidate + rebuild Redis cache blobs (TTL reset)
```

---

## 9. Database Schema (Key Tables)

### Raw / Instance Tables
| Table | Contents |
|---|---|
| `ohlcv_1m` | Raw 1-min bars: instrument, timestamp, open, high, low, close, volume |
| `sessions` | Session windows per day: instrument, date, session type, open/close time |
| `news_events` | ForexFactory events: date, time, currency, impact, name |
| `fvg_instances` | Every FVG: instrument, TF, bounds, creation_time, fill_time, fill_pct, status |
| `order_block_instances` | Every OB: instrument, TF, origin_candle, direction, first_test_time, outcome |
| `liquidity_levels` | BSL/SSL: instrument, session, price, swept (bool), sweep_time, post_sweep_direction, magnitude |
| `po3_instances` | Per window row: instrument, window_type, date, open, hod, lod, hod_time, lod_time, phase, manip_depth_pct, news_flag, pd_array_held_hod_fk, pd_array_held_lod_fk |
| `po3_phase_labels` | Manual overrides: po3_instance_id, confirmed_phase, admin_user_id, timestamp |
| `key_opens` | Per open time: instrument, date, open_type (18:00/00:00/10:00), open_price, respected (bool), time_to_test, deviation_pts, reversal_magnitude |
| `options_chain_snapshots` | Raw chain data: timestamp, underlying, strike, expiry, call_oi, put_oi, call_gamma, put_gamma |
| `gex_levels_daily` | Computed GEX levels per day: date, underlying, call_wall, put_wall, gex_flip, zero_gamma, max_pain |

### Aggregated Report Tables
| Table | Contents |
|---|---|
| `report_fvg_stats` | Fill rates, fill times — sliced by instrument, TF, session, lookback, weekday |
| `report_ob_stats` | Respect/break rates — sliced by instrument, TF, session, weekday, HTF bias |
| `report_liquidity_stats` | Sweep rates, reversal rates, magnitudes — sliced by session, weekday, instrument |
| `report_po3_stats` | HOD/LOD distributions, phase rates, avg range, PD array breakdowns — per window, per filter combo |
| `report_keyopen_stats` | Respect rates, deviation, reversal magnitude — per open time, instrument, weekday |
| `report_gex_stats` | Historical GEX level respect rates — by level type, session, instrument |
| `report_opening_gap_stats` | NDOG/NWOG fill rates, fill times — by instrument, weekday, gap size, lookback |
| `report_news_candle_stats` | News candle H/L sweep rates — by event type, release time, instrument, weekday |
| `report_macro_stats` | Macro directional rates, magnitudes — per window, per situational filter combo |

---

## 10. UI Design Principles

- **Dark mode only** — standard for trading platforms, no light mode toggle
- **Dense information layout** — power users want maximum data on one screen
- **Zero onboarding** — no tooltips explaining what an FVG is, no onboarding modals
- **Sample size always visible** — every stat shows `n=142`; red warning badge if `n < 30`
- **URL-persistent filters** — all filter states reflected in URL; bookmarkable and shareable
- **Consistent report layout** — same skeleton across all report pages; traders learn once, navigate everywhere

---

## 11. v1 Scope

### IN v1
- ICT Reports: FVGs, Order Blocks, Killzones/Sessions, Liquidity Sweeps, Power of 3 (7 windows), Key Opens (18:00/00:00/10:00), Opening Gaps (NDOG/NWOG), News Data Highs & Lows, Macros (5 windows, context-aware)
- Options & GEX: GEX levels, historical GEX stats, P/C ratio, OI by strike (yfinance, free)
- Hybrid PD array detection: algorithmic + admin manual override queue
- PO3 phase auto-classification + admin confirmation flow
- ForexFactory news correlation
- Dark mode, dense professional UI, URL-persistent filters
- Admin panel for PO3 phase label overrides

### OUT of v1
- Live "What's In Play" dashboard → v2
- Multi-instrument screener → v2
- QT Reports module → v2
- Options flow (large prints, sweeps) → v2 (paid source)
- Public API → v2
- Algo execution → future
- Mobile app → future
- Cross-variable custom filter builder (e.g. "NY PO3 avg range when London expanded >40pts") → v2

---

## 12. Future Roadmap (v2+)

- **Live dashboard** — real-time "what's in play" view per instrument: current PO3 phase, HOD/LOD status, active FVGs/OBs, GEX proximity
- **Multi-instrument screener** — morning prep view across all instruments in 30 seconds
- **QT module** — NWOG/NDOG stats, AMD cycle data, quarterly shifts
- **Cross-variable filter builder** — "Show me NY Session PO3 stats when: London expanded >40pts AND Daily PO3 is bullish AND 8:30 news present"
- **Options flow** — large prints, sweeps, unusual activity via paid source
- **Public API** — REST API for pulling report data into Claude/external tools
- **All-timeframe PO3 expansion** — every timeframe, every session, fully filterable
