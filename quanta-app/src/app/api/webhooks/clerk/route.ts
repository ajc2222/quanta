import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';
import { supabase } from '@/lib/supabase/client';

export async function POST(request: NextRequest) {
  const SIGNING_SECRET = process.env.CLERK_WEBHOOK_SECRET!;
  if (!SIGNING_SECRET) {
    return NextResponse.json({ error: 'Missing webhook secret' }, { status: 500 });
  }

  const wh = new Webhook(SIGNING_SECRET);
  const payload = await request.text();
  const svixId = request.headers.get('svix-id');
  const svixTimestamp = request.headers.get('svix-timestamp');
  const svixSignature = request.headers.get('svix-signature');

  if (!svixId || !svixTimestamp || !svixSignature) {
    return NextResponse.json({ error: 'Missing svix headers' }, { status: 400 });
  }

  let evt: { type: string; data: Record<string, unknown> };
  try {
    evt = wh.verify(payload, {
      'svix-id': svixId,
      'svix-timestamp': svixTimestamp,
      'svix-signature': svixSignature,
    }) as typeof evt;
  } catch {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  if (evt.type === 'user.created' || evt.type === 'user.updated') {
    const clerkId = evt.data.id as string;
    const email = ((evt.data.email_addresses as Array<{ email_address: string }>)?.[0]?.email_address) ?? '';
    const isAdmin = checkIfAdmin(email);
    if (isAdmin) {
      await supabase.from('admin_users').upsert(
        { clerk_id: clerkId, email, role: 'admin' },
        { onConflict: 'clerk_id' },
      );
    }
  }

  if (evt.type === 'user.deleted') {
    const clerkId = evt.data.id as string;
    await supabase.from('admin_users').delete().eq('clerk_id', clerkId);
  }

  return NextResponse.json({ success: true });
}

function checkIfAdmin(email: string): boolean {
  const admins = (process.env.ADMIN_EMAILS ?? '').split(',').map(e => e.trim().toLowerCase());
  return admins.includes(email.toLowerCase());
}
