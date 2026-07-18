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
  artifacts: Array<{
    artifactId: string;
    type: "TEXT" | "IMAGE";
    status: "COMPLETED" | "FAILED";
    analysis: (Record<string, unknown> & { ela_heatmap_url?: string }) | null;
  }>;
  imageAnalysis: (Record<string, unknown> & { ela_heatmap_url?: string }) | null;
}
