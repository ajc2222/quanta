# Edgeful: Complete Product Teardown & Competitive Intelligence Report

## TL;DR
- **Edgeful is a web-based trading statistics platform** that turns 7–8 years of exchange-direct market data into 150+ pre-built "probability reports" (gap fills, opening range breakouts, initial balance breakouts, etc.), plus a live dashboard, screener, AI research tool, 50+ TradingView indicators, and an optional automated-algo execution layer. Founded 2023 by ex-Goldman Sachs analyst André Arslanian; priced at $49/mo (Essential) and $299/mo (All Access with algos).
- **It is NOT a charting platform, broker, journal, or options/order-flow tool** — it is a probability-research layer that sits on top of TradingView/NinjaTrader/Tradovate/ProjectX. Its core value is answering "how often has this specific setup worked on this specific ticker, in this session, over this lookback."
- **To replicate it yourself:** the realistic solo build is Databento (cheap pay-as-you-go 1-min CME futures history) + Polygon.io or Alpha Vantage (stocks/forex/crypto), precompute the probability reports in a batch job into Postgres, and serve via a Next.js/Vercel front end — which mirrors Edgeful's own stack.

## Key Findings
- Edgeful's moat is **not technology — it's the pre-computed, session-aware, filterable statistics library** plus education/community. The underlying math (win-rate counting on historical OHLCV) is simple; the value is that it's done for 3,000+ tickers, updated continuously, and packaged so a discretionary trader can check it in seconds.
- **Futures (CME) is the real focus** despite marketing across four asset classes. ES, NQ, GC, CL, YM, RTY, MES, MNQ dominate; the tool is built with futures prop-firm traders in mind.
- **Sentiment is genuinely positive** (Trustpilot 4.5/5 "Excellent," 159 reviews; Trustpilot's own summary notes that across 97 reviews "reviewers overwhelmingly had a great experience") for the reports, education, and support — but with two consistent criticisms: a steep learning curve, and complaints that the $299 algos underdeliver on default settings and that reports omit average gain/loss (making true risk/reward hard to assess).
- **Reproducing the reports is very achievable** for a personal build; the hardest/most expensive part is sourcing clean multi-asset intraday history, and no single affordable vendor covers all four asset classes with deep intraday.

## Details

### 1. What Edgeful Is
- **Positioning:** "institutional-level data analytics for retail traders" / "trade with data, not your emotions." Marketed as "your personal financial analyst" and a "personal quant."
- **Core concept:** Instead of charts + indicators, it aggregates years of historical market behavior and shows *how often* a given setup has played out — e.g., "NQ gap downs over the last 6 months in the NY session have filled 75% of the time." It gives probabilities, not signals.
- **Founder:** André Arslanian, founded 2023. Background: analyst at Goldman Sachs and employee at hedge fund Weiss Asset Management; finance/accounting background; now a full-time trader. Built the tool because his own Excel-based statistical modeling was too expensive and time-consuming.
- **Company:** edgeful LLC, registered at 2810 N Church St, PMB 248446, Wilmington, DE 19802. Contact help@edgeful.com.
- **Target audience:** futures day traders (primary), prop-firm/funded-account traders, stock/ETF day traders, forex and crypto day traders, algo traders, and TradingView users. Explicitly NOT for long-term investors, options-flow traders, or complete beginners with zero experience.
- **Delivery:** browser-based (works on desktop/tablet/mobile), no standalone mobile app. Sign up with email or Google.

### 2. Features & Tools (complete inventory)

**a) Reports (the core) — 150+ probability reports**
- Grouped into 6 categories. Workflow: pick asset class → ticker → report → session → lookback (3mo/6mo/1yr/custom) → optional subreport → optional custom inputs. Results load instantly.
- Report types include: **Gap Fill, Opening Range Breakout (ORB, 5/15/30-min), Initial Balance (IB, first hour), Outside Days, Previous Day's Range, ICT Opening/Midnight Retracement, Opening Candle Continuation, Inside Bars, Power Hour Breakout, ATR/ADR, Engulfing Candles, Market Session Breakout, VWAP, FVG (fair value gaps), and event reports (FOMC, CPI, NFP, earnings windows).**
- **Subreports (the "real edge"):** by weekday, by size, by spike (adverse excursion before reversal), by retracement, by levels/extension, by close, by fill time, by previous candle, by rejection, by performance, by double break. The IB report alone has 10 subreports.
- Reports **update dynamically** as new market data comes in (not a static PDF/one-time backtest). Custom report requests: if the report you need doesn't exist, Edgeful will build it.

