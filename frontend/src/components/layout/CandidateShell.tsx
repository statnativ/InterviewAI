import type { ReactNode } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { useAppStore } from "@/store/useAppStore";

export function CandidateShell({
  children,
  minimal = false,
}: {
  children: ReactNode;
  minimal?: boolean;
}) {
  const candidate = useAppStore((s) => s.currentCandidate);

  return (
    <div className="flex min-h-screen flex-col bg-neutral-50">
      <header className="flex items-center justify-between border-b border-neutral-200 bg-white px-8 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-primary text-xs font-bold text-white">
            A
          </div>
          <span className="text-sm font-semibold text-neutral-900">
            Statnativ
          </span>
        </div>
        {!minimal && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-neutral-500">
              {candidate.name}
            </span>
            <Avatar name={candidate.name} size="sm" />
          </div>
        )}
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}
