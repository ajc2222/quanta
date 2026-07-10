import type { StatCardData } from '../../types';

const STATUS_CONFIG = {
  healthy: { dot: 'bg-green', text: 'text-green', label: 'HEALTHY' },
  low: { dot: 'bg-amber', text: 'text-amber', label: 'LOW' },
  warning: { dot: 'bg-red', text: 'text-red', label: 'WARNING' },
} as const;

export default function StatCard({ label, value, secondary, status }: StatCardData) {
  return (
    <div className="bg-surface border border-border p-4">
      <div className="text-[10px] uppercase tracking-wider text-muted mb-2">{label}</div>
      <div className="text-4xl font-bold text-text-highlight font-mono leading-none mb-2">
        {value}
      </div>
      {(secondary || status) && (
        <div className="flex items-center gap-2 min-h-[16px]">
          {secondary && <span className="text-[11px] text-muted">{secondary}</span>}
          {status && (
            <span className="flex items-center gap-1.5 text-[11px]">
              <span className={`inline-block w-2 h-2 rounded-full ${STATUS_CONFIG[status].dot}`} />
              <span className={`${STATUS_CONFIG[status].text} font-medium`}>
                {STATUS_CONFIG[status].label}
              </span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
