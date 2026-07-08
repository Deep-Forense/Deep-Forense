import { Container } from "@/components/atoms/Container";
import { DashboardStatCard } from "@/components/molecules/DashboardStatCard";
import { DashboardHeader } from "@/components/organisms/DashboardHeader";
import { Footer } from "@/components/organisms/Footer";
import { ForensicScannerCard } from "@/components/organisms/ForensicScannerCard";
import { ScanHistoryTable } from "@/features/scan/components/ScanHistoryTable";
import { DASHBOARD_STATS, MOCK_SCAN_HISTORY } from "@/features/scan/mocks/dashboard.mock";

export default function DashboardPage() {
  const [scannerKey, setScannerKey] = useState(0);

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

          <ForensicScannerCard key={scannerKey} authenticated />

          <section className="mt-8 grid gap-4 md:grid-cols-3" aria-label="Resumen de actividad">
            {DASHBOARD_STATS.map((stat) => <DashboardStatCard key={stat.id} {...stat} />)}
          </section>

          <div className="mt-8">
            <ScanHistoryTable jobs={MOCK_SCAN_HISTORY} />
          </div>
        </Container>
      </main>
      <Footer />
    </div>
  );
}
import { useState } from "react";
