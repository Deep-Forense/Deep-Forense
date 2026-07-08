export default function CapabilityCard({ icon: Icon, title, description }) {
  return (
    <article
      className="
        rounded-3xl border border-border-soft bg-white p-6
        shadow-sm transition hover:-translate-y-1 hover:shadow-xl
      "
    >
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-tertiary text-primary">
        <Icon className="text-2xl" />
      </div>

      <h3 className="text-lg font-bold text-secondary">{title}</h3>

      <p className="mt-3 text-sm leading-6 text-text-soft">{description}</p>
    </article>
  );
}