**b) What's In Play (WIP)** — a live daily dashboard consolidating your favorite reports for ONE ticker into a single view (current price, directional bias, distance to target, key levels). Auto-hides data no longer "in play" (e.g., a gap that already filled).

**c) Screener / Daily Bias Screener** — multi-ticker, multi-report bias tool. Screens up to 49 tickers across 4 reports simultaneously; aggregates into an overall daily bias bar; identifies market direction "in 30 seconds." Pre-built templates: morning trader, daily bias, end of day. Green across the board = bullish; red = bearish; mixed = choppy/sit-out day.

**d) Edgeful AI** (launched Feb 28, 2026) — natural-language research tool that reads the actual raw report data (16 main reports, individually or combined) and finds cross-report patterns. Not a prediction engine and not a generic chatbot — every answer cites source reports and sample sizes you can reproduce. Example: "what weekday has the highest double break rate on ES?"

**e) Algos (All Access tier)** — 8 fully automated strategies (gap fill, IB breakout, ORB, engulfing candles, engulfing candles 2TP, + more) built on the report data. Fully customizable (ticker, session, position size, stop loss, take profit, R:R, direction, entry logic, trade times). Connect broker → algo executes automatically. Can run multiple simultaneously.

**f) Algo Optimizer** — tests up to 10 million parameter combinations in seconds, ranked by a reliability "score" (not just raw P&L), per weekday.

**g) Algo Analyzer / Backtester** — upload TradingView strategy exports; runs: **Monte Carlo simulation (1,000 randomized paths), drawdown analysis, optimization analysis, prop-firm pass testing, equity-curve visualization, stress test, and built-in overfit detection.** Backtesting shows % return, max drawdown, win rate, profit factor.

**h) TradingView indicators** — 50+ (some sources say 35+) free member indicators that auto-plot report levels: ORB, IB, gap fill, session markers, VWAP, ATR zones, pivots. Fully customizable. Plus 12+ NinjaTrader indicators.

**i) Public API** (new, launched 2026) — REST API at api.edgeful.com to pull all 150+ reports into Claude/ChatGPT/Cursor. Details below.

**j) Community & education:** Discord (TradersLog cites "over 4,700 members"; Edgeful marketing rounds this to "5k+"), weekly live streams, explainer video library (10 onboarding videos), "Stay Sharp" weekly newsletter (free), free "Understanding Reports & Setups" course, free resources page (5-lesson futures course, risk calculator, free IB algo course), economic calendar, risk calculator, monthly 1-on-1 algo optimization calls (algos tier), 24/7 email support + in-app AI support agent. Published streaming schedule (per TradersLog): "Monday & Friday 9-11AM EST, André & James live trade using edgeful; Tuesday, Wednesday, Thursday 9-11AM EST, Brice live trades; Wednesday, Thursday, Friday 8-8:30AM EST, James live streams his premarket prep."

### 3. Data Provided
- **Types:** intraday and daily OHLCV-derived statistics. Session-aware (New York, London, Asia, full globex, or custom windows). Session windows: futures/stocks NY 9:30am–4pm ET; forex NY 8am–5pm ET; London 8am–4pm ET; Asia 8am–5pm Tokyo.
- **NOT provided:** tick/order-flow data, options chains, GEX/gamma exposure, options flow, volume delta, footprint charts, live order book, market internals. It is historical probability data, not live tape.
- **Historical depth:** stated as **5+ years** (homepage/marketing) and **7+ / 8+ years** (pricing page and later reviews) directly from the exchanges. The public API tier caps history at 1 year; deeper history (8y) sits behind the All Access tier.
- **Asset classes:** futures, stocks, ETFs, forex, crypto — 3,000+ tickers total. Futures is the practical focus.
- **Timeframes:** intraday (1/5/15/30-min, hourly), daily, weekly; session-based windows.
- **Data sources (named):** direct exchange feeds — **Nasdaq, CME, Coinbase, and OANDA.** Reports described as built on "raw market data sourced directly from exchanges," no third-party distortion. Note: for live algo execution via TradingView, users must buy their own CME real-time data package on TradingView (default is ~10-min delayed) — this is a TradingView requirement, not Edgeful's.
- **Proprietary metrics:** the packaged subreport breakdowns (single/double/no break rates, retracement %, spike/adverse excursion, extension levels) and confluence "stacking" across reports are Edgeful's distinctive framing.

