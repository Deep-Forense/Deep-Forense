import { FiCpu } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { FLAG_LABELS, IMAGE_CLASSIFICATION_PRESENTATION } from "@/features/scan/domain/scanPresentation";

export default function ImageClassificationPanel({ analysis }) {
  if (!analysis) return null;
  const classification = analysis.image_classification || "INCONCLUSIVE";
  const presentation = IMAGE_CLASSIFICATION_PRESENTATION[classification] || IMAGE_CLASSIFICATION_PRESENTATION.INCONCLUSIVE;
  const flags = [...new Set(analysis.gemini_flags || analysis.ai_flags || [])];

  return (
    <section className="rounded-3xl border border-border-soft bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 font-bold text-secondary"><FiCpu className="text-primary" /> Clasificación de origen</h3>
        <Badge variant={presentation.variant}>{presentation.label}</Badge>
      </div>
      <p className="mt-3 text-sm leading-6 text-text-soft">
        {analysis.image_classification_message || "El análisis anterior no incluye todavía una clasificación estructurada."}
      </p>
      {flags.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {flags.map((flag) => <Badge key={flag} variant="neutral">{FLAG_LABELS[flag] || flag}</Badge>)}
        </div>
      ) : (
        <p className="mt-4 text-xs text-text-soft">Gemini no devolvió indicadores visuales específicos.</p>
      )}
    </section>
  );
}
