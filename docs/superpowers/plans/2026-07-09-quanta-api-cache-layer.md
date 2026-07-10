# Quanta — API Layer & Cache Strategy

**Date:** 2026-07-09
**Stack:** Next.js 14 App Router, Supabase Postgres, Upstash Redis, Clerk Auth
**Principle:** Python pipeline writes to Postgres. Next.js reads from Postgres via Redis cache. App never writes — only admin panel does.

---

## Files Created

```
src/
  lib/
    reports/
      types.ts              # Shared response types, query params, report shapes
      query.ts              # Base report query builder
      fvg.ts                # FVG report queries
      ob.ts                 # Order Blocks report queries
      liquidity.ts          # Liquidity Sweeps report queries
      po3.ts                # Power of 3 report queries
      keyopens.ts           # Key Opens report queries
      gaps.ts               # Opening Gaps report queries
      news.ts               # News Candle stat queries
      macros.ts             # Macros report queries
      gex.ts                # GEX levels + historical + pc-ratio + OI queries
    cache/
      client.ts             # Upstash Redis client singleton
      keys.ts               # Cache key builder
      get-or-compute.ts     # getOrCompute utility
    supabase/
      client.ts             # Supabase client singleton
  app/
    api/
      reports/
        fvg/route.ts
        ob/route.ts
        liquidity/route.ts
        po3/route.ts
        key-opens/route.ts
        gaps/route.ts
        news/route.ts
        macros/route.ts
        gex/route.ts
        gex/historical/route.ts
        gex/pc-ratio/route.ts
        gex/oi/route.ts
      admin/
        po3-queue/route.ts
        po3-label/route.ts
      webhooks/
        clerk/route.ts
      _middleware.ts          # Route-level auth middleware helpers
```

---

## 1. Shared Types (`src/lib/reports/types.ts`)

```typescript
// ── Query Parameters ──────────────────────────────────────────

export interface ReportQuery {
  instrument?: string;
  lookback?: '3mo' | '6mo' | '1yr' | string;   // string for custom ISO range
  session?: string;
  weekday?: string;                                // 0-6 or name
  phase?: string;                                  // bullish/bearish/ambiguous
  window?: string;                                 // PO3 window or macro window name
}

// ── Common Response Envelope ──────────────────────────────────

export interface ReportResponse<T> {
  data: T;
  sampleSize: number;
  isLowSample: boolean;   // true when n < 30
  lastUpdated: string;    // ISO timestamp
}

// ── Report-specific shapes ────────────────────────────────────
// (One per report module. Only showing representative subset here;
//  each module file defines its own shape and exports it.)

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
```

---

## 2. Supabase Client (`src/lib/supabase/client.ts`)

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

// Singleton — one client for the entire server process
export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: { persistSession: false },  // server-side, no session persistence
});
```

---

## 3. Redis Cache Layer

### 3a. Client (`src/lib/cache/client.ts`)

```typescript
import { Redis } from '@upstash/redis';

const UPSTASH_REDIS_REST_URL = process.env.UPSTASH_REDIS_REST_URL!;
const UPSTASH_REDIS_REST_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN!;

export const redis = new Redis({
  url: UPSTASH_REDIS_REST_URL,
  token: UPSTASH_REDIS_REST_TOKEN,
});
```

### 3b. Cache Key Builder (`src/lib/cache/keys.ts`)

```typescript
import { createHash } from 'crypto';
import type { ReportQuery } from '@/lib/reports/types';

/**
 * Build a deterministic cache key from report type and query params.
 *
 * Key schema:  report:{type}:{instrument}:{lookback}:{session}:{filters_hash}
 *
 * filters_hash is an MD5 of the remaining params (weekday, phase, window, etc.)
 * sorted alphabetically so equivalent queries produce identical keys.
 */
export function buildCacheKey(type: string, query: ReportQuery): string {
  const { instrument = 'all', lookback = '1yr', session = 'all', ...rest } = query;

  // Serialize remaining params sorted by key
  const filterEntries = Object.entries(rest)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .sort(([a], [b]) => a.localeCompare(b));

  const filterStr = JSON.stringify(Object.fromEntries(filterEntries));
  const hash = createHash('md5').update(filterStr).digest('hex').slice(0, 12);

  return `report:${type}:${instrument}:${lookback}:${session}:${hash}`;
}

