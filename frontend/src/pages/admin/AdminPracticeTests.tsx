import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { AdminTopbar } from "@/components/layout/AdminShell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { adminApi, type AdminPracticeTest, type AdminTenant } from "@/lib/adminApi";

const modes = ["Chat", "Voice", "Avatar"];

export function AdminPracticeTests() {
  const [tests, setTests] = useState<AdminPracticeTest[]>([]);
  const [tenants, setTenants] = useState<AdminTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const [tenantId, setTenantId] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState("Chat");
  const [duration, setDuration] = useState(30);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () =>
    Promise.all([adminApi.listPracticeTests(), adminApi.listTenants()]).then(([p, t]) => {
      setTests(p);
      setTenants(t);
    });

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const openModal = () => {
    setTenantId(tenants[0]?.id ?? "");
    setTitle("");
    setMode("Chat");
    setDuration(30);
    setError("");
    setOpen(true);
  };

  const handleCreate = async () => {
    setError("");
    setSubmitting(true);
    try {
      await adminApi.createPracticeTest({ tenantId, title, mode, duration });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create practice test");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <AdminTopbar
        title="Practice Tests"
        actions={
          <Button onClick={openModal} disabled={tenants.length === 0} title={tenants.length === 0 ? "Create a tenant first" : undefined}>
            <Plus className="h-4 w-4" /> New practice test
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-5 py-3">Title</th>
                <th className="px-5 py-3">Tenant</th>
                <th className="px-5 py-3">Mode</th>
                <th className="px-5 py-3">Duration</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {tests.map((p) => (
                <tr key={p.id}>
                  <td className="px-5 py-3 font-medium text-neutral-900">{p.title}</td>
                  <td className="px-5 py-3 text-neutral-600">{p.tenantName}</td>
                  <td className="px-5 py-3 text-neutral-600">{p.mode}</td>
                  <td className="px-5 py-3 text-neutral-600">{p.duration} min</td>
                  <td className="px-5 py-3">
                    <Badge tone="strong">{p.status}</Badge>
                  </td>
                </tr>
              ))}
              {!loading && tests.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-neutral-400">
                    No practice tests yet.
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
        title="New practice test"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={submitting || !tenantId || !title}>
              {submitting ? "Creating…" : "Create practice test"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="pt-tenant">Tenant</Label>
            <select
              id="pt-tenant"
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
            <Label htmlFor="pt-title">Title</Label>
            <Input id="pt-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="pt-mode">Mode</Label>
            <select
              id="pt-mode"
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary"
            >
              {modes.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="pt-duration">Duration (minutes)</Label>
            <Input
              id="pt-duration"
              type="number"
              min={5}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
            />
          </div>
          {error && <p className="text-sm text-status-weak-text">{error}</p>}
        </div>
      </Modal>
    </>
  );
}
