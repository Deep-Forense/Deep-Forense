import { FiLock } from "react-icons/fi";

export default function LockedInsight({ label }) {
  return (
    <div className="flex min-h-14 items-center gap-2 rounded-xl border border-border-soft bg-slate-50 px-3 py-2 text-xs text-slate-400">
      <FiLock className="shrink-0 text-sm" />
      <span>{label}</span>
    </div>
  );
}