/**
 * Prefix for bulk-invalidation after pipeline runs.
 * Pipeline calls DEL with pattern `report:{type}:*` or `report:*`.
 */
export function buildTypePrefix(type: string): string {
  return `report:${type}:*`;
}

export const ALL_REPORTS_PREFIX = 'report:*';
```

### 3c. getOrCompute Utility (`src/lib/cache/get-or-compute.ts`)

```typescript
import { redis } from './client';
import type { ReportResponse } from '@/lib/reports/types';

type DbQuery<T> = () => Promise<{
  data: T;
  sampleSize: number;
  lastUpdated: string;
}>;

type CacheValue<T> = Omit<ReportResponse<T>, 'isLowSample'>;

/**
 * Cache-aside read pattern.
 *
 * 1. Try Redis GET — return on hit.
 * 2. On miss: run dbQuery, write result to Redis with TTL, return.
 * 3. Stale-while-revalidate: if stale is set, return stale data + revalidate.
 *
 * TTLs:
 *   - GEX data (refresh every 30m):    1800s
 *   - Historical stats (daily refresh): 3600s
 *   - Reports (post-pipeline):          7200s
 */
export async function getOrCompute<T>(
  cacheKey: string,
  dbQuery: DbQuery<T>,
  options: { ttl?: number; serveStale?: boolean } = {},
): Promise<ReportResponse<T>> {
  const { ttl = 7200, serveStale = false } = options;
  const MIN_SAMPLE_SIZE = 30;

  // 1. Try cache
  const cached = await redis.get<CacheValue<T>>(cacheKey);
  if (cached) {
    return {
      ...cached,
      isLowSample: cached.sampleSize < MIN_SAMPLE_SIZE,
    };
  }

  // 2. Query database
  const result = await dbQuery();

  // 3. Write to cache (don't await — fire and forget)
  const cacheValue: CacheValue<T> = {
    data: result.data,
    sampleSize: result.sampleSize,
    lastUpdated: result.lastUpdated,
  };

  // ponytail: no error handling on write — cache failure shouldn't block the response.
  // Add queue-based retry if write failures become visible in metrics.
  redis.set(cacheKey, JSON.stringify(cacheValue), { ex: ttl }).catch(() => {});

  return {
    ...result,
    isLowSample: result.sampleSize < MIN_SAMPLE_SIZE,
  };
}
```

---

## 4. Base Report Query Builder (`src/lib/reports/query.ts`)

```typescript
import { supabase } from '@/lib/supabase/client';
import type { ReportQuery } from './types';

/**
 * Build a Supabase query for any report_*_stats table.
 *
 * Applies filters shared across all report types:
 *   - instrument (exact match)
 *   - lookback (date range, translates 3mo/6mo/1yr to INTERVAL)
 *   - session (exact match)
 *   - weekday (exact match on 0-6)
 *   - phase (for PO3)
 *   - window (for PO3 / macros)
 *
 * Each report module calls this then adds its own specific aggregations/columns.
 */
export function buildReportQuery(table: string, { instrument, lookback, session, weekday, phase, window }: ReportQuery) {
  let query = supabase.from(table).select('*');

  if (instrument && instrument !== 'all') {
    query = query.eq('instrument', instrument.toUpperCase());
  }

  if (lookback && lookback !== 'all') {
    const days = lookback === '3mo' ? 90 : lookback === '6mo' ? 180 : lookback === '1yr' ? 365 : null;
    if (days) {
      const cutoff = new Date(Date.now() - days * 86400000).toISOString();
      query = query.gte('trade_date', cutoff);
    }
    // custom: treat lookback as raw ISO date range "start,end"
    if (lookback.includes(',')) {
      const [start, end] = lookback.split(',');
      if (start) query = query.gte('trade_date', start);
      if (end) query = query.lte('trade_date', end);
    }
  }

  if (session && session !== 'all') {
    query = query.eq('session', session);
  }

  if (weekday && weekday !== 'all') {
    query = query.eq('weekday', weekday);
  }

  if (phase && phase !== 'all') {
    query = query.eq('phase', phase);
  }

  if (window && window !== 'all') {
    query = query.eq('window', window);
  }

  return query;
}

