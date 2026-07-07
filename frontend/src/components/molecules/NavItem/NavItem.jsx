export default function NavItem({ href = "#", children }) {
  return (
    <a
      href={href}
      className="text-sm font-medium text-slate-600 transition hover:text-primary"
    >
      {children}
    </a>
  );
}
