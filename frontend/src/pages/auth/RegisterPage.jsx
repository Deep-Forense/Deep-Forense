import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiLock, FiMail, FiShield, FiUser } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";
import { FormField } from "@/components/molecules/FormField";
import { SocialAuthButtons } from "@/components/molecules/SocialAuthButtons";
import { AuthTemplate } from "@/components/templates/AuthTemplate";
import { paths } from "@/routes/paths";
import { registerAndLogin } from "@/features/auth/services/auth.service";
import { getApiErrorMessage } from "@/utils/apiError";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const password = form.get("password");

    if (password !== form.get("passwordConfirmation")) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setIsSubmitting(true);
    try {
      await registerAndLogin({ name: form.get("name"), email: form.get("email"), password });
      navigate(paths.dashboard);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "No fue posible crear la cuenta."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthTemplate>
      <div className="w-full max-w-lg rounded-[1.75rem] border border-border-soft bg-white p-6 shadow-xl shadow-secondary/5 sm:p-9">
        <h1 className="text-3xl font-extrabold tracking-tight text-secondary">Crea tu cuenta</h1>
        <p className="mt-2 text-sm leading-6 text-text-soft">Accede a reportes completos, historial de análisis y evidencia técnica.</p>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          <FormField label="Nombre completo" name="name" icon={FiUser} placeholder="Juan Pérez" required />
          <FormField label="Correo electrónico" name="email" type="email" icon={FiMail} placeholder="analista@empresa.com" required />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Contraseña" name="password" type="password" minLength="8" icon={FiLock} placeholder="••••••••" required />
            <FormField label="Confirmar" name="passwordConfirmation" type="password" minLength="8" icon={FiShield} placeholder="••••••••" required />
          </div>

          <label className="flex items-start gap-2 text-[11px] leading-4 text-text-soft">
            <input type="checkbox" required className="mt-0.5 h-4 w-4 shrink-0 accent-primary" />
            <span>Acepto los <button type="button" className="font-semibold text-primary">Términos de servicio</button> y la <button type="button" className="font-semibold text-primary">Política de privacidad</button>.</span>
          </label>

          {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-xs font-medium text-red-700">{error}</p>}

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creando cuenta..." : "Crear cuenta"}
          </Button>
        </form>

        <div className="my-6 flex items-center gap-3 text-[11px] text-text-soft before:h-px before:flex-1 before:bg-border-soft after:h-px after:flex-1 after:bg-border-soft">
          O regístrate con
        </div>
        <SocialAuthButtons />

        <p className="mt-7 text-center text-sm text-text-soft">
          ¿Ya tienes cuenta?{" "}
          <Link to={paths.login} className="font-bold text-primary hover:underline">Inicia sesión</Link>
        </p>
      </div>
    </AuthTemplate>
  );
}
