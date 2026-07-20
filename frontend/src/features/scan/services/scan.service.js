import apiClient, { analyzeDemo, analyzeAuthenticated, getJob, listJobs } from "@/api/client";

export const scanDemoFile = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await analyzeDemo(formData);
  return response.data;
};

export const scanAuthenticatedFile = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await analyzeAuthenticated(formData);
  return response.data;
};

export const scanUrl = async (url, authenticated = false) => {
  const formData = new FormData();
  formData.append("url", url);
  const response = authenticated
    ? await analyzeAuthenticated(formData)
    : await analyzeDemo(formData);
  return response.data;
};

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const CONSOLIDATION_PRESENTATION = {
  worst_case_dominates: { label: "Prevalece la evidencia de mayor riesgo", description: "Si hay varios elementos, el resultado global toma el porcentaje del elemento con mayor riesgo." },
  weighted_average: { label: "Promedio ponderado de evidencias", description: "Combina todos los elementos y da mayor peso a las imágenes (70%) que al texto (30%)." },
};

export const normalizeScanResult = (job) => {
  const consolidated = job.consolidated || {};
  const riskPercentage = consolidated.risk_percentage ?? Math.round((consolidated.fraud_score ?? 0) * 100);
  const authenticityPercentage = consolidated.analysis_complete === false
    ? null
    : (consolidated.authenticity_percentage ?? 100 - riskPercentage);
  const verdict = consolidated.verdict || "SUSPICIOUS";
  const artifacts = (job.artifacts || []).map((artifact) => ({
    artifactId: artifact.artifact_id,
    type: artifact.type,
    origin: artifact.origin,
    status: artifact.status,
    analysis: artifact.analysis || null,
  }));
  const imageArtifact = artifacts.find((artifact) => artifact.type === "IMAGE" && artifact.analysis);
  const documentArtifact = artifacts.find((artifact) => artifact.type === "TEXT" && artifact.analysis);

  return {
    jobId: job.job_id,
    status: job.status,
    detailLevel: job.detail_level || "basic",
    verdict,
    authenticityPercentage,
    riskPercentage,
    fraudScore: consolidated.fraud_score ?? riskPercentage / 100,
    model: "forensic-worker · pipeline de análisis",
    policyApplied: consolidated.policy_applied || "pending",
    policyPresentation: CONSOLIDATION_PRESENTATION[consolidated.policy_applied] || {
      label: "Resultado individual", description: "El resultado se calculó con la evidencia disponible.",
    },
    summary:
      verdict === "INCONCLUSIVE"
        ? "El análisis no pudo completar una evaluación crítica; no se afirma autenticidad."
        : verdict === "APPROVED"
        ? "No se detectaron indicadores críticos en el análisis consolidado."
        : "El análisis detectó indicadores que requieren revisión adicional.",
    artifacts,
    imageAnalysis: imageArtifact?.analysis || null,
    documentAnalysis: documentArtifact?.analysis || null,
    createdAt: job.created_at,
    completedAt: job.completed_at,
  };
};

export const getJobDetail = async (jobId) => {
  const { data: job } = await getJob(jobId);
  return normalizeScanResult(job);
};


export const fetchElaHeatmapObjectUrl = async (relativeUrl) => {
  const response = await apiClient.get(relativeUrl, { responseType: "blob" });
  return URL.createObjectURL(response.data);
};


const STATUS_EVENT_TYPE = {
  PENDING: "JOB_CREATED",
  PROCESSING: "JOB_PROCESSING",
  COMPLETED: "JOB_COMPLETED",
  FAILED: "JOB_FAILED",
};

export const waitForScanResult = async (jobId, { attempts = 120, interval = 1500, onEvent } = {}) => {
  let lastStatus = null;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const { data: job } = await getJob(jobId);

    if (job.status !== lastStatus) {
      lastStatus = job.status;
      onEvent?.({ type: STATUS_EVENT_TYPE[job.status], timestamp: new Date().toISOString() });
    }

    if (job.status === "COMPLETED") return normalizeScanResult(job);
    if (job.status === "FAILED") throw new Error("El backend no pudo completar el análisis.");

    await wait(interval);
  }

  throw new Error("El análisis continúa procesándose. Inténtalo nuevamente en unos segundos.");
};

export const submitAndWaitForScan = async ({ file, authenticated, onEvent }) => {
  const created = authenticated
    ? await scanAuthenticatedFile(file)
    : await scanDemoFile(file);
  return waitForScanResult(created.job_id, { onEvent });
};

export const getScanHistory = async ({ page = 1, pageSize = 20, verdict } = {}) => {
  const params = { page, page_size: pageSize };
  if (verdict) params.verdict = verdict;

  const { data } = await listJobs(params);
  return {
    ...data,
    items: data.items.map((job) => {
      const riskPercentage = job.fraud_score == null ? null : Math.round(job.fraud_score * 100);
      return {
        jobId: job.job_id,
        fileName: job.input_source === "URL" ? "Contenido desde URL" : "Archivo cargado",
        artifactType: job.input_source === "URL" ? "URL" : "UPLOAD",
        status: job.status,
        riskPercentage,
        authenticityPercentage: job.verdict === "INCONCLUSIVE" || riskPercentage == null ? null : 100 - riskPercentage,
        verdict: job.verdict || (job.status === "FAILED" ? "FAILED" : "PENDING"),
        createdAt: new Intl.DateTimeFormat("es-EC", {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(new Date(job.created_at)),
      };
    }),
  };
};
