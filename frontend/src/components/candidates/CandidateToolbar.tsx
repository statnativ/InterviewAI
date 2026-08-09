import type { Candidate, PipelineStage } from "@/data/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import {
  defaultFilters,
  decisionOptions,
  scoreBand,
  SOURCE_OPTIONS,
  stageOptions,
  type CandidateFilters,
  type SortKey,
} from "@/lib/candidates";
import { Search, ArrowDown, ArrowUp, X } from "lucide-react";

export function FilterSelect({
  label,
  value,
  onChange,
  options,
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-xs text-neutral-400">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-neutral-300 bg-white px-2 text-sm text-neutral-700 outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

export function SortSelect({
  value,
  dir,
  onSortKey,
  onDir,
}: {
  value: SortKey;
  dir: "asc" | "desc";
  onSortKey: (k: SortKey) => void;
  onDir: () => void;
}) {
  const keyLabel: Record<SortKey, string> = {
    score: "Score",
    name: "Name",
    appliedAt: "Applied",
    yearsExp: "Experience",
  };
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-neutral-400">Sort by</span>
      <select
        value={value}
        onChange={(e) => onSortKey(e.target.value as SortKey)}
        className="h-9 rounded-md border border-neutral-300 bg-white px-2 text-sm text-neutral-700 outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20"
      >
        {Object.entries(keyLabel).map(([k, label]) => (
          <option key={k} value={k}>
            {label}
          </option>
        ))}
      </select>
      <button
        onClick={onDir}
        className="flex h-9 items-center gap-1 rounded-md border border-neutral-300 bg-white px-2 text-sm text-neutral-600 hover:bg-neutral-50"
        title={`Sort ${dir === "asc" ? "ascending" : "descending"}`}
      >
        {dir === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}

export function FilterChip({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active
          ? "border-brand-primary bg-brand-primary-subtle text-brand-primary"
          : "border-neutral-300 text-neutral-600 hover:bg-neutral-50"
      )}
    >
      {label}
      {active && <X className="h-3 w-3" />}
    </button>
  );
}

export function FilterBar({
  filters,
  onChange,
  showSource = true,
}: {
  filters: CandidateFilters;
  onChange: (f: CandidateFilters) => void;
  showSource?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative w-56">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        <Input
          placeholder="Search name or email..."
          className="h-9 pl-9"
          value={filters.query}
          onChange={(e) => onChange({ ...filters, query: e.target.value })}
        />
      </div>
      <FilterSelect
        label="Stage"
        value={filters.stage}
        onChange={(v) => onChange({ ...filters, stage: v as CandidateFilters["stage"] })}
        options={["all", ...stageOptions]}
      />
      <FilterSelect
        label="Decision"
        value={filters.decision}
        onChange={(v) => onChange({ ...filters, decision: v as CandidateFilters["decision"] })}
        options={["all", ...decisionOptions]}
      />
      <div className="flex items-center gap-1">
        <FilterChip
          active={filters.band === "strong"}
          label="Strong"
          onClick={() => onChange({ ...filters, band: filters.band === "strong" ? "all" : "strong" })}
        />
        <FilterChip
          active={filters.band === "possible"}
          label="Possible"
          onClick={() => onChange({ ...filters, band: filters.band === "possible" ? "all" : "possible" })}
        />
        <FilterChip
          active={filters.band === "weak"}
          label="Weak"
          onClick={() => onChange({ ...filters, band: filters.band === "weak" ? "all" : "weak" })}
        />
      </div>
      {showSource && (
        <FilterSelect
          label="Source"
          value={filters.source}
          onChange={(v) => onChange({ ...filters, source: v })}
          options={["all", ...SOURCE_OPTIONS]}
        />
      )}
      <SortSelect
        value={filters.sortKey}
        dir={filters.sortDir}
        onSortKey={(k) => onChange({ ...filters, sortKey: k })}
        onDir={() =>
          onChange({ ...filters, sortDir: filters.sortDir === "asc" ? "desc" : "asc" })
        }
      />
    </div>
  );
}

export interface BulkToolbarProps {
  selectedIds: string[];
  selectedCandidates: Candidate[];
  onShortlist: () => void;
  onDecision: (d: Candidate["decision"]) => void;
  onStage: (s: PipelineStage) => void;
  onClear: () => void;
}

export function BulkToolbar({
  selectedIds,
  selectedCandidates,
  onShortlist,
  onDecision,
  onStage,
  onClear,
}: BulkToolbarProps) {
  if (selectedIds.length === 0) return null;
  const allShortlisted = selectedCandidates.every((c) => c.shortlisted);
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-brand-primary/30 bg-brand-primary-subtle/40 px-3 py-2">
      <span className="text-sm font-medium text-neutral-800">
        {selectedIds.length} selected
      </span>
      <Button size="sm" variant="secondary" onClick={onShortlist}>
        {allShortlisted ? "Unshortlist" : "Shortlist"}
      </Button>
      <Button size="sm" variant="secondary" onClick={() => onDecision("Approved")}>
        Approve
      </Button>
      <Button size="sm" variant="secondary" onClick={() => onDecision("Hold")}>
        Hold
      </Button>
      <Button size="sm" variant="danger" onClick={() => onDecision("Rejected")}>
        Reject
      </Button>
      <select
        onChange={(e) => {
          const s = e.target.value as PipelineStage;
          if (s) onStage(s);
          e.target.value = "";
        }}
        defaultValue=""
        className="h-8 rounded-md border border-neutral-300 bg-white px-2 text-xs text-neutral-700 outline-none"
      >
        <option value="" disabled>
          Move to stage…
        </option>
        {stageOptions.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <button onClick={onClear} className="ml-auto text-xs text-neutral-500 hover:text-neutral-800">
        Clear selection
      </button>
    </div>
  );
}

export function ScoreBadge({ score }: { score: number }) {
  const band = scoreBand(score);
  return (
    <Badge tone={band === "strong" ? "strong" : band === "possible" ? "possible" : "weak"}>
      {score}
    </Badge>
  );
}

export { defaultFilters };
