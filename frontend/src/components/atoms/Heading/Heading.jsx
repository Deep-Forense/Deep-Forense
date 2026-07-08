const variants = {
  h1: "text-4xl font-extrabold tracking-tight md:text-6xl",
  h2: "text-3xl font-bold tracking-tight md:text-4xl",
  h3: "text-2xl font-bold",
  h4: "text-xl font-semibold",
};

export default function Heading({ children, as = "h2", className = "" }) {
  const Tag = as;

  return (
    <Tag className={`${variants[as] || variants.h2} ${className}`}>
      {children}
    </Tag>
  );
}
