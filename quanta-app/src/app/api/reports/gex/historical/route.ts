import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, badRequest, notFound, internalError, requireUser, validateReportParams } from '../../../helpers';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryGexHistorical } from '@/lib/reports/gex';

const REPORT_TYPE = 'gex-historical';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const query = parseReportQuery(request);
    const authError = await requireUser();
    if (authError) return authError;
    const validationError = validateReportParams(query);
    if (validationError) return badRequest(validationError);
    const cacheKey = buildCacheKey(REPORT_TYPE, query);
    const result = await getOrCompute(cacheKey, () => queryGexHistorical(query), { ttl: 3600 });

    if (result.sampleSize === 0) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600' },
    });
  } catch (error) {
    return internalError(error);
  }
}
