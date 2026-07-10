import { fetchAllReportRows, avg } from './query';
import type { ReportQuery, MacrosStats } from './types';

interface MacrosRow {
  trade_date: string;
  instrument: string;
  window: string;
  phase: string;
  magnitude: number;
  hod_time: string;
  lod_time: string;
  continued: boolean;
  reversed: boolean;
}

const TABLE = 'report_macros_stats';

export async function queryMacrosStats(query: ReportQuery): Promise<{
  data: MacrosStats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { rows: typedRows, count } = await fetchAllReportRows<MacrosRow>(TABLE, query);
  if (typedRows.length === 0) {
    return {
      data: {
        bullishPct: 0, bearishPct: 0, choppyPct: 0, avgMagnitude: 0,
        hodDistribution: [], lodDistribution: [],
        continuationRate: 0, reversalRate: 0, window: query.window || 'daily',
      },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  const total = typedRows.length;
  const bullishPct = typedRows.filter(r => r.phase === 'bullish').length / total;
  const bearishPct = typedRows.filter(r => r.phase === 'bearish').length / total;
  const choppyPct = typedRows.filter(r => r.phase === 'choppy').length / total;
  const avgMagnitude = avg(typedRows.map(r => r.magnitude));
  const continuationRate = typedRows.filter(r => r.continued).length / total;
  const reversalRate = typedRows.filter(r => r.reversed).length / total;

  const hodDistribution = bucketByTime(typedRows.map(r => r.hod_time), 30);
  const lodDistribution = bucketByTime(typedRows.map(r => r.lod_time), 30);

  return {
    data: {
      bullishPct, bearishPct, choppyPct, avgMagnitude,
      hodDistribution, lodDistribution,
      continuationRate, reversalRate,
      window: query.window || 'daily',
    },
    sampleSize: count ?? total,
    lastUpdated: typedRows[0].trade_date,
  };
}

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
