import { useNavigate } from "react-router-dom";
import { FiLogOut, FiPlus } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";
import { Container } from "@/components/atoms/Container";
import { Logo } from "@/components/atoms/Logo";
import { paths } from "@/routes/paths";
import { logout } from "@/features/auth/services/auth.service";

export default function DashboardHeader({ onNewAnalysis }) {
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate(paths.home);
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border-soft bg-white/90 backdrop-blur-xl">
      <Container>
        <div className="flex h-20 items-center justify-between gap-4">
          <div className="flex items-center gap-5">
            <Logo />
            <span className="hidden border-l border-border-soft pl-5 text-sm font-bold text-secondary sm:block">Panel de análisis</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={onNewAnalysis}><FiPlus /> <span className="hidden sm:inline">Hacer otro análisis</span></Button>
            <Button variant="outline" size="sm" onClick={handleLogout}><FiLogOut /> <span className="hidden sm:inline">Salir</span></Button>
          </div>
        </div>
      </Container>
    </header>
  );
}
