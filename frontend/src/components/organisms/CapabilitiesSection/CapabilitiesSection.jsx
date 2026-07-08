import {
  FiFileText,
  FiImage,
  FiLink,
  FiSearch,
  FiCheckSquare,
  FiCpu,
} from "react-icons/fi";
import { Container } from "@/components/atoms/Container";
import { Heading } from "@/components/atoms/Heading";
import { Text } from "@/components/atoms/Text";
import { CapabilityCard } from "@/components/molecules/CapabilityCard";

const capabilities = [
  {
    icon: FiFileText,
    title: "Documentos PDF",
    description:
      "Analiza certificados, comprobantes, formularios y documentos institucionales.",
  },
  {
    icon: FiImage,
    title: "Imágenes",
    description:
      "Evalúa fotografías, capturas y archivos visuales para detectar señales sospechosas.",
  },
  {
    icon: FiLink,
    title: "Análisis por URL",
    description:
      "Permite revisar contenido remoto usando una dirección web como entrada.",
  },
  {
    icon: FiSearch,
    title: "OCR documental",
    description:
      "Extrae texto de documentos escaneados para validar información relevante.",
  },
  {
    icon: FiCheckSquare,
    title: "Resultado simple",
    description:
      "Muestra un porcentaje inicial de autenticidad para usuarios sin sesión.",
  },
  {
    icon: FiCpu,
    title: "Motor forense",
    description:
      "Integra filtros ligeros para ofrecer una respuesta rápida y de bajo consumo.",
  },
];

export default function CapabilitiesSection() {
  return (
    <section id="capabilities" className="py-20">
      <Container>
        <div className="mx-auto max-w-3xl text-center">
          <Heading as="h2" className="text-secondary">
            Capacidades principales
          </Heading>

          <Text className="mt-4 text-text-soft">
            DeepForense está diseñado para validar entradas simples: un archivo,
            una imagen, un documento o una URL por análisis.
          </Text>
        </div>

        <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {capabilities.map((capability) => (
            <CapabilityCard
              key={capability.title}
              icon={capability.icon}
              title={capability.title}
              description={capability.description}
            />
          ))}
        </div>
      </Container>
    </section>
  );
}
