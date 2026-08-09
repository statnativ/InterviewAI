import type { Candidate, Job, RubricCriterion } from "@/data/types";
import { SKILL_DICTIONARY } from "./skills";

// Scoring formula ported from scripts/synthetic/convert/to_frontend_seed.py
// (derive_score). Deterministic — same job + skills always yields the same
// result, and reproduces the seeded scores exactly (rubric.label == skill name).
//
//   matched_must = Σ weight of Must-have criteria whose label ∈ candidate.skills
//   matched_nice = Σ weight of Nice-to-have criteria whose label ∈ candidate.skills
//   score = min(99, round(30 + 65·matched_must/total_must + 5·matched_nice/total_nice))
//
// "Disqualifying" criteria never contribute to the score (must/nice only).

export interface ScreeningResult {
  score: number;
  scorecard: Candidate["scorecard"];
  aiNote: string;
  compareVerdict: Candidate["compareVerdict"];
  shortlisted: boolean;
}

export function skillMatches(label: string, skills: string[]): boolean {
  const needle = label.trim().toLowerCase();
  if (!needle) return false;
  return skills.some((s) => s.trim().toLowerCase() === needle);
}

// Python's round() is half-to-even (banker's rounding); JS Math.round is half-up.
// The pipeline was authored in Python, so reproduce it exactly to match seeds.
function pyRound(x: number): number {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (Math.abs(frac - 0.5) < 1e-9) return floor % 2 === 0 ? floor : floor + 1;
  return Math.round(x);
}

export function deriveScore(
  job: Pick<Job, "rubric">,
  candidate: Pick<Candidate, "skills">
): ScreeningResult {
  const skills = candidate.skills;
  const must = job.rubric.filter((r) => r.tag === "Must-have");
  const nice = job.rubric.filter((r) => r.tag === "Nice-to-have");

  const totalMust = must.reduce((sum, r) => sum + r.weight, 0) || 1;
  const totalNice = nice.reduce((sum, r) => sum + r.weight, 0) || 1;

  const matchedMust = must
    .filter((r) => skillMatches(r.label, skills))
    .reduce((sum, r) => sum + r.weight, 0);
  const matchedNice = nice
    .filter((r) => skillMatches(r.label, skills))
    .reduce((sum, r) => sum + r.weight, 0);

  const score = Math.min(
    99,
    pyRound(30 + 65 * (matchedMust / totalMust) + 5 * (matchedNice / totalNice))
  );

  const scorecard = [...job.rubric]
    .sort((a, b) => b.weight - a.weight)
    .map((r) => {
      const hit = skillMatches(r.label, skills);
      return {
        criterion: r.label,
        weight: r.weight,
        score: hit ? 100 : 35,
        note: hit
          ? `Direct evidence of ${r.label} on resume.`
          : `${r.label} not evidenced — coverage gap against required skills.`,
      };
    });

  const covered = must.filter((r) => skillMatches(r.label, skills)).length;
  const total = must.length;
  const aiNote = `Screening score ${score}/100 — ${covered} of ${total} must-have skills covered.`;
  const compareVerdict: Candidate["compareVerdict"] =
    score >= 80 ? "Advance" : score >= 55 ? "Maybe" : "Pass";

  return {
    score,
    scorecard,
    aiNote,
    compareVerdict,
    shortlisted: score >= 80,
  };
}

// Deterministic keyword extraction against the corpus vocabulary. Falls back to
// word-boundary substring matching so "Go, PostgreSQL, Kafka" works.
export function extractSkills(text: string, dictionary: string[] = SKILL_DICTIONARY): string[] {
  const lower = ` ${text.toLowerCase()} `;
  const hits: string[] = [];
  for (const skill of dictionary) {
    const needle = skill.toLowerCase();
    const inText =
      lower.includes(` ${needle} `) ||
      lower.includes(` ${needle},`) ||
      lower.includes(` ${needle}.`) ||
      lower.includes(` ${needle};`) ||
      lower.includes(` ${needle}:`) ||
      lower.includes(` ${needle}/`) ||
      lower.includes(`${needle} `) && lower.includes(needle);
    if (inText) hits.push(skill);
  }
  // Prioritize multi-word skills first so "React Native" wins over "React".
  hits.sort((a, b) => b.length - a.length);
  return hits;
}

