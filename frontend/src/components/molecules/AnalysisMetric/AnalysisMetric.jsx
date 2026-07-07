import { ProgressBar } from "@/components/atoms/ProgressBar";

export default function AnalysisMetric({ label, value, tone = "primary", hint }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4 text-xs">
        <span className="font-medium text-secondary">{label}</span>
        <strong className={tone === "risk" ? "text-amber-600" : "text-primary"}>
          {value}%
        </strong>
      </div>
      <ProgressBar value={value} tone={tone} label={label} />
      {hint && <p className="mt-1.5 text-[10px] text-text-soft">{hint}</p>}
    </div>
  );
}
