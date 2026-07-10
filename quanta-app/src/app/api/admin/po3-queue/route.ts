import { NextRequest, NextResponse } from 'next/server';
import { requireAdmin, internalError } from '../../helpers';

export async function GET(request: NextRequest) {
  const adminError = await requireAdmin();
  if (adminError) return adminError;

  try {
    const { supabase } = await import('@/lib/supabase/client');
    const { searchParams } = request.nextUrl;

    let query = supabase
      .from('po3_unconfirmed')
      .select('*')
      .order('trade_date', { ascending: false })
      .limit(50);

    const instrument = searchParams.get('instrument');
    if (instrument) query = query.eq('instrument', instrument.toUpperCase());

    const { data, error } = await query;
    if (error) throw error;

    return NextResponse.json({ data, total: data?.length ?? 0 });
  } catch (error) {
    return internalError(error);
  }
}
