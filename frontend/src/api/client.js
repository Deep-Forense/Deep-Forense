import axios from "axios";

// Todas las peticiones pasan por Kong (punto único de entrada).
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("deepforense_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- auth-service -----------------------------------------------------
export const register = (payload) => apiClient.post("/api/auth/register", payload);
export const login = (payload) => apiClient.post("/api/auth/login", payload);
export const logout = () => apiClient.post("/api/auth/logout");
export const getCurrentUser = () => apiClient.get("/api/auth/me");

// --- forensic-api -------------------------------------------------------
export const analyzeDemo = (formData) =>
  apiClient.post("/api/forensic/demo/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const analyzeAuthenticated = (formData) =>
  apiClient.post("/api/forensic/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const getJob = (jobId) => apiClient.get(`/api/forensic/jobs/${jobId}`);

export const listJobs = (params) => apiClient.get("/api/forensic/jobs", { params });

export default apiClient;
