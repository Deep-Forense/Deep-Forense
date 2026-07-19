import { FiClock, FiEye } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { Pagination } from "@/components/molecules/Pagination";

const statusVariant = {
  COMPLETED: "success",
  PROCESSING: "warning",
  FAILED: "danger",
};

const verdictConfig = {
  APPROVED: { label: "Sin riesgo crítico", variant: "success" },
  REJECTED: { label: "Fraudulento", variant: "danger" },
  SUSPICIOUS: { label: "Requiere revisión", variant: "warning" },
  INCONCLUSIVE: { label: "Análisis incompleto", variant: "warning" },
  PENDING: { label: "Pendiente", variant: "warning" },
  FAILED: { label: "Fallido", variant: "danger" },
};

export default function ScanHistoryTable({
  jobs,
  loading = false,
  error = "",
  onRetry,
  onViewDetail,
  page = 1,
  pageSize = 10,
  total = 0,
  onPageChange,
}) {
  return (
    <section className="overflow-hidden rounded-3xl border border-border-soft bg-white shadow-lg shadow-secondary/5">
      <div className="flex flex-col gap-2 border-b border-border-soft bg-slate-50/80 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-bold text-secondary">
            <FiClock className="text-primary" /> Últimos análisis procesados
          </h2>
          <p className="mt-1 text-xs text-text-soft">Historial de trabajos forenses asociados a tu cuenta.</p>
        </div>
        <button type="button" onClick={onRetry} className="text-xs font-bold text-primary hover:underline">Actualizar</button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[780px] text-left text-xs">
          <thead className="border-b border-border-soft bg-background text-[10px] uppercase tracking-wide text-text-soft">
            <tr>
              <th className="px-5 py-3 font-semibold">Nombre del archivo</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Estado</th>
              <th className="px-4 py-3 font-semibold">Autenticidad</th>
              <th className="px-4 py-3 font-semibold">Riesgo</th>
              <th className="px-4 py-3 font-semibold">Veredicto</th>
              <th className="px-4 py-3 text-center font-semibold">Detalle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-soft">
            {(loading || error || jobs.length === 0) && (
              <tr>
                <td colSpan="7" className="px-5 py-8 text-center text-sm text-text-soft">
                  {loading ? "Cargando historial..." : error || "Todavía no tienes análisis registrados."}
                </td>
              </tr>
            )}
            {jobs.map((job) => {
              const verdict = verdictConfig[job.verdict] || verdictConfig.PENDING;
              return (
                <tr key={job.jobId} className="transition hover:bg-tertiary/30">
                  <td className="px-5 py-4">
                    <p className="max-w-52 truncate font-semibold text-secondary">{job.fileName}</p>
                    <p className="mt-1 text-[10px] text-text-soft">{job.createdAt} · {job.jobId}</p>
                  </td>
                  <td className="px-4 py-4 text-text-soft">{job.artifactType}</td>
                  <td className="px-4 py-4"><Badge variant={statusVariant[job.status] || "neutral"}>{job.status}</Badge></td>
                  <td className="px-4 py-4 font-bold text-secondary">{job.authenticityPercentage == null ? "—" : `${job.authenticityPercentage}%`}</td>
                  <td className="px-4 py-4 font-bold text-secondary">{job.riskPercentage == null ? "—" : `${job.riskPercentage}%`}</td>
                  <td className="px-4 py-4"><Badge variant={verdict.variant}>{verdict.label}</Badge></td>
                  <td className="px-4 py-4 text-center">
                    <button
                      type="button"
                      aria-label={`Ver ${job.fileName}`}
                      onClick={() => onViewDetail?.(job)}
                      className="rounded-lg p-2 text-text-soft transition hover:bg-tertiary hover:text-primary"
                    >
                      <FiEye />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {!loading && !error && jobs.length > 0 && (
        <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange} itemLabel="análisis" />
      )}
    </section>
  );
}
