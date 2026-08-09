import { type ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  width = "md",
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: "sm" | "md" | "lg" | "xl";
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const widthClass = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-2xl",
  }[width];

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-neutral-900/40 backdrop-blur-[1px]"
        onClick={onClose}
      />
      <div
        className={cn(
          "relative w-full rounded-lg bg-white shadow-xl",
          widthClass
        )}
      >
        {(title || description) && (
          <div className="flex items-start justify-between border-b border-neutral-200 px-6 py-4">
            <div>
              {title && (
                <h2 className="text-base font-semibold text-neutral-900">
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-0.5 text-sm text-neutral-500">
                  {description}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="max-h-[70vh] overflow-y-auto px-6 py-5">
          {children}
        </div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-neutral-200 px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
