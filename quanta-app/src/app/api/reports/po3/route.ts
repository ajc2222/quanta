import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, validateReportParams, badRequest, notFound, internalError, requireUser } from '../../helpers';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryPo3Stats } from '@/lib/reports/po3';

const REPORT_TYPE = 'po3';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const query = parseReportQuery(request);
    const authError = await requireUser();
    if (authError) return authError;

    const paramsError = validateReportParams(query);
    if (paramsError) return badRequest(paramsError);

    const validWindows = ['daily', '4h-6am', '4h-10am', '30m-930', '30m-1000', 'ny-session', '15m-945'];

    if (query.window && query.window !== 'all' && !validWindows.includes(query.window)) {
      return badRequest(
        `Invalid window. Must be one of: ${validWindows.join(', ')} or omit for default.`,
      );
    }

    const cacheKey = buildCacheKey(REPORT_TYPE, query);

    const result = await getOrCompute(cacheKey, () => queryPo3Stats(query), { ttl: 7200 });

    if (result.sampleSize === 0) {
      return notFound();
    }

    return NextResponse.json(result, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    });
  } catch (error) {
    return internalError(error);
  }
}
