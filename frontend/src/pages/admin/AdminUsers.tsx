import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { AdminTopbar } from "@/components/layout/AdminShell";
import { Card } from "@/components/ui/Card";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { adminApi, type AdminTenant, type AdminUser } from "@/lib/adminApi";

const statusTone: Record<AdminUser["status"], BadgeTone> = {
  pending: "pending",
  active: "strong",
  disabled: "neutral",
};

const roles = ["admin", "recruiter", "hiring_manager"];

export function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [tenants, setTenants] = useState<AdminTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [tenantId, setTenantId] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("recruiter");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () =>
    Promise.all([adminApi.listUsers(), adminApi.listTenants()]).then(([u, t]) => {
      setUsers(u);
      setTenants(t);
    });

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const openModal = () => {
    setTenantId(tenants[0]?.id ?? "");
    setEmail("");
    setName("");
    setRole("recruiter");
    setPassword("");
    setError("");
    setOpen(true);
  };

  const handleCreate = async () => {
    setError("");
    setSubmitting(true);
    try {
      await adminApi.createUser({ tenantId, email, name: name || undefined, role, password });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (id: string) => {
    setBusyId(id);
    try {
      await adminApi.approveUser(id);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  const handleDisable = async (id: string) => {
    setBusyId(id);
    try {
      await adminApi.disableUser(id);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <AdminTopbar
        title="Users"
        actions={
          <Button onClick={openModal} disabled={tenants.length === 0} title={tenants.length === 0 ? "Create a tenant first" : undefined}>
            <Plus className="h-4 w-4" /> New user
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Tenant</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-5 py-3 font-medium text-neutral-900">{u.email}</td>
                  <td className="px-5 py-3 text-neutral-600">{u.name ?? "—"}</td>
                  <td className="px-5 py-3 text-neutral-600">{u.tenantName}</td>
                  <td className="px-5 py-3 text-neutral-600">{u.role}</td>
                  <td className="px-5 py-3">
                    <Badge tone={statusTone[u.status]}>{u.status}</Badge>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {u.status === "pending" && (
                      <Button size="sm" variant="secondary" disabled={busyId === u.id} onClick={() => handleApprove(u.id)}>
                        Approve
                      </Button>
                    )}
                    {u.status === "active" && (
                      <Button size="sm" variant="secondary" disabled={busyId === u.id} onClick={() => handleDisable(u.id)}>
                        Disable
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-neutral-400">
                    No users yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      </div>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New user"
        description="New users start pending until approved."
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={submitting || !tenantId || !email || !password}>
              {submitting ? "Creating…" : "Create user"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="user-tenant">Tenant</Label>
            <select
              id="user-tenant"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="user-email">Email</Label>
            <Input id="user-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="user-name">Name</Label>
            <Input id="user-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="user-role">Role</Label>
            <select
              id="user-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
            >
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="user-password">Temporary password</Label>
            <Input id="user-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p className="text-sm text-status-weak-text">{error}</p>}
        </div>
      </Modal>
    </>
  );
}
