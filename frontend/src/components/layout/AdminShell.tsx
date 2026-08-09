import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { Building2, LogOut, Users, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";
import { adminApi } from "@/lib/adminApi";

const navItems = [
  { to: "/admin/tenants", label: "Tenants", icon: Building2 },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/practice-tests", label: "Practice Tests", icon: ClipboardList },
];

// The app's first real route guard: unlike OrgAppShell/CandidateShell (which
// trust client-supplied dev headers per M6 Phase 1/2), this checks a real
// session cookie via GET /auth/me and redirects unauthenticated visitors —
// scoped only to /admin/*, doesn't touch the dev-header flow elsewhere.
export function AdminShell() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<"checking" | "ok" | "unauthorized">("checking");
  const [username, setUsername] = useState("");

  useEffect(() => {
    let cancelled = false;
    adminApi
      .me()
      .then((me) => {
        if (cancelled) return;
        setUsername(me.username);
        setStatus("ok");
      })
      .catch(() => {
        if (!cancelled) setStatus("unauthorized");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 text-sm text-neutral-500">
        Checking session…
      </div>
    );
  }

  if (status === "unauthorized") {
    return <Navigate to="/admin/login" replace />;
  }

  const handleLogout = async () => {
    await adminApi.logout();
    navigate("/admin/login", { replace: true });
  };

  return (
    <div className="flex min-h-screen bg-neutral-50">
      <aside className="flex w-60 shrink-0 flex-col border-r border-neutral-200 bg-white">
        <div className="flex items-center gap-2 border-b border-neutral-200 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-neutral-900 text-sm font-bold text-white">
            A
          </div>
          <div>
            <span className="block text-[15px] font-semibold text-neutral-900">
              Platform Admin
            </span>
          </div>
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
                    ? "bg-neutral-900 text-white"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-neutral-200 px-4 py-3">
          <p className="truncate text-sm font-medium text-neutral-900">{username}</p>
          <button
            onClick={handleLogout}
            className="mt-1 flex items-center gap-1.5 text-xs font-medium text-neutral-500 hover:text-neutral-800"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
        <Outlet />
      </div>
    </div>
  );
}

export function AdminTopbar({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-neutral-200 bg-white px-8 py-4">
      <h1 className="text-xl font-semibold text-neutral-900">{title}</h1>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
