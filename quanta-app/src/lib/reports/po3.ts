import { fetchAllReportRows } from './query';
import type { ReportQuery, Po3Stats } from './types';

interface Po3StatRow {
  instrument: string;
  window_type: string;
  weekday: number;
  phase_filter: string;
  news_filter: string;
  lookback_days: string;
  sample_size: number;
  bullish_rate_pct: number | null;
  bearish_rate_pct: number | null;
  ambiguous_rate_pct: number | null;
  avg_range_points: number | null;
  avg_manip_depth_pct: number | null;
  hod_time_distribution: Record<string, number> | null;
  lod_time_distribution: Record<string, number> | null;
  pd_array_held_hod_breakdown: Record<string, number> | null;
  pd_array_held_lod_breakdown: Record<string, number> | null;
}

const TABLE = 'report_po3_stats';

export async function queryPo3Stats(query: ReportQuery): Promise<{
  data: Po3Stats;
  sampleSize: number;
  lastUpdated: string;
}> {
  const { rows, count } = await fetchAllReportRows<Po3StatRow>(TABLE, query);
  if (rows.length === 0) {
    return {
      data: {
        hodTimeDistribution: [], lodTimeDistribution: [], avgRangeByWeekday: [],
        newsVsNonNews: [], pdArrayHeldHod: [], pdArrayHeldLod: [],
        manipulationDepth: [], phaseRatesByWeekday: [],
        window: query.window || 'daily', phase: query.phase || 'all',
      },
      sampleSize: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  // Aggregate: phase_filter='all', weekday=-1, news_filter='all'
  const aggRow = rows.find(r => r.phase_filter === 'all' && r.weekday === -1 && r.news_filter === 'all');

  // byWeekday
  const weekdayRows = rows.filter(r => r.weekday !== -1 && r.phase_filter === 'all' && r.news_filter === 'all');
  const avgRangeByWeekday = weekdayRows.map(r => ({
    weekday: String(r.weekday),
    avgRange: r.avg_range_points ?? 0,
    sampleSize: r.sample_size,
  })).sort((a, b) => Number(a.weekday) - Number(b.weekday));

  // News vs Non-news
  const newsRow = rows.find(r => r.news_filter === 'news_day' && r.weekday === -1 && r.phase_filter === 'all');
  const nonNewsRow = rows.find(r => r.news_filter === 'non_news_day' && r.weekday === -1 && r.phase_filter === 'all');
  const newsVsNonNews = [
    { condition: 'News Day', avgRange: newsRow?.avg_range_points ?? 0, phaseRate: (newsRow?.bullish_rate_pct ?? 0) / 100 },
    { condition: 'Non-News', avgRange: nonNewsRow?.avg_range_points ?? 0, phaseRate: (nonNewsRow?.bullish_rate_pct ?? 0) / 100 },
  ];

  // Phase rates by weekday
  const dayNames = ['0', '1', '2', '3', '4', '5', '6'];
  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const phaseRatesByWeekday = weekdayRows.map(r => {
    const bullish = rows.find(x => x.weekday === r.weekday && x.phase_filter === 'bullish' && x.news_filter === 'all');
    const bearish = rows.find(x => x.weekday === r.weekday && x.phase_filter === 'bearish' && x.news_filter === 'all');
    const ambiguous = rows.find(x => x.weekday === r.weekday && x.phase_filter === 'unconfirmed' && x.news_filter === 'all');
    const wkIdx = r.weekday >= 0 && r.weekday <= 6 ? r.weekday : 1;
    return {
      weekday: weekdays[wkIdx],
      bullish: bullish?.sample_size ? (bullish.sample_size / r.sample_size) : 0,
      bearish: bearish?.sample_size ? (bearish.sample_size / r.sample_size) : 0,
      ambiguous: ambiguous?.sample_size ? (ambiguous.sample_size / r.sample_size) : 0,
    };
  });

  // Convert JSONB distributions to arrays
  const distToArray = (dist: Record<string, number> | null): { bucket: string; count: number }[] =>
    dist ? Object.entries(dist).map(([bucket, count]) => ({ bucket, count })).sort((a, b) => a.bucket.localeCompare(b.bucket)) : [];

  const pdArrayHeldHod = aggRow?.pd_array_held_hod_breakdown
    ? Object.entries(aggRow.pd_array_held_hod_breakdown).map(([label, pct]) => ({ label, pct: pct / 100 }))
    : [];
  const pdArrayHeldLod = aggRow?.pd_array_held_lod_breakdown
    ? Object.entries(aggRow.pd_array_held_lod_breakdown).map(([label, pct]) => ({ label, pct: pct / 100 }))
    : [];

  return {
    data: {
      hodTimeDistribution: distToArray(aggRow?.hod_time_distribution ?? null),
      lodTimeDistribution: distToArray(aggRow?.lod_time_distribution ?? null),
      avgRangeByWeekday,
      newsVsNonNews,
      pdArrayHeldHod,
      pdArrayHeldLod,
      manipulationDepth: aggRow?.avg_manip_depth_pct
        ? [{ bucket: '0%–5%', count: aggRow.avg_manip_depth_pct },
           { bucket: '5%–10%', count: 0 },
           { bucket: '10%+', count: 0 }]
        : [],
      phaseRatesByWeekday,
      window: query.window || 'daily',
      phase: query.phase || 'all',
    },
    sampleSize: aggRow?.sample_size ?? count,
    lastUpdated: new Date().toISOString(),
  };
}
