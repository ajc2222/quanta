'use client'

export default function ReportPlaceholder({ params }: { params: Promise<{ slug: string }> }) {
  return (
    <div className="flex items-center justify-center h-64 text-muted font-mono text-sm">
      Report coming soon
    </div>
  )
}
