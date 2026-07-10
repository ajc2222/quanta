import { supabase } from '@/lib/supabase/client';
import type { ReportQuery } from './types';

export function buildReportQuery(
  table: string,
  { instrument, lookback }: ReportQuery,
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let query = (supabase as any).from(table).select('*');

  if (instrument && instrument !== 'all') {
    query = query.eq('instrument', instrument.toUpperCase());
  }

  if (lookback && lookback !== 'all') {
    if (['3mo', '6mo', '1yr'].includes(lookback)) {
      query = query.eq('lookback_days', lookback);
    } else if (lookback.includes(',')) {
      // Custom range: apply as computed_at filter
      const [start] = lookback.split(',');
      if (start) query = query.gte('computed_at', start);
    }
  }

  return query;
}

export async function fetchAllReportRows<T>(
  table: string,
  query: ReportQuery,
): Promise<{ rows: T[]; count: number }> {
  const dbQuery = buildReportQuery(table, query);
  const { data, error, count } = await (dbQuery as any)
    .select('*', { count: 'exact' });

  if (error) throw error;
  return { rows: (data ?? []) as T[], count: count ?? 0 };
}

export function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function groupBy<T extends Record<string, any>, R>(
  rows: T[],
  key: keyof T,
  fn: (group: T[]) => R,
): any[] {
  const groups: Record<string, T[]> = {};
  for (const r of rows) {
    const k = String(r[key]);
    if (!groups[k]) groups[k] = [];
    groups[k].push(r);
  }
  return Object.entries(groups).map(([k, g]) => ({ [key]: k, ...fn(g) }));
}
