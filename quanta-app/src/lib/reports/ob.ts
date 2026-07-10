import { fetchAllReportRows } from './query';
import type { ReportQuery, ObStats } from './types';

interface ObStatRow {
  instrument: string;
  timeframe: string;
  session_type: string;
  weekday: number;
  direction: string;
  lookback_days: string;
  sample_size: number;
  respect_rate_pct: number | null;
  avg_reversal_magnitude_points: number | null;
  avg_mitigation_time_minutes: number | null;
}

const TABLE = 'report_ob_stats';

export async function queryObStats(query: ReportQuery): Promise<{
  data: ObStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { rows, count } = await fetchAllReportRows<ObStatRow>(TABLE, query);
  if (rows.length === 0) {
    return {
      data: { successRate: 0, avgReversalPips: 0, avgDurationBars: 0, byWeekday: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const aggRow = rows.find(r => r.direction === 'all' && r.session_type === 'All' && r.weekday === -1);
  const weekdayRows = rows.filter(r => r.weekday !== -1 && r.session_type === 'All' && r.direction === 'all');

  return {
    data: {
      successRate: (aggRow?.respect_rate_pct ?? 0) / 100,
      avgReversalPips: aggRow?.avg_reversal_magnitude_points ?? 0,
      avgDurationBars: aggRow?.avg_mitigation_time_minutes ?? 0,
      byWeekday: weekdayRows.map(r => ({
        weekday: String(r.weekday),
        successRate: (r.respect_rate_pct ?? 0) / 100,
        sampleSize: r.sample_size,
      })),
    },
    sampleSize: aggRow?.sample_size ?? count,
    lastUpdated: new Date().toISOString(),
  };
}
