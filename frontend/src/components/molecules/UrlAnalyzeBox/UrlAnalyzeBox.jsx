import { useState } from "react";
import { FiLink } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";

export default function UrlAnalyzeBox({ onAnalyzeUrl }) {
  const [url, setUrl] = useState("");
  const [validationError, setValidationError] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!url.trim()) {
      setValidationError("Pega el enlace directo de una imagen.");
      return;
    }

    try {
      const parsed = new URL(url.trim());
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
    } catch {
      setValidationError("Ingresa un enlace HTTP o HTTPS válido y vuelve a intentarlo.");
      return;
    }

    setValidationError("");

    if (onAnalyzeUrl) {
      onAnalyzeUrl(url.trim());
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="
        flex flex-col gap-3 rounded-3xl border border-border-soft
        bg-white p-4 md:flex-row md:flex-wrap md:items-center
      "
    >
      <div className="flex flex-1 items-center gap-3 rounded-full bg-background px-4 py-3">
        <FiLink className="text-lg text-primary" />

        <input
          type="url"
          value={url}
          onChange={(event) => { setUrl(event.target.value); setValidationError(""); }}
          placeholder="Enlace directo a imagen JPG, PNG o WEBP"
          className="w-full bg-transparent text-sm text-secondary outline-none placeholder:text-slate-400"
        />
      </div>

      <Button type="submit" variant="secondary">
        Analizar imagen
      </Button>
      {validationError && <p role="alert" className="text-xs font-medium text-red-600 md:basis-full">{validationError}</p>}
    </form>
  );
}
