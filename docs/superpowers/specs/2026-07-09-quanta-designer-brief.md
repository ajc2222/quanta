# Quanta — AI Designer Brief
**For:** AI design agent (Figma AI, v0, Lovable, or similar)
**Date:** 2026-07-09
**Deliverable:** Full UI design for a professional web-based trading statistics platform

---

## What You Are Designing

**Quanta** is a trading statistics platform for advanced professional futures day traders who use ICT (Inner Circle Trader) methodology. It is NOT a charting platform, brokerage, or beginner tool. It is a data and probability research layer — traders come here to see historical statistics on specific setups before they trade. Think of it as a professional analytics dashboard that answers: *"How often has this exact setup worked, in this session, on this instrument, over the last year?"*

The closest reference product is **Edgeful** (edgeful.com) — but Quanta is built specifically for ICT methodology and goes significantly deeper. Assume the user knows every trading term and needs zero explanation. The UI should treat them like a Bloomberg terminal user, not a retail app user.

---

## Visual Identity

### Personality
- **Professional. Dense. Precise.** Like a Bloomberg terminal crossed with a modern SaaS dashboard.
- Cold, data-forward, no decoration for decoration's sake.
- Every pixel earns its place by conveying information.
- No gradients on data. No rounded-corner softness on stat cards. Sharp edges, high contrast.

### Color Palette
- **Background:** `#0A0A0F` — near-black with a very slight blue undertone (not pure black)
- **Surface / Card background:** `#111118` — slightly lighter than background for cards and panels
- **Border / Divider:** `#1E1E2E` — subtle, not harsh
- **Primary accent:** `#4F6EF7` — electric blue, used for active states, selected filters, primary CTAs
- **Bullish / Positive:** `#22C55E` — clean green (Tailwind green-500)
- **Bearish / Negative:** `#EF4444` — clean red (Tailwind red-500)
- **Warning (low sample size):** `#F59E0B` — amber, used for n < 30 warnings
- **Muted text:** `#6B7280` — gray for secondary labels, timestamps, metadata
- **Primary text:** `#E5E7EB` — off-white, easy on eyes for long sessions
- **Highlight text / Stats:** `#FFFFFF` — pure white for the most important numbers only

### Typography
- **Primary font:** `Inter` — clean, legible at small sizes, industry standard for data dashboards
- **Monospace font:** `JetBrains Mono` or `Fira Code` — used for all numerical data (stat percentages, prices, sample sizes, timestamps). This is critical — numbers must be monospaced so columns align perfectly.
- **Size scale:**
  - Primary stat numbers: 32–40px, bold, white
  - Stat labels: 11–12px, uppercase, letter-spaced, muted gray
  - Body / table text: 13–14px, regular weight
  - Navigation labels: 13px, medium weight
  - Section headers: 16–18px, semibold

### Dark Mode Only
There is no light mode. No toggle. The entire product exists in dark mode. Do not design light mode variants.

---

## Layout Architecture

### Global Shell

