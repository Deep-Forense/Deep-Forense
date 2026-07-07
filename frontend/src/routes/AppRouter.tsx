import { BrowserRouter, Route, Routes } from "react-router-dom";
import LandingPage from "@/pages/public/LandingPage";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import DashboardPage from "@/pages/scan/DashboardPage";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { paths } from "./paths";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={paths.home} element={<LandingPage />} />
        <Route path={paths.login} element={<LoginPage />} />
        <Route path={paths.register} element={<RegisterPage />} />
        <Route path={paths.dashboard} element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="*" element={<LandingPage />} />
      </Routes>
    </BrowserRouter>
  );
}
