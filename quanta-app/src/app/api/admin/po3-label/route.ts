import { NextRequest, NextResponse } from 'next/server';
import { requireAdmin, badRequest, internalError } from '../../helpers';

export async function POST(request: NextRequest) {
  const adminError = await requireAdmin();
  if (adminError) return adminError;

  try {
    const body = await request.json();
    const { instanceId, phase } = body;

    if (!instanceId || !phase) {
      return badRequest('instanceId and phase are required');
    }

    if (!['bullish', 'bearish', 'exclude'].includes(phase)) {
      return badRequest('phase must be bullish, bearish, or exclude');
    }

    const { supabase } = await import('@/lib/supabase/client');

    if (phase === 'exclude') {
      const { error } = await supabase
        .from('po3_unconfirmed')
        .update({ excluded: true })
        .eq('id', instanceId);
      if (error) throw error;
    } else {
      const { data: instance, error: fetchError } = await supabase
        .from('po3_unconfirmed')
        .select('*')
        .eq('id', instanceId)
        .single();
      if (fetchError) throw fetchError;
      if (!instance) return badRequest('Instance not found');

      const { error: insertError } = await supabase
        .from('po3_confirmed')
        .insert({
          instrument: instance.instrument,
          trade_date: instance.trade_date,
          window: instance.window,
          open: instance.open,
          hod: instance.hod,
          lod: instance.lod,
          phase,
          labeled_by: instance.assigned_admin,
        });
      if (insertError) throw insertError;

      await supabase.from('po3_unconfirmed').delete().eq('id', instanceId);
    }

    // Invalidate PO3 cache
    const { redis } = await import('@/lib/cache/client');
    const { buildTypePrefix } = await import('@/lib/cache/keys');
    let cursor = '0';
    const keys: string[] = [];
    do {
      const [nextCursor, batch] = await redis.scan(cursor, { match: buildTypePrefix('po3'), count: 100 });
      cursor = nextCursor;
      keys.push(...batch);
    } while (cursor !== '0');
    if (keys.length > 0) await redis.del(...keys);

    return NextResponse.json({ success: true });
  } catch (error) {
    return internalError(error);
  }
}
