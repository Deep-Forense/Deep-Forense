import { Navbar } from "@/components/organisms/Navbar";
import { HeroSection } from "@/components/organisms/HeroSection";
import { CapabilitiesSection } from "@/components/organisms/CapabilitiesSection";
import { FraudDetectionSection } from "@/components/organisms/FraudDetectionSection";
import { Footer } from "@/components/organisms/Footer";

export default function LandingTemplate() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection />
        <CapabilitiesSection />
        <FraudDetectionSection />
      </main>
      <Footer />
    </div>
  );
}
