import { FiCheckCircle, FiCpu, FiEye, FiShield } from "react-icons/fi";
import { Logo } from "@/components/atoms/Logo";

const benefits = [
  {
    icon: FiEye,
    title: "Identidad de origen",
    text: "Rastreo de metadatos y validación inicial de autenticidad.",
  },
  {
    icon: FiCpu,
    title: "Análisis forense",
    text: "Accede al detalle técnico, flags y evidencias por artefacto.",
  },
  {
    icon: FiShield,
    title: "Historial protegido",
    text: "Conserva tus análisis y consulta su trazabilidad cuando la necesites.",
  },
];

export default function AuthBenefits() {
  return (
    <aside className="relative hidden overflow-hidden bg-secondary p-10 text-white lg:flex lg:flex-col lg:justify-between">
      <div className="absolute -right-24 top-32 h-72 w-72 rounded-full bg-primary/40 blur-3xl" />
      <div className="relative">
        <Logo variant="light" />
        <p className="mt-2 text-xs uppercase tracking-[0.2em] text-sky-200">Sistema de análisis avanzado</p>

        <div className="mt-16 space-y-9">
          {benefits.map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-xl text-sky-200">
                <Icon />
              </div>
              <div>
                <h2 className="text-sm font-bold">{title}</h2>
                <p className="mt-1 text-sm leading-6 text-slate-300">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="relative flex items-center gap-2 text-xs text-slate-400">
        <FiCheckCircle /> Entorno forense seguro · DeepForense
      </p>
    </aside>
  );
}
