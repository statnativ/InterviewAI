import { cn } from "@/lib/utils";

export function scoreTone(score: number): "strong" | "possible" | "weak" {
  if (score >= 80) return "strong";
  if (score >= 55) return "possible";
  return "weak";
}

const label: Record<string, string> = {
  strong: "STRONG",
  possible: "POSSIBLE",
  weak: "WEAK",
};

export function ScorePill({
  score,
  size = "md",
  className,
}: {
  score: number;
  size?: "sm" | "md";
  className?: string;
}) {
  const tone = scoreTone(score);
  const sizeClasses =
    size === "sm" ? "h-9 w-9 text-sm" : "h-12 w-12 text-base";
  return (
    <div className={cn("flex flex-col items-center gap-0.5", className)}>
      <div
        className={cn(
          "flex items-center justify-center rounded-lg border font-bold",
          sizeClasses,
          tone === "strong" &&
            "bg-status-strong-bg text-status-strong-text border-status-strong-border",
          tone === "possible" &&
            "bg-status-possible-bg text-status-possible-text border-status-possible-border",
          tone === "weak" &&
            "bg-status-weak-bg text-status-weak-text border-status-weak-border"
        )}
      >
        {score}
      </div>
      {size === "md" && (
        <span
          className={cn(
            "text-[10px] font-semibold tracking-wide",
            tone === "strong" && "text-status-strong-text",
            tone === "possible" && "text-status-possible-text",
            tone === "weak" && "text-status-weak-text"
          )}
        >
          {label[tone]}
        </span>
      )}
    </div>
  );
}
