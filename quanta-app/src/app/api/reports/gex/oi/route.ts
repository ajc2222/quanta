import { NextRequest, NextResponse } from 'next/server';
import { parseReportQuery, badRequest, notFound, internalError, requireUser } from '../../../helpers';
import { buildCacheKey, getOrCompute } from '@/lib/cache';
import { queryOiByStrike } from '@/lib/reports/gex';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(request: NextRequest) {
  try {
    const { instrument } = parseReportQuery(request);
    const authError = await requireUser();
    if (authError) return authError;
    if (!instrument || instrument === 'all') {
      return badRequest('instrument is required for OI by strike');
    }

    const cacheKey = buildCacheKey('gex-oi', { instrument });
    const result = await getOrCompute(cacheKey, () => queryOiByStrike(instrument), { ttl: 3600 });

    if (result.sampleSize === 0) return notFound();

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600' },
    });
  } catch (error) {
    return internalError(error);
  }
}
