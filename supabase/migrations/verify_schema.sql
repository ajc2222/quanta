-- Schema verification script for Quanta
-- Run against the database after migrations to verify all tables, indexes, and RLS

-- 1. Verify all 24 tables exist
SELECT 'table_check' AS check_name, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 2. Verify partitioned table structure
SELECT 'partition_check' AS check_name, inhrelid::regclass::text AS tablename
FROM pg_inherits WHERE inhparent = 'ohlcv_1m'::regclass;

-- 3. Count all indexes
SELECT 'index_check' AS check_name, indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 4. Verify RLS is enabled on all tables
SELECT 'rls_check' AS check_name, relname AS table_name,
       relrowsecurity AS rls_enabled,
       relforcerowsecurity AS rls_forced
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relkind = 'r'
  AND relname NOT LIKE 'ohlcv_1m_%'
ORDER BY relname;

-- 5. Verify all RLS policies
SELECT 'policy_check' AS check_name, schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- 6. Verify functions exist
SELECT 'function_check' AS check_name, proname, prosrc
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
  AND proname IN ('is_admin', 'ensure_ohlcv_partition');

-- 7. Verify extensions
SELECT 'extension_check' AS check_name, extname, extversion
FROM pg_extension
WHERE extname IN ('pgcrypto', 'uuid-ossp');
