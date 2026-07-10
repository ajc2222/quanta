interface TooltipPayloadEntry {
  color?: string
  name?: string
  value?: number | string
}

export default function ChartTooltip({ active, payload, label }: Record<string, any>) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#0A0A0F] border border-accent px-3 py-2 text-text-highlight font-mono text-[12px] shadow-lg">
      {label && <div className="text-muted text-[11px] font-sans mb-1">{label}</div>}
      {(payload as TooltipPayloadEntry[]).map((entry, i) => (
        <div key={i} className="flex items-center gap-2">
          {entry.color && (
            <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
          )}
          <span>
            {entry.name ? `${entry.name}: ` : ''}
            {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}
