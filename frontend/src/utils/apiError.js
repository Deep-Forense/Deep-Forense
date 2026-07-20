export function getApiErrorMessage(error, fallback = "No fue posible completar la solicitud.") {
  const data = error?.response?.data;

  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.error === "string") return data.error;
  if (!error?.response && error?.message === "Network Error") {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    return `No se pudo conectar con Kong en ${baseUrl}. Verifica que Docker Compose esté levantado o que el puerto esté abierto.`;
  }

  return fallback;
}
