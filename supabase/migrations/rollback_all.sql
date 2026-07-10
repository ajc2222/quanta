-- Rollback all migrations (reverse order as specified in plan section 8)
-- Run manually via SQL if needed. Only use for full schema teardown.

DROP TABLE IF EXISTS report_gex_stats;
DROP TABLE IF EXISTS report_macro_stats;
DROP TABLE IF EXISTS report_news_candle_stats;
DROP TABLE IF EXISTS report_opening_gap_stats;
DROP TABLE IF EXISTS report_keyopen_stats;
DROP TABLE IF EXISTS report_po3_stats;
DROP TABLE IF EXISTS report_liquidity_stats;
DROP TABLE IF EXISTS report_ob_stats;
DROP TABLE IF EXISTS report_fvg_stats;
DROP TABLE IF EXISTS gex_levels_daily;
DROP TABLE IF EXISTS options_chain_snapshots;
DROP TABLE IF EXISTS macro_instances;
DROP TABLE IF EXISTS news_candle_instances;
DROP TABLE IF EXISTS opening_gap_instances;
DROP TABLE IF EXISTS key_opens;
DROP TABLE IF EXISTS po3_phase_labels;
DROP TABLE IF EXISTS po3_instances;
DROP TABLE IF EXISTS liquidity_levels;
DROP TABLE IF EXISTS order_block_instances;
DROP TABLE IF EXISTS fvg_instances;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS news_events;
DROP TABLE IF EXISTS ohlcv_1m CASCADE;
DROP TABLE IF EXISTS admin_users;
DROP FUNCTION IF EXISTS public.is_admin;
DROP FUNCTION IF EXISTS public.ensure_ohlcv_partition;
