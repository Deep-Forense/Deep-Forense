import whaleIcon from "@/assets/brand/DeepForenseLogo.png";

export default function Logo({ variant = "dark" }) {
  const textColor = variant === "light" ? "text-white" : "text-secondary";

  return (
    <div className="flex items-center gap-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-tertiary">
        <img
          src={whaleIcon}
          alt="DeepForense"
          className="h-6 w-6 object-contain"
        />
      </div>

      <span className={`text-lg font-bold tracking-tight ${textColor}`}>
        DeepForense
      </span>
    </div>
  );
}