### 4. How It Works (Methodology)
- **Core calc:** simple frequency/probability counting on historical session data. E.g., Gap Fill: price opens above/below prior session close (PSC); a "fill" = price touches the PSC during the session; report counts fills ÷ total gaps = fill rate. Users can customize the fill target (100% full, 50% half, or any %).
- **Initial Balance report:** identifies the first hour's high/low, then classifies each day as breakout (only IB high broken), breakdown (only IB low broken), double break (both), or no break. Break can be defined by close or by wick. Computes single/double/no-break percentages. Example published stats: NQ single-break ~73–82% in NY session; IB breakout win rates up to ~76.8% on YM (87.5% on Thursdays).
- **Filtering logic:** by ticker, session, day of week, setup size, lookback period, retracement level, fill %, spike, previous candle. Custom sessions and custom date ranges supported.
- **Confluence-based analysis:** the signature methodology is "stacking confluences" — combining multiple reports (e.g., the "Ultimate Bullish Setup" on NQ combines inside day + ORB + IB + gap fill, each near ~80%, for a high-conviction trade). The API page showcases a 3-filter confluence: green opening candle + 15-min ORB breakout + IB high break → 96.9% green-close rate (63 of 65 sessions vs 55% baseline).
- **Sample size:** Edgeful shows the sample size for each stat (e.g., "142 days," "403 trades," "258 sessions") and markets this transparency as a differentiator. However, there is no enforced minimum-sample threshold — short lookbacks (3–6 months on a specific weekday) can yield small samples (e.g., weekday gap-fill stats can rest on ~20–30 observations), which is a real statistical caveat.
- **Backtesting methodology:** conducted on TradingView's strategy tester using Edgeful's algo with default or customized settings; Monte Carlo (1,000 paths) + overfit detection to weed out over-optimized settings. Edgeful explicitly warns probabilities drift ("a pattern that worked at 85% 6 months ago drops to 50%") and recommends monthly re-optimization.

### 5. Pricing & Plans
| Plan | Monthly | Annual (save ~20–33%) | What's included |
|---|---|---|---|
| **Essential** | $49/mo | $39/mo ($468/yr) | All 150+ reports, subreports, What's In Play, Daily Bias Screener, Edgeful AI, 50+ TradingView indicators, 12+ NinjaTrader indicators, 7–8yr history, custom lookbacks/sessions/templates, Discord, weekly streams, newsletter, risk calculator, economic calendar, 24/7 support. **Limited API access:** 4 tickers, 3 reports, 6mo history. |
| **All Access (Algos)** | $299/mo | $239/mo | Everything in Essential + 8 automated algos, full algo customization, algo optimizer (10M combos), in-depth backtesting + mobile alerts, automated broker execution (NinjaTrader/Tradovate/ProjectX), full API (3,000+ tickers, 150 reports, 8y history, live data), monthly optimization calls, algos-only Discord, custom algo requests, premium support. |
| **API Pro** (standalone add-on) | $99/mo | — | 3,000+ tickers, 150+ reports, 1yr history, live WIP + screener data. 30 req/min, 500/hr. |
- **No free trial** (discontinued early 2026). Free resources available without subscription. Cancel anytime. Standard discount = annual billing (~20% off). Google/StreetInsider quote a claimed 250% return on $10k over 7 months with default algo settings (marketing claim — not independently verified).

### 6. Uniqueness vs Competitors
- **Edgeful's niche is genuinely differentiated:** it's a *price-action probability/statistics* engine, which is a different category from journals, screeners, and backtesters. Reviewers repeatedly note "no other platform delivering this kind of price action statistics at scale."
- **vs TradeZella / Tradervue / Edgewonk (journals):** those analyze *your own* trade history after the fact; Edgeful analyzes *the market's* history before you trade. Complementary, not overlapping. TradeZella ~$29+/mo with 11+ yrs backtest data and behavioral AI; Edgewonk ~$197/yr.
- **vs TrendSpider (~$82–349/mo):** automated charting, pattern recognition, multi-timeframe scanning, now native options data. Edgeful is quant-style probability clarity, not visual automation; complements TradingView rather than replacing it.
- **vs Trade Ideas / Finviz (scanners):** real-time condition scanners vs Edgeful's historical outcome probabilities.
- **vs NinjaTrader / Quantower / MetaTrader (platforms/backtesters):** those are execution + code-based backtesting; Edgeful is no-code, pre-built, data-first.
- **Bottom line:** Edgeful has "no direct competition" for its exact offering per multiple reviewers; its closest overlap is with a trader building their own stats in Excel/Python — which is precisely the user's goal here.

