import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FiFileText, FiImage, FiRefreshCw, FiShield } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { AnalysisMetric } from "@/components/molecules/AnalysisMetric";
import { ImageClassificationPanel } from "@/features/scan/components/ImageClassificationPanel";
import { VerdictBadge } from "@/features/scan/components/VerdictBadge";
import { percentScore, VERDICT_PRESENTATION } from "@/features/scan/domain/scanPresentation";
import { getElaHeatmap } from "@/api/client";
import { InfoTip } from "@/components/molecules/InfoTip";

function EvidencePreview({ previewUrl, fileName }) {
  if (previewUrl) return <img src={previewUrl} alt="Evidencia original analizada" className="h-full min-h-64 w-full object-contain" />;
  return <div className="flex min-h-64 flex-col items-center justify-center bg-secondary text-white/80"><FiFileText className="text-6xl" /><span className="mt-3 max-w-64 truncate px-4 text-xs">{fileName}</span></div>;
}

function SignalCard({ label, score, unavailableText = "No aplicable", explanation }) {
  const percentage = percentScore(score);
  return (
    <div className="rounded-2xl border border-border-soft bg-slate-50 p-4">
      <p className="flex items-center text-[10px] font-bold uppercase tracking-wide text-text-soft">
        {label}<InfoTip title={`Cómo interpretar ${label}`}>{explanation}</InfoTip>
      </p>
      <strong className="mt-2 block text-2xl text-secondary">{percentage == null ? "—" : `${percentage}%`}</strong>
      <p className="mt-1 text-[10px] text-text-soft">{percentage == null ? unavailableText : "Nivel de anomalía detectado"}</p>
    </div>
  );
}

