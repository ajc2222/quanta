import { NextRequest, NextResponse } from 'next/server';
import { redis } from '@/lib/cache/client';
import { ALL_REPORTS_PREFIX } from '@/lib/cache/keys';

const PIPELINE_API_KEY = process.env.PIPELINE_API_KEY;

export async function POST(request: NextRequest) {
  const auth = request.headers.get('authorization');
  if (!PIPELINE_API_KEY || auth !== `Bearer ${PIPELINE_API_KEY}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json().catch(() => ({}));
    const type = body.type as string | undefined;

    let keys: string[];
    if (type) {
      const { buildTypePrefix } = await import('@/lib/cache/keys');
      keys = await redis.keys(buildTypePrefix(type));
    } else {
      keys = await redis.keys(ALL_REPORTS_PREFIX);
    }

    if (keys.length > 0) {
      await redis.del(...keys);
    }

    if (type) {
      await warmCache(type).catch(() => {});
    }

    return NextResponse.json({ invalidated: keys.length });
  } catch (error) {
    console.error('[Revalidate Error]', error);
    return NextResponse.json({ error: 'Revalidation failed' }, { status: 500 });
  }
}

async function warmCache(type: string): Promise<void> {
  const popularCombos = [
    { instrument: 'ES', lookback: '1yr', session: 'all' },
    { instrument: 'ES', lookback: '6mo', session: 'all' },
    { instrument: 'NQ', lookback: '1yr', session: 'all' },
    { instrument: 'NQ', lookback: '6mo', session: 'all' },
    { instrument: 'ES', lookback: '3mo', session: 'all' },
  ];

  const moduleMap: Record<string, string> = {
    fvg: 'fvg', ob: 'ob', liquidity: 'liquidity',
    po3: 'po3', keyopens: 'keyopens', gaps: 'gaps',
    news: 'news', macros: 'macros',
  };

  const modPath = moduleMap[type];
  if (!modPath) return;

  // static map required — bundler can't analyze template-literal dynamic imports
  const mods: Record<string, () => Promise<Record<string, unknown>>> = {
    fvg:      () => import('@/lib/reports/fvg'),
    ob:       () => import('@/lib/reports/ob'),
    liquidity: () => import('@/lib/reports/liquidity'),
    po3:      () => import('@/lib/reports/po3'),
    keyopens: () => import('@/lib/reports/keyopens'),
    gaps:     () => import('@/lib/reports/gaps'),
    news:     () => import('@/lib/reports/news'),
    macros:   () => import('@/lib/reports/macros'),
  };
  const modLoader = mods[modPath];
  if (!modLoader) return;
  const mod = await modLoader();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const queryFn = mod[`query${type.charAt(0).toUpperCase() + type.slice(1)}Stats`] as ((...args: any[]) => any) | undefined;
  if (!queryFn) return;

  const { getOrCompute } = await import('@/lib/cache/get-or-compute');
  const { buildCacheKey } = await import('@/lib/cache/keys');

  await Promise.allSettled(
    popularCombos.map(combo =>
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      getOrCompute(buildCacheKey(type, combo as any), () => queryFn(combo), { ttl: 7200 }),
    ),
  );
}
