import { FiLoader } from "react-icons/fi";
import { JobTimeline } from "@/features/scan/components/JobTimeline";

export default function JobProgress({ events, fileName }) {
  return (
    <div className="rounded-3xl border border-border-soft bg-white p-6">
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-secondary text-white">
          <FiLoader className="animate-spin text-xl" />
        </span>
        <div className="min-w-0">
          <h3 className="font-bold text-secondary">Analizando evidencia...</h3>
          <p className="truncate text-sm text-text-soft">{fileName || "Procesando tu solicitud"}</p>
        </div>
      </div>
      <div className="mt-6">
        <JobTimeline events={events} />
      </div>
    </div>
  );
}
