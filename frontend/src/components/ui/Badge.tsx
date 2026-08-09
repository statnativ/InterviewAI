import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type BadgeTone =
  | "strong"
  | "possible"
  | "weak"
  | "pending"
  | "info"
  | "neutral"
  | "brand";

const toneClasses: Record<BadgeTone, string> = {
  strong: "bg-status-strong-bg text-status-strong-text border-status-strong-border",
  possible:
    "bg-status-possible-bg text-status-possible-text border-status-possible-border",
  weak: "bg-status-weak-bg text-status-weak-text border-status-weak-border",
  pending:
    "bg-status-pending-bg text-status-pending-text border-status-pending-border",
  info: "bg-status-info-bg text-status-info-text border-status-info-border",
  neutral: "bg-neutral-100 text-neutral-700 border-neutral-200",
  brand: "bg-brand-primary-subtle text-brand-primary border-brand-primary/20",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
