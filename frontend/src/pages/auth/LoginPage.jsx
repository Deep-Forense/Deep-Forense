import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiLock, FiMail } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";
import { FormField } from "@/components/molecules/FormField";
import { SocialAuthButtons } from "@/components/molecules/SocialAuthButtons";
import { AuthTemplate } from "@/components/templates/AuthTemplate";
import { paths } from "@/routes/paths";
import { login } from "@/features/auth/services/auth.service";
import { getApiErrorMessage } from "@/utils/apiError";

export default function LoginPage() {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const form = new FormData(event.currentTarget);
    try {
      await login({ email: form.get("email"), password: form.get("password") });
      navigate(paths.dashboard);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Correo o contraseña incorrectos."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthTemplate>
      <div className="w-full max-w-md rounded-[1.75rem] border border-border-soft bg-white p-6 shadow-xl shadow-secondary/5 sm:p-9">
        <h1 className="text-3xl font-extrabold tracking-tight text-secondary">Iniciar sesión</h1>
        <p className="mt-2 text-sm text-text-soft">Accede a tu terminal de análisis forense.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <FormField label="Correo electrónico" name="email" type="email" icon={FiMail} placeholder="analista@deepforense.com" required />
          <FormField
            label="Contraseña"
            type="password"
            name="password"
            icon={FiLock}
            placeholder="••••••••"
            required
            hint={<button type="button" className="font-medium text-primary hover:underline">¿Olvidaste tu contraseña?</button>}
          />

          {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-xs font-medium text-red-700">{error}</p>}

          <label className="flex items-center gap-2 text-xs text-text-soft">
            <input type="checkbox" className="h-4 w-4 accent-primary" />
            Recordar sesión por 30 días
          </label>

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Verificando..." : "Iniciar sesión"}
          </Button>
        </form>

        <div className="my-7 flex items-center gap-3 text-[11px] text-text-soft before:h-px before:flex-1 before:bg-border-soft after:h-px after:flex-1 after:bg-border-soft">
          O inicia sesión con
        </div>
        <SocialAuthButtons />

        <p className="mt-8 text-center text-sm text-text-soft">
          ¿No tienes cuenta?{" "}
          <Link to={paths.register} className="font-bold text-primary hover:underline">Crear cuenta</Link>
        </p>
      </div>
    </AuthTemplate>
  );
}
