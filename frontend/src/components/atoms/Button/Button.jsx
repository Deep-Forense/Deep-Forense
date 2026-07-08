const variants = {
  primary:
    "bg-primary text-white hover:bg-primary-dark shadow-lg shadow-primary/20",
  secondary:
    "bg-secondary text-white hover:bg-slate-900 shadow-lg shadow-secondary/20",
  outline:
    "border border-border-soft bg-white text-secondary hover:border-primary hover:text-primary",
  ghost: "bg-transparent text-secondary hover:bg-muted-soft",
};

const sizes = {
  sm: "px-4 py-2 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-6 py-3 text-base",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) {
  return (
    <button
      className={`
        inline-flex items-center justify-center gap-2 rounded-full
        font-semibold transition-all duration-200 disabled:cursor-not-allowed
        disabled:opacity-60
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
}
