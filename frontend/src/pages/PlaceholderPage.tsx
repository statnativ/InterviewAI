import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card, CardContent } from "@/components/ui/Card";
import type { LucideIcon } from "lucide-react";

export function PlaceholderPage({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <OrgAppShell>
      <PageTopbar title={title} />
      <div className="flex-1 px-8 py-6">
        <Card>
          <CardContent className="flex flex-col items-center py-16 text-center">
            <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-primary-subtle text-brand-primary">
              <Icon className="h-6 w-6" />
            </span>
            <h2 className="text-base font-semibold text-neutral-900">{title}</h2>
            <p className="mt-1 max-w-sm text-sm text-neutral-500">{description}</p>
          </CardContent>
        </Card>
      </div>
    </OrgAppShell>
  );
}
