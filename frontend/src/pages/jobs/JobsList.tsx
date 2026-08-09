import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { OrgAppShell, PageTopbar } from "@/components/layout/OrgAppShell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppStore } from "@/store/useAppStore";
import { NewJobModal } from "./NewJobModal";
import { Plus, Search } from "lucide-react";
import type { JobStatus } from "@/data/types";

const statusTone: Record<JobStatus, "strong" | "pending" | "possible" | "neutral"> = {
  Open: "strong",
  Draft: "pending",
  Paused: "possible",
  Closed: "neutral",
};

export function JobsList() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const jobs = useAppStore((s) => s.jobs);
  const candidates = useAppStore((s) => s.candidates);
  const [query, setQuery] = useState("");

  const filtered = jobs.filter((j) =>
    j.title.toLowerCase().includes(query.toLowerCase())
  );

  const closeModal = () => {
    params.delete("new");
    setParams(params, { replace: true });
  };

  return (
    <OrgAppShell>
      <PageTopbar
        title="Jobs"
        actions={
          <Button onClick={() => setParams({ new: "1" })}>
            <Plus className="h-4 w-4" /> New job
          </Button>
        }
      />

      <div className="flex-1 px-8 py-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="relative w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <Input
              placeholder="Search jobs..."
              className="pl-9"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>

        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="px-5 py-3">Job title</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Location</th>
                <th className="px-5 py-3">Candidates</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filtered.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="cursor-pointer hover:bg-neutral-50"
                >
                  <td className="px-5 py-4 font-medium text-neutral-900">{job.title}</td>
                  <td className="px-5 py-4 text-neutral-600">{job.department}</td>
                  <td className="px-5 py-4 text-neutral-600">{job.location}</td>
                  <td className="px-5 py-4 text-neutral-600">
                    {candidates.filter((c) => c.jobId === job.id).length}
                  </td>
                  <td className="px-5 py-4">
                    <Badge tone={statusTone[job.status]}>{job.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <NewJobModal open={params.get("new") === "1"} onClose={closeModal} />
    </OrgAppShell>
  );
}
