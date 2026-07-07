const variants = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-700 ring-amber-200",
  danger: "bg-red-50 text-red-700 ring-red-200",
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
};

export default function Badge({ children, variant = "neutral", className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