```
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px fixed)  │  MAIN CONTENT AREA (fluid)           │
│                         │                                        │
│  [Logo: QUANTA]         │  [Top bar: instrument + filters]      │
│                         │  ─────────────────────────────────── │
│  ─────────────────      │                                        │
│  ICT REPORTS            │  [Report content]                     │
│    Fair Value Gaps      │                                        │
│    Order Blocks         │                                        │
│    Killzones            │                                        │
│    Liquidity Sweeps     │                                        │
│    Power of 3           │                                        │
│    Key Opens            │                                        │
│    Opening Gaps         │                                        │
│    News Data H/L        │                                        │
│    Macros               │                                        │
│                         │                                        │
│  ─────────────────      │                                        │
│  OPTIONS & GEX          │                                        │
│    GEX Levels           │                                        │
│    Historical Stats     │                                        │
│    Put/Call Ratio       │                                        │
│    OI by Strike         │                                        │
│                         │                                        │
│  ─────────────────      │                                        │
│  QT REPORTS             │                                        │
│  [COMING SOON badge]    │                                        │
│                         │                                        │
│  ─────────────────      │                                        │
│  [Account / Settings]   │                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Sidebar details:**
- Fixed width 240px, never collapses on desktop
- Logo "QUANTA" top-left — wordmark only, no icon, white text, slightly spaced lettering
- Section headers (ICT REPORTS, OPTIONS & GEX, QT REPORTS) in 10px uppercase muted gray, not clickable
- Nav items: 13px, medium, left-padded. Active item: primary accent left border (3px) + accent text color + slightly lighter background
- "COMING SOON" badge on QT Reports: tiny pill badge, amber color, sits inline after the label
- Bottom of sidebar: small avatar + email + settings gear icon

---

## Global Filter Bar (Top of every report page)

This sits below the page title, above the report content. It is the same on every report page.

```
┌─────────────────────────────────────────────────────────────────┐
│  [ES ▾]  [NQ ▾]  [GC ▾]  [CL ▾]       [3mo] [6mo] [1yr] [Custom]   [Session ▾]  │
└─────────────────────────────────────────────────────────────────┘
```

- Instrument pills: multiple selectable, accent border when active
- Lookback: segmented button group (3mo / 6mo / 1yr / Custom), not a dropdown
- Session: dropdown (All / London / NY AM / NY PM / Overnight / Globex)
- All filter state is reflected in the URL (bookmarkable)
- Filters apply instantly — no "apply" button needed

---

## Standard Report Page Layout

Every ICT report page follows this exact skeleton. The content within each section changes per report — the structure never does.

```
PAGE TITLE                                          [filter bar above]
─────────────────────────────────────────────────────────────────────

ROW 1: PRIMARY STAT CARDS (3–5 cards across full width)
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ FILL RATE    │ │ AVG FILL TIME│ │ PARTIAL FILL │ │ SAMPLE SIZE  │
│              │ │              │ │              │ │              │
│    74.2%     │ │   1h 22m     │ │    18.6%     │ │  n = 403     │
│              │ │              │ │              │ │              │
│ n=403 ──────│ │              │ │              │ │ ● HEALTHY    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

─────────────────────────────────────────────────────────────────────

ROW 2: SUBREPORT TABS
[ By Weekday ] [ By Size ] [ By Session ] [ By News Day ] [ By HTF Phase ]
─────────────────────────────────────────────────────────────────────

ROW 3: CHART + DATA TABLE (side by side or stacked depending on report)
┌──────────────────────────────────┐ ┌──────────────────────────────┐
│ BAR CHART / HISTOGRAM            │ │ DATA TABLE                    │
│ (e.g. fill rate by weekday)      │ │ Mon  │ 78.4% │ n=82  │ ████  │
│                                  │ │ Tue  │ 71.2% │ n=79  │ ███   │
│                                  │ │ Wed  │ 82.1% │ n=88  │ █████ │
│                                  │ │ Thu  │ 69.4% │ n=71  │ ███   │
│                                  │ │ Fri  │ 61.3% │ n=83  │ ██    │
└──────────────────────────────────┘ └──────────────────────────────┘

─────────────────────────────────────────────────────────────────────

SAMPLE SIZE WARNING (only appears when n < 30):
⚠ Low sample size (n=17) — treat this stat with caution
```

**Stat card design specifics:**
- Card background: `#111118`
- Border: `#1E1E2E`, 1px
- Label: 10px uppercase, muted gray, top of card
- Primary number: 36px, bold, white, monospaced font
- Secondary label (e.g. "n=403"): 11px, muted gray, bottom of card
- Status indicator on sample size card: green dot "HEALTHY" if n≥100, amber "LOW" if n=30–99, red warning if n<30
- No shadows. No gradients. Flat card.

**Chart design specifics:**
- Background: matches card background (`#111118`)
- Grid lines: extremely subtle, `#1E1E2E`
- Bars: accent blue by default; green for bullish stats; red for bearish stats
- Axis labels: 11px, muted gray, monospaced
- No chart borders — chart bleeds to card edge with padding only
- Hover tooltip: dark card (`#0A0A0F`), white text, monospaced numbers, 1px accent border

