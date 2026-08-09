// UX audit re-run using Playwright, driven directly (no @playwright/test runner) so we can
// capture a labeled PASS/FAIL screenshot for every check regardless of outcome, plus a set of
// plain "tour" screenshots of the main screens. Mirrors the checks in
// ProductResearch/UX Review.md (findings #1-#11) against the live dev stack.
//
// Prereqs: backend on :8000, frontend dev server on :5173 (see Runbook.md), Chromium installed
// via `npx playwright install chromium`.
//
// Usage: node e2e/ux-audit.mjs

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");
mkdirSync(OUT_DIR, { recursive: true });

const BASE = "http://localhost:5173";
const API = "http://127.0.0.1:8000";

// Fixed reference IDs pulled from the live seeded DB at audit time.
const JOB_RAG = "145def63-3e04-4a11-a9e7-f8fec8dac402"; // has a JD, no rubric-editing UI
const JOB_DANIEL = "20f92100-3caf-4c54-8b67-66838d70c421"; // Daniel Wright's job
const CANDIDATE_DANIEL = "dccbc1a6-dee2-4dba-af88-756946e9a015";
const INTERVIEW_ARCHIVED = "49cc124b-3b1c-4191-a389-cb71506918cd"; // Staff SRE, Avatar, Archived
const INTERVIEW_VOICE = "830fbf98-491b-4524-85dc-278c5d17e5cf"; // Product Designer, Voice, Active

const results = [];
let n = 0;

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

async function shot(page, name) {
  n += 1;
  const file = `${String(n).padStart(2, "0")}-${slug(name)}.png`;
  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: false });
  return file;
}