### 7. User Reviews & Community Sentiment
- **Trustpilot: 4.5/5 "Excellent"** across 159 reviews (Trustpilot's summary of one batch of 97 reviews: "reviewers overwhelmingly had a great experience with this company"). (Note: Edgeful's own site badges "4.6/5"; Trustpilot's live score reads 4.5.)
- **Positive themes:** game-changer for confidence/discipline; excellent customer service (founder André personally engages); strong education/onboarding; data-backed targets/entries/stops; passing prop-firm challenges; "net value-adding" complement to discretionary trading; users report red-week-free streaks and best months.
- **Negative/critical themes (important for a build):**
  - **Steep learning curve** — the single most common complaint; 150+ reports overwhelm new users; some want blogs/Substack instead of "too many videos."
  - **Algos underdeliver** — multiple reviewers say the $299 algos didn't perform in forward testing; "default settings are garbage" despite marketing implying they work out of the box; one cancelled after 2 months (reports 5★, algos 1★). Edgeful responds that algos require watching onboarding videos + optimization.
  - **Missing risk data** — reports omit average gain/average loss. A named Trustpilot reviewer (Jean) put it bluntly: "Edgeful only provides win rate. No risk/reward ratio. No average gain. No average loss. This is a massive gap." Edgeful's public reply: "our reports and features give you the insights to build your own data-backed strategies but we're not a signals platform."
  - **Accuracy doubts** — a few users claim "stats are not accurate, do a manual count," and that indicators are available free elsewhere on TradingView.
  - **Value for money** — some feel data is obtainable free elsewhere; algos are a big extra cost baited as if included.
- **Forums:** NexusFi (futures) threads are cautiously positive — users like the intraday timing, prior high/low, session-correlation and range-by-weekday reports; clarify it's analytics, not an auto-trader. Reddit has a dedicated r/edgeful sub; broader day-trading subs treat it as a legit-but-niche research tool. YouTube has founder walkthroughs and third-party algo reviews.

### 8. Technical Stack Hints
- **Frontend:** Next.js (confirmed via `/_next/image` optimizer paths).
- **Hosting:** Vercel (confirmed via `dpl_...` deployment-ID fingerprints on image URLs).
- **CMS:** Sanity (blog images served from cdn.sanity.io).
- **Auth:** likely Clerk (sign-in/sign-up flow uses `redirect_url` + `auth-check` params matching Clerk's hosted pattern — inferred, not confirmed).
- **Payments:** likely Stripe (standard for this stack — inferred).
- **Public API:** REST at api.edgeful.com, bearer-token auth, JSON responses, OpenAPI 3.1 spec at edgeful.com/docs/openapi-public.json, code samples in curl/Python/JavaScript. Rate limits: 30 req/min sustained, 5 req/5s burst, 500 req/hr per key. Marketed as "the trading data API for AI agents."
- **Data pipeline (inferred):** exchange feeds (CME, Nasdaq, Coinbase, OANDA) → batch computation of probability reports → served through app + API with live WIP/screener streams.

### 9. Anything Else
- **Integrations:** TradingView (indicators + algo alerts), NinjaTrader (indicators + execution), Tradovate (execution), ProjectX (prop-firm execution), Rithmic (execution). Affiliate program at affiliates.edgeful.com.
- **Content/blog:** active blog (Sanity-powered) with weekly "Stay Sharp" data-backed strategy breakdowns, plus per-report deep dives and per-indicator guides — an excellent free reference for the exact report definitions if you're rebuilding them.
- **Social:** YouTube @edgeful, X @edgeful, Instagram @getedgeful, TikTok @edgeful, Reddit r/edgeful, Discord.
- **Roadmap signals:** AI-driven natural-language custom report building, coding-your-own-strategies via Edgeful AI ("not quite there yet"), faster report loading.

## Recommendations (for building your own version)

**Stage 1 — Prove the concept cheaply (weekend build):**
- Start with ONE asset class you actually trade. If futures: pull years of **1-minute CME OHLCV from Databento** (pay-as-you-go `ohlcv-1m` on GLBX.MDP3). Databento gives new users **$125 in free data credits for historical data, shared across your team and expiring in six months**, billed usage-based per byte — and OHLCV bars are tiny, so this credit likely covers your entire initial pull. If stocks/forex/crypto: use **Polygon.io** (per-asset tiers $29–199/mo) or **Alpha Vantage** (Standard $49.99/mo = 75 requests/min, 15-min-delayed US data, 20+ years of historical intraday OHLCV via the intraday endpoint — but polling only, no WebSocket/streaming, and full-history output is premium-gated).
- Recreate 2–3 reports first: **Gap Fill, Initial Balance, ORB.** These are the highest-value and simplest (frequency counting on session-bucketed bars). Edgeful's own blog posts define the exact rules — use them as your spec.
- Store computed stats in **Postgres**; compute in a nightly batch job (Python/pandas). Serve via a simple Next.js/Vercel front end (mirrors Edgeful's own stack).

**Stage 2 — Add rigor:**
- Implement session bucketing (NY/London/Asia) and the key subreports (by weekday, by size, by retracement, by extension) — this is where the real edge lives.
- **Add what Edgeful omits:** average gain, average loss, and expectancy per setup (its most substantive criticism — the named Jean review above). Compute win rate × avg win − loss rate × avg loss.
- Enforce a **minimum sample size** (e.g., flag any stat with n < 30) and show confidence intervals — this fixes the small-sample weakness of short lookbacks.

**Stage 3 — Confluence + live:**
- Build a confluence engine that intersects multiple report conditions (Edgeful's 96.9% 3-filter example shows the payoff, but beware multiple-comparisons/overfitting: with enough filters any dataset yields spurious "edges").
- Add a live "what's in play" layer using a real-time feed (Databento live, or your broker's API / IBKR as a live+execution layer — but avoid IBKR for *historical* futures because it drops expired contracts older than 2 years).

**Multi-asset reality check:** No single affordable vendor covers futures + stocks + forex + crypto with deep intraday. Realistic stack = **Databento (futures) + Polygon or Alpha Vantage (stocks/forex/crypto)**. Budget ~$100–250/mo if you want live multi-asset, or near-zero for a historical-only backtesting build. For a canonical/source-of-truth futures option, **CME DataMine** sells one-time historical purchases (with a 50% academic discount) but requires DIY contract-roll stitching.

**Benchmarks that would change the plan:**
- If you only trade one instrument → skip multi-vendor; Databento pay-as-you-go alone is enough and near-free.
- If you want live automation → you need real-time data (adds cost) + a broker API; otherwise keep it a research/backtest tool.
- If your computed edges rely on n < 30 or don't survive out-of-sample/Monte-Carlo testing → don't trade them.

## Caveats
- **Historical depth is stated inconsistently** by Edgeful itself: "5+ years" on the homepage, "7+ years" and "8+ years" on the pricing/alternatives pages, and "1 year" on the API Pro tier. Treat 5 years as the conservative floor and 8 years as the max behind the top tier.
- **Report/indicator counts vary by source and over time:** "100+" (older reviews), "150+" (current), "40+" (one outdated review); TradingView indicators cited as both "35+" and "50+." The platform is actively expanding, so counts drift.
- **Marketing performance claims** are company-provided and explicitly "past performance, not indicative of future results" — not independently verified. The most cited backtest (via Prop Firm App): "the IB strategy backtested on GC futures from January 2025 to January 2026 showed a 65.76% win rate across 403 trades with a profit factor of 1.935 and a net P&L of +$105,890." Also unverified: a claimed 250% return on $10k in 7 months, and a testimonial of a user putting a down payment on a house.
- **Auth (Clerk) and payments (Stripe) are informed inferences** from URL patterns, not confirmed from source code.
- **Databento per-GB cost for a specific futures pull** is computed at request time, not a fixed published number; the "covered by the $125 credit" estimate is directional. **CME DataMine** prices are quote-at-order, not publicly listed.
- **The statistics themselves are descriptive, not predictive** — they describe historical frequency and can (and do) decay as market regimes change. Edgeful's own data is dynamic for this reason; any clone must re-compute continuously to stay useful.
- **Trustpilot rating discrepancy:** Edgeful's site displays "4.6/5"; Trustpilot's live score is 4.5/5. Minor, but worth noting when citing.