import { useNavigate } from "react-router-dom";
import { Button } from "@/components/atoms/Button";
import { Container } from "@/components/atoms/Container";
import { Logo } from "@/components/atoms/Logo";
import { NavItem } from "@/components/molecules/NavItem";
import { paths } from "@/routes/paths";

export default function Navbar() {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 border-b border-border-soft/70 bg-background/90 backdrop-blur-xl">
      <Container>
        <nav className="flex h-20 items-center justify-between">
          <a href="#hero" aria-label="Ir al inicio">
            <Logo />
          </a>

          <div className="hidden items-center gap-8 md:flex">
            <NavItem href="#scanner">Deep Scan</NavItem>
            <NavItem href="#capabilities">Capacidades</NavItem>
            <NavItem href="#about">Nosotros</NavItem>
          </div>

          <div className="hidden items-center gap-3 md:flex">
            <Button variant="ghost" onClick={() => navigate(paths.home)}>Inicio</Button>
            <Button variant="outline" onClick={() => navigate(paths.login)}>Iniciar sesión</Button>
            <Button variant="primary" onClick={() => navigate(paths.register)}>Crear cuenta</Button>
          </div>

          <div className="md:hidden">
            <Button variant="outline" size="sm" onClick={() => navigate(paths.login)}>
              Iniciar sesión
            </Button>
          </div>
        </nav>
      </Container>
    </header>
  );
}
