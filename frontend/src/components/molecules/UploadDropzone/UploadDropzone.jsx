import { FiUploadCloud } from "react-icons/fi";

export default function UploadDropzone({ mode = "document", onFileSelect }) {
  const isDocument = mode === "document";

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];

    if (file && onFileSelect) {
      onFileSelect(file);
    }
  };

  return (
    <label
      className="
        flex cursor-pointer flex-col items-center justify-center rounded-3xl
        border-2 border-dashed border-border-soft bg-white px-6 py-10
        text-center transition hover:border-primary hover:bg-tertiary/40
      "
    >
      <input
        type="file"
        className="hidden"
        accept={
          isDocument
            ? ".pdf"
            : ".jpg,.jpeg,.png,.webp"
        }
        onChange={handleFileChange}
      />

      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-tertiary text-primary">
        <FiUploadCloud className="text-3xl" />
      </div>

      <span className="text-base font-semibold text-secondary">
        {isDocument
          ? "Arrastra y suelta documentos aquí"
          : "Arrastra y suelta imágenes aquí"}
      </span>

      <span className="mt-2 text-sm text-text-soft">
        {isDocument
          ? "PDF hasta 50MB"
          : "JPG, PNG o WEBP hasta 50MB"}
      </span>

      <span className="mt-5 rounded-full bg-primary px-5 py-2 text-sm font-semibold text-white">
        Seleccionar archivo
      </span>
    </label>
  );
}
