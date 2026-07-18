import { FiFileText, FiImage } from "react-icons/fi";

export const SCAN_MODES = [
  {
    id: "document",
    label: "Documento",
    description: "PDF con texto o páginas escaneadas.",
    icon: FiFileText,
  },
  {
    id: "image",
    label: "Imagen",
    description: "Fotografías, capturas y archivos visuales.",
    icon: FiImage,
  },
];
