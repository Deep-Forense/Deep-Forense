import { Container } from "@/components/atoms/Container";
import { Logo } from "@/components/atoms/Logo";

export default function Footer() {
  return (
    <footer className="border-t border-border-soft bg-white py-8">
      <Container>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <Logo />

          <p className="text-sm text-text-soft">
            © {new Date().getFullYear()} DeepForense. Análisis forense digital
            académico.
          </p>
        </div>
      </Container>
    </footer>
  );
}
