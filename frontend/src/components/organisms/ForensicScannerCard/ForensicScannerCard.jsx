import { useState } from "react";
import { motion } from "framer-motion";
import { FiShield, FiCheckCircle } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";
import { SCAN_MODES } from "@/features/scan/components/ScanModeTabs/ScanModeTabs";
import { ScanResult } from "@/features/scan/components/ScanResult";
import { AdvancedScanResult } from "@/features/scan/components/AdvancedScanResult";
import { JobProgress } from "@/features/scan/components/JobProgress";
import { scanUrl, submitAndWaitForScan, waitForScanResult } from "@/features/scan/services/scan.service";
import { UploadDropzone } from "@/components/molecules/UploadDropzone";
import { UrlAnalyzeBox } from "@/components/molecules/UrlAnalyzeBox";
import { StatCard } from "@/components/molecules/StatCard";
import { getApiErrorMessage } from "@/utils/apiError";

export default function ForensicScannerCard({ authenticated = false, onAnalysisCompleted }) {
  const [activeMode, setActiveMode] = useState("document");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [processingEvents, setProcessingEvents] = useState([]);
  const [scanResult, setScanResult] = useState(null);
  const [error, setError] = useState("");

  const handleFileSelect = (file) => {
    const maxBytes = 50 * 1024 * 1024;
    if (file.size > maxBytes) {
      setSelectedFile(null);
      setError("El archivo supera el límite de 50 MB.");
      return;
    }
    const extension = file.name.toLowerCase();
    if (activeMode === "document" && !extension.endsWith(".pdf")) {
      setSelectedFile(null);
      setError("Solo se admiten documentos PDF.");
      return;
    }
    setSelectedFile(file);
    setScanResult(null);
    setError("");
  };

  const runAnalysis = async () => {
    if (!selectedFile) return;
    setError("");
    setProcessingEvents([]);
    setIsAnalyzing(true);

    try {
      const result = await submitAndWaitForScan({
        file: selectedFile,
        authenticated,
        onEvent: (event) => setProcessingEvents((current) => [...current, event]),
      });
      setScanResult(result);
      onAnalysisCompleted?.(result);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, requestError.message || "No fue posible analizar el archivo."));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyzeUrl = async (url) => {
    setActiveMode("image");
    setSelectedFile({ name: url, type: "image/url" });
    setError("");
    setProcessingEvents([]);
    setIsAnalyzing(true);

    try {
      const created = await scanUrl(url, authenticated);
      const result = await waitForScanResult(created.job_id, {
        onEvent: (event) => setProcessingEvents((current) => [...current, event]),
      });
      setScanResult(result);
      onAnalysisCompleted?.(result);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "No se encontró una imagen en ese enlace. Corrígelo y vuelve a intentarlo."));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetScanner = () => {
    setSelectedFile(null);
    setScanResult(null);
    setIsAnalyzing(false);
    setProcessingEvents([]);
    setError("");
  };

  return (
    <motion.section
      id="scanner"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7 }}
      className="
        relative overflow-hidden rounded-[2rem] border border-border-soft
        bg-white p-5 shadow-2xl shadow-primary/10 md:p-6
      "
    >
      <div className="absolute right-0 top-0 h-40 w-40 rounded-full bg-tertiary blur-3xl" />

      {scanResult ? (
        <div className="relative">
          {authenticated ? (
            <AdvancedScanResult file={selectedFile} mode={activeMode} result={scanResult} onReset={resetScanner} />
          ) : (
            <ScanResult file={selectedFile} mode={activeMode} result={scanResult} onReset={resetScanner} />
          )}
        </div>
      ) : isAnalyzing ? (
        <div className="relative">
          <JobProgress events={processingEvents} fileName={selectedFile?.name} />
        </div>
      ) : (
      <div className="relative grid gap-5 lg:grid-cols-[220px_1fr]">
        <aside className="space-y-3">
          {SCAN_MODES.map((mode) => {
            const Icon = mode.icon;
            const isActive = activeMode === mode.id;

            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => {
                  setActiveMode(mode.id);
                  setSelectedFile(null);
                  setScanResult(null);
                  setError("");
                }}
                className={`
                  w-full rounded-3xl border p-4 text-left transition
                  ${
                    isActive
                      ? "border-primary bg-primary text-white shadow-lg shadow-primary/20"
                      : "border-border-soft bg-background text-secondary hover:border-primary"
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`
                      flex h-11 w-11 items-center justify-center rounded-2xl
                      ${
                        isActive
                          ? "bg-white/20 text-white"
                          : "bg-tertiary text-primary"
                      }
                    `}
                  >
                    <Icon className="text-2xl" />
                  </div>

                  <div>
                    <strong className="block text-sm font-bold">
                      {mode.label}
                    </strong>
                    <span
                      className={`mt-1 block text-xs leading-5 ${
                        isActive ? "text-white/75" : "text-text-soft"
                      }`}
                    >
                      {mode.description}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </aside>

        <div className="space-y-5">
          <div className="rounded-3xl bg-background p-4">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-secondary text-white">
                <FiShield className="text-xl" />
              </div>

              <div>
                <h3 className="font-bold text-secondary">
                  Análisis forense rápido
                </h3>
                <p className="text-sm text-text-soft">
                  Sube un archivo o pega una URL para estimar su autenticidad.
                </p>
              </div>
            </div>

            <UploadDropzone mode={activeMode} onFileSelect={handleFileSelect} />

            {selectedFile && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm text-secondary">
                  <FiCheckCircle className="shrink-0 text-primary" />
                  <span className="font-medium">Archivo seleccionado:</span>
                  <span className="truncate text-text-soft">
                    {selectedFile.name}
                  </span>
                </div>
                <Button type="button" className="w-full" size="lg" onClick={runAnalysis}>
                  Analizar archivo
                </Button>
              </div>
            )}

            {error && (
              <p role="alert" className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-xs font-medium leading-5 text-red-700">
                {error}
              </p>
            )}
          </div>

          <UrlAnalyzeBox onAnalyzeUrl={handleAnalyzeUrl} />

          <div className="grid grid-cols-3 gap-3">
            <StatCard value="5" label="Filtros" />
            <StatCard value="OCR" label="Documentos" />
            <StatCard value="URL" label="Análisis" />
          </div>
        </div>
      </div>
      )}
    </motion.section>
  );
}
