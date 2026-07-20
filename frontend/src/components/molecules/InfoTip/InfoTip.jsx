import { FiHelpCircle } from "react-icons/fi";

export default function InfoTip({ title = "Cómo interpretar", children }) {
  return (
    <details className="group relative inline-block align-middle">
      <summary className="ml-1 inline-flex cursor-pointer list-none items-center text-text-soft hover:text-primary" aria-label={title}>
        <FiHelpCircle aria-hidden="true" />
      </summary>
      <div className="absolute left-0 top-6 z-30 w-72 max-w-[80vw] rounded-2xl border border-border-soft bg-white p-4 text-left text-xs font-normal normal-case leading-5 tracking-normal text-text-soft shadow-xl">
        <strong className="block text-secondary">{title}</strong>
        <div className="mt-2 space-y-2">{children}</div>
      </div>
    </details>
  );
}