/**
 * Count total rows matching the filter — used for sample size.
 * Accepts the same filters as buildReportQuery.
 */
export async function countSampleSize(table: string, query: ReportQuery): Promise<number> {
  const q = buildReportQuery(table, query);
  const { count, error } = await q.select('*', { count: 'exact', head: true });
  if (error) throw error;
  return count ?? 0;
}
```

---

## 5. Per-Report Query Modules

Each module follows the same structure: a single exported async function that accepts `ReportQuery` and returns the stat shape + sampleSize + lastUpdated.

### 5a. PO3 (`src/lib/reports/po3.ts`)

Shown in full as the most complex example:

```typescript
import { buildReportQuery } from './query';
import type { ReportQuery, Po3Stats } from './types';

interface Po3Row {
  trade_date: string;
  instrument: string;
  window: string;
  phase: string;
  hod_time: string;
  lod_time: string;
  range: number;
  is_news_day: boolean;
  pd_array_held_hod: string;
  pd_array_held_lod: string;
  manipulation_depth_pct: number;
  weekday: string;
}

const TABLE = 'report_po3_stats';

export async function queryPo3Stats(query: ReportQuery): Promise<{
  data: Po3Stats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery(TABLE, query);
  const { data: rows, error, count } = await dbQuery
    .select<Po3Row[]>('*', { count: 'exact' })
    .order('trade_date', { ascending: false });

  if (error) throw error;
  if (!rows || rows.length === 0) {
    return {
      data: emptyPo3Stats(query),
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  // ── HOD / LOD time distributions (15-min buckets) ──────────
  const hodBuckets = bucketByTime(rows.map(r => r.hod_time), 15);
  const lodBuckets = bucketByTime(rows.map(r => r.lod_time), 15);

  // ── Avg range by weekday ────────────────────────────────────
  const byWeekday = aggregateByWeekday(rows);

  // ── News vs Non-news ────────────────────────────────────────
  const newsRows = rows.filter(r => r.is_news_day);
  const nonNewsRows = rows.filter(r => !r.is_news_day);
  const newsVsNonNews = [
    { condition: 'News Day', avgRange: avg(newsRows.map(r => r.range)), phaseRate: bullishRate(newsRows) },
    { condition: 'Non-News', avgRange: avg(nonNewsRows.map(r => r.range)), phaseRate: bullishRate(nonNewsRows) },
  ];

  // ── PD Array held ───────────────────────────────────────────
  const pdArrayHeldHod = breakdownPct(rows.map(r => r.pd_array_held_hod));
  const pdArrayHeldLod = breakdownPct(rows.map(r => r.pd_array_held_lod));

  // ── Manipulation depth ──────────────────────────────────────
  const manipBuckets = bucketByStep(rows.map(r => r.manipulation_depth_pct), 5);

  // ── Phase rates by weekday ──────────────────────────────────
  const phaseRatesByWeekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(day => {
    const dayRows = rows.filter(r => r.weekday === day);
    const total = dayRows.length;
    return {
      weekday: day,
      bullish: total ? dayRows.filter(r => r.phase === 'bullish').length / total : 0,
      bearish: total ? dayRows.filter(r => r.phase === 'bearish').length / total : 0,
      ambiguous: total ? dayRows.filter(r => r.phase === 'ambiguous').length / total : 0,
    };
  });

  return {
    data: {
      hodTimeDistribution: hodBuckets,
      lodTimeDistribution: lodBuckets,
      avgRangeByWeekday: byWeekday,
      newsVsNonNews,
      pdArrayHeldHod,
      pdArrayHeldLod,
      manipulationDepth: manipBuckets,
      phaseRatesByWeekday,
      window: query.window || 'daily',
      phase: query.phase || 'all',
    },
    sampleSize: count ?? rows.length,
    lastUpdated: rows[0].trade_date,  // ponytail: using trade_date as proxy; add explicit updated_at column if timeliness matters
  };
}

// ── Helpers ───────────────────────────────────────────────────

function bucketByTime(times: string[], intervalMinutes: number): { bucket: string; count: number }[] {
  const buckets: Record<string, number> = {};
  for (const t of times) {
    if (!t) continue;
    const [h, m] = t.split(':').map(Number);
    const rounded = Math.floor(m / intervalMinutes) * intervalMinutes;
    const key = `${String(h).padStart(2, '0')}:${String(rounded).padStart(2, '0')}`;
    buckets[key] = (buckets[key] ?? 0) + 1;
  }
  return Object.entries(buckets)
    .map(([bucket, count]) => ({ bucket, count }))
    .sort((a, b) => a.bucket.localeCompare(b.bucket));
}

function bucketByStep(values: number[], step: number): { bucket: string; count: number }[] {
  const buckets: Record<string, number> = {};
  for (const v of values) {
    const base = Math.floor(v / step) * step;
    const key = `${base}%–${base + step}%`;
    buckets[key] = (buckets[key] ?? 0) + 1;
  }
  return Object.entries(buckets).map(([bucket, count]) => ({ bucket, count }));
}

function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function bullishRate(rows: Po3Row[]): number {
  if (rows.length === 0) return 0;
  return rows.filter(r => r.phase === 'bullish').length / rows.length;
}

function aggregateByWeekday(rows: Po3Row[]): { weekday: string; avgRange: number; sampleSize: number }[] {
  const groups: Record<string, number[]> = {};
  for (const r of rows) {
    if (!groups[r.weekday]) groups[r.weekday] = [];
    groups[r.weekday].push(r.range);
  }
  return Object.entries(groups).map(([weekday, ranges]) => ({
    weekday,
    avgRange: avg(ranges),
    sampleSize: ranges.length,
  }));
}

function breakdownPct(values: string[]): { label: string; pct: number }[] {
  const total = values.length;
  if (total === 0) return [];
  const counts: Record<string, number> = {};
  for (const v of values) counts[v] = (counts[v] ?? 0) + 1;
  return Object.entries(counts).map(([label, count]) => ({ label, pct: count / total }));
}

function emptyPo3Stats(query: ReportQuery): Po3Stats {
  return {
    hodTimeDistribution: [],
    lodTimeDistribution: [],
    avgRangeByWeekday: [],
    newsVsNonNews: [],
    pdArrayHeldHod: [],
    pdArrayHeldLod: [],
    manipulationDepth: [],
    phaseRatesByWeekday: [],
    window: query.window || 'daily',
    phase: query.phase || 'all',
  };
}
```

### 5b. Other modules — structure

Every other module in `src/lib/reports/{fvg,ob,liquidity,keyopens,gaps,news,macros,gex}.ts` follows the same pattern:

```
export async function query<Report>Stats(query: ReportQuery): Promise<{
  data: <ReportType>;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery('<table_name>', query);
  const { data: rows, error, count } = await dbQuery
    .select<RowType[]>('*', { count: 'exact' })
    .order('trade_date', { ascending: false });

  if (error) throw error;

  // Transform rows into report shape + compute derived stats
  // ...

  return { data: { ... }, sampleSize: count ?? rows.length, lastUpdated: ... };
}
```

Table mapping for each module:

| Module      | Table                  |
|-------------|------------------------|
| `fvg.ts`    | `report_fvg_stats`     |
| `ob.ts`     | `report_ob_stats`      |
| `liquidity.ts` | `report_liquidity_stats` |
| `po3.ts`    | `report_po3_stats`     |
| `keyopens.ts` | `report_keyopens_stats` |
| `gaps.ts`   | `report_gaps_stats`    |
| `news.ts`   | `report_news_stats`    |
| `macros.ts` | `report_macros_stats`  |
| `gex.ts`    | `gex_levels` (no lookback), `gex_historical_stats`, `gex_pc_ratio`, `gex_oi` |

The `gex.ts` module has four exported functions since GEX data has separate tables and no lookback filtering:

```typescript
export async function queryGexLevels(instrument: string): Promise<...>;
export async function queryGexHistorical(query: ReportQuery): Promise<...>;
export async function queryPcRatio(query: ReportQuery): Promise<...>;
export async function queryOiByStrike(instrument: string): Promise<...>;
```

---

## 6. API Routes

### 6a. Common utility (`src/app/api/_middleware.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

/**
 * Parse common query params for report routes.
 * Returns typed ReportQuery with defaults.
 */
export function parseReportQuery(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  return {
    instrument: searchParams.get('instrument') ?? 'all',
    lookback: searchParams.get('lookback') ?? '1yr',
    session: searchParams.get('session') ?? 'all',
    weekday: searchParams.get('weekday') ?? 'all',
    phase: searchParams.get('phase') ?? 'all',
    window: searchParams.get('window') ?? 'all',
  };
}

/**
 * Respond with 400 + detail.
 */
export function badRequest(detail: string) {
  return NextResponse.json({ error: detail }, { status: 400 });
}

/**
 * Respond with 404.
 */
export function notFound() {
  return NextResponse.json({ error: 'No data for this filter combination' }, { status: 404 });
}

/**
 * Respond with 500.
 */
export function internalError(error: unknown) {
  console.error('[API Error]', error);
  return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
}

/**
 * Server-side admin check.
 */
export async function requireAdmin(): Promise<NextResponse | null> {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  // ponytail: checks admin_users table on every request.
  // Cache the user's admin status in Redis with a 5-min TTL if this becomes a bottleneck.
  const { supabase } = await import('@/lib/supabase/client');
  const { data } = await supabase
    .from('admin_users')
    .select('id')
    .eq('clerk_id', userId)
    .single();

  if (!data) return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  return null; // is admin
}
```

### 6b. PO3 Route (most complex example) (`src/app/api/reports/po3/route.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, badRequest, notFound, internalError } from '../../_middleware';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryPo3Stats } from '@/lib/reports/po3';

