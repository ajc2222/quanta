import { buildReportQuery, avg, groupBy } from './query';
import type { ReportQuery, GapsStats } from './types';

interface GapsRow {
  trade_date: string;
  instrument: string;
  direction: string;
  filled: boolean;
  fill_percent: number;
  fill_time_minutes: number;
}

const TABLE = 'report_gaps_stats';

export async function queryGapsStats(query: ReportQuery): Promise<{
  data: GapsStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const dbQuery = buildReportQuery(TABLE, query);
  const { data: rows, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' })
    .order('trade_date', { ascending: false });

  if (error) throw error;
  const typedRows = (rows ?? []) as GapsRow[];
  if (typedRows.length === 0) {
    return {
      data: { fillRate: 0, avgFillPercent: 0, avgFillTimeMinutes: 0, byGapDirection: [] },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const total = typedRows.length;
  const fillRate = typedRows.filter(r => r.filled).length / total;
  const avgFillPercent = avg(typedRows.map(r => r.fill_percent));
  const avgFillTimeMinutes = avg(typedRows.map(r => r.fill_time_minutes));

  const byGapDirection = groupBy(typedRows, 'direction', (g) => ({
    fillRate: g.filter(r => r.filled).length / g.length,
    sampleSize: g.length,
  }));

  return {
    data: { fillRate, avgFillPercent, avgFillTimeMinutes, byGapDirection },
    sampleSize: count ?? total,
    lastUpdated: typedRows[0].trade_date,
  };
}

