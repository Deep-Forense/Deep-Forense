import { analyzeDemo, analyzeAuthenticated, getJob } from "@/api/client";

export const scanDemoFile = async (file, mode) => {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("type", mode);

  const response = await analyzeDemo(formData);
  return response.data;
};

export const scanAuthenticatedFile = async (file, mode) => {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("type", mode);

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

export const normalizeScanResult = (job) => {
  const consolidated = job.consolidated || {};
  const riskPercentage = consolidated.risk_percentage ?? Math.round((consolidated.fraud_score ?? 0) * 100);
  const authenticityPercentage = consolidated.authenticity_percentage ?? 100 - riskPercentage;
  const verdict = consolidated.verdict || "SUSPICIOUS";

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
    summary:
      verdict === "APPROVED"
        ? "No se detectaron indicadores críticos en el análisis consolidado."
        : "El análisis detectó indicadores que requieren revisión adicional.",
    artifacts: job.artifacts || [],
    createdAt: job.created_at,
    completedAt: job.completed_at,
  };
};

export const waitForScanResult = async (jobId, { attempts = 40, interval = 1500 } = {}) => {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const { data: job } = await getJob(jobId);

    if (job.status === "COMPLETED") return normalizeScanResult(job);
    if (job.status === "FAILED") throw new Error("El backend no pudo completar el análisis.");

    await wait(interval);
  }

  throw new Error("El análisis continúa procesándose. Inténtalo nuevamente en unos segundos.");
};

export const submitAndWaitForScan = async ({ file, mode, authenticated }) => {
  const created = authenticated
    ? await scanAuthenticatedFile(file, mode)
    : await scanDemoFile(file, mode);
  return waitForScanResult(created.job_id);
};
