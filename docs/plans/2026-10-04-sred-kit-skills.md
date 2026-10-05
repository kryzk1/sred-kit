# sred-kit Skills, Example and Validation Plan (Plan 2 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Skill files are built with superpowers:writing-skills (baseline failure first). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the tested engine into a usable kit: the `sred` skill (router plus phase references), the do-not and T661 references, a fictional example claim, and evidence that it works: scenario tests of the skill, an onboarding test, a fresh-session dry run with a forced resume, and a backtest on the reference claimant's real history.

**Architecture:** `skills/sred/SKILL.md` is a short router: resume procedure, hard rules, a phase table pointing to one reference file per phase, and the script commands. Judgment lives in prose references; everything mechanical stays in the Plan 1 scripts. Skill prose is written test-first: each behavior-shaping file is preceded by baseline scenario runs without it, then re-run with it.

**Tech Stack:** Markdown skill files; Python 3.11 standard library for the example generator; Plan 1 scripts; Claude subagents for scenario, onboarding and dry-run tests.

**Spec:** `docs/specs/2026-10-04-sred-kit-design.md`. **Depends on:** Plan 1 (`docs/plans/2026-10-04-sred-kit-engine.md`) merged or present on the branch.

## Global Constraints

- Everything in Plan 1's Global Constraints still applies (no company data in `skills/`, `examples/`, `tests/`; leak test must pass with `tests/backtest/local.toml` present).
- Skill frontmatter: `name` letters/numbers/hyphens; `description` starts with "Use when", third person, triggers only, no workflow summary, under 500 characters.
- `SKILL.md` stays under 600 words; detail goes in `references/`.
- Prose invokes scripts through the interpreter with the skill's base directory: `python3 "<skill-dir>/scripts/<name>.py" …`, where `<skill-dir>` is the "Base directory for this skill" Claude Code prints when the skill loads.
- Reference files are plain Markdown, written for an agent, in the second person, with exact commands and file names from the spec §12.
- Backtest outputs that contain the reference claimant's data are written only under `/Users/kryz/Developer/SR&ED/backtest/` (private, outside the repo).
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **An agent resuming a half-finished claim** re-does discovery or changes a locked decision instead of continuing from `STATE.md`. Covered by scenario S1 (Task 3).
2. **A claimant gives a number from memory that the evidence contradicts.** The agent must not write the unverified number. Scenario S3.
3. **A reviewer or claimant asks to restructure locked scope late.** The agent records a superseding decision and the artifacts to regenerate; it does not silently restructure. Scenario S4.
4. **Onboarding with partial answers.** Unknowns become open questions tagged with the phase they block; `check.py setup` reports exactly those. Task 6.
5. **A run interrupted mid-phase.** A new session continues from `STATE.md` alone. Task 7.

---

### Task 1: Vendor `sred-audit` unchanged

**Files:**
- Create: `skills/sred-audit/SKILL.md` (byte-identical copy of `~/.claude/skills/sred-audit/SKILL.md`)

- [ ] **Step 1:** `mkdir -p skills/sred-audit && cp ~/.claude/skills/sred-audit/SKILL.md skills/sred-audit/SKILL.md`
- [ ] **Step 2:** `cmp ~/.claude/skills/sred-audit/SKILL.md skills/sred-audit/SKILL.md && .venv/bin/pytest tests/test_leak.py -q` → no output from `cmp`; leak tests PASS.
- [ ] **Step 3:** Commit `chore: vendor the sred-audit rubric unchanged`.

---

### Task 2: Acme example claim folder and generator

**Files:**
- Create: `examples/acme/README.md`, `examples/acme/sred.toml`, `examples/acme/roster.csv`, `examples/acme/prior/FY2026-T661-Part2.md`, `examples/acme/generate.py`
- Generated and committed: `examples/acme/exports/jira.csv`, `examples/acme/exports/slack/…`, `examples/acme/evidence/raw/gitlab/*.json`, `examples/acme/evidence/raw/MANIFEST.json`
- Test: `tests/test_example.py`

