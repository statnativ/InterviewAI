import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { AlertTriangle } from "lucide-react";

export function AntiCheatingModal({
  open,
  onClose,
  violationCount,
}: {
  open: boolean;
  onClose: () => void;
  violationCount: number;
}) {
  return (
    <Modal open={open} onClose={onClose} width="sm">
      <div className="text-center">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-status-weak-bg text-status-weak-text">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h2 className="text-base font-semibold text-neutral-900">
          Tab switch detected
        </h2>
        <p className="mt-2 text-sm text-neutral-500">
          We noticed you navigated away from the interview window. This has
          been logged and will be visible to the hiring team
          {violationCount > 1 ? ` (violation #${violationCount})` : ""}.
        </p>
        <Button className="mt-5 w-full" onClick={onClose}>
          Return to interview
        </Button>
      </div>
    </Modal>
  );
}