/** Run a check: screenshot first (current state), then evaluate, rename file with PASS/FAIL. */
async function check(page, { id, name, tour = false, fn }) {
  n += 1;
  const base = `${String(n).padStart(2, "0")}-${slug(name)}`;
  let passed = null;
  let detail = "";
  try {
    const r = await fn();
    passed = typeof r === "boolean" ? r : true;
    detail = typeof r === "string" ? r : "";
  } catch (e) {
    passed = false;
    detail = e.message.split("\n")[0];
  }
  const tag = tour ? "TOUR" : passed ? "PASS" : "FAIL";
  const file = `${base}-${tag}.png`;
  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: false });
  const row = { id, name, tag, detail, file };
  results.push(row);
  console.log(`[${tag}] ${id ? id + " — " : ""}${name}${detail ? " :: " + detail : ""}`);
  return passed;
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // ---- Tour: org login + dashboard ----
  // Login form fields are pre-filled (defaultValue) and submit just navigates on preventDefault
  // — no real auth yet (per Project Overview's M6 status) — so signing in is just a click.
  await page.goto(`${BASE}/login`);
  await check(page, { name: "org login screen", tour: true, fn: async () => true });

  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL(`${BASE}/dashboard`);
  await check(page, { name: "dashboard after sign in", tour: true, fn: async () => true });

  await page.goto(`${BASE}/jobs`);
  await check(page, { name: "jobs list", tour: true, fn: async () => true });

  // ---- Finding #1: blank-page-on-deep-link bug (fixed) ----
  // 1a. Hard navigation straight to a nested job/candidate/interview route with a REAL id.
  await page.goto(`${BASE}/jobs/${JOB_DANIEL}/pipeline`);
  await check(page, {
    id: "#1a",
    name: "hard nav to pipeline board renders content (not blank)",
    fn: async () => {
      await page.waitForTimeout(500);
      const heading = await page.getByText("Pipeline Board").count();
      const bodyText = (await page.locator("body").innerText()).trim();
      if (heading === 0) throw new Error("Pipeline Board heading not found — blank/broken page");
      if (bodyText.length < 100) throw new Error(`page body suspiciously empty (${bodyText.length} chars)`);
      return true;
    },
  });

  // 1b. Hard navigation to a candidate detail deep link (the "Copy link" scenario).
  await page.goto(`${BASE}/jobs/${JOB_DANIEL}/candidates/${CANDIDATE_DANIEL}`);
  await check(page, {
    id: "#1b",
    name: "hard nav to candidate detail deep link renders content",
    fn: async () => {
      await page.waitForTimeout(500);
      const name = await page.getByRole("heading", { name: "Daniel Wright" }).count();
      if (name === 0) throw new Error("candidate name heading not found — blank/broken page");
      return true;
    },
  });

  // 1c. A genuinely bad id should show a not-found state, not a blank page.
  await page.goto(`${BASE}/jobs/00000000-0000-0000-0000-000000000000`);
  await check(page, {
    id: "#1c",
    name: "bad job id shows not-found state, not blank",
    fn: async () => {
      await page.waitForTimeout(500);
      const notFound = await page.getByText(/doesn't exist or may have been removed/i).count();
      if (notFound === 0) throw new Error("no not-found message rendered");
      return true;
    },
  });

  // ---- Finding #4: rubric editor still doesn't let you edit weights (deliberately out of scope) ----
  await page.goto(`${BASE}/jobs/${JOB_RAG}`);
  await check(page, {
    id: "#4",
    name: "rubric weight is a real editable input (known open gap, expected to fail)",
    fn: async () => {
      await page.waitForTimeout(500);
      const weightBox = page.locator("span", { hasText: "%" }).first();
      const tag = await weightBox.evaluate((el) => el.tagName);
      if (tag !== "INPUT") {
        throw new Error(`weight is rendered as a <${tag.toLowerCase()}>, not an editable field — real editing is still unbuilt (tracked, out of scope)`);
      }
      return true;
    },
  });

  // ---- Finding #5: boilerplate rubric descriptions (fixed) ----
  await check(page, {
    id: "#5-before",
    name: "rubric before regenerate",
    tour: true,
    fn: async () => true,
  });
  await page.getByRole("button", { name: "Regenerate rubric" }).click();
  await page.waitForTimeout(800);
  await check(page, {
    id: "#5",
    name: "rubric criteria have distinct descriptions after regenerate",
    fn: async () => {
      const descs = await page
        .locator("div.divide-y.divide-neutral-100 p.text-neutral-500")
        .allInnerTexts();
      const candidateDescs = descs.filter((d) => d.length > 20);
      const unique = new Set(candidateDescs);
      if (candidateDescs.length < 2) throw new Error("not enough criteria to compare");
      if (unique.size < 2) throw new Error("all criteria still share the identical description");
      return true;
    },
  });

  // ---- Finding #10: Jobs<->Interviews IA disconnect (fixed by M3) ----
  await check(page, {
    id: "#10",
    name: "job detail links to its interview",
    fn: async () => {
      // Exclude the OrgAppShell sidebar, which always has an "Interviews" nav link regardless
      // of page — that's chrome, not a job<->interview cross-link, and would false-PASS this.
      const mainText = await page.evaluate(() => {
        const clone = document.body.cloneNode(true);
        clone.querySelector("aside")?.remove();
        return clone.innerText;
      });
      if (/interview/i.test(mainText)) return true;
      throw new Error("JobDetail's main content has no visible reference to an associated interview (only the sidebar's generic nav link exists)");
    },
  });

  // ---- Finding #11: JobsList vs CandidatesList filter parity (still open) ----
  await page.goto(`${BASE}/jobs`);
  await check(page, {
    id: "#11",
    name: "jobs list has status/department filters like candidates list (known open gap, expected to fail)",
    fn: async () => {
      const selects = await page.locator("select").count();
      if (selects === 0) throw new Error("JobsList has only a text search box, no status/department filter — still a gap vs. CandidatesList");
      return true;
    },
  });

  // ---- Findings #7: accessibility fixes (fixed) ----
  await page.goto(`${BASE}/candidates`);
  await check(page, {
    id: "#7a",
    name: "candidate row button has a real accessible name",
    fn: async () => {
      await page.waitForTimeout(500);
      const btn = page.getByRole("button", { name: /Open .+'s profile/ }).first();
      const count = await btn.count();
      if (count === 0) throw new Error("no candidate row button with an accessible name found");
      return true;
    },
  });

  // ---- Finding #9: raw ISO timestamps (still open) ----
  await check(page, {
    id: "#9",
    name: "applied date is human-formatted, not raw ISO (known open gap, expected to fail)",
    fn: async () => {
      const bodyText = await page.locator("body").innerText();
      if (/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(bodyText)) {
        throw new Error("raw ISO timestamp still visible in CandidatesList rows");
      }
      return true;
    },
  });

  await page.goto(`${BASE}/interviews`);
  await check(page, {
    id: "#7b",
    name: "interview card is keyboard-reachable with a real accessible name",
    fn: async () => {
      await page.waitForTimeout(500);
      const card = page.getByRole("button", { name: /Edit .+/ }).first();
      const count = await card.count();
      if (count === 0) throw new Error("no interview card exposed as an accessible/keyboard button");
      const tabindex = await card.getAttribute("tabindex");
      if (tabindex !== "0") throw new Error(`card tabindex is "${tabindex}", not keyboard-focusable`);
      return true;
    },
  });

  // ---- Finding #6: decorative SSO buttons (neutralized) ----
  await page.goto(`${BASE}/login`);
  await check(page, {
    id: "#6a",
    name: "org login SSO buttons are disabled, not silently dead",
    fn: async () => {
      const google = page.getByRole("button", { name: "Google" });
      const disabled = await google.isDisabled();
      if (!disabled) throw new Error("Google SSO button is not disabled — still looks fully functional");
      return true;
    },
  });

  await page.goto(`${BASE}/candidate/login`);
  await check(page, {
    id: "#6b",
    name: "candidate login SSO buttons are disabled, not silently dead",
    fn: async () => {
      const google = page.getByRole("button", { name: "Google" });
      const disabled = await google.isDisabled();
      if (!disabled) throw new Error("Google SSO button is not disabled — still looks fully functional");
      return true;
    },
  });

  // ---- Candidate side: log in as Sophia ----
  await page.goto(`${BASE}/candidate/login`);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL(`${BASE}/candidate`);
  await check(page, { name: "candidate landing page", tour: true, fn: async () => true });

  // ---- Finding #3: archived interview no longer offered as startable (fixed) ----
  await check(page, {
    id: "#3",
    name: "archived interview does not appear as an upcoming/startable interview",
    fn: async () => {
      const bodyText = await page.locator("body").innerText();
      if (/Staff SRE — Incident Leadership/.test(bodyText)) {
        throw new Error("Archived interview is still listed as upcoming/startable");
      }
      return true;
    },
  });

  // ---- Finding #2: mode-mismatch routing (fixed) ----
  await check(page, {
    id: "#2",
    name: "Voice-mode Start button routes to consent flow, not avatar disclosure",
    fn: async () => {
      // Scope to the specific row by title text — "Start" alone fuzzy-matches the unrelated
      // "Start a practice session" button too, which sits later in the same DOM subtree.
      const row = page
        .locator("div.rounded-md.border.border-neutral-200.p-4")
        .filter({ hasText: "Product Designer" });
      await row.getByRole("button", { name: "Start" }).click();
      await page.waitForTimeout(400);
      const url = page.url();
      if (url.includes("/avatar/")) {
        throw new Error(`Voice-mode interview routed to ${url} — still going through the Avatar disclosure flow`);
      }
      if (!url.includes("/session/") || !url.includes("/consent")) {
        throw new Error(`unexpected route after Start: ${url}`);
      }
      return true;
    },
  });

  // ---- Finding #8: Avatar flow skips the device-readiness check (still open) ----
  // Independent repro: go straight to the avatar disclosure screen and continue.
  await page.goto(`${BASE}/avatar/${INTERVIEW_ARCHIVED.replace(INTERVIEW_ARCHIVED, INTERVIEW_ARCHIVED)}/disclosure`);
  // (Archived interview still exists as a record; disclosure screen doesn't filter by status.)
  await check(page, {
    id: "#8-before",
    name: "avatar disclosure screen",
    tour: true,
    fn: async () => true,
  });
  const continueBtn = page.getByRole("button", { name: /I understand, continue/i });
  if ((await continueBtn.count()) > 0) {
    await continueBtn.click();
    await page.waitForTimeout(600);
  }
  await check(page, {
    id: "#8",
    name: "avatar flow includes a device/camera check before the interview (known open gap, expected to fail)",
    fn: async () => {
      const url = page.url();
      if (/\/device/.test(url)) return true; // would mean a device check step exists
      throw new Error(`Avatar flow went straight to ${url} with no device-check step — camera/mic problems surface only after the interview starts`);
    },
  });

  await browser.close();

  // ---- Report ----
  const summary = {
    generatedAt: new Date().toISOString(),
    total: results.length,
    pass: results.filter((r) => r.tag === "PASS").length,
    fail: results.filter((r) => r.tag === "FAIL").length,
    tour: results.filter((r) => r.tag === "TOUR").length,
    results,
  };
  writeFileSync(path.join(OUT_DIR, "report.json"), JSON.stringify(summary, null, 2));

  const md = [
    "# UX audit — Playwright re-run",
    "",
    `Generated ${summary.generatedAt}`,
    "",
    `**${summary.pass} PASS · ${summary.fail} FAIL (known open items) · ${summary.tour} tour screenshots**`,
    "",
    "| # | Finding | Result | Detail | Screenshot |",
    "|---|---|---|---|---|",
    ...results
      .filter((r) => r.tag !== "TOUR")
      .map((r) => `| ${r.id ?? ""} | ${r.name} | ${r.tag} | ${r.detail ?? ""} | ${r.file} |`),
    "",
    "## Tour screenshots",
    "",
    ...results.filter((r) => r.tag === "TOUR").map((r) => `- ${r.name} — ${r.file}`),
  ].join("\n");
  writeFileSync(path.join(OUT_DIR, "report.md"), md);

  console.log("\n===");
  console.log(`${summary.pass} PASS, ${summary.fail} FAIL, ${summary.tour} tour shots`);
  console.log(`Screenshots + report saved to ${OUT_DIR}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
