import { useState } from "react";
import { FiLink } from "react-icons/fi";
import { Button } from "@/components/atoms/Button";

export default function UrlAnalyzeBox({ onAnalyzeUrl }) {
  const [url, setUrl] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!url.trim()) return;

    if (onAnalyzeUrl) {
      onAnalyzeUrl(url.trim());
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="
        flex flex-col gap-3 rounded-3xl border border-border-soft
        bg-white p-4 md:flex-row md:items-center
      "
    >
      <div className="flex flex-1 items-center gap-3 rounded-full bg-background px-4 py-3">
        <FiLink className="text-lg text-primary" />

        <input
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="Pega una URL para analizar"
          className="w-full bg-transparent text-sm text-secondary outline-none placeholder:text-slate-400"
        />
      </div>

      <Button type="submit" variant="secondary">
        Analizar URL
      </Button>
    </form>
  );
}
