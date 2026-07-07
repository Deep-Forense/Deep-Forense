export default function Input({ icon: Icon, className = "", ...props }) {
  return (
    <div className="relative">
      {Icon && (
        <Icon className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-sm text-slate-400" />
      )}
      <input
        className={`w-full rounded-xl border border-border-soft bg-background px-4 py-3 text-sm text-secondary outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10 ${Icon ? "pl-10" : ""} ${className}`}
        {...props}
      />
    </div>
  );
}
