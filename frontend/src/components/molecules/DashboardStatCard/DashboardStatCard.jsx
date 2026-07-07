import { FiActivity, FiAlertTriangle, FiFolder } from "react-icons/fi";

const icons = { analyzed: FiFolder, risk: FiActivity, suspicious: FiAlertTriangle };

export default function DashboardStatCard({ id, label, value, trend, tone = "primary" }) {
  const Icon = icons[id] || FiActivity;
  const isDanger = tone === "danger";

  return (
    <article className="flex items-center gap-4 rounded-3xl border border-border-soft bg-white p-5 shadow-lg shadow-secondary/5">
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-xl ${isDanger ? "bg-red-50 text-red-500" : "bg-tertiary text-primary"}`}>
        <Icon />
      </div>
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-text-soft">{label}</p>
        <div className="mt-1 flex items-end gap-2">
          <strong className={`text-2xl font-extrabold ${isDanger ? "text-red-500" : "text-secondary"}`}>{value}</strong>
          <span className={`pb-1 text-[10px] font-bold ${isDanger ? "text-red-500" : "text-emerald-600"}`}>{trend}</span>
        </div>
      </div>
    </article>
  );
}
