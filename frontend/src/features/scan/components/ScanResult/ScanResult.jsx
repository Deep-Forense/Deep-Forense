import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FiFileText,
  FiImage,
  FiInfo,
  FiLock,
  FiRefreshCw,
} from "react-icons/fi";
import { Button } from "@/components/atoms/Button";
import { AnalysisMetric } from "@/components/molecules/AnalysisMetric";
import { LockedInsight } from "@/components/molecules/LockedInsight";
import { VerdictBadge } from "@/features/scan/components/VerdictBadge";
import { paths } from "@/routes/paths";

const lockedInsights = ["Análisis OCR", "Mapa ELA", "Texto extraído", "Regiones sospechosas"];

export default function ScanResult({ file, mode, result, onReset }) {
  const navigate = useNavigate();
  const [previewUrl, setPreviewUrl] = useState("");
  const isImage = file?.type?.startsWith("image/");
  const FileIcon = mode === "image" ? FiImage : FiFileText;

  useEffect(() => {
    if (!isImage || !(file instanceof Blob)) return undefined;
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file, isImage]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-3xl border border-border-soft bg-white"
    >
      <div className="flex flex-col gap-3 border-b border-border-soft bg-slate-50/80 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <FileIcon className="shrink-0 text-lg text-primary" />
          <div className="min-w-0">
            <h3 className="font-bold text-secondary">Resultado rápido del análisis</h3>
            <p className="truncate text-xs text-text-soft">{file?.name || "Archivo de demostración"}</p>
          </div>
        </div>
        <VerdictBadge verdict={result.verdict} />
      </div>

      <div className="grid gap-6 p-5 md:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-4">
          <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-2xl bg-secondary">
            {previewUrl ? (
              <img src={previewUrl} alt="Vista previa del archivo analizado" className="h-full w-full object-cover" />
            ) : (
              <div className="text-center text-white/80">
                <FiFileText className="mx-auto text-5xl" />
                <p className="mt-3 max-w-48 truncate px-4 text-xs">{file?.name}</p>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-primary/15 bg-tertiary/70 p-4">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-primary">
              <FiInfo /> Resumen técnico
            </div>
            <p className="text-xs italic leading-5 text-secondary">“{result.summary}”</p>
          </div>
        </div>

        <div className="flex flex-col">
          <div className="space-y-5">
            <AnalysisMetric
              label="Autenticidad estimada"
              value={result.authenticityPercentage}
              hint="Complemento del riesgo; no prueba autenticidad"
              explanation={<><p>Se calcula como 100% menos el riesgo forense.</p><p>Un valor alto significa menos señales detectadas, no certeza de autenticidad.</p></>}
            />
            <AnalysisMetric
              label="Riesgo forense"
              value={result.riskPercentage}
              tone="risk"
              hint="Interprete el porcentaje antes de tomar decisiones"
              explanation={<><p><strong>0–39%:</strong> sin riesgo crítico. <strong>40–70%:</strong> revisión recomendada. <strong>71–100%:</strong> alto riesgo.</p><p>Combina señales técnicas y flags de IA.</p></>}
            />
          </div>

          <div className="mt-5 rounded-2xl bg-background p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-text-soft">Modelo utilizado</p>
            <p className="mt-1 text-xs font-semibold text-secondary">{result.model}</p>
            <p className="mt-1 text-[10px] text-text-soft">{result.policyPresentation.label}</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {lockedInsights.map((insight) => <LockedInsight key={insight} label={insight} />)}
          </div>

          <div className="mt-5 border-t border-border-soft pt-5">
            <div className="mb-4 flex gap-2 text-xs leading-5 text-text-soft">
              <FiLock className="mt-0.5 shrink-0" />
              <p>Inicia sesión para consultar evidencia técnica, flags, trazabilidad y el detalle por artefacto.</p>
            </div>
            <Button type="button" className="w-full" variant="secondary" onClick={() => navigate(paths.login)}>
              Iniciar sesión para ver detalles
            </Button>
            <button type="button" onClick={() => navigate(paths.register)} className="mt-3 w-full text-xs font-semibold text-primary hover:underline">
              Crear cuenta gratis
            </button>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border-soft px-5 py-3 text-[10px] text-text-soft">
        <span>Job: {result.jobId} · Vista {result.detailLevel}</span>
        <button type="button" onClick={onReset} className="inline-flex items-center gap-1.5 font-semibold text-primary hover:underline">
          <FiRefreshCw /> Analizar otro archivo
        </button>
      </div>
    </motion.div>
  );
}
