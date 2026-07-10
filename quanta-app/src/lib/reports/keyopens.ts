import { buildReportQuery, avg, groupBy } from './query';
import type { ReportQuery, KeyOpensStats } from './types';

interface KeyOpensRow {
  trade_date: string;
  instrument: string;
  direction: string;
  continued: boolean;
  reversed: boolean;
  move_points: number;
}

const TABLE = 'report_keyopens_stats';

export async function queryKeyOpensStats(query: ReportQuery): Promise<{
  data: KeyOpensStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery(TABLE, query);
  const { data: rows, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' })
    .order('trade_date', { ascending: false });

  if (error) throw error;
  const typedRows = (rows ?? []) as KeyOpensRow[];
  if (typedRows.length === 0) {
    return {
      data: { continuationRate: 0, reversalRate: 0, avgMovePoints: 0, byDirection: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const total = typedRows.length;
  const continuationRate = typedRows.filter(r => r.continued).length / total;
  const reversalRate = typedRows.filter(r => r.reversed).length / total;
  const avgMovePoints = avg(typedRows.map(r => r.move_points));

  const byDirection = groupBy(typedRows, 'direction', (g) => ({
    rate: g.filter(r => r.continued).length / g.length,
    sampleSize: g.length,
  }));

  return {
    data: { continuationRate, reversalRate, avgMovePoints, byDirection },
    sampleSize: count ?? total,
    lastUpdated: typedRows[0].trade_date,
  };
}