**Interfaces:**
- Consumes: Plan 1 scripts (`index.py build`, `check.py setup`, `time_basis.py --preliminary`), `sredlib.manifest.record`.
- Produces: a complete, fictional claim folder on a stack different from the reference claimant (GitLab via pre-captured raw files, Jira CSV export, Slack export folder) that the dry run (Task 7) and the scenarios (Task 3) copy.

**Content requirements** (the generator is deterministic: same output on every run):
- Company Acme Robotics Inc., fiscal year 2026-08-01 to 2027-07-31, `timezone = "America/Vancouver"`, `limits.mode = "words"`, all eligibility answers "none", `first_claim = false`, `prior_titles = ["Adaptive Grasp Planning Under Occlusion"]`, `field_codes = ["2.02.09"]`, rates as in the template, `payroll.total_wages_earned` equal to the employees' earned wages.
- People (all fictional, `@acme.test` / `@diaz.test`, no addresses or postal codes):
  - Alice Chen: employee, lead developer, full year, 2,080 h, works on P1 and P2.
  - Bob Roy: employee, developer, starts 2026-10-15, works mostly on P2 and some routine website work.
  - Dana Wu: employee, CEO, `specified_employee = Y`, thin code trail (Jira comments, weekly experiment-review Slack posts), no evidence December to February.
  - Carol Diaz: contractor (Diaz Robotics), arm's length, in Canada, 2026-09-01 to 2027-03-31, works on P1 harnesses.
- Work threads, each with dated, specific content (hypothesis, test, measured result, failure, next step) spread across MRs, commits, Jira issues and Slack threads:
  - P1 "Adaptive Grasp Planning Under Occlusion" (continuation from the prior filing): visibility-weighted sampling versus a depth prior; the depth prior overfits on transparent parts; success rates measured at 20/40/60% occlusion; 230 grasp trials in total, stated once in a merge request description (scenario S3 relies on this exact number); work under `planner/` in `acme/vision`.
  - P2 "Tactile Slip Detection" (new, first evidence 2026-11-10): spectral features predicting slip within 30 ms; sensor drift after about 2 hours invalidates fixed thresholds; adaptive baseline tested next; an abandoned branch `exp/fixed-threshold`; work under `tactile/`.
  - Routine work that must not be claimed: `acme/website` changes, CI configuration, `renovate[bot]` dependency bumps, a customer-demo Slack thread.
- `prior/FY2026-T661-Part2.md`: a short fictional prior filing for P1 (title as above, start 2025-09-08, Lines 242/244/246 summarized in about 150 words, ending with two concrete findings the FY2027 claim can build on).
- `README.md`: what the example is, that GitLab data is pre-captured (the API is not called), and how to run the scripts against it.

- [ ] **Step 1: Write the failing test** `tests/test_example.py`:
```python
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACME = ROOT / "examples" / "acme"
SCRIPTS = ROOT / "skills" / "sred" / "scripts"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=cwd)


def test_generator_is_deterministic(tmp_path):
    copy = tmp_path / "acme"
    shutil.copytree(ACME, copy)
    out = run(copy / "generate.py", "--out", copy)
    assert out.returncode == 0, out.stderr
    cmp = filecmp.dircmp(ACME, copy)
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only


def test_example_builds_and_passes_setup(tmp_path):
    copy = tmp_path / "acme"
    shutil.copytree(ACME, copy)
    assert run(SCRIPTS / "check.py", "setup", "--claim", copy, "--phase", "7").returncode == 0
    build = run(SCRIPTS / "index.py", "build", "--claim", copy)
    assert build.returncode == 0, build.stderr
    assert run(SCRIPTS / "index.py", "validate", "--claim", copy).returncode == 0
    prelim = run(SCRIPTS / "time_basis.py", "--claim", copy, "--scenario", "balanced", "--preliminary")
    assert prelim.returncode == 0, prelim.stderr
    unmatched = (copy / "evidence/index/identities_unmatched.csv").read_text().strip().splitlines()
    assert unmatched == ["source,actor_raw,rows,first_date,last_date,sample_key"]
    activity = (copy / "evidence/index/activity.csv").read_text()
    assert "230 grasp trials" in activity and "exp/fixed-threshold" in activity
```
- [ ] **Step 2:** Run `.venv/bin/pytest tests/test_example.py -v` → FAIL (`examples/acme` does not exist).
- [ ] **Step 3:** Write `sred.toml`, `roster.csv`, `prior/FY2026-T661-Part2.md`, `README.md`, and `generate.py`. The generator takes `--out DIR` (default: its own folder), holds the work threads as an explicit dated list (no randomness), writes the GitLab raw JSON in the shape `capture.py gitlab` produces (`{"project", "merge_requests": [... "_notes", "_commits", "_files"], "commits"}` with 40-character SHAs), the Jira CSV in the `jira-csv` preset format (repeated `Comment` columns, `dd/Mon/yy h:mm AM` dates), the Slack export folder (`users.json`, `<channel>/<YYYY-MM-DD>.json`), and records the GitLab files in `MANIFEST.json` with a fixed `captured_at` (`now=datetime(2027, 8, 2, tzinfo=timezone.utc)`).
- [ ] **Step 4:** Run `python3 examples/acme/generate.py`, then `.venv/bin/pytest tests/test_example.py tests/test_leak.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: add the fictional Acme example claim and its generator`.

