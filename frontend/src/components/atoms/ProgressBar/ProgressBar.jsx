export default function ProgressBar({ value, tone = "primary", label }) {
  const safeValue = Math.min(100, Math.max(0, value));
  const tones = {
    primary: "bg-primary",
    risk: "bg-gradient-to-r from-emerald-500 via-amber-400 to-red-500",
  };

  return (
    <div
      className="h-2 overflow-hidden rounded-full bg-slate-200"
      role="progressbar"
      aria-label={label}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={safeValue}
    >
      <div
        className={`h-full rounded-full transition-all duration-700 ${tones[tone]}`}
        style={{ width: `${safeValue}%` }}
      />
    </div>
  );
}
