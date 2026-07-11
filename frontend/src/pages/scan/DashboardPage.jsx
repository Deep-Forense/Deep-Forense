import { useCallback, useEffect, useMemo, useState } from "react";
import { Container } from "@/components/atoms/Container";
import { DashboardStatCard } from "@/components/molecules/DashboardStatCard";
import { DashboardHeader } from "@/components/organisms/DashboardHeader";
import { Footer } from "@/components/organisms/Footer";
import { ForensicScannerCard } from "@/components/organisms/ForensicScannerCard";
import { ScanHistoryTable } from "@/features/scan/components/ScanHistoryTable";
import { getScanHistory } from "@/features/scan/services/scan.service";
import { getApiErrorMessage } from "@/utils/apiError";

export default function DashboardPage() {
  const [scannerKey, setScannerKey] = useState(0);
  const [history, setHistory] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await getScanHistory({ pageSize: 20 });
      setHistory(data.items);
      setHistoryTotal(data.total);
    } catch (error) {
      setHistoryError(getApiErrorMessage(error, "No se pudo cargar el historial."));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const dashboardStats = useMemo(() => {
    const scored = history.filter((job) => job.riskPercentage != null);
    const averageRisk = scored.length
      ? Math.round(scored.reduce((sum, job) => sum + job.riskPercentage, 0) / scored.length)
      : 0;
    const suspicious = history.filter((job) => ["SUSPICIOUS", "REJECTED"].includes(job.verdict)).length;
    return [
      { id: "analyzed", label: "Archivos analizados", value: historyTotal, trend: "Total", tone: "primary" },
      { id: "risk", label: "Promedio de riesgo", value: `${averageRisk}%`, trend: "Últimos 20", tone: "primary" },
      { id: "suspicious", label: "Casos sospechosos", value: suspicious, trend: "Últimos 20", tone: "danger" },
    ];
  }, [history, historyTotal]);

  const startNewAnalysis = () => {
    setScannerKey((current) => current + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader onNewAnalysis={startNewAnalysis} />
      <main className="py-10">
        <Container>
          <div className="mb-7">
            <p className="text-sm font-semibold text-primary">Área privada</p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-tight text-secondary">Análisis de documentos</h1>
            <p className="mt-2 text-sm text-text-soft">Sube evidencia digital, consulta resultados y revisa tus trabajos recientes.</p>
          </div>

          <ForensicScannerCard key={scannerKey} authenticated onAnalysisCompleted={loadHistory} />

          <section className="mt-8 grid gap-4 md:grid-cols-3" aria-label="Resumen de actividad">
            {dashboardStats.map((stat) => <DashboardStatCard key={stat.id} {...stat} />)}
          </section>

          <div className="mt-8">
            <ScanHistoryTable jobs={history} loading={historyLoading} error={historyError} onRetry={loadHistory} />
          </div>
        </Container>
      </main>
      <Footer />
    </div>
  );
}