const REPORT_TYPE = 'po3';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const query = parseReportQuery(request);
    const validWindows = ['daily', '4h-6am', '4h-10am', '30m-930', '30m-1000', 'ny-session', '15m-945'];

    if (query.window && query.window !== 'all' && !validWindows.includes(query.window)) {
      return badRequest(
        `Invalid window. Must be one of: ${validWindows.join(', ')} or omit for default.`
      );
    }

    const cacheKey = buildCacheKey(REPORT_TYPE, query);

    const result = await getOrCompute(cacheKey, () => queryPo3Stats(query), { ttl: 7200 });

    if (result.sampleSize === 0) {
      return notFound();
    }

    return NextResponse.json(result, {
      headers: {
        // Allow CDN to serve stale while revalidating in background (for exploration)
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    });
  } catch (error) {
    return internalError(error);
  }
}
```

### 6c. Other report routes — pattern

Every other report route (`/api/reports/{fvg,ob,liquidity,key-opens,gaps,news,macros,gex,gex/historical,gex/pc-ratio,gex/oi}`) follows the identical pattern with three deltas:

1. Import the correct query function from `@/lib/reports/<module>`
2. Set `REPORT_TYPE` to the report name
3. Add route-specific param validation where needed (e.g., GEX instruments, macro window names)

Example — FVG route would be:

```typescript
// src/app/api/reports/fvg/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, notFound, internalError } from '../../_middleware';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryFvgStats } from '@/lib/reports/fvg';

