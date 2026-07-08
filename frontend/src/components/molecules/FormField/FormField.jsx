import { Input } from "@/components/atoms/Input";

export default function FormField({ label, hint, ...inputProps }) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center justify-between gap-3 text-xs font-semibold text-secondary">
        {label}
        {hint}
      </span>
      <Input {...inputProps} />
    </label>
  );
}
