import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FiFileText, FiImage, FiRefreshCw, FiShield } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { Button } from "@/components/atoms/Button";
import { AnalysisMetric } from "@/components/molecules/AnalysisMetric";
import { HeatmapViewer } from "@/components/molecules/HeatmapViewer";
import { InfoTip } from "@/components/molecules/InfoTip";
import { ImageClassificationPanel } from "@/features/scan/components/ImageClassificationPanel";
import { VerdictBadge } from "@/features/scan/components/VerdictBadge";
import {
  FLAG_LABELS,
  percentScore,
  VERDICT_PRESENTATION,
} from "@/features/scan/domain/scanPresentation";
import { fetchElaHeatmapObjectUrl } from "@/features/scan/services/scan.service";

function EvidencePreview({ previewUrl, fileName }) {
  if (previewUrl)
    return (
      <img
        src={previewUrl}
        alt="Evidencia original analizada"
        className="h-full min-h-64 w-full object-contain"
      />
    );
  return (
    <div className="flex min-h-64 flex-col items-center justify-center bg-secondary text-white/80">
      <FiFileText className="text-6xl" />
      <span className="mt-3 max-w-64 truncate px-4 text-xs">{fileName}</span>
    </div>
  );
}

function SignalCard({
  label,
  score,
  unavailableText = "No aplicable",
  explanation,
}) {
  const percentage = percentScore(score);
  return (
    <div className="rounded-2xl border border-border-soft bg-slate-50 p-4">
      <p className="flex items-center text-[10px] font-bold uppercase tracking-wide text-text-soft">
        {label}
        <InfoTip title={`Cómo interpretar ${label}`}>{explanation}</InfoTip>
      </p>
      <strong className="mt-2 block text-2xl text-secondary">
        {percentage == null ? "—" : `${percentage}%`}
      </strong>
      <p className="mt-1 text-[10px] text-text-soft">
        {percentage == null ? unavailableText : "Nivel de anomalía detectado"}
      </p>
    </div>
  );
}

