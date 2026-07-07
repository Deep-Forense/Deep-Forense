import { motion } from "framer-motion";
import { Button } from "@/components/atoms/Button";
import { Container } from "@/components/atoms/Container";
import { Heading } from "@/components/atoms/Heading";
import { Text } from "@/components/atoms/Text";
import { ForensicScannerCard } from "@/components/organisms/ForensicScannerCard";
import { FiArrowRight, FiShield } from "react-icons/fi";

export default function HeroSection() {
  return (
    <section id="hero" className="relative overflow-hidden py-16 md:py-24">
      <div className="absolute left-1/2 top-10 h-72 w-72 -translate-x-1/2 rounded-full bg-tertiary blur-3xl" />

      <Container className="relative">
        <div className="grid items-center gap-12 lg:grid-cols-[0.9fr_1.1fr]">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border-soft bg-white px-4 py-2 text-sm font-semibold text-primary shadow-sm">
              <FiShield />
              Verificación forense inteligente
            </div>

            <Heading as="h1" className="text-secondary">
              Verifica documentos digitales antes de confiar en ellos
            </Heading>

            <Text className="mt-6 max-w-2xl text-lg text-text-soft">
              DeepForense analiza documentos, imágenes y URLs mediante filtros
              forenses ligeros para estimar si el contenido parece auténtico,
              alterado o sospechoso.
            </Text>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button size="lg">
                Iniciar análisis
                <FiArrowRight />
              </Button>

              <Button variant="outline" size="lg">
                Ver capacidades
              </Button>
            </div>

            <div className="mt-8 grid max-w-xl grid-cols-3 gap-3">
              <div>
                <strong className="block text-2xl font-extrabold text-primary">
                  OCR
                </strong>
                <span className="text-xs text-text-soft">
                  lectura documental
                </span>
              </div>

              <div>
                <strong className="block text-2xl font-extrabold text-primary">
                  5+
                </strong>
                <span className="text-xs text-text-soft">filtros forenses</span>
              </div>

              <div>
                <strong className="block text-2xl font-extrabold text-primary">
                  1
                </strong>
                <span className="text-xs text-text-soft">
                  archivo por análisis
                </span>
              </div>
            </div>
          </motion.div>

          <ForensicScannerCard />
        </div>
      </Container>
    </section>
  );
}
