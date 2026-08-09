import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { AdminTopbar } from "@/components/layout/AdminShell";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { adminApi, type AdminTenant } from "@/lib/adminApi";
import { formatRelativeTime } from "@/lib/utils";

export function AdminTenants() {
  const [tenants, setTenants] = useState<AdminTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => adminApi.listTenants().then(setTenants);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    setError("");
    setSubmitting(true);
    try {
      await adminApi.createTenant({ name, slug });
      setOpen(false);
      setName("");
      setSlug("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tenant");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <AdminTopbar
        title="Tenants"
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" /> New tenant
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Slug</th>
                <th className="px-5 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {tenants.map((t) => (
                <tr key={t.id}>
                  <td className="px-5 py-3 font-medium text-neutral-900">{t.name}</td>
                  <td className="px-5 py-3 text-neutral-600">{t.slug}</td>
                  <td className="px-5 py-3 text-neutral-500">{formatRelativeTime(t.createdAt)}</td>
                </tr>
              ))}
              {!loading && tenants.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-5 py-8 text-center text-neutral-400">
                    No tenants yet.
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
        title="New tenant"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={submitting || !name || !slug}>
              {submitting ? "Creating…" : "Create tenant"}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <Label htmlFor="tenant-name">Name</Label>
            <Input id="tenant-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Corp" />
          </div>
          <div>
            <Label htmlFor="tenant-slug">Slug</Label>
            <Input id="tenant-slug" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="acme-corp" />
          </div>
          {error && <p className="text-sm text-status-weak-text">{error}</p>}
        </div>
      </Modal>
    </>
  );
}
