import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';
import { checkRateLimit } from '@/lib/rate-limit';
import type { ReportQuery } from '@/lib/reports/types';

export function parseReportQuery(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  return {
    instrument: searchParams.get('instrument') ?? 'all',
    lookback: searchParams.get('lookback') ?? '1yr',
    session: searchParams.get('session') ?? 'all',
    weekday: searchParams.get('weekday') ?? 'all',
    phase: searchParams.get('phase') ?? 'all',
    window: searchParams.get('window') ?? 'all',
  };
}

export function badRequest(detail: string) {
  return NextResponse.json({ error: detail }, { status: 400 });
}

export function notFound() {
  return NextResponse.json({ error: 'No data for this filter combination' }, { status: 404 });
}

export function internalError(error: unknown) {
  console.error('[API Error]', error);
  return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
}

export async function requireUser(options?: { rateLimit?: boolean }): Promise<NextResponse | null> {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  if (options?.rateLimit !== false) {
    const { allowed, remaining } = await checkRateLimit(userId);
    if (!allowed) {
      return NextResponse.json(
        { error: 'Too many requests', retryAfter: 60 },
        { status: 429, headers: { 'X-RateLimit-Remaining': '0' } as any },
      );
    }
  }

  return null;
}

export function validateReportParams(params: ReportQuery): string | null {
  if (params.instrument && !/^[A-Z]{1,4}$/.test(params.instrument)) {
    return 'Invalid instrument';
  }
  if (params.lookback && !['3mo', '6mo', '1yr'].includes(params.lookback)) {
    if (!/^\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2}$/.test(params.lookback)) {
      return 'Invalid lookback';
    }
  }
  if (params.session && !['all', 'london', 'ny_am', 'ny_pm', 'overnight', 'globex'].includes(params.session)) {
    return 'Invalid session';
  }
  return null;
}

export async function requireAdmin(): Promise<NextResponse | null> {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { supabase } = await import('@/lib/supabase/client');
  const { data } = await supabase
    .from('admin_users')
    .select('id')
    .eq('clerk_id', userId)
    .single();

  if (!data) return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  return null;
}
