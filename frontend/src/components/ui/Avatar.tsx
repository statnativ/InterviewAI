import { cn } from "@/lib/utils";
import { initials } from "@/lib/utils";

const palette = [
  "bg-brand-primary/15 text-brand-primary",
  "bg-status-info-bg text-status-info-text",
  "bg-status-strong-bg text-status-strong-text",
  "bg-status-possible-bg text-status-possible-text",
];

function hashName(name: string) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return h;
}

export function Avatar({
  name,
  size = "md",
  className,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const sizeClasses = {
    sm: "h-7 w-7 text-xs",
    md: "h-9 w-9 text-sm",
    lg: "h-12 w-12 text-base",
  }[size];
  const color = palette[hashName(name) % palette.length];

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full font-semibold",
        sizeClasses,
        color,
        className
      )}
    >
      {initials(name)}
    </div>
  );
}
