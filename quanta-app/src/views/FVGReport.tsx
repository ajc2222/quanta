'use client'
import { useState } from 'react';
import FilterBar from '../components/layout/FilterBar';
import StatCard from '../components/reports/StatCard';
import DataTable from '../components/reports/DataTable';
import SubreportTabs from '../components/reports/SubreportTabs';
import SampleSizeWarning from '../components/reports/SampleSizeWarning';
import type { DataTableColumn, DataRow, SubreportTab } from '../types';

const TABS: SubreportTab[] = [
  { id: 'weekday', label: 'By Weekday' },
  { id: 'size', label: 'By Size' },
  { id: 'session', label: 'By Session' },
  { id: 'news', label: 'By News Day' },
  { id: 'htf', label: 'By HTF Phase' },
];

const COLUMNS: DataTableColumn[] = [
  { key: 'day', label: 'Day' },
  { key: 'fillRate', label: 'Fill Rate', align: 'right', renderBar: true },
  { key: 'sample', label: 'Sample', align: 'right' },
];

const ROWS: DataRow[] = [
  { day: 'Mon', fillRate: 78.4, sample: 82 },
  { day: 'Tue', fillRate: 71.2, sample: 79 },
  { day: 'Wed', fillRate: 82.1, sample: 88 },
  { day: 'Thu', fillRate: 69.4, sample: 71 },
  { day: 'Fri', fillRate: 61.3, sample: 83 },
];

const LOW_N_ROWS: DataRow[] = [
  { day: 'Mon', fillRate: 55.0, sample: 5 },
  { day: 'Tue', fillRate: 60.0, sample: 4 },
  { day: 'Wed', fillRate: 72.0, sample: 6 },
  { day: 'Thu', fillRate: 48.0, sample: 3 },
  { day: 'Fri', fillRate: 50.0, sample: 5 },
];

export default function FVGReport() {
  const [activeTab, setActiveTab] = useState('weekday');
  /* ponytail: static sample data, wire to API when data fetching layer lands */

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-lg font-semibold text-text-highlight">Fair Value Gaps</h1>

      <FilterBar />

      {/* Row 1: Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Fill Rate" value="74.2%" secondary="n=403" status="healthy" />
        <StatCard label="Avg Fill Time" value="1h 22m" />
        <StatCard label="Partial Fill" value="18.6%" status="low" />
        <StatCard label="Sample Size" value="n=403" status="healthy" />
      </div>

      {/* Row 2: Subreport tabs */}
      <SubreportTabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Row 3: Chart + Table */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface border border-border flex items-center justify-center text-muted text-[13px] font-mono" style={{ minHeight: 260 }}>
          Chart area
        </div>
        <div className="bg-surface border border-border p-3">
          <DataTable columns={COLUMNS} rows={ROWS} />
        </div>
      </div>

      {/* Sample size warning (shown with low n example) */}
      <SampleSizeWarning sampleSize={403} />
      <SampleSizeWarning sampleSize={17} />
    </div>
  );
}
