import { FiImage } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { severityFromScore } from "@/features/scan/domain/scanPresentation";

export default function HeatmapViewer({ heatmapUrl, label = "Mapa de calor ELA", score, isPreview = false }) {
  const severity = severityFromScore(score);

  return (
    <div className="overflow-hidden rounded-2xl border border-border-soft bg-slate-50">
      <div className="flex items-center justify-between gap-2 px-4 pt-4">
        <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-text-soft">
          <FiImage className="text-primary" /> {label}
        </p>
        <div className="flex items-center gap-2">
          {isPreview && <Badge variant="neutral">Vista previa · dato de ejemplo</Badge>}
          <Badge variant={severity.variant}>{severity.label}</Badge>
        </div>
      </div>
      <div className="relative mt-3 aspect-video w-full bg-slate-950">
        {heatmapUrl ? (
          <img src={heatmapUrl} alt={label} className="h-full w-full object-contain" />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-white/60">
            Mapa de calor no disponible
          </div>
        )}
        {isPreview && heatmapUrl && (
          <p className="pointer-events-none absolute inset-x-0 bottom-0 bg-black/60 px-3 py-1.5 text-center text-[10px] font-semibold text-white/90">
            Imagen de ejemplo — no es el análisis real de este archivo (backend aún no genera el heatmap)
          </p>
        )}
      </div>
    </div>
  );
}