**Table design specifics:**
- No outer border on table
- Row dividers: 1px `#1E1E2E`
- Header row: 10px uppercase, muted gray, not bold
- Data rows: 13px, regular weight
- Numbers: monospaced font, right-aligned
- Mini inline bar (sparkbar): thin horizontal bar after the % number, accent color, proportional to value
- Hover state on row: very subtle background lift (`#161620`)

---

## Power of 3 Report Page (Special Layout)

This report has the most complex layout. It uses the standard skeleton but adds:

**Window Selector** (above filter bar, full width):
```
[ Daily ] [ 4H · 6AM ] [ 4H · 10AM ] [ 30m · 9:30 ] [ 30m · 10:00 ] [ NY Session ] [ 15m · 9:45 ]
```
Segmented pill selector. Selected window: accent background + white text. Unselected: ghost style.

**Phase Filter** (inline with filter bar):
```
Phase: [ All ] [ Bullish ] [ Bearish ] [ Ambiguous ]
```

**HTF Context Builder** (below filter bar, collapsible):
```
▶ HTF Context Filter
  Daily PO3 Phase: [ Any ▾ ]   →   4H Phase: [ Any ▾ ]   →   applies to selected window
```

**Main content grid (2×2):**
```
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ HOD TIME DISTRIBUTION       │ │ LOD TIME DISTRIBUTION        │
│ (histogram, 15-min buckets) │ │ (histogram, 15-min buckets)  │
│ Green bars                  │ │ Red bars                     │
└─────────────────────────────┘ └─────────────────────────────┘

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ AVG RANGE BY WEEKDAY        │ │ NEWS DAY vs NON-NEWS         │
│ (horizontal bar chart)      │ │ Two side-by-side stat stacks │
│                             │ │ News: avg range, phase rates │
│                             │ │ No news: same               │
└─────────────────────────────┘ └─────────────────────────────┘

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ PD ARRAY HELD HOD           │ │ PD ARRAY HELD LOD            │
│ Donut chart breakdown:      │ │ Donut chart breakdown:       │
│ FVG / OB / Key Open /       │ │ FVG / OB / Key Open /        │
│ Round # / None              │ │ Round # / None               │
└─────────────────────────────┘ └─────────────────────────────┘

┌─────────────────────────────┐ ┌─────────────────────────────┐
│ MANIPULATION DEPTH DIST.    │ │ PHASE RATES BY WEEKDAY       │
│ (histogram: % below open)   │ │ Stacked bar: Bull/Bear/Ambig │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## Macros Report Page (Special Layout)

**Macro Window Selector** (top, full width):
```
[ 9:50–10:10 ] [ 10:50–11:10 ] [ 1:10–1:40 ] [ 2:10–2:40 ] [ 3:15–4:00 ]
```

**Situational Filter Panel** (collapsible section, below filter bar):
```
▶ Prior Context Filters
  HOD/LOD Made: [ Any ] [ HOD made ] [ LOD made ] [ Neither ]
  Preceding PO3 Phase: [ Any ▾ ]
  Approaching PD Array: [ Any ] [ Inside FVG ] [ At OB ] [ None ]
  News Present: [ Any ] [ 8:30 news ] [ 10:00 news ] [ None ]
  NY Open (9:30) Direction: [ Any ] [ Bullish ] [ Bearish ]
  London Direction: [ Any ] [ Bullish ] [ Bearish ]
```

**Main content:**
- Row 1: Stat cards (Bullish %, Bearish %, Choppy %, Avg Magnitude, Sample Size)
- Row 2: HOD/LOD time distribution within macro window (twin histograms)
- Row 3: Continuation % vs Reversal % breakdown (context-filtered)
- Row 4: Data table showing each situational combo's stats

---

## Options & GEX Module

### GEX Levels Page

```
[ES ▾] [NQ ▾]                              Last updated: 14:32 ET · refreshes every 30m

┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  CALL WALL   │ │  PUT WALL    │ │  GEX FLIP    │ │  ZERO GAMMA  │ │  MAX PAIN    │
│              │ │              │ │              │ │              │ │              │
│   5,875      │ │   5,700      │ │   5,800      │ │   5,780      │ │   5,750      │
│              │ │              │ │              │ │              │ │              │
│ Resistance   │ │ Support      │ │ Regime flip  │ │ Neutral zone │ │ Options pain │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