const REPORT_TYPE = 'fvg';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const query = parseReportQuery(request);
    const cacheKey = buildCacheKey(REPORT_TYPE, query);
    const result = await getOrCompute(cacheKey, () => queryFvgStats(query), { ttl: 7200 });

    if (result.sampleSize === 0) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600' },
    });
  } catch (error) {
    return internalError(error);
  }
}
```

### 6d. GEX Route — special handling (`/api/reports/gex/route.ts`)

GEX levels are current data, not historical. No lookback filtering. Cache TTL is 30 minutes.

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, badRequest, notFound, internalError } from '../../_middleware';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryGexLevels } from '@/lib/reports/gex';

export async function GET(request: NextRequest) {
  try {
    const { instrument } = parseReportQuery(request);
    if (!instrument || instrument === 'all') {
      return badRequest('instrument is required for GEX levels');
    }

    const cacheKey = buildCacheKey('gex-levels', { instrument });
    const result = await getOrCompute(
      cacheKey,
      () => queryGexLevels(instrument),
      { ttl: 1800 },  // 30 min — GEX refreshes every 30m
    );

    if (!result.data) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-cache' },  // GEX is current, no stale serving
    });
  } catch (error) {
    return internalError(error);
  }
}
```

### 6e. Admin Routes

#### PO3 Queue (`/api/admin/po3-queue/route.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { requireAdmin, internalError } from '../_middleware';