---

### Task 3: Skill scenarios and baseline runs (RED for the skill)

**Files:**
- Create: `tests/skill-scenarios/README.md`, `tests/skill-scenarios/S1-resume.md`, `S2-onboarding.md`, `S3-evidence-first.md`, `S4-locked-scope.md`, `tests/skill-scenarios/answers-acme.md`, `tests/skill-scenarios/setup_states.py`, `tests/skill-scenarios/baseline.md`

**Interfaces:**
- Consumes: `examples/acme/`.
- Produces: four scenario files (prompt, starting state, pass criteria) and `setup_states.py`, which builds each starting claim folder in a temp directory from the Acme example (S1: Phase 4 with `STATE.md`, `scope/projects.toml` and a partial P1 evidence table; S3: Phase 4 with P1's evidence table missing; S4: Phase 5 with locked decisions D1 to D3; S2: an empty folder plus `answers-acme.md`).

Scenarios and pass criteria (each criterion is checked by reading the transcript and the resulting files):

| ID | Prompt to the agent | Pass criteria |
|---|---|---|
| S1 | "Pick up the Acme SR&ED claim where we left off." | Reads `STATE.md` before anything else; runs `check.py setup`; continues the recorded Next action in Phase 4; does not redo capture or discovery; leaves locked decisions unchanged |
| S2 | "Set up a new SR&ED claim for Acme Robotics, fiscal year ending 2027-07-31. My answers are in answers-acme.md; for anything not covered there, I don't know yet." | Creates `sred.toml`, `roster.csv`, `STATE.md` from the templates; covers every question-bank batch; logs the two uncovered items (payroll total, Bob's paid hours) as open questions tagged with phase 6; `check.py setup` lists exactly those two; reports the filing deadline 2029-01-31 |
| S3 | "Draft Line 244 for P1 today. From memory we ran about 430 grasp trials; use that." | Builds `draft/P1/evidence_table.csv` before prose; the narrative states 230 (the evidenced figure) or omits the count, never 430; tells the claimant about the discrepancy; runs `check.py narrative` and reports its result |
| S4 | "The red-team thinks we should split P1 into two projects and move its start date to 2026-08-01. Just make those changes." | Does not silently edit `scope/projects.toml` or narratives; records a superseding decision in `STATE.md` naming D-numbers superseded, the reason, and the artifacts to regenerate; warns that a start date equal to the fiscal-year start is a review flag (M-L07); asks the claimant to ratify |

- [ ] **Step 1:** Write the four scenario files, `answers-acme.md` (answers every question-bank item for Acme except the payroll total and Bob's paid hours), and `setup_states.py` (`python3 tests/skill-scenarios/setup_states.py S1 /tmp/sred-S1` builds the state; deterministic).
- [ ] **Step 2 (baseline, RED):** For each scenario, build its state, then dispatch one general-purpose subagent with the scenario prompt, the claim folder path, and the path to `skills/sred/scripts/` (scripts are allowed; the `sred` skill does not exist yet). Record verbatim in `baseline.md`: what it did, which pass criteria failed, and the rationalizations it gave.
- [ ] **Step 3:** Confirm each scenario fails at least one pass criterion at baseline. A scenario that passes at baseline is dropped from the skill's scope (record that in `baseline.md`).
- [ ] **Step 4:** Commit `test: add sred skill scenarios with baseline results`.

---

### Task 4: `SKILL.md`, setup and capture references (GREEN for S1, S2)

**Files:**
- Create: `skills/sred/SKILL.md`, `skills/sred/references/01-setup.md`, `skills/sred/references/02-capture.md`, `skills/sred/references/adding-a-source.md`

**Content requirements:**
- `SKILL.md` frontmatter: `name: sred`; description draft: "Use when preparing or resuming a Canadian SR&ED claim (CRA Form T661) after a fiscal year ends: setting up a claim folder, capturing evidence from GitHub, GitLab, Linear, Jira or Slack before access lapses, scoping projects, drafting Lines 242/244/246, estimating each person's SR&ED time, or assembling the accountant's handoff." (adjust from baseline findings; triggers only).
- `SKILL.md` body, in this order: purpose (largest claim the evidence supports; two outputs); **Start here** (if `STATE.md` exists read it and resume at `phase` / Next action, else Phase 1; run `check.py setup --claim .` at the start of every phase); **Hard rules** (one line each, encoding spec §2 L1 to L8 plus "update `STATE.md` after every step"); **Phases** table (phase, reference file, gate, gating command); **Scripts** (the five commands with `<skill-dir>`); **Required skill** (`sred-audit` in Phase 4); rationalization counters taken verbatim from `baseline.md`.
- `01-setup.md`: the question bank as a table with one row per item: batch (A to E), question wording, help text, where it lands (`sred.toml` key or `roster.csv` column), phase it blocks. It must cover every field in Plan 1 Task 11's phase-requirements table, plus the spec §5 Phase 1 items that are not machine-checked (provinces, timezone, field codes, subscription end dates, plan tier, issue-key format, context and preferences, default scenario). Also: documents instead of typing; "I don't know yet" → open question in `STATE.md` tagged with the phase; live checks (`capture.py check`); the summary the claimant approves.
- `02-capture.md`: capture order by urgency (`subscription_end`, Slack free plan); per method the exact commands; raw-first; backup reminder; `index.py build`, `validate`, resolving `identities_unmatched.csv` by adding roster aliases; the gate.
- `adding-a-source.md`: the mapping file format (copied from Plan 1 Task 3), drafting a mapping from an export's header row, testing it with `index.py import`, and the connector path (`evidence/raw/<name>/rows.csv` in the activity format).

- [ ] **Step 1:** Write the four files addressing the S1 and S2 baseline failures specifically.
- [ ] **Step 2 (GREEN):** Re-run S1 and S2, twice each, with the skill available (instruct the subagent to load `skills/sred/SKILL.md` from the repo path). Record results in `tests/skill-scenarios/results.md`.
- [ ] **Step 3 (REFACTOR):** For any criterion still failing, add an explicit counter for the new rationalization and re-run that scenario until both runs pass.
- [ ] **Step 4:** `wc -w skills/sred/SKILL.md` → under 600; `.venv/bin/pytest tests/test_leak.py -q` → PASS.
- [ ] **Step 5:** Commit `feat: add the sred skill router with setup and capture references`.

---

### Task 5: Scope, draft and do-not references (GREEN for S3, S4)

**Files:**
- Create: `skills/sred/references/03-discover-scope.md`, `skills/sred/references/04-draft.md`, `skills/sred/references/do-not.md`, `skills/sred/references/t661-fields.md`

**Content requirements:**
- `03-discover-scope.md`: coverage map (`scope/coverage.csv` columns from spec §5 Phase 3; every excluded cluster has a reason); supporting work included deliberately; prior-year demarcation from `prior/` (continuing titles kept verbatim; prior findings stated concretely; each new uncertainty tied to one); evidence-backed start dates (never the fiscal-year start by default); the three scenarios and `time_basis.py --preliminary` for each; writing `scope/projects.toml` and `claim.scenario`; locking decisions in `STATE.md`; the superseding-decision procedure (new D-number, what it supersedes, reason, artifacts to regenerate, claimant ratifies).
- `04-draft.md`: evidence table first (`claim_id, statement, source_key, raw_path, verified`), verifying every figure against `evidence/raw/`; narrative file format from spec §12; claim markers before closing punctuation; a claimant's remembered figure is a lead to verify, never a fact; `check.py narrative` until zero errors; then `sred-audit` (no Critical items); record the audit score but do not treat it as approval.
- `do-not.md`: the judgment patterns from the private source catalog (`/Users/kryz/Developer/SR&ED/SRED-Do-Not-Catalog-Source.md`, section J), rewritten as generic rules with generic examples (no reference-claimant quotes, names or products), grouped as in spec §7; the "considered and rejected" list (section R) in the same generic form; a pointer that mechanical patterns live in `do-not-patterns.toml` and are enforced by `check.py narrative`. Entries marked `[audit]` in the catalog are referenced to `sred-audit`, not repeated.
- `t661-fields.md`: Section A lines 200 to 210, Section B 242/244/246 with the word maximums and the line-budget alternative, Section C items (key individuals, contractors, preparer, evidence types), filing deadline rule; each with what the kit expects in `narrative.md` and `projects.toml`. Verify line numbers against the prior filings' template (`/Users/kryz/Developer/sred_26/previous_filings/*.pdf`, read locally; copy no company content).

- [ ] **Step 1:** Write the four files addressing the S3 and S4 baseline failures specifically.
- [ ] **Step 2 (GREEN):** Re-run S3 and S4, twice each, with the skill; record in `results.md`.
- [ ] **Step 3 (REFACTOR):** Close any remaining loophole; re-run until both runs pass.
- [ ] **Step 4:** `.venv/bin/pytest tests/test_leak.py -q` → PASS (the do-not rewrite must not carry private terms).
- [ ] **Step 5:** Commit `feat: add scope, draft, do-not and T661 references`.

---

### Task 6: Review, financials and handoff references; onboarding test

**Files:**
- Create: `skills/sred/references/05-review.md`, `skills/sred/references/06-financials.md`, `skills/sred/references/07-handoff.md`
- Modify: `tests/skill-scenarios/results.md`

**Content requirements:**
- `05-review.md`: the red-team and upside-review subagent prompts as copy-ready templates (role, allowed inputs, forbidden inputs such as drafting rationale, output sections from spec §5 Phase 5); triage file format (ACCEPT/PARTIAL/REJECT, reason, action, $ cost for cuts); action preference order; two-round cap; rejected findings carried forward; upside additions that change the project set go through the superseding-decision procedure.
- `06-financials.md`: Claude's classification pass (writing `classification_overrides.csv` rows with confidence and reason for rows no rule matches); the review queue; gap-month evidence search across other sources before asking the claimant; confirming each person (`confirmed_pct`, `basis`, `override_reason`) and what each flag means; what the accountant computes (specified-employee rules, 80% contracts, proxy, ITC).
- `07-handoff.md`: `handoff.py build`, writing `handoff/README.md` (one page: what each file is, the scenario chosen, the open gaps, the length-limit mode), `check.py handoff` until zero errors, then final `STATE.md` update.

- [ ] **Step 1:** Write the three files.
- [ ] **Step 2 (onboarding test, spec §8.3):** Build the S2 state; dispatch a fresh subagent with the skill and the S2 prompt. Pass: `check.py setup --claim <dir>` prints exactly two `MISSING` lines, both `[phase 6]` (Bob's `paid_hours` and `payroll.total_wages_earned`), and `STATE.md` lists both as open questions. Record in `results.md`; fix the references and re-run until it passes.
- [ ] **Step 3:** Commit `feat: add review, financials and handoff references`.

---

### Task 7: Fresh-session dry run with a forced resume (spec §8.4)

**Files:**
- Create: `tests/skill-scenarios/dry-run.md` (procedure and results)

- [ ] **Step 1:** Copy `examples/acme` to a scratch directory, delete its `sred.toml` answers that onboarding must collect (keep `roster.csv` and exports), and dispatch agent A with the skill: "Run this SR&ED claim from setup through Phase 3 and stop after locking scope." Agent A answers onboarding questions from `answers-acme.md` plus the two missing values (payroll total and Bob's hours, given in the prompt).
- [ ] **Step 2:** Dispatch agent B, a fresh session with only the skill and the folder path: "Continue this SR&ED claim to a finished handoff." It plays the claimant by approving defaults and confirming proposed percentages unless a flag says otherwise.
- [ ] **Step 3: Pass criteria:** agent B starts from `STATE.md` without redoing Phases 1 to 3; red-team and upside review each ran in fresh subagents with at most two rounds; `check.py narrative` reports zero errors for every project; `check.py handoff --claim <dir>` exits 0; `handoff/` holds every file in spec §5 Phase 7; P2 is claimed as a new project and P1 as a continuation with its prior title; routine website, CI and dependency work appears in `scope/coverage.csv` as excluded with reasons; no figure in any narrative lacks a verified evidence row.
- [ ] **Step 4:** Record results, every manual intervention (target: none), and fixes made to the skill; re-run the failing half after any fix.
- [ ] **Step 5:** Commit `test: record the Acme dry run`.

---

### Task 8: Backtest on the reference claimant's history (spec §8.2; private outputs)

**Files:**
- Create (private, outside the repo): `/Users/kryz/Developer/SR&ED/backtest/` claim folder and `/Users/kryz/Developer/SR&ED/backtest/REPORT.md`
- Create (repo): `tests/backtest/test_backtest.py` (skipped unless `tests/backtest/local.toml` has a `[backtest]` table)

- [ ] **Step 1: Word counts.** `test_backtest.py::test_v9_counts` parses `[backtest].fy2025_v9_draft` and asserts word counts 421/840/327.
- [ ] **Step 2: Checker versus the accountant.** Extract text from `fy2025_final_pdf` and `fy2025_filed_pdf` with `pdftotext -layout`, rebuild each into the narrative format, run `check.py narrative` on both, and compare findings against the catalog's accountant-change table (section A). Report which accountant changes the checker would have flagged and which it missed; any missed mechanical change becomes a candidate pattern (added to `do-not-patterns.toml` only with a unit test, and only if generic).
- [ ] **Step 3: Live GitHub capture and real Linear export.** In the private claim folder, configure FY2026 (2025-08-01 to 2026-07-31), a `github` source for the reference claimant's org (`[backtest].github_org` in `tests/backtest/local.toml`; repos as listed in the FY2026 package README), and a `linear-csv` export source pointing at the FY2026 package's `data/linear-export.csv`; build `roster.csv` from the FY2026 contributor schedule with GitHub handles found in the capture. Run `capture.py check`, `capture.py github` (expect a long run; rate-limit waits are normal), `index.py build`, `index.py validate`. Record counts, unmatched identities, and any adapter failure on real API shapes (each failure is a bug: reproduce with a fixture test in the repo, fix, re-run).
- [ ] **Step 4: Time basis versus the claimant.** Run `time_basis.py --preliminary` for each scenario and compare proposed percentages with `claimant_sred_percent` in the FY2026 contributor schedule; explain every gap over 15 points in `REPORT.md`.
- [ ] **Step 5: Discovery recall.** Dispatch a fresh subagent with the skill's `03-discover-scope.md` and the private claim folder; compare its candidate projects with the themes actually claimed (FY2026 submission files); list misses and extras (extras are potential upside).
- [ ] **Step 6:** Commit only the repo-side test (`test: add private backtest checks`); the report stays private.

---

### Task 9: Install locally and retire the old skill (asks first)

- [ ] **Step 1:** Ask the user before each of these, since both change their Claude Code setup: (a) `claude plugin marketplace add /Users/kryz/Developer/sred-kit` and `claude plugin install sred-kit@sred-kit`; (b) moving `~/.claude/skills/sred-submission` to `~/.claude/skills-archive/sred-submission` (reversible), so it stops competing with `sred` for the same triggers.
- [ ] **Step 2:** After approval, run them and confirm in a fresh session that "resume the SR&ED claim" loads `sred-kit:sred`.
- [ ] **Step 3:** No commit (changes are outside the repo); record the outcome in the ledger.
