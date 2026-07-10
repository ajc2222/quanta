// ── Query Parameters ──────────────────────────────────────────

export interface ReportQuery {
  instrument?: string;
  lookback?: '3mo' | '6mo' | '1yr' | string;
  session?: string;
  weekday?: string;
  phase?: string;
  window?: string;
}

// ── Common Response Envelope ──────────────────────────────────

export interface ReportResponse<T> {
  data: T;
  sampleSize: number;
  isLowSample: boolean;
  lastUpdated: string;
}

// ── Report-specific shapes ────────────────────────────────────

export interface FvgStats {
  fillRate: number;
  avgFillTimeMinutes: number;
  partialFillRate: number;
  byWeekday: { weekday: string; fillRate: number; sampleSize: number }[];
  bySession: { session: string; fillRate: number; sampleSize: number }[];
}

export interface ObStats {
  successRate: number;
  avgReversalPips: number;
  avgDurationBars: number;
  byWeekday: { weekday: string; successRate: number; sampleSize: number }[];
}

export interface LiquidityStats {
  sweepRate: number;
  avgSweepDepth: number;
  continuationRate: number;
  bySession: { session: string; sweepRate: number; sampleSize: number }[];
}

export interface Po3Stats {
  hodTimeDistribution: { bucket: string; count: number }[];
  lodTimeDistribution: { bucket: string; count: number }[];
  avgRangeByWeekday: { weekday: string; avgRange: number; sampleSize: number }[];
  newsVsNonNews: { condition: string; avgRange: number; phaseRate: number }[];
  pdArrayHeldHod: { label: string; pct: number }[];
  pdArrayHeldLod: { label: string; pct: number }[];
  manipulationDepth: { bucket: string; count: number }[];
  phaseRatesByWeekday: { weekday: string; bullish: number; bearish: number; ambiguous: number }[];
  window: string;
  phase: string;
}

export interface KeyOpensStats {
  continuationRate: number;
  reversalRate: number;
  avgMovePoints: number;
  byDirection: { direction: string; rate: number; sampleSize: number }[];
}

export interface GapsStats {
  fillRate: number;
  avgFillPercent: number;
  avgFillTimeMinutes: number;
  byGapDirection: { direction: string; fillRate: number; sampleSize: number }[];
}

export interface NewsStats {
  avgHighMove: number;
  avgLowMove: number;
  directionalBias: number;
  byEvent: { event: string; avgMove: number; sampleSize: number }[];
}

export interface MacrosStats {
  bullishPct: number;
  bearishPct: number;
  choppyPct: number;
  avgMagnitude: number;
  hodDistribution: { bucket: string; count: number }[];
  lodDistribution: { bucket: string; count: number }[];
  continuationRate: number;
  reversalRate: number;
  window: string;
}

export interface GexLevels {
  callWall: number;
  putWall: number;
  gexFlip: number;
  zeroGamma: number;
  maxPain: number;
  profile: { strike: number; callGex: number; putGex: number }[];
  lastUpdated: string;
}

export interface GexHistoricalStats {
  byWeek: { week: string; totalGex: number; callWall: number; putWall: number }[];
}

export interface PcRatio {
  daily: { date: string; ratio: number }[];
  rolling20Avg: { date: string; ratio: number }[];
}

export interface OiByStrike {
  strike: number;
  callOi: number;
  putOi: number;
  currentPrice: number;
}
