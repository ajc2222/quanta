-- 20260709000002_admin_users.sql
CREATE TABLE admin_users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id    TEXT NOT NULL UNIQUE,          -- Clerk user ID
    email       TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('admin', 'superadmin')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active' CHECK (status IN ('active', 'disabled'));

CREATE INDEX idx_admin_users_clerk_id ON admin_users (clerk_id);

-- Helper function for RLS policies
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM admin_users
        WHERE clerk_id = current_setting('request.jwt.claims', true)::json->>'sub'
          AND role IN ('admin', 'superadmin')
          AND (status IS NULL OR status = 'active')
    );
$$
SET search_path = public;