export default function AdvancedScanResult({ file, mode, result, onReset }) {
  const [previewUrl, setPreviewUrl] = useState("");
  const [elaHeatmapUrl, setElaHeatmapUrl] = useState("");
  const isImage = file?.type?.startsWith("image/");
  const presentation = VERDICT_PRESENTATION[result.verdict] || VERDICT_PRESENTATION.SUSPICIOUS;
  const imageAnalysis = result.imageAnalysis;

  useEffect(() => {
    if (!isImage || !(file instanceof Blob)) return undefined;
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file, isImage]);

  useEffect(() => {
    const artifactId = result.artifacts?.find((artifact) => artifact.type === "IMAGE" && artifact.analysis)?.artifactId;
    if (!artifactId || result.detailLevel !== "full") return undefined;

    let objectUrl = "";
    getElaHeatmap(result.jobId, artifactId)
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        setElaHeatmapUrl(objectUrl);
      })
      .catch(() => setElaHeatmapUrl(""));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [result.artifacts, result.detailLevel, result.jobId]);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <header className="flex flex-col gap-3 rounded-2xl border border-border-soft bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2"><h2 className="truncate text-xl font-extrabold text-secondary">{file?.name || "evidencia-digital"}</h2><Badge variant="neutral">{mode}</Badge></div>
          <p className="mt-1 text-xs text-text-soft">Job {result.jobId} · Reporte técnico autenticado</p>
        </div>
        <VerdictBadge verdict={result.verdict} />
      </header>

      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-text-soft">Veredicto consolidado</p>
          <div className={`mt-4 flex items-center gap-3 ${presentation.tone}`}><FiShield className="text-4xl" /><strong className="text-2xl">{presentation.label}</strong></div>
          <p className="mt-3 text-xs leading-5 text-text-soft">{result.summary}</p>
          <div className="mt-6 space-y-5">
            <AnalysisMetric label="Autenticidad estimada" value={result.authenticityPercentage}
              explanation={<><p>Es 100% menos el riesgo forense. No es una probabilidad científica de autenticidad.</p><p>Un valor alto significa que se encontraron menos señales de riesgo.</p></>} />
            <AnalysisMetric label="Riesgo forense" value={result.riskPercentage} tone="risk"
              explanation={<><p>Combina 70% de señales técnicas y 30% de flags de IA. IA generada/modificada tiene un mínimo de 75%; edición/composición, 40%.</p><p><strong>0–39%:</strong> sin riesgo crítico. <strong>40–70%:</strong> revisión recomendada. <strong>71–100%:</strong> alto riesgo.</p></>} />
          </div>
          <div className="mt-6 rounded-2xl bg-background p-3 text-xs">
            <p className="font-semibold text-secondary">Cómo se combinaron las evidencias</p>
            <p className="mt-1 font-semibold text-primary">{result.policyPresentation.label}</p>
            <p className="mt-1 text-[10px] leading-4 text-text-soft">{result.policyPresentation.description}</p>
          </div>
        </section>

        <section className="overflow-hidden rounded-3xl border border-border-soft bg-tertiary/50 p-4">
          <p className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-primary"><FiImage /> Evidencia original</p>
          <div className="overflow-hidden rounded-2xl bg-slate-950"><EvidencePreview previewUrl={previewUrl} fileName={file?.name} /></div>
        </section>
      </div>

      {imageAnalysis && <ImageClassificationPanel analysis={imageAnalysis} />}

      {imageAnalysis && (
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <h3 className="font-bold text-secondary">Señales técnicas reales</h3>
          <p className="mt-1 text-xs text-text-soft">Los porcentajes representan anomalía de cada técnica, no probabilidad directa de IA.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <SignalCard label="Metadatos EXIF" score={imageAnalysis.exif_score} explanation={<><p>Heurística acumulativa: sin EXIF +20%; software de edición +45%; fechas distintas +35%; fecha original eliminada +15%.</p><p>No tener EXIF no prueba manipulación.</p></>} />
            <SignalCard label="Análisis ELA" score={imageAnalysis.ela_score} explanation={<><p>Diferencia media tras recomprimir como JPEG, dividida para 25 y limitada a 100%.</p><p>No tiene intervalos de veredicto propios: es una señal continua y debe leerse junto al mapa.</p></>} />
            <SignalCard label="DCT / Benford" score={imageAnalysis.dct_benford_score} unavailableText={imageAnalysis.benford_applicable === false ? "No aplicable al formato" : "Sin resultado"} explanation={<><p>Solo aplica a JPEG. Compara coeficientes DCT con la distribución de Benford.</p><p>Distancia 0 = 0%; distancia 0.30 o mayor = 100%. No es probabilidad de fraude.</p></>} />
          </div>
        </section>
      )}


      {imageAnalysis && elaHeatmapUrl && (
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <h3 className="flex items-center font-bold text-secondary">Mapa de calor ELA
            <InfoTip title="Cómo leer el mapa ELA">
              <p><strong>Azul:</strong> diferencia baja. <strong>Verde/amarillo:</strong> intermedia. <strong>Rojo:</strong> alta tras recomprimir.</p>
              <p>Compare cada región con su entorno. Bordes, texto, ruido y múltiples guardados también pueden iluminarse; no demuestra fraude por sí solo.</p>
            </InfoTip>
          </h3>
          <p className="mt-1 text-xs leading-5 text-text-soft">
            Resalta diferencias de recompresión. Las zonas más intensas indican errores de compresión distintos al entorno; pueden orientar una revisión, pero no prueban por sí solas que exista edición o fraude.
          </p>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <figure className="overflow-hidden rounded-2xl bg-slate-950">
              <img src={previewUrl} alt="Imagen original analizada" className="h-full min-h-64 w-full object-contain" />
              <figcaption className="bg-slate-900 px-3 py-2 text-center text-[10px] text-white/70">Original</figcaption>
            </figure>
            <figure className="overflow-hidden rounded-2xl bg-slate-950">
              <img src={elaHeatmapUrl} alt="Mapa de diferencias de recompresión ELA" className="h-full min-h-64 w-full object-contain" />
              <figcaption className="bg-slate-900 px-3 py-2 text-center text-[10px] text-white/70">Diferencias ELA amplificadas</figcaption>
            </figure>
          </div>
        </section>
      )}

      {!imageAnalysis && (
        <section className="rounded-3xl border border-border-soft bg-white p-5 text-sm text-text-soft">
          Este artefacto no contiene análisis visual. Los detalles disponibles dependen del tipo de archivo procesado.
        </section>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 text-xs text-text-soft">
        <span>{result.completedAt ? `Completado: ${new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeStyle: "short" }).format(new Date(result.completedAt))}` : "Análisis completado"}</span>
        <Button type="button" variant="outline" onClick={onReset}><FiRefreshCw /> Analizar otro archivo</Button>
      </footer>
    </motion.div>
  );
}
