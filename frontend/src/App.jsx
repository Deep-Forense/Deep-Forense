import { useEffect, useRef, useState } from "react";
import { analyzeDemo, getJob } from "./api/client";

// T1.F1: landing con formulario de upload (archivo o URL)
// T1.F2: polling del job cada 2-3s hasta COMPLETED/FAILED
// T1.F3: pantalla de resultado básico (veredicto + porcentajes)

const POLL_INTERVAL_MS = 2500;

export default function App() {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef(null);

  useEffect(() => {
    return () => clearInterval(pollRef.current);
  }, []);

  const startPolling = (id) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await getJob(id);
        setJob(data);
        if (data.status === "COMPLETED" || data.status === "FAILED") {
          clearInterval(pollRef.current);
        }
      } catch (err) {
        setError(err?.response?.data?.message || "Error consultando el job.");
        clearInterval(pollRef.current);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setJob(null);

    if (!file && !url) {
      setError("Debes subir un archivo o ingresar una URL.");
      return;
    }

    const formData = new FormData();
    if (file) formData.append("file", file);
    if (url) formData.append("url", url);

    try {
      setSubmitting(true);
      const { data } = await analyzeDemo(formData);
      setJobId(data.job_id);
      setJob({ status: data.status });
      startPolling(data.job_id);
    } catch (err) {
      setError(err?.response?.data?.message || "Error al enviar el análisis.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.container}>
      <h1>DeepForense</h1>
      <p style={styles.subtitle}>
        Verificación de autenticidad de imágenes y documentos.
      </p>

      <form onSubmit={handleSubmit} style={styles.form}>
        <label style={styles.label}>
          Archivo (imagen o PDF)
          <input
            type="file"
            onChange={(e) => {
              setFile(e.target.files[0] || null);
              setUrl("");
            }}
            disabled={!!url}
          />
        </label>

        <div style={styles.orDivider}>o</div>

        <label style={styles.label}>
          URL a analizar
          <input
            type="text"
            placeholder="https://..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setFile(null);
            }}
            disabled={!!file}
            style={styles.input}
          />
        </label>

        <button type="submit" disabled={submitting} style={styles.button}>
          {submitting ? "Enviando..." : "Analizar"}
        </button>
      </form>

      {error && <p style={styles.error}>{error}</p>}

      {jobId && (
        <div style={styles.resultBox}>
          <p>
            <strong>Job ID:</strong> {jobId}
          </p>
          <p>
            <strong>Estado:</strong> {job?.status}
          </p>

          {job?.status === "PENDING" || job?.status === "PROCESSING" ? (
            <p>Procesando análisis...</p>
          ) : null}

          {job?.status === "COMPLETED" && job?.consolidated && (
            <div>
              <p>
                <strong>Veredicto:</strong> {job.consolidated.verdict}
              </p>
              <p>
                <strong>Autenticidad:</strong> {job.consolidated.authenticity_percentage}%
              </p>
              <p>
                <strong>Riesgo:</strong> {job.consolidated.risk_percentage}%
              </p>
            </div>
          )}

          {job?.status === "FAILED" && <p style={styles.error}>El análisis falló.</p>}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { maxWidth: 520, margin: "40px auto", fontFamily: "sans-serif" },
  subtitle: { color: "#555" },
  form: { display: "flex", flexDirection: "column", gap: 12, marginTop: 24 },
  label: { display: "flex", flexDirection: "column", gap: 4 },
  input: { padding: 8 },
  orDivider: { textAlign: "center", color: "#888" },
  button: { padding: "10px 16px", cursor: "pointer" },
  error: { color: "#b00020" },
  resultBox: { marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 8 },
};