GEX PROFILE CHART (full width bar chart, strikes on X axis, GEX on Y axis)
Call GEX: green bars above zero line
Put GEX: red bars below zero line
Current price: vertical dashed white line
Key levels labeled with thin horizontal dashed lines
```

### OI by Strike Page

Full-width horizontal bar chart. Each strike has two bars: call OI (green, right) and put OI (red, left) — mirrored layout like a population pyramid. Current price marked with vertical line. Strikes sorted by price.

### Put/Call Ratio Page

Line chart, full width. Two lines: daily P/C ratio (white) and 20-day rolling average (accent blue). X axis: date. Overbought/oversold bands as very subtle background fills.

---

## Sidebar "Coming Soon" State (QT Reports)

```
QT REPORTS                              [SOON]
  ─ Quarterly Shifts
  ─ Weekly Range Stats
  ─ AMD Cycle Data
  ─ NWOG / NDOG
```

Items are visible but dimmed (40% opacity). No hover state. Single "SOON" amber pill badge next to section header. Clicking any item shows a small inline message: "QT Reports coming soon. ICT module is live now." — not a modal, just an inline toast at the top of the content area.

---

## Admin Panel (Protected Route: /admin)

Simple, functional. No design flourishes.

```
QUANTA ADMIN                                        [logged in as: admin@quanta.com]

PO3 PHASE REVIEW QUEUE                             [47 unconfirmed]

┌────────────────────────────────────────────────────────────────────────────────┐
│ Date       │ Instrument │ Window      │ Open   │ HOD    │ LOD    │ Action      │
├────────────────────────────────────────────────────────────────────────────────┤
│ 2026-07-08 │ ES         │ Daily       │ 5,821  │ 5,847  │ 5,798  │ [B] [Bear] [X] │
│ 2026-07-08 │ NQ         │ 4H · 6AM   │ 21,440 │ 21,510 │ 21,390 │ [B] [Bear] [X] │
│ 2026-07-07 │ ES         │ NY Session  │ 5,803  │ 5,830  │ 5,795  │ [B] [Bear] [X] │
└────────────────────────────────────────────────────────────────────────────────┘

[B] = confirm Bullish (green button)
[Bear] = confirm Bearish (red button)
[X] = Exclude from dataset (muted button)
```

Row highlight: green tint on hover for bullish candidate, red tint for bearish candidate. No pagination needed — infinite scroll, newest first.

---

## Key Screens to Design (Priority Order)

Design these screens in this order:

1. **FVG Report page** — the simplest report, use it to establish the standard layout template
2. **Power of 3 Report page (Daily window)** — the flagship, most complex layout
3. **Macros Report page (9:50–10:10 window)** — context filter panel
4. **GEX Levels page** — the Options module anchor
5. **OI by Strike page** — mirrored bar chart
6. **Sidebar + shell** — the navigation chrome that wraps all pages
7. **Admin panel** — phase review queue
8. **Empty/loading states** — skeleton loaders for every card and chart
9. **Low sample size warning states** — amber warning banner on any stat with n < 30

---

## Interaction Notes

- **No page reloads** — all filter changes update content in place via client-side state
- **Skeleton loaders** — when data is loading, show animated skeleton shapes in the exact dimensions of cards and charts. Never show a spinner in the center of the page.
- **Hover tooltips on charts** — dark card, white monospaced text, show exact stat + sample size
- **URL persistence** — every filter combination should be representable as a URL. Sharing a URL gives the exact same view.
- **Tab active states** — subreport tabs use an underline indicator (3px accent color), not a filled background
- **Filter pills** — when a non-default filter is active, the pill gets an accent border + small "×" to clear it

---

## What NOT to Design

- No light mode
- No onboarding flow, tooltips, or explainer modals
- No marketing landing page (this brief is for the authenticated app only)
- No mobile layout (desktop only in v1)
- No empty "welcome" states — assume data is always present
- No decorative illustrations or icons beyond functional UI icons (chevrons, close, etc.)
- No color gradients on data elements
- No animations beyond skeleton loaders and hover transitions (< 150ms)