export async function GET(request: NextRequest) {
  const adminError = await requireAdmin();
  if (adminError) return adminError;

  try {
    const { supabase } = await import('@/lib/supabase/client');
    const { searchParams } = request.nextUrl;

    let query = supabase
      .from('po3_unconfirmed')
      .select('*')
      .order('trade_date', { ascending: false })
      .limit(50);

    const instrument = searchParams.get('instrument');
    if (instrument) query = query.eq('instrument', instrument.toUpperCase());

    const { data, error } = await query;
    if (error) throw error;

    return NextResponse.json({ data, total: data?.length ?? 0 });
  } catch (error) {
    return internalError(error);
  }
}
```

#### PO3 Label Submission (`/api/admin/po3-label/route.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { requireAdmin, badRequest, internalError } from '../_middleware';

export async function POST(request: NextRequest) {
  const adminError = await requireAdmin();
  if (adminError) return adminError;

  try {
    const body = await request.json();
    const { instanceId, phase } = body;

    if (!instanceId || !phase) {
      return badRequest('instanceId and phase are required');
    }

    if (!['bullish', 'bearish', 'exclude'].includes(phase)) {
      return badRequest('phase must be bullish, bearish, or exclude');
    }

    const { supabase } = await import('@/lib/supabase/client');

    if (phase === 'exclude') {
      const { error } = await supabase
        .from('po3_unconfirmed')
        .update({ excluded: true })
        .eq('id', instanceId);
      if (error) throw error;
    } else {
      // Move from unconfirmed to confirmed with human label
      const { data: instance, error: fetchError } = await supabase
        .from('po3_unconfirmed')
        .select('*')
        .eq('id', instanceId)
        .single();
      if (fetchError) throw fetchError;
      if (!instance) return badRequest('Instance not found');

      const { error: insertError } = await supabase
        .from('po3_confirmed')
        .insert({
          instrument: instance.instrument,
          trade_date: instance.trade_date,
          window: instance.window,
          open: instance.open,
          hod: instance.hod,
          lod: instance.lod,
          phase,
          labeled_by: instance.assigned_admin,
        });
      if (insertError) throw insertError;

      // Remove from queue
      await supabase.from('po3_unconfirmed').delete().eq('id', instanceId);
    }

    // Invalidate PO3 cache so next report fetch picks up new data
    // ponytail: flushing all PO3 cache on every label is brute-force.
    // Prefix-invalidate only the affected instrument if pipeline allows partial flushes.
    const { redis } = await import('@/lib/cache/client');
    const { buildTypePrefix } = await import('@/lib/cache/keys');
    const keys = await redis.keys(buildTypePrefix('po3'));
    if (keys.length > 0) await redis.del(...keys);

    return NextResponse.json({ success: true });
  } catch (error) {
    return internalError(error);
  }
}
```

---

## 7. Authentication & Webhooks

### 7a. Clerk Webhook (`/api/webhooks/clerk/route.ts`)

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';
import { supabase } from '@/lib/supabase/client';

// ponytail: syncs every Clerk event to admin_users.
// If user count grows beyond ~100, batch the sync or switch to lazy registration.
export async function POST(request: NextRequest) {
  const SIGNING_SECRET = process.env.CLERK_WEBHOOK_SECRET!;
  if (!SIGNING_SECRET) {
    return NextResponse.json({ error: 'Missing webhook secret' }, { status: 500 });
  }

  const wh = new Webhook(SIGNING_SECRET);
  const payload = await request.text();
  const svixId = request.headers.get('svix-id');
  const svixTimestamp = request.headers.get('svix-timestamp');
  const svixSignature = request.headers.get('svix-signature');

  if (!svixId || !svixTimestamp || !svixSignature) {
    return NextResponse.json({ error: 'Missing svix headers' }, { status: 400 });
  }

  let evt: { type: string; data: Record<string, unknown> };
  try {
    evt = wh.verify(payload, {
      'svix-id': svixId,
      'svix-timestamp': svixTimestamp,
      'svix-signature': svixSignature,
    }) as typeof evt;
  } catch {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  if (evt.type === 'user.created' || evt.type === 'user.updated') {
    const clerkId = evt.data.id as string;
    const email = ((evt.data.email_addresses as Array<{ email_address: string }>)?.[0]?.email_address) ?? '';
    const isAdmin = await checkIfAdmin(email);
    // upsert — handles both create and update
    await supabase.from('admin_users').upsert(
      { clerk_id: clerkId, email, role: isAdmin ? 'admin' : 'viewer' },
      { onConflict: 'clerk_id' },
    );
  }

  if (evt.type === 'user.deleted') {
    const clerkId = evt.data.id as string;
    await supabase.from('admin_users').delete().eq('clerk_id', clerkId);
  }

  return NextResponse.json({ success: true });
}

/**
 * Check if an email belongs to the admin list.
 * Simple config-based list in env; extend to DB-backed if admins grow.
 */
function checkIfAdmin(email: string): boolean {
  const admins = (process.env.ADMIN_EMAILS ?? '').split(',').map(e => e.trim().toLowerCase());
  return admins.includes(email.toLowerCase());
}
```

