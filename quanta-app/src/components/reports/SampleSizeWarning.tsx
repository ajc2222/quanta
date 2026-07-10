interface SampleSizeWarningProps {
  sampleSize: number;
}

export default function SampleSizeWarning({ sampleSize }: SampleSizeWarningProps) {
  if (sampleSize >= 30) return null;

  return (
    <div className="border-l-4 border-amber bg-amber/5 rounded px-4 py-3 mt-4">
      <p className="text-[13px] text-amber flex items-center gap-2">
        <span>&#9888;</span>
        <span>Low sample size (n={sampleSize}) &mdash; treat this stat with caution</span>
      </p>
    </div>
  );
}
