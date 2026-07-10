import { buildReportQuery, avg, groupBy } from './query';
import type { ReportQuery, NewsStats } from './types';

interface NewsRow {
  trade_date: string;
  instrument: string;
  event: string;
  high_move: number;
  low_move: number;
  directional_bias: number;
}

const TABLE = 'report_news_stats';

export async function queryNewsStats(query: ReportQuery): Promise<{
  data: NewsStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery(TABLE, query);
  const { data: rows, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' })
    .order('trade_date', { ascending: false });

  if (error) throw error;
  const typedRows = (rows ?? []) as NewsRow[];
  if (typedRows.length === 0) {
    return {
      data: { avgHighMove: 0, avgLowMove: 0, directionalBias: 0, byEvent: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const total = typedRows.length;
  const avgHighMove = avg(typedRows.map(r => r.high_move));
  const avgLowMove = avg(typedRows.map(r => r.low_move));
  const directionalBias = typedRows.reduce((sum, r) => sum + r.directional_bias, 0) / total;

  const byEvent = groupBy(typedRows, 'event', (g) => ({
    avgMove: avg(g.map(r => (r.high_move + r.low_move) / 2)),
    sampleSize: g.length,
  }));

  return {
    data: { avgHighMove, avgLowMove, directionalBias, byEvent },
    sampleSize: count ?? total,
    lastUpdated: typedRows[0].trade_date,
  };
}

