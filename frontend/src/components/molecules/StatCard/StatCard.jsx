export default function StatCard({ value, label }) {
  return (
    <div className="rounded-2xl bg-white/80 p-4 text-center shadow-sm ring-1 ring-border-soft">
      <strong className="block text-2xl font-extrabold text-primary">
        {value}
      </strong>
      <span className="mt-1 block text-xs font-medium text-text-soft">
        {label}
      </span>
    </div>
  );
}
