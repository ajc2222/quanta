import { fetchAllReportRows } from './query';
import type { ReportQuery, FvgStats } from './types';

interface FvgStatRow {
  instrument: string;
  timeframe: string;
  session_type: string;
  weekday: number;
  lookback_days: string;
  sample_size: number;
  fill_rate_full_pct: number | null;
  fill_rate_partial_pct: number | null;
  avg_fill_time_minutes: number | null;
}

const TABLE = 'report_fvg_stats';

export async function queryFvgStats(query: ReportQuery): Promise<{
  data: FvgStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { rows, count } = await fetchAllReportRows<FvgStatRow>(TABLE, query);
  if (rows.length === 0) {
    return {
      data: { fillRate: 0, avgFillTimeMinutes: 0, partialFillRate: 0, byWeekday: [], bySession: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  // Aggregate row: session_type='All', weekday=-1
  const aggRow = rows.find(r => r.session_type === 'All' && r.weekday === -1);

  // byWeekday: weekday != -1 and session_type='All'
  const weekdayRows = rows.filter(r => r.weekday !== -1 && r.session_type === 'All');
  const byWeekday = weekdayRows
    .map(r => ({
      weekday: String(r.weekday),
      fillRate: (r.fill_rate_full_pct ?? 0) / 100,
      sampleSize: r.sample_size,
    }))
    .sort((a, b) => Number(a.weekday) - Number(b.weekday));

  // bySession: session_type != 'All' and weekday=-1
  const sessionRows = rows.filter(r => r.session_type !== 'All' && r.weekday === -1);
  const bySession = sessionRows.map(r => ({
    session: r.session_type,
    fillRate: (r.fill_rate_full_pct ?? 0) / 100,
    sampleSize: r.sample_size,
  }));

  return {
    data: {
      fillRate: (aggRow?.fill_rate_full_pct ?? 0) / 100,
      avgFillTimeMinutes: aggRow?.avg_fill_time_minutes ?? 0,
      partialFillRate: (aggRow?.fill_rate_partial_pct ?? 0) / 100,
      byWeekday,
      bySession,
    },
    sampleSize: aggRow?.sample_size ?? count,
    lastUpdated: new Date().toISOString(),
  };
}