---

## 8. Cache Invalidation Strategy

### 8a. After Pipeline Run (in Python pipeline, triggered via an HTTP call to Next.js)

The Python pipeline hits a `/api/revalidate` endpoint after each aggregation completes:

```typescript
// src/app/api/revalidate/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { redis } from '@/lib/cache/client';
import { ALL_REPORTS_PREFIX } from '@/lib/cache/keys';

const PIPELINE_API_KEY = process.env.PIPELINE_API_KEY;

export async function POST(request: NextRequest) {
  const auth = request.headers.get('authorization');
  if (!PIPELINE_API_KEY || auth !== `Bearer ${PIPELINE_API_KEY}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json().catch(() => ({}));
    const type = body.type as string | undefined;  // optional: 'po3' | 'fvg' | etc

    let keys: string[];
    if (type) {
      const { buildTypePrefix } = await import('@/lib/cache/keys');
      keys = await redis.keys(buildTypePrefix(type));
    } else {
      keys = await redis.keys(ALL_REPORTS_PREFIX);
    }

    if (keys.length > 0) {
      await redis.del(...keys);
    }

    // Optionally trigger cache warming for the most popular filter combos
    if (type) {
      await warmCache(type).catch(() => {});
    }

    return NextResponse.json({ invalidated: keys.length });
  } catch (error) {
    console.error('[Revalidate Error]', error);
    return NextResponse.json({ error: 'Revalidation failed' }, { status: 500 });
  }
}

/**
 * Pre-compute popular filter combos into cache after pipeline run.
 * Add more combos as usage patterns emerge.
 */
