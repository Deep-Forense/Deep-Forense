import { Link } from "react-router-dom";
import { FiArrowLeft } from "react-icons/fi";
import { AuthBenefits } from "@/components/organisms/AuthBenefits";
import { paths } from "@/routes/paths";

export default function AuthTemplate({ children }) {
  return (
    <main className="min-h-screen bg-background p-3 sm:p-6">
      <div className="mx-auto grid min-h-[calc(100vh-1.5rem)] max-w-6xl overflow-hidden rounded-[2rem] border border-border-soft bg-white shadow-2xl shadow-secondary/10 sm:min-h-[calc(100vh-3rem)] lg:grid-cols-[0.85fr_1.15fr]">
        <AuthBenefits />

        <section className="relative flex items-center justify-center bg-slate-50/70 px-5 py-12 sm:px-10">
          <Link
            to={paths.home}
            className="absolute left-6 top-6 inline-flex items-center gap-2 text-xs font-semibold text-text-soft transition hover:text-primary"
          >
            <FiArrowLeft /> Volver al inicio
          </Link>
          {children}
        </section>
      </div>
    </main>
  );
}
