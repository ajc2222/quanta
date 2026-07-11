import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'http://localhost';
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? 'placeholder';

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: { persistSession: false },
});
