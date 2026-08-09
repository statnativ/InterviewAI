import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center gap-2 py-24 text-sm text-neutral-400">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function NotFoundState({
  message,
  backLabel,
  onBack,
}: {
  message: string;
  backLabel: string;
  onBack: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-24 text-center">
      <p className="text-sm text-neutral-400">{message}</p>
      <Button variant="secondary" size="sm" onClick={onBack}>
        {backLabel}
      </Button>
    </div>
  );
}
