import { useCallback, useEffect, useMemo, useState } from "react";
import { Container } from "@/components/atoms/Container";
import { Modal } from "@/components/molecules/Modal";
import { DashboardStatCard } from "@/components/molecules/DashboardStatCard";
import { DashboardHeader } from "@/components/organisms/DashboardHeader";
import { Footer } from "@/components/organisms/Footer";
import { ForensicScannerCard } from "@/components/organisms/ForensicScannerCard";
import { AdvancedScanResult } from "@/features/scan/components/AdvancedScanResult";
import { ScanHistoryTable } from "@/features/scan/components/ScanHistoryTable";
import { getJobDetail, getScanHistory } from "@/features/scan/services/scan.service";
import { getApiErrorMessage } from "@/utils/apiError";

const HISTORY_PAGE_SIZE = 10;

export default function DashboardPage() {
  const [scannerKey, setScannerKey] = useState(0);
  const [history, setHistory] = useState([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetail, setJobDetail] = useState(null);
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const [jobDetailError, setJobDetailError] = useState("");

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await getScanHistory({ page: historyPage, pageSize: HISTORY_PAGE_SIZE });
      setHistory(data.items);
      setHistoryTotal(data.total);
    } catch (error) {
      setHistoryError(getApiErrorMessage(error, "No se pudo cargar el historial."));
    } finally {
      setHistoryLoading(false);
    }
  }, [historyPage]);

  useEffect(() => { loadHistory(); }, [loadHistory]);


  const reloadHistoryFromStart = useCallback(() => {
    if (historyPage === 1) {
      loadHistory();
    } else {
      setHistoryPage(1);
    }
  }, [historyPage, loadHistory]);

  const handleHistoryPageChange = useCallback((newPage) => {
    const maxPage = Math.max(1, Math.ceil(historyTotal / HISTORY_PAGE_SIZE));
    setHistoryPage(Math.min(Math.max(newPage, 1), maxPage));
  }, [historyTotal]);

  const dashboardStats = useMemo(() => {
    const scored = history.filter((job) => job.riskPercentage != null);
    const averageRisk = scored.length
      ? Math.round(scored.reduce((sum, job) => sum + job.riskPercentage, 0) / scored.length)
      : 0;
    const suspicious = history.filter((job) => ["SUSPICIOUS", "REJECTED", "INCONCLUSIVE"].includes(job.verdict)).length;
    return [
      { id: "analyzed", label: "Archivos analizados", value: historyTotal, trend: "Total", tone: "primary" },
      { id: "risk", label: "Promedio de riesgo", value: `${averageRisk}%`, trend: `Últimos ${HISTORY_PAGE_SIZE}`, tone: "primary" },
      { id: "suspicious", label: "Casos sospechosos", value: suspicious, trend: `Últimos ${HISTORY_PAGE_SIZE}`, tone: "danger" },
    ];
  }, [history, historyTotal]);

  const startNewAnalysis = () => {
    setScannerKey((current) => current + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const viewJobDetail = async (job) => {
    setSelectedJob(job);
    setJobDetail(null);
    setJobDetailError("");
    setJobDetailLoading(true);
    try {
      const detail = await getJobDetail(job.jobId);
      setJobDetail(detail);
    } catch (error) {
      setJobDetailError(getApiErrorMessage(error, "No se pudo cargar el detalle del análisis."));
    } finally {
      setJobDetailLoading(false);
    }
  };

  const closeJobDetail = () => setSelectedJob(null);

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

          <ForensicScannerCard key={scannerKey} authenticated onAnalysisCompleted={reloadHistoryFromStart} />

          <section className="mt-8 grid gap-4 md:grid-cols-3" aria-label="Resumen de actividad">
            {dashboardStats.map((stat) => <DashboardStatCard key={stat.id} {...stat} />)}
          </section>

          <div className="mt-8">
            <ScanHistoryTable
              jobs={history}
              loading={historyLoading}
              error={historyError}
              onRetry={reloadHistoryFromStart}
              onViewDetail={viewJobDetail}
              page={historyPage}
              pageSize={HISTORY_PAGE_SIZE}
              total={historyTotal}
              onPageChange={handleHistoryPageChange}
            />
          </div>
        </Container>
      </main>
      <Footer />

      <Modal open={Boolean(selectedJob)} onClose={closeJobDetail}>
        {jobDetailLoading && <p className="p-4 text-sm text-text-soft">Cargando detalle del análisis...</p>}
        {!jobDetailLoading && jobDetailError && (
          <p role="alert" className="p-4 text-sm text-red-700">{jobDetailError}</p>
        )}
        {!jobDetailLoading && !jobDetailError && jobDetail && (
          <AdvancedScanResult
            file={{ name: selectedJob?.fileName, type: selectedJob?.artifactType === "URL" ? "text/html" : "" }}
            mode={selectedJob?.artifactType}
            result={jobDetail}
            onReset={closeJobDetail}
            resetLabel="Cerrar"
          />
        )}
      </Modal>
    </div>
  );
}
