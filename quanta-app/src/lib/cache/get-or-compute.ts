import { redis } from './client';
import type { ReportResponse } from '@/lib/reports/types';

type DbQuery<T> = () => Promise<{
  data: T;
  sampleSize: number;
  lastUpdated: string;
}>;

type CacheValue<T> = Omit<ReportResponse<T>, 'isLowSample'>;

const MIN_SAMPLE_SIZE = 30;

export async function getOrCompute<T>(
  cacheKey: string,
  dbQuery: DbQuery<T>,
  options: { ttl?: number; serveStale?: boolean } = {},
): Promise<ReportResponse<T>> {
  const { ttl = 7200, serveStale: _serveStale = false } = options;

  // 1. Try cache
  const cached = await redis.get<CacheValue<T>>(cacheKey);
  if (cached) {
    return {
      ...cached,
      isLowSample: cached.sampleSize < MIN_SAMPLE_SIZE,
    };
  }

  // 2. Query database
  const result = await dbQuery();

  // 3. Write to cache (fire and forget)
  const cacheValue: CacheValue<T> = {
    data: result.data,
    sampleSize: result.sampleSize,
    lastUpdated: result.lastUpdated,
  };

  // ponytail: no error handling on write — cache failure shouldn't block the response.
  redis.set(cacheKey, JSON.stringify(cacheValue), { ex: ttl }).catch(() => {});

  return {
    ...result,
    isLowSample: result.sampleSize < MIN_SAMPLE_SIZE,
  };
}
