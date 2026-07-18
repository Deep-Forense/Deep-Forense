import { ProgressBar } from "@/components/atoms/ProgressBar";
import { InfoTip } from "@/components/molecules/InfoTip";

export default function AnalysisMetric({ label, value, tone = "primary", hint, explanation }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4 text-xs">
        <span className="flex items-center font-medium text-secondary">
          {label}{explanation && <InfoTip title={`Cómo interpretar ${label}`}>{explanation}</InfoTip>}
        </span>
        <strong className={tone === "risk" ? "text-amber-600" : "text-primary"}>
          {value}%
        </strong>
      </div>
      <ProgressBar value={value} tone={tone} label={label} />
      {hint && <p className="mt-1.5 text-[10px] text-text-soft">{hint}</p>}
    </div>
  );
}
