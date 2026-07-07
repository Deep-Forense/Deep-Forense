export type ScanVerdict = "APPROVED" | "SUSPICIOUS" | "REJECTED";

export interface ScanResult {
  jobId: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  detailLevel: "basic" | "full";
  verdict: ScanVerdict;
  authenticityPercentage: number;
  riskPercentage: number;
  fraudScore: number;
  model: string;
  policyApplied: string;
  summary: string;
}