const REQUIRED_HINT = /\b(required|must have|must-have|need|needs|experience with|proficiency|expertise)\b/i;
const DISQUALIFYING_HINT = /\b(no |no, |disqualif|automatic reject|red flag|minimum bar)\b/i;

// Heuristic JD -> rubric generator. Deterministic keyword classification:
// skills near requirement language become Must-have, plain mentions become
// Nice-to-have, disqualifier hints become Disqualifying. Weights auto-balance
// to 100, must-haves weighted highest.
export function generateRubric(
  description: string,
  dictionary: string[] = SKILL_DICTIONARY
): RubricCriterion[] {
  const candidates = extractSkills(description, dictionary).map((label) => {
    const idx = description.toLowerCase().indexOf(label.toLowerCase());
    const before = description.slice(Math.max(0, idx - 80), idx);
    const tag = DISQUALIFYING_HINT.test(before)
      ? ("Disqualifying" as const)
      : REQUIRED_HINT.test(before)
      ? ("Must-have" as const)
      : ("Nice-to-have" as const);
    return { label, tag };
  });

  const must = candidates.filter((c) => c.tag === "Must-have").map((c) => c.label);
  const nice = candidates.filter((c) => c.tag === "Nice-to-have").map((c) => c.label);
  const disqual = candidates
    .filter((c) => c.tag === "Disqualifying")
    .map((c) => c.label);

  const total = Math.max(candidates.length, 1);
  const weights = distributeWeights({ must, nice, disqual }, total);

  const categoryFor = (label: string) => {
    if (["Go", "Python", "Java", "SQL", "TypeScript", "JavaScript", "C#", "Kotlin", "Swift", "React", "Vue.js", "Angular", "Next.js", "Node.js", "AWS", "Azure", "GCP", "Kubernetes", "Docker", "Terraform", "PostgreSQL", "Redis", "Kafka", "Django", "FastAPI", "PyTorch", "TensorFlow"].includes(label)) {
      return "Technical Skills";
    }
    if (["Team Leadership", "Technical Mentorship", "Stakeholder Communication", "Agile Delivery", "Hiring & Onboarding", "Performance Management"].includes(label)) {
      return "Soft Skills";
    }
    return "Skills";
  };

  return candidates.map(({ label, tag }) => ({
    id: `r${label.replace(/[^a-z0-9]/gi, "").slice(0, 12)}`,
    label,
    description:
      tag === "Disqualifying"
        ? `Disqualifying criterion for this role.`
        : tag === "Must-have"
        ? `Required must have competency for this role.`
        : `Preferred nice to have competency for this role.`,
    tag,
    category: categoryFor(label),
    weight: weights[label] ?? 0,
  }));
}

function distributeWeights(
  groups: { must: string[]; nice: string[]; disqual: string[] },
  _total: number
): Record<string, number> {
  const result: Record<string, number> = {};
  const buckets: Array<[string, number]> = [];
  for (const label of groups.must) buckets.push([label, 3]);
  for (const label of groups.nice) buckets.push([label, 1]);
  for (const label of groups.disqual) buckets.push([label, 1]);
  if (buckets.length === 0) return result;

  const raw = buckets.reduce((sum, [, w]) => sum + w, 0);
  let assigned = 0;
  buckets.forEach(([label, w]) => {
    const share = Math.round((w / raw) * 100);
    result[label] = share;
    assigned += share;
  });
  // Snap rounding drift back to exactly 100 on the largest weight.
  const drift = 100 - assigned;
  if (drift !== 0 && buckets.length > 0) {
    const largest = [...buckets].sort((a, b) => b[1] - a[1])[0][0];
    result[largest] += drift;
  }
  return result;
}
