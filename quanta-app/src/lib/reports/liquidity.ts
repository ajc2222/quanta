import { fetchAllReportRows } from './query';
import type { ReportQuery, LiquidityStats } from './types';

interface LiquidityStatRow {
  instrument: string;
  level_type: string;
  session_type: string;
  weekday: number;
  lookback_days: string;
  sample_size: number;
  sweep_rate_pct: number | null;
  avg_reversal_magnitude_points: number | null;
  continuation_after_sweep_pct: number | null;
}

const TABLE = 'report_liquidity_stats';

export async function queryLiquidityStats(query: ReportQuery): Promise<{
  data: LiquidityStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { rows, count } = await fetchAllReportRows<LiquidityStatRow>(TABLE, query);
  if (rows.length === 0) {
    return {
      data: { sweepRate: 0, avgSweepDepth: 0, continuationRate: 0, bySession: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const aggRow = rows.find(r => r.level_type === 'all' && r.session_type === 'All' && r.weekday === -1);
  const sessionRows = rows.filter(r => r.session_type !== 'All' && r.weekday === -1 && r.level_type === 'all');

  return {
    data: {
      sweepRate: (aggRow?.sweep_rate_pct ?? 0) / 100,
      avgSweepDepth: aggRow?.avg_reversal_magnitude_points ?? 0,
      continuationRate: (aggRow?.continuation_after_sweep_pct ?? 0) / 100,
      bySession: sessionRows.map(r => ({
        session: r.session_type,
        sweepRate: (r.sweep_rate_pct ?? 0) / 100,
        sampleSize: r.sample_size,
      })),
    },
    sampleSize: aggRow?.sample_size ?? count,
    lastUpdated: new Date().toISOString(),
  };
}
