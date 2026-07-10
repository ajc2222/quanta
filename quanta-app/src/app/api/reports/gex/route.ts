import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, badRequest, notFound, internalError, requireUser } from '../../helpers';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryGexLevels } from '@/lib/reports/gex';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const { instrument } = parseReportQuery(request);
    const authError = await requireUser();
    if (authError) return authError;
    if (!instrument || instrument === 'all') {
      return badRequest('instrument is required for GEX levels');
    }

    const cacheKey = buildCacheKey('gex-levels', { instrument });
    const result = await getOrCompute(
      cacheKey,
      () => queryGexLevels(instrument),
      { ttl: 1800 },
    );

    if (!result.data) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-cache' },
    });
  } catch (error) {
    return internalError(error);
  }
}
