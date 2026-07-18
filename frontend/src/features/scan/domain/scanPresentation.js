export const VERDICT_PRESENTATION = {
  APPROVED: { label: "Sin riesgo crítico", variant: "success", tone: "text-emerald-600" },
  SUSPICIOUS: { label: "Sospechoso", variant: "warning", tone: "text-amber-600" },
  REJECTED: { label: "Alto riesgo", variant: "danger", tone: "text-red-600" },
};

export const IMAGE_CLASSIFICATION_PRESENTATION = {
  AI_GENERATED: { label: "Generada por IA", variant: "danger" },
  AI_MODIFIED: { label: "Modificada por IA", variant: "danger" },
  SCREENSHOT: { label: "Captura de pantalla", variant: "neutral" },
  EDITED: { label: "Editada o compuesta", variant: "warning" },
  AUTHENTIC: { label: "Sin señales concluyentes", variant: "success" },
  INCONCLUSIVE: { label: "Origen no concluyente", variant: "warning" },
};

export const FLAG_LABELS = {
  ai_generation_artifacts: "Artefactos de generación por IA",
  synthetic_texture: "Texturas sintéticas",
  anatomical_inconsistency: "Inconsistencias anatómicas",
  ai_inpainting_artifacts: "Rastros de relleno mediante IA",
  generative_fill_artifacts: "Relleno generativo",
  cloned_region: "Regiones clonadas",
  compositing_artifacts: "Indicios de composición",
  inconsistent_lighting: "Iluminación inconsistente",
  warped_text: "Texto deformado",
  screenshot_ui_elements: "Elementos de interfaz capturados",
  screen_capture_artifacts: "Rastros de captura de pantalla",
};

export const percentScore = (score) => score == null ? null : Math.round(score * 100);

export const JOB_STEP_LABELS = {
  JOB_CREATED: "Creado",
  JOB_PROCESSING: "Procesando",
  JOB_COMPLETED: "Completado",
  JOB_FAILED: "Fallido",
};

export const severityFromScore = (score) => {
  const percentage = percentScore(score);
  if (percentage == null) return { label: "Sin datos", variant: "neutral" };
  if (percentage >= 66) return { label: "Anomalía alta", variant: "danger" };
  if (percentage >= 33) return { label: "Anomalía moderada", variant: "warning" };
  return { label: "Anomalía baja", variant: "success" };
};
