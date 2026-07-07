import { FaApple, FaFacebookF, FaGoogle, FaMicrosoft } from "react-icons/fa";

const providers = [
  { name: "Google", icon: FaGoogle, color: "text-red-500" },
  { name: "Facebook", icon: FaFacebookF, color: "text-blue-600" },
  { name: "Microsoft", icon: FaMicrosoft, color: "text-sky-600" },
  { name: "Apple", icon: FaApple, color: "text-slate-900" },
];

export default function SocialAuthButtons() {
  return (
    <div className="grid grid-cols-4 gap-2.5">
      {providers.map(({ name, icon: Icon, color }) => (
        <button
          key={name}
          type="button"
          title={`${name} (demostración)`}
          aria-label={`Continuar con ${name}`}
          className="flex h-11 items-center justify-center rounded-xl border border-border-soft bg-white transition hover:-translate-y-0.5 hover:border-primary hover:shadow-md"
        >
          <Icon className={color} />
        </button>
      ))}
    </div>
  );
}
