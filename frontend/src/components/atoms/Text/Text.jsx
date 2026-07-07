const variants = {
  body: "text-base leading-7",
  small: "text-sm leading-6",
  caption: "text-xs leading-5",
};

export default function Text({ children, variant = "body", className = "" }) {
  return <p className={`${variants[variant]} ${className}`}>{children}</p>;
}
