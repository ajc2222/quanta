import { createHash } from 'crypto';
import type { ReportQuery } from '@/lib/reports/types';

export function buildCacheKey(type: string, query: ReportQuery): string {
  const { instrument = 'all', lookback = '1yr', session = 'all', ...rest } = query;

  const filterEntries = Object.entries(rest)
    .filter(([_, v]) => v !== undefined && v !== null && v !== '')
    .sort(([a], [b]) => a.localeCompare(b));

  const filterStr = JSON.stringify(Object.fromEntries(filterEntries));
  const hash = createHash('md5').update(filterStr).digest('hex').slice(0, 12);

  return `report:${type}:${instrument}:${lookback}:${session}:${hash}`;
}

export function buildTypePrefix(type: string): string {
  return `report:${type}:*`;
}

export const ALL_REPORTS_PREFIX = 'report:*';
