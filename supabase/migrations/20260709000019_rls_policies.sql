-- 20260709000019_rls_policies.sql

-- -- Enable RLS on all tables --
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ohlcv_1m ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE fvg_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_block_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE liquidity_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE po3_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE po3_phase_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE key_opens ENABLE ROW LEVEL SECURITY;
ALTER TABLE opening_gap_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_candle_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE options_chain_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE gex_levels_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_fvg_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_ob_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_liquidity_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_po3_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_keyopen_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_opening_gap_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_news_candle_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_macro_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_gex_stats ENABLE ROW LEVEL SECURITY;


-- -- Admin users table: only admins can read --
CREATE POLICY "admin_users_select_self"
    ON admin_users FOR SELECT
    USING (clerk_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "admin_users_select_admin"
    ON admin_users FOR SELECT
    USING (is_admin());


-- -- Read-only: authenticated users can SELECT all instance and report tables --
-- ohlcv_1m
CREATE POLICY "authenticated_select"
    ON ohlcv_1m FOR SELECT
    TO authenticated
    USING (true);

-- news_events
CREATE POLICY "authenticated_select"
    ON news_events FOR SELECT
    TO authenticated
    USING (true);

-- sessions
CREATE POLICY "authenticated_select"
    ON sessions FOR SELECT
    TO authenticated
    USING (true);

-- fvg_instances
CREATE POLICY "authenticated_select"
    ON fvg_instances FOR SELECT
    TO authenticated
    USING (true);

-- order_block_instances
CREATE POLICY "authenticated_select"
    ON order_block_instances FOR SELECT
    TO authenticated
    USING (true);

-- liquidity_levels
CREATE POLICY "authenticated_select"
    ON liquidity_levels FOR SELECT
    TO authenticated
    USING (true);

-- po3_instances
CREATE POLICY "authenticated_select"
    ON po3_instances FOR SELECT
    TO authenticated
    USING (true);

-- po3_phase_labels
CREATE POLICY "authenticated_select"
    ON po3_phase_labels FOR SELECT
    TO authenticated
    USING (true);

-- key_opens
CREATE POLICY "authenticated_select"
    ON key_opens FOR SELECT
    TO authenticated
    USING (true);

-- opening_gap_instances
CREATE POLICY "authenticated_select"
    ON opening_gap_instances FOR SELECT
    TO authenticated
    USING (true);

-- news_candle_instances
CREATE POLICY "authenticated_select"
    ON news_candle_instances FOR SELECT
    TO authenticated
    USING (true);

-- macro_instances
CREATE POLICY "authenticated_select"
    ON macro_instances FOR SELECT
    TO authenticated
    USING (true);

-- options_chain_snapshots
CREATE POLICY "authenticated_select"
    ON options_chain_snapshots FOR SELECT
    TO authenticated
    USING (true);

-- gex_levels_daily
CREATE POLICY "authenticated_select"
    ON gex_levels_daily FOR SELECT
    TO authenticated
    USING (true);

-- report_fvg_stats
CREATE POLICY "authenticated_select"
    ON report_fvg_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_ob_stats
CREATE POLICY "authenticated_select"
    ON report_ob_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_liquidity_stats
CREATE POLICY "authenticated_select"
    ON report_liquidity_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_po3_stats
CREATE POLICY "authenticated_select"
    ON report_po3_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_keyopen_stats
CREATE POLICY "authenticated_select"
    ON report_keyopen_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_opening_gap_stats
CREATE POLICY "authenticated_select"
    ON report_opening_gap_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_news_candle_stats
CREATE POLICY "authenticated_select"
    ON report_news_candle_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_macro_stats
CREATE POLICY "authenticated_select"
    ON report_macro_stats FOR SELECT
    TO authenticated
    USING (true);

-- report_gex_stats
CREATE POLICY "authenticated_select"
    ON report_gex_stats FOR SELECT
    TO authenticated
    USING (true);


-- -- Admin write access: po3_phase_labels --
CREATE POLICY "admin_insert_po3_labels"
    ON po3_phase_labels FOR INSERT
    TO authenticated
    WITH CHECK (is_admin());

CREATE POLICY "admin_update_po3_labels"
    ON po3_phase_labels FOR UPDATE
    TO authenticated
    USING (is_admin())
    WITH CHECK (is_admin());


-- -- Admin can UPDATE po3_instances.phase when a label is confirmed --
-- Application code should call admin_set_po3_phase() instead of UPDATE directly.
-- RLS alone cannot restrict which columns are updated; the SECURITY DEFINER
-- function provides that column-level control.
CREATE OR REPLACE FUNCTION public.admin_set_po3_phase(
    p_instance_id UUID,
    p_new_phase TEXT
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT is_admin() THEN
        RAISE EXCEPTION 'Permission denied: admin role required';
    END IF;

    UPDATE po3_instances
    SET phase = p_new_phase
    WHERE id = p_instance_id;
END;
$$;

DROP POLICY IF EXISTS admin_update_po3_phase ON po3_instances;

CREATE POLICY admin_update_po3_phase ON po3_instances
    FOR UPDATE TO authenticated
    USING (is_admin())
    WITH CHECK (is_admin());


-- -- Service role: full access (pipeline). Supabase service_role key bypasses RLS.
--    No explicit policy needed -- service_role is exempt by default when RLS is enabled.
