import { Navigate } from "react-router-dom";
import { isAuthenticated } from "@/features/auth/services/auth.service";
import { paths } from "@/routes/paths";

export default function ProtectedRoute({ children }) {
  return isAuthenticated() ? children : <Navigate to={paths.login} replace />;
}