async function warmCache(type: string): Promise<void> {
  const popularCombos = [
    { instrument: 'ES', lookback: '1yr', session: 'all' },
    { instrument: 'ES', lookback: '6mo', session: 'all' },
    { instrument: 'NQ', lookback: '1yr', session: 'all' },
    { instrument: 'NQ', lookback: '6mo', session: 'all' },
    { instrument: 'ES', lookback: '3mo', session: 'all' },
  ];

  // Dynamic import of the correct query function
  // ponytail: hardcoded module map; add if this grows beyond a few entries.
  const moduleMap: Record<string, string> = {
    fvg: 'fvg', ob: 'ob', liquidity: 'liquidity',
    po3: 'po3', keyopens: 'keyopens', gaps: 'gaps',
    news: 'news', macros: 'macros',
  };

  const modPath = moduleMap[type];
  if (!modPath) return;

  const mod = await import(`../lib/reports/${modPath}`);
  const queryFn = mod[`query${type.charAt(0).toUpperCase() + type.slice(1)}Stats`];
  if (!queryFn) return;

  const { getOrCompute } = await import('@/lib/cache/get-or-compute');
  const { buildCacheKey } = await import('@/lib/cache/keys');

  await Promise.allSettled(
    popularCombos.map(combo =>
      getOrCompute(buildCacheKey(type, combo), () => queryFn(combo), { ttl: 7200 })
    ),
  );
}
```

### 8b. TTL Summary

| Data             | TTL      | Rationale                              |
|------------------|----------|----------------------------------------|
| Report stats     | 7200s    | Updated once per pipeline run (daily)  |
| GEX levels       | 1800s    | Refreshes every 30 min                 |
| GEX historical   | 3600s    | Daily refresh                          |
| PC Ratio / OI    | 3600s    | Daily refresh                          |
| Cache warming    | 7200s    | Matches report TTL                     |

---

## 9. Error Handling & Response Shape

Every API response follows a consistent shape:

**Success:**
```json
{
  "data": { /* report-specific shape */ },
  "sampleSize": 403,
  "isLowSample": false,
  "lastUpdated": "2026-07-09T14:30:00Z"
}
```

**Client Error (400/401/403/404):**
```json
{
  "error": "Invalid window. Must be one of: daily, 4h-6am, ..."
}
```

**Server Error (500):**
```json
{
  "error": "Internal server error"
}
```

---

## 10. Implementation Order

1. **`src/lib/supabase/client.ts`** — Supabase singleton
2. **`src/lib/reports/types.ts`** — All shared types
3. **`src/lib/reports/query.ts`** — Base query builder
4. **`src/lib/cache/client.ts`** + **`keys.ts`** + **`get-or-compute.ts`** — Cache layer
5. **`src/lib/reports/fvg.ts`** — Simplest report module (reference for others)
6. **`src/lib/reports/po3.ts`** — Most complex report module
7. **`src/app/api/_middleware.ts`** — Route utilities
8. **`src/app/api/reports/po3/route.ts`** — Validate pattern with complex route
9. **`src/app/api/reports/fvg/route.ts`** — All remaining report routes (parallel)
10. **`src/app/api/reports/gex/route.ts`** + sub-routes — GEX family
11. **`src/app/api/admin/po3-queue/route.ts`** + **`po3-label/route.ts`** — Admin routes
12. **`src/app/api/webhooks/clerk/route.ts`** — Clerk sync
13. **`src/app/api/revalidate/route.ts`** — Cache invalidation endpoint

---

## 11. Environment Variables Required

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# Upstash Redis
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
CLERK_WEBHOOK_SECRET=

# Admin
ADMIN_EMAILS=aidancady15@gmail.com

# Pipeline API key (shared secret between Python pipeline and Next.js)
PIPELINE_API_KEY=
```

---

## 12. Database Tables Expected (read-only from app)

The Python pipeline maintains these tables. The app only reads them:

| Table                    | Purpose                                    |
|--------------------------|--------------------------------------------|
| `report_fvg_stats`       | FVG fill rate statistics                   |
| `report_ob_stats`        | Order Block success rates                  |
| `report_liquidity_stats` | Liquidity sweep stats                      |
| `report_po3_stats`       | PO3 time/range/phase distributions         |
| `report_keyopens_stats`  | Key open continuation/reversal rates       |
| `report_gaps_stats`      | Opening gap fill stats                     |
| `report_news_stats`      | News candle high/low move stats            |
| `report_macros_stats`    | Macro window bullish/bearish/choppy rates  |
| `gex_levels`             | Current GEX call wall, put wall, etc.      |
| `gex_historical_stats`   | Historical GEX by week                     |
| `gex_pc_ratio`           | Daily put/call ratio                       |
| `gex_oi`                 | Open interest by strike                    |
| `po3_unconfirmed`        | PO3 queue awaiting admin labeling          |
| `po3_confirmed`          | Human-labeled PO3 instances                |
| `admin_users`            | Clerk ID -> role mapping                   |
