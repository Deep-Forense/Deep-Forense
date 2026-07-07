import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  FiActivity,
  FiCheckCircle,
  FiCpu,
  FiFileText,
  FiImage,
  FiRefreshCw,
  FiSearch,
  FiShield,
} from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { AnalysisMetric } from "@/components/molecules/AnalysisMetric";

const evidence = [
  { label: "Integridad EXIF", value: "0.88", note: "Metadatos consistentes", tone: "success" },
  { label: "Anomalía ELA", value: "0.28", note: "Sin regiones críticas", tone: "success" },
  { label: "Patrón DCT", value: "0.19", note: "Compresión estable", tone: "success" },
  { label: "Confianza OCR", value: "0.92", note: "Texto legible", tone: "primary" },
];

const timeline = [
  { icon: FiFileText, label: "Recibido", time: "14:32:01" },
  { icon: FiSearch, label: "OCR", time: "14:32:05" },
  { icon: FiImage, label: "ELA / DCT", time: "14:32:12" },
  { icon: FiCpu, label: "Scoring", time: "14:32:16" },
  { icon: FiCheckCircle, label: "Completado", time: "14:32:21" },
];

function EvidencePreview({ previewUrl, fileName }) {
  if (!previewUrl) {
    return (
      <div className="flex h-full min-h-56 flex-col items-center justify-center bg-secondary text-white/80">
        <FiFileText className="text-6xl" />
        <span className="mt-3 max-w-52 truncate px-4 text-xs">{fileName}</span>
      </div>
    );
  }
  return <img src={previewUrl} alt="Evidencia original analizada" className="h-full min-h-56 w-full object-cover" />;
}

export default function AdvancedScanResult({ file, mode, result, onReset }) {
  const [previewUrl, setPreviewUrl] = useState("");
  const isImage = file?.type?.startsWith("image/");

  useEffect(() => {
    if (!isImage) return undefined;
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file, isImage]);

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <header className="flex flex-col gap-3 rounded-2xl border border-border-soft bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-xl font-extrabold text-secondary">{file?.name || "evidencia-digital"}</h2>
            <Badge variant="neutral">{mode}</Badge>
          </div>
          <p className="mt-1 text-xs text-text-soft">Job {result.jobId} · Reporte técnico autenticado</p>
        </div>
        <Badge variant="success"><FiCheckCircle /> {result.verdict}</Badge>
      </header>

      <div className="grid gap-5 lg:grid-cols-[0.72fr_1.28fr]">
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-text-soft">Veredicto del análisis</p>
          <div className="mt-4 flex items-center gap-3 text-emerald-600">
            <FiShield className="text-4xl" />
            <div><strong className="text-2xl">Auténtico</strong><p className="text-xs text-text-soft">Riesgo forense bajo</p></div>
          </div>
          <div className="mt-6 space-y-5">
            <AnalysisMetric label="Autenticidad" value={result.authenticityPercentage} />
            <AnalysisMetric label="Riesgo de fraude" value={result.riskPercentage} tone="risk" />
          </div>
          <div className="mt-6 rounded-2xl bg-background p-3 text-xs">
            <p className="font-semibold text-secondary">Modelo y consolidación</p>
            <p className="mt-1 text-text-soft">{result.model}</p>
            <code className="mt-1 block text-[10px] text-primary">{result.policyApplied}</code>
          </div>
        </section>

        <section className="overflow-hidden rounded-3xl border border-border-soft bg-white">
          <div className="grid md:grid-cols-2">
            <div className="bg-tertiary/70 p-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-primary">Evidencia original</p>
              <div className="overflow-hidden rounded-2xl"><EvidencePreview previewUrl={previewUrl} fileName={file?.name} /></div>
            </div>
            <div className="p-4">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-primary">ELA · Error Level Analysis</p>
              <div className="relative overflow-hidden rounded-2xl bg-slate-950">
                {previewUrl ? (
                  <img src={previewUrl} alt="Mapa ELA simulado" className="h-56 w-full object-cover opacity-70 [filter:contrast(2.4)_saturate(2)_hue-rotate(155deg)]" />
                ) : (
                  <div className="flex h-56 items-center justify-center"><FiActivity className="text-6xl text-cyan-300" /></div>
                )}
                <span className="absolute bottom-3 left-3 rounded-full bg-emerald-500 px-3 py-1 text-[10px] font-bold text-white">Sin anomalías críticas</span>
              </div>
              <p className="mt-3 text-xs leading-5 text-text-soft">El mapa simulado no identifica diferencias severas de compresión ni regiones dominantes sospechosas.</p>
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <div className="flex items-center justify-between"><h3 className="font-bold text-secondary">Extracción y hallazgos técnicos</h3><Badge variant="success">Confianza 92%</Badge></div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <pre className="overflow-hidden whitespace-pre-wrap rounded-2xl border border-border-soft bg-slate-50 p-4 text-[10px] leading-5 text-secondary">{`[OCR] Archivo: ${file?.name}\nEstado: legible\nFecha detectada: 12/06/2024\nFirma digital: no encontrada\nResultado: revisión completada`}</pre>
            <div className="space-y-2">
              <div className="rounded-2xl bg-amber-50 p-3 text-xs text-amber-800"><strong>Compresión regional</strong><p className="mt-1">Variación leve dentro del rango esperado.</p></div>
              <div className="rounded-2xl bg-tertiary p-3 text-xs text-primary"><strong>Integridad de metadatos</strong><p className="mt-1">Origen y formato consistentes.</p></div>
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <h3 className="font-bold text-secondary">Vector de confianza</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {evidence.map((item) => (
              <div key={item.label} className="rounded-2xl bg-background p-3">
                <p className="text-[10px] text-text-soft">{item.label}</p>
                <strong className="mt-1 block text-xl text-primary">{item.value}</strong>
                <p className="mt-1 text-[9px] text-emerald-600">{item.note}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-3xl border border-border-soft bg-white p-5">
        <h3 className="text-xs font-bold uppercase tracking-wider text-text-soft">Línea de tiempo forense</h3>
        <div className="mt-5 grid grid-cols-5 gap-2">
          {timeline.map(({ icon: Icon, label, time }, index) => (
            <div key={label} className="relative text-center before:absolute before:left-0 before:right-0 before:top-5 before:h-px before:bg-border-soft first:before:left-1/2 last:before:right-1/2">
              <span className="relative z-10 mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white"><Icon /></span>
              <p className="mt-2 text-[10px] font-bold text-secondary">{label}</p><p className="text-[9px] text-text-soft">{time}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="flex justify-end"><Button type="button" variant="outline" onClick={onReset}><FiRefreshCw /> Analizar otro archivo</Button></div>
    </motion.div>
  );
}
