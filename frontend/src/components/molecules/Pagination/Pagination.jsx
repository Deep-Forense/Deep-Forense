import { FiChevronLeft, FiChevronRight } from "react-icons/fi";

const navButtonClass =
  "inline-flex items-center gap-1 text-xs font-bold text-primary transition disabled:cursor-not-allowed disabled:opacity-40";

export default function Pagination({ page, pageSize, total, onPageChange, itemLabel = "resultados" }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  if (total === 0) return null;

  const isFirstPage = page <= 1;
  const isLastPage = page >= totalPages;

  return (
    <div className="flex flex-col gap-3 border-t border-border-soft px-5 py-4 text-xs text-text-soft sm:flex-row sm:items-center sm:justify-between">
      <p>
        Mostrando {start}–{end} de {total} {itemLabel}
      </p>
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={isFirstPage}
          className={navButtonClass}
        >
          <FiChevronLeft /> Anterior
        </button>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={isLastPage}
          className={navButtonClass}
        >
          Siguiente <FiChevronRight />
        </button>
      </div>
    </div>
  );
}
