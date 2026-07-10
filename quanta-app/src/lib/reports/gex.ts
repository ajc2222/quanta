import { supabase } from '@/lib/supabase/client';
import { buildReportQuery } from './query';
import type { ReportQuery, GexLevels, GexHistoricalStats, PcRatio, OiByStrike } from './types';

// ── GEX Levels (current data, no lookback) ────────────────────

interface GexLevelsRow {
  instrument: string;
  call_wall: number;
  put_wall: number;
  gex_flip: number;
  zero_gamma: number;
  max_pain: number;
  profile: { strike: number; call_gex: number; put_gex: number }[];
  last_updated: string;
}

export async function queryGexLevels(instrument: string): Promise<{
  data: GexLevels;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { data: rows, error } = await supabase
    .from('gex_levels')
    .select('*')
    .eq('instrument', instrument.toUpperCase())
    .order('last_updated', { ascending: false })
    .limit(1);

  if (error) throw error;
  if (!rows || rows.length === 0) {
    return {
      data: null as unknown as GexLevels,
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const row = rows[0] as GexLevelsRow;
  return {
    data: {
      callWall: row.call_wall,
      putWall: row.put_wall,
      gexFlip: row.gex_flip,
      zeroGamma: row.zero_gamma,
      maxPain: row.max_pain,
      profile: (row.profile || []).map(p => ({
        strike: p.strike,
        callGex: p.call_gex,
        putGex: p.put_gex,
      })),
      lastUpdated: row.last_updated,
    },
    sampleSize: 1,
    lastUpdated: row.last_updated,
  };
}

// ── GEX Historical ────────────────────────────────────────────

interface GexHistoricalRow {
  week: string;
  total_gex: number;
  call_wall: number;
  put_wall: number;
}

export async function queryGexHistorical(query: ReportQuery): Promise<{
  data: GexHistoricalStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery('gex_historical_stats', query);
  const { data: rows, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' })
    .order('week', { ascending: false });

  if (error) throw error;
  const typedRows = (rows ?? []) as GexHistoricalRow[];
  if (typedRows.length === 0) {
    return { data: { byWeek: [] }, sampleSize: 0, lastUpdated: new Date().toISOString() };
  }

  const byWeek = typedRows.map(r => ({
    week: r.week,
    totalGex: r.total_gex,
    callWall: r.call_wall,
    putWall: r.put_wall,
  }));

  return { data: { byWeek }, sampleSize: count ?? typedRows.length, lastUpdated: typedRows[0].week };
}

// ── PC Ratio ──────────────────────────────────────────────────

interface PcRatioRow {
  date: string;
  ratio: number;
}

const PC_RATIO_TABLE = 'gex_pc_ratio';

export async function queryPcRatio(query: ReportQuery): Promise<{
  data: PcRatio;
  sampleSize: number;
  lastUpdated: string;
}> {
  let dbQuery = supabase.from(PC_RATIO_TABLE).select('*');

  if (query.lookback && query.lookback !== 'all') {
    const days =
      query.lookback === '3mo' ? 90 : query.lookback === '6mo' ? 180 : query.lookback === '1yr' ? 365 : null;
    if (days) {
      const cutoff = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
      dbQuery = dbQuery.gte('date', cutoff);
    }
  }

  if (query.instrument && query.instrument !== 'all') {
    dbQuery = dbQuery.eq('instrument', query.instrument.toUpperCase());
  }

  const { data: rows, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' })
    .order('date', { ascending: false });

  if (error) throw error;
  const typedRows = (rows ?? []) as PcRatioRow[];
  if (typedRows.length === 0) {
    return { data: { daily: [], rolling20Avg: [] }, sampleSize: 0, lastUpdated: new Date().toISOString() };
  }

  const daily = typedRows.map(r => ({ date: r.date, ratio: r.ratio })).reverse();

  const rolling20Avg = daily
    .map((_, i) => {
      if (i < 19) return null;
      const slice = daily.slice(i - 19, i + 1);
      const avgRatio = slice.reduce((s, d) => s + d.ratio, 0) / slice.length;
      return { date: daily[i].date, ratio: avgRatio };
    })
    .filter(Boolean) as { date: string; ratio: number }[];

  return { data: { daily, rolling20Avg }, sampleSize: count ?? typedRows.length, lastUpdated: typedRows[0].date };
}

// ── Open Interest by Strike ───────────────────────────────────

interface OiRow {
  instrument: string;
  strike: number;
  call_oi: number;
  put_oi: number;
  current_price: number;
}

export async function queryOiByStrike(instrument: string): Promise<{
  data: OiByStrike[];
  sampleSize: number;
  lastUpdated: string;
}> {
  const { data: rows, error } = await supabase
    .from('gex_oi')
    .select('*')
    .eq('instrument', instrument.toUpperCase())
    .order('strike', { ascending: true });

  if (error) throw error;
  if (!rows || rows.length === 0) {
    return { data: [], sampleSize: 0, lastUpdated: new Date().toISOString() };
  }

  const data = (rows as OiRow[]).map(r => ({
    strike: r.strike,
    callOi: r.call_oi,
    putOi: r.put_oi,
    currentPrice: r.current_price,
  }));

  return { data, sampleSize: rows.length, lastUpdated: new Date().toISOString() };
}
