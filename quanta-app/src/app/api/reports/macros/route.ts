import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, notFound, internalError, requireUser } from '../../helpers';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryMacrosStats } from '@/lib/reports/macros';

const REPORT_TYPE = 'macros';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const query = parseReportQuery(request);
    const authError = await requireUser();
    if (authError) return authError;
    const validWindows = ['daily', 'weekly', 'monthly', 'ny-close', 'asia-open', 'london-open'];
    if (query.window && query.window !== 'all' && !validWindows.includes(query.window)) {
      return NextResponse.json(
        { error: `Invalid window. Must be one of: ${validWindows.join(', ')}` },
        { status: 400 },
      );
    }

    const cacheKey = buildCacheKey(REPORT_TYPE, query);
    const result = await getOrCompute(cacheKey, () => queryMacrosStats(query), { ttl: 7200 });

    if (result.sampleSize === 0) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600' },
    });
  } catch (error) {
    return internalError(error);
  }
}
