export function getApiErrorMessage(error, fallback = "No fue posible completar la solicitud.") {
  const data = error?.response?.data;

  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.error === "string") return data.error;
  if (!error?.response && error?.message === "Network Error") {
    return "No se pudo conectar con Kong en http://localhost:8000. Verifica que Docker Compose esté levantado.";
  }

  return fallback;
}