export default function AdvancedScanResult({
  file,
  mode,
  result,
  onReset,
  resetLabel = "Analizar otro archivo",
}) {
  const [previewUrl, setPreviewUrl] = useState("");
  const [realHeatmapUrl, setRealHeatmapUrl] = useState("");
  const [documentHeatmapUrl, setDocumentHeatmapUrl] = useState("");
  const isImage = file?.type?.startsWith("image/");
  const presentation =
    VERDICT_PRESENTATION[result.verdict] || VERDICT_PRESENTATION.SUSPICIOUS;
  const imageAnalysis = result.imageAnalysis;
  const documentAnalysis = result.documentAnalysis;
  const documentHeatmapPath = documentAnalysis?.document_visual_heatmap_url;
  const heatmapPath = imageAnalysis?.ela_heatmap_url;

  useEffect(() => {
    if (!isImage || !(file instanceof Blob)) return undefined;
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file, isImage]);

  useEffect(() => {
    if (!heatmapPath) {
      setRealHeatmapUrl("");
      return undefined;
    }

    let cancelled = false;
    let objectUrl = "";
    fetchElaHeatmapObjectUrl(heatmapPath).then(
      (url) => {
        if (cancelled) return;
        objectUrl = url;
        setRealHeatmapUrl(url);
      },
      () => {
        if (!cancelled) setRealHeatmapUrl("");
      },
    );

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [heatmapPath]);

  useEffect(() => {
    if (!documentHeatmapPath) {
      setDocumentHeatmapUrl("");
      return undefined;
    }
    let cancelled = false;
    let objectUrl = "";
    fetchElaHeatmapObjectUrl(documentHeatmapPath).then((url) => {
      if (!cancelled) { objectUrl = url; setDocumentHeatmapUrl(url); }
    }, () => { if (!cancelled) setDocumentHeatmapUrl(""); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentHeatmapPath]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5"
    >
      <header className="flex flex-col gap-3 rounded-2xl border border-border-soft bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-xl font-extrabold text-secondary">
              {file?.name || "evidencia-digital"}
            </h2>
            <Badge variant="neutral">{mode}</Badge>
          </div>
          <p className="mt-1 text-xs text-text-soft">
            Job {result.jobId} · Reporte técnico autenticado
          </p>
        </div>
        <VerdictBadge verdict={result.verdict} />
      </header>

      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-text-soft">
            Veredicto consolidado
          </p>
          <div className={`mt-4 flex items-center gap-3 ${presentation.tone}`}>
            <FiShield className="text-4xl" />
            <strong className="text-2xl">{presentation.label}</strong>
          </div>
          <p className="mt-3 text-xs leading-5 text-text-soft">
            {result.summary}
          </p>
          <div className="mt-6 space-y-5">
            <AnalysisMetric
              label="Autenticidad estimada"
              value={result.authenticityPercentage}
              explanation={
                <>
                  <p>
                    Es 100% menos el riesgo forense. No es una probabilidad
                    científica de autenticidad.
                  </p>
                  <p>
                    Un valor alto significa que se encontraron menos señales de
                    riesgo.
                  </p>
                </>
              }
            />
            <AnalysisMetric
              label="Riesgo forense"
              value={result.riskPercentage}
              tone="risk"
              explanation={
                <>
                  <p>
                    Combina 70% de señales técnicas y 30% de flags de IA. IA
                    generada/modificada tiene un mínimo de 75%;
                    edición/composición, 40%.
                  </p>
                  <p>
                    <strong>0–39%:</strong> sin riesgo crítico.{" "}
                    <strong>40–70%:</strong> revisión recomendada.{" "}
                    <strong>71–100%:</strong> alto riesgo.
                  </p>
                </>
              }
            />
          </div>
          <div className="mt-6 rounded-2xl bg-background p-3 text-xs">
            <p className="font-semibold text-secondary">
              Cómo se combinaron las evidencias
            </p>
            <p className="mt-1 font-semibold text-primary">
              {result.policyPresentation.label}
            </p>
            <p className="mt-1 text-[10px] leading-4 text-text-soft">
              {result.policyPresentation.description}
            </p>
          </div>
        </section>

        <section className="overflow-hidden rounded-3xl border border-border-soft bg-tertiary/50 p-4">
          <p className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-primary">
            <FiImage /> Evidencia original
          </p>
          <div className="overflow-hidden rounded-2xl bg-slate-950">
            <EvidencePreview previewUrl={previewUrl} fileName={file?.name} />
          </div>
        </section>
      </div>

      {imageAnalysis && <ImageClassificationPanel analysis={imageAnalysis} />}

      {documentAnalysis && (
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <h3 className="font-bold text-secondary">Análisis del documento PDF</h3>
          <p className="mt-1 text-xs text-text-soft">
            Extracción por página, comprobaciones aritméticas y análisis estadístico cuando corresponde.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <SignalCard
              label="Benford documental"
              score={documentAnalysis.benford_score}
              unavailableText={documentAnalysis.benford_applicable === false ? "No aplicable" : "Sin datos suficientes"}
              explanation={<p>Solo se aplica con al menos 30 montos diversos y distribuidos en dos órdenes de magnitud. Una desviación no demuestra fraude.</p>}
            />
            <SignalCard
              label="Coherencia aritmética"
              score={documentAnalysis.document_consistency_score}
              unavailableText="No se identificaron subtotal, impuestos y total"
              explanation={<p>Comprueba de forma determinista si subtotal más impuestos coincide con el total reportado.</p>}
            />
            <div className="rounded-2xl border border-border-soft bg-slate-50 p-4">
              <p className="text-[10px] font-bold uppercase text-text-soft">Páginas procesadas</p>
              <strong className="mt-2 block text-2xl text-secondary">
                {documentAnalysis.document_analyzed_pages ?? "—"}/{documentAnalysis.document_page_count ?? "—"}
              </strong>
              <p className="mt-1 text-[10px] text-text-soft">
                {documentAnalysis.document_truncated ? "El análisis se limitó a las primeras páginas" : "Documento procesado completamente"}
              </p>
            </div>
            <div className="rounded-2xl border border-border-soft bg-slate-50 p-4">
              <p className="text-[10px] font-bold uppercase text-text-soft">Contenido detectado</p>
              <p className="mt-2 text-xs text-secondary">Texto digital: {documentAnalysis.document_text_layer_pages ?? 0} páginas</p>
              <p className="mt-1 text-xs text-secondary">OCR: {documentAnalysis.document_ocr_pages ?? 0} páginas</p>
              <p className="mt-1 text-xs text-secondary">Imágenes: {documentAnalysis.document_embedded_images ?? 0}</p>
            </div>
          </div>
          {(documentAnalysis.ai_flags || []).length > 0 && (
            <div className="mt-4 rounded-2xl bg-amber-50 p-4">
              <p className="text-xs font-bold text-amber-800">Indicadores para revisión</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-800">
                {[...new Set(documentAnalysis.ai_flags)].map((flag) => (
                  <li key={flag}>{FLAG_LABELS[flag] || flag.replaceAll("_", " ")}</li>
                ))}
              </ul>
            </div>
          )}
          {(documentAnalysis.analysis_warnings || []).length > 0 && (
            <div className="mt-4 rounded-2xl bg-blue-50 p-4 text-xs text-blue-800">
              <p className="font-bold">Análisis parcial</p>
              <p className="mt-1">Algún proveedor no estuvo disponible. Se conservaron las evidencias técnicas y estructurales obtenidas.</p>
            </div>
          )}
          {(documentAnalysis.document_consistency_checks || []).length > 0 && (
            <div className="mt-4 rounded-2xl border border-border-soft p-4">
              <p className="text-xs font-bold text-secondary">Comprobaciones aritméticas</p>
              <div className="mt-2 space-y-2">
                {documentAnalysis.document_consistency_checks.map((check, index) => (
                  <div key={`${check.rule}-${check.line || index}`} className="flex items-center justify-between gap-3 text-xs">
                    <span className="text-text-soft">{check.rule.replaceAll("_", " ")}{check.line ? ` · línea ${check.line}` : ""}</span>
                    <span className={check.passed ? "font-bold text-emerald-600" : "font-bold text-red-600"}>{check.passed ? "Correcto" : `Diferencia ${check.difference}`}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(documentAnalysis.document_visual_evidence || []).length > 0 && (
            <div className="mt-5">
              <h4 className="text-sm font-bold text-secondary">Imágenes originales extraídas del PDF</h4>
              <p className="mt-1 text-xs text-text-soft">
                Las funciones asignadas son candidatas heurísticas; no demuestran que un elemento sea una firma o sello.
              </p>
              {documentHeatmapUrl && (
                <div className="mt-4">
                  <HeatmapViewer
                    heatmapUrl={documentHeatmapUrl}
                    score={documentAnalysis.document_visual_score}
                    label="ELA de la imagen embebida con mayor señal técnica"
                  />
                </div>
              )}
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {documentAnalysis.document_visual_evidence.map((evidence) => (
                  <article key={evidence.index} className="rounded-2xl border border-border-soft bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-bold text-secondary">Imagen {evidence.index} · página {evidence.page}</p>
                        <p className="mt-1 text-[10px] text-text-soft">{evidence.width}×{evidence.height} · {evidence.role.replaceAll("_", " ")}</p>
                      </div>
                      <strong className="text-lg text-primary">{percentScore(evidence.technical_score) == null ? "—" : `${percentScore(evidence.technical_score)}%`}</strong>
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[10px] text-text-soft">
                      <span>EXIF<br /><b>{percentScore(evidence.exif_score) == null ? "—" : `${percentScore(evidence.exif_score)}%`}</b></span>
                      <span>ELA<br /><b>{percentScore(evidence.ela_score) == null ? "—" : `${percentScore(evidence.ela_score)}%`}</b></span>
                      <span>DCT<br /><b>{percentScore(evidence.dct_benford_score) == null ? "—" : `${percentScore(evidence.dct_benford_score)}%`}</b></span>
                    </div>
                    {evidence.duplicate_of && <p className="mt-3 text-[10px] text-amber-700">Coincide exactamente con la imagen {evidence.duplicate_of}.</p>}
                    {!evidence.cognitive_available && <p className="mt-3 text-[10px] text-text-soft">IA visual no disponible; se conservaron las señales técnicas.</p>}
                  </article>
                ))}
              </div>
            </div>
          )}
          {documentAnalysis.pdf_structure && (
            <div className="mt-5 rounded-2xl border border-border-soft p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-sm font-bold text-secondary">Estructura y autenticidad del PDF</h4>
                  <p className="mt-1 text-xs text-text-soft">La presencia de software, formularios o revisiones no implica fraude por sí sola.</p>
                </div>
                <span className="rounded-full bg-background px-3 py-1 text-xs font-bold text-primary">
                  Riesgo estructural {percentScore(documentAnalysis.pdf_structure_score) ?? 0}%
                </span>
              </div>
              <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl bg-slate-50 p-3"><b>Revisiones</b><p className="mt-1 text-text-soft">{documentAnalysis.pdf_structure.incremental_updates ?? 0} incrementales</p></div>
                <div className="rounded-xl bg-slate-50 p-3"><b>Elementos interactivos</b><p className="mt-1 text-text-soft">{documentAnalysis.pdf_structure.form_fields ?? 0} campos · {documentAnalysis.pdf_structure.annotations ?? 0} anotaciones</p></div>
                <div className="rounded-xl bg-slate-50 p-3"><b>Contenido adicional</b><p className="mt-1 text-text-soft">{documentAnalysis.pdf_structure.embedded_files?.length ?? 0} adjuntos · {documentAnalysis.pdf_structure.optional_content_groups ?? 0} capas</p></div>
                <div className="rounded-xl bg-slate-50 p-3"><b>Composición</b><p className="mt-1 text-text-soft">{documentAnalysis.pdf_structure.unique_fonts ?? 0} fuentes · {documentAnalysis.pdf_structure.overlapping_text_image_objects ?? 0} superposiciones</p></div>
              </div>
              {(documentAnalysis.pdf_structure.active_content || []).length > 0 && (
                <p className="mt-3 rounded-xl bg-red-50 p-3 text-xs text-red-700">Contenido activo: {documentAnalysis.pdf_structure.active_content.join(", ")}</p>
              )}
              {(documentAnalysis.pdf_structure_flags || []).length > 0 && (
                <ul className="mt-3 list-disc space-y-1 rounded-xl bg-amber-50 p-3 pl-8 text-xs text-amber-800">
                  {documentAnalysis.pdf_structure_flags.map((flag) => <li key={flag}>{FLAG_LABELS[flag] || flag.replaceAll("_", " ")}</li>)}
                </ul>
              )}
              {(documentAnalysis.pdf_structure.editing_software_detected || []).length > 0 && (
                <p className="mt-3 text-xs text-text-soft">Software declarado: {documentAnalysis.pdf_structure.editing_software_detected.join(", ")}. Es información contextual, no una condena.</p>
              )}
              {(documentAnalysis.pdf_structure.digital_signatures || []).length > 0 ? (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-bold text-secondary">Firmas digitales</p>
                  {documentAnalysis.pdf_structure.digital_signatures.map((signature, index) => (
                    <div key={`${signature.field_name}-${index}`} className="rounded-xl bg-slate-50 p-3 text-xs">
                      <p className="font-semibold text-secondary">{signature.field_name || `Firma ${index + 1}`} · {signature.validation_status}</p>
                      <p className="mt-1 text-text-soft">Integridad: {signature.intact ? "conservada" : "no confirmada"} · Certificado confiable localmente: {signature.trusted ? "sí" : "no confirmado"}</p>
                      {signature.signer_subject && <p className="mt-1 truncate text-text-soft">Firmante: {signature.signer_subject}</p>}
                      {signature.modification_level && <p className="mt-1 text-text-soft">Cambios posteriores: {signature.modification_level}</p>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-xs text-text-soft">No se encontraron firmas digitales embebidas. Una firma manuscrita visible es una imagen y se reporta en la evidencia visual.</p>
              )}
            </div>
          )}
        </section>
      )}

      {imageAnalysis && (
        <section className="rounded-3xl border border-border-soft bg-white p-5">
          <h3 className="font-bold text-secondary">Señales técnicas reales</h3>
          <p className="mt-1 text-xs text-text-soft">
            Los porcentajes representan anomalía de cada técnica, no
            probabilidad directa de IA.
          </p>
          <div className="mt-4">
            <HeatmapViewer
              heatmapUrl={realHeatmapUrl}
              score={imageAnalysis.ela_score}
              label="Mapa de calor · Análisis ELA"
            />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <SignalCard
              label="Metadatos EXIF"
              score={imageAnalysis.exif_score}
              explanation={
                <>
                  <p>
                    Heurística acumulativa: software de edición +45%; fechas
                    distintas +35%; fecha original eliminada +15%.
                  </p>
                  <p>No tener EXIF suma 0% porque es común que aplicaciones y redes sociales lo eliminen.</p>
                </>
              }
            />
            <SignalCard
              label="Análisis ELA"
              score={imageAnalysis.ela_score}
              explanation={
                <>
                  <p>
                    Diferencia media tras recomprimir como JPEG, dividida para
                    25 y limitada a 100%.
                  </p>
                  <p>
                    No tiene intervalos de veredicto propios: es una señal
                    continua y debe leerse junto al mapa.
                  </p>
                </>
              }
            />
            <SignalCard
              label="DCT / Benford"
              score={imageAnalysis.dct_benford_score}
              unavailableText={
                imageAnalysis.benford_applicable === false
                  ? "No aplicable al formato"
                  : "Sin resultado"
              }
              explanation={
                <>
                  <p>
                    Solo aplica a JPEG. Compara coeficientes DCT con la
                    distribución de Benford.
                  </p>
                  <p>
                    Distancia 0 = 0%; distancia 0.30 o mayor = 100%. No es
                    probabilidad de fraude.
                  </p>
                </>
              }
            />
          </div>
        </section>
      )}

      {!imageAnalysis && !documentAnalysis && (
        <section className="rounded-3xl border border-border-soft bg-white p-5 text-sm text-text-soft">
          Este artefacto no contiene análisis visual. Los detalles disponibles
          dependen del tipo de archivo procesado.
        </section>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 text-xs text-text-soft">
        <span>
          {result.completedAt
            ? `Completado: ${new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeStyle: "short" }).format(new Date(result.completedAt))}`
            : "Análisis completado"}
        </span>
        <Button type="button" variant="outline" onClick={onReset}>
          <FiRefreshCw /> {resetLabel}
        </Button>
      </footer>
    </motion.div>
  );
}
