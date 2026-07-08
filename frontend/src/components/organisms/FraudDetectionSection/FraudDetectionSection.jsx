import { FiActivity, FiEye, FiLock, FiZap } from "react-icons/fi";
import { Container } from "@/components/atoms/Container";
import { Heading } from "@/components/atoms/Heading";
import { Text } from "@/components/atoms/Text";

const items = [
  {
    icon: FiEye,
    title: "Inspección visual asistida",
    text: "Detecta señales de alteración en imágenes o documentos digitalizados.",
  },
  {
    icon: FiActivity,
    title: "Filtros forenses",
    text: "Aplica verificaciones ligeras para estimar inconsistencias en el archivo.",
  },
  {
    icon: FiZap,
    title: "Respuesta rápida",
    text: "Pensado para entregar resultados simples sin procesos pesados.",
  },
  {
    icon: FiLock,
    title: "Detalles con sesión",
    text: "Los usuarios autenticados pueden acceder a información ampliada del análisis.",
  },
];

export default function FraudDetectionSection() {
  return (
    <section id="about" className="py-20">
      <Container>
        <div className="overflow-hidden rounded-[2rem] bg-secondary p-8 text-white md:p-12">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold text-tertiary">
                Motor Deep Scan
              </span>

              <Heading as="h2" className="mt-6 text-white">
                Detección forense ligera para documentos e imágenes
              </Heading>

              <Text className="mt-5 text-slate-300">
                El objetivo no es reemplazar una pericia forense profesional,
                sino ofrecer una primera evaluación automatizada, rápida y clara
                sobre la autenticidad del contenido.
              </Text>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {items.map((item) => {
                const Icon = item.icon;

                return (
                  <article
                    key={item.title}
                    className="rounded-3xl border border-white/10 bg-white/5 p-5"
                  >
                    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-tertiary">
                      <Icon className="text-xl" />
                    </div>

                    <h3 className="font-bold text-white">{item.title}</h3>

                    <p className="mt-2 text-sm leading-6 text-slate-300">
                      {item.text}
                    </p>
                  </article>
                );
              })}
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
