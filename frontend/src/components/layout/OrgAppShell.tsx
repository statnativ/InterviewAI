import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  Briefcase,
  Users,
  Zap,
  PlayCircle,
  HelpCircle,
  Bookmark,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar } from "@/components/ui/Avatar";
import { useAppStore } from "@/store/useAppStore";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/candidates", label: "Candidates", icon: Users },
  { to: "/interviews", label: "Interviews", icon: MessageSquare },
  { to: "/jobs", label: "Jobs", icon: Briefcase },
  { to: "/practices", label: "Practices", icon: Zap },
  { to: "/sessions", label: "Sessions", icon: PlayCircle },
  { to: "/questions", label: "Questions", icon: HelpCircle },
  { to: "/answer-bank", label: "Answer Bank", icon: Bookmark },
];

export function OrgAppShell({ children }: { children: ReactNode }) {
  const currentUser = useAppStore((s) => s.currentUser);

  return (
    <div className="flex min-h-screen bg-neutral-50">
      <aside className="flex w-60 shrink-0 flex-col border-r border-neutral-200 bg-white">
        <div className="flex items-center gap-2 border-b border-neutral-200 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-primary text-sm font-bold text-white">
            A
          </div>
          <span className="text-[15px] font-semibold text-neutral-900">
            Statnativ
          </span>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-primary-subtle text-brand-primary"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2.5 border-t border-neutral-200 px-4 py-3">
          <Avatar name={currentUser.name} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-neutral-900">
              {currentUser.name}
            </p>
            <p className="truncate text-xs text-neutral-500">
              {currentUser.company}
            </p>
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
        {children}
      </div>
    </div>
  );
}

export function PageTopbar({
  breadcrumb,
  title,
  actions,
}: {
  breadcrumb?: string;
  title: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-8 py-4">
      <div>
        {breadcrumb && (
          <p className="text-xs text-neutral-400">{breadcrumb}</p>
        )}
        <h1 className="text-xl font-semibold text-neutral-900">{title}</h1>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
