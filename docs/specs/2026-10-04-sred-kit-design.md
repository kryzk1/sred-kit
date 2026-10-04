# sred-kit: design

**Date:** 2026-10-04
**Status:** Draft for review

## 1. Purpose

A small, shareable kit that lets someone who was not part of a previous claim turn a finished fiscal year into a complete SR&ED handoff package for their accountant:

1. **Written portion:** CRA Form T661 Part 2 for each project (Section A fields, Lines 242/244/246, Section C fields).
2. **Financial portion:** the accountant's Wages & Labour Summary, with each person's SR&ED % backed by an evidence-derived time basis.

**Goal: maximize the defensible claim.** The kit looks back across everything done in the tax year and finds all eligible work, including directly supporting work, which claims most often miss. Every claimed dollar must trace to verbatim evidence. A claim that gets audited down ends up smaller plus interest, so defensibility is how size is protected.

**Users:** any Canadian company (generic core) plus the reference claimant, whose company-specific config lives in its own claim folder, never in the kit.

**Cadence:** one run, after fiscal year end.

**Success:** a newcomer goes from "fiscal year closed" to "package with the accountant" in a few days. No more than two review rounds, no reopening of locked scope decisions without a logged reason, and every number traceable to a raw record.

## 2. Lessons this design encodes

Each comes from the reference claimant's FY2025 and FY2026 claim history.

| # | What went wrong | Rule in the kit |
|---|---|---|
| L1 | Linear/Slack links died when subscriptions were cancelled; agent-written digests were mistaken for evidence | Capture raw records verbatim first; only raw records and their durable keys count as evidence |
| L2 | Narrative-first drafting produced three factual errors (a spend figure, a test count, a mis-cited PR) | Evidence table before prose; every load-bearing fact carries a claim marker that the checker resolves |
| L3 | Project count changed four times; start date moved five times; 15 narrative versions | Scope decisions are made once, ratified by the claimant, and locked in `STATE.md` |
| L4 | Drafts exceeded word limits (421/350, 840/700) and used trigger words | A script enforces word limits and mechanical do-not patterns |
| L5 | Self-audits scored 48–50/50; an adversarial review said to disregard them | Approval requires an independent red-team review; `sred-audit` is a quality floor, not the gate |
| L6 | Time-basis hours were never reconstructed (all hours cells blank); a uniform % across people is itself a review flag | Per-person % proposed from activity evidence, confirmed by the claimant, both recorded |
| L7 | Time-basis script depended on an LLM runtime; register build had a 7-vs-9-character commit ID bug; build scripts lived in scratch folders | Scripts are deterministic, stdlib-only, versioned in the kit; commit IDs are always 40 characters |
| L8 | No saved state; resuming a session found nothing | `STATE.md` is the single resume point for every phase |

## 3. Components

Two skills.

- **`sred`** (new): phase router, rules, scripts, templates. Replaces the outdated `sred-submission` skill.
- **`sred-audit`** (existing, unchanged): the Line 242/244/246 quality rubric. `sred` lists it as a required skill. The kit ships an unchanged copy so outside companies get it; plugin skill names are prefixed with the plugin name, so it does not clash with an existing installed copy.

### 3.1 Kit layout (shareable; contains no company data)

```
sred-kit/
  .claude-plugin/plugin.json
  skills/
    sred/
      SKILL.md                    phase router, hard rules, resume procedure
      references/
        01-setup.md
        02-capture.md
        03-discover-scope.md
        04-draft.md
        05-review.md              red-team + upside review, prompts and triage format
        06-financials.md
        07-handoff.md
        do-not.md                 judgment patterns (generic statements, generic examples)
        do-not-patterns.toml      mechanical patterns read by check.py
        t661-fields.md            Section A/B/C field guide
        adding-a-source.md        mapping-file format and connector path
      mappings/                   export presets: jira-csv, linear-csv, asana-csv, clickup-csv,
                                  shortcut-csv, azure-devops-csv, slack-export
      scripts/
        capture.py                github | gitlab | linear | jira | git-log
        index.py                  build | import | validate
        check.py                  narrative | handoff
        time_basis.py             ledger aggregation, gap months, person summary, labour summary
      templates/
        sred.toml
        roster.csv
        STATE.md
        labour-summary-columns.csv
    sred-audit/
      SKILL.md                    unchanged copy
  examples/acme/                  fictional claim folder on a different stack (GitLab, Jira, Slack export)
  tests/
    fixtures/                     recorded and synthetic inputs, no real company data
    backtest/local.toml           gitignored; points at a real claimant's private history
  docs/specs/
```

Scripts use Python 3.11+ standard library only (config is TOML because `tomllib` is in the standard library), plus the `gh` CLI for GitHub. Tests use pytest.

### 3.2 Claim folder (one per company per fiscal year; private)

```
FY<year>/
  sred.toml                company, fiscal year, prior filings, sources, classification rules, optional rates
  roster.csv               people, aliases, pay, employee/contractor, flags
  STATE.md                 phase, locked decisions, open questions, next action
  evidence/
    raw/<source>/          verbatim captures, never edited
    raw/MANIFEST.json      per source: counts, date range, capture time, method, sha256
    index/activity.csv     the shared format every later phase reads
    index/identities_unmatched.csv
  scope/                   coverage, demarcation, scenarios, questions
  draft/<project>/         evidence table, narrative, checker output, audit
  draft/review/            red-team, upside review, triage per round
  financials/              ledger, overrides, time basis, gap months, person summary, labour summary
  handoff/                 what goes to the accountant
```

## 4. State and resume

`STATE.md` structure:

```markdown
# SR&ED claim state: <company> FY<year>
phase: 4-draft
updated: YYYY-MM-DD

## Locked decisions
- D1 (YYYY-MM-DD, ratified by <role>): scenario = balanced; projects P1, P2
- D2 (...): P1 start date 2026-09-14, evidence: <keys>

## Open questions for the claimant
- Q3: ...

## Phase log
- YYYY-MM-DD capture complete; manifest reviewed

## Next action
<one line>
```

Rules:
- On every invocation, `sred` reads `STATE.md` first and resumes at `phase` / `Next action`.
- Changing a locked decision requires a new decision entry that names the one it supersedes, gives the reason, and lists the artifacts to regenerate. Silent changes are not allowed.
- Every judgment call made by Claude is recorded as a decision with the default taken; the claimant ratifies or reverses it.

## 5. Phases

Each phase has a reference file loaded only when that phase runs. Phase 6 can run alongside Phases 4–5 once Phase 3 is locked.

### Phase 1: Setup

- **Inputs:** claimant answers; prior T661 filings (PDF); payroll and contractor figures.
- **Produces:** `sred.toml`, `roster.csv`, `STATE.md`, folder skeleton.
- **Checks:** fiscal year dates; each source has a method; credentials present for `api` sources; export files present for `export` sources; prior filings present (otherwise logged as first claim); Slack plan warning (free plans hide history older than 90 days).
- **Gate:** config and roster complete; claimant confirms.

### Phase 2: Capture

**Sources are pluggable.** Each source in `sred.toml` declares `kind` (`code | tracker | chat | meetings | docs`), `tool`, and `method`. Nothing downstream of `activity.csv` knows which tool a row came from, so switching tools never changes Phases 3–7.

| Method | How it works | Built in for |
|---|---|---|
| `api` | `capture.py <tool>` pulls raw records with the tool's API or CLI | GitHub (`gh`), GitLab (REST, token), Linear (GraphQL), Jira Cloud (REST, including changelog) |
| `export` | The tool's own export file is the raw record; `index.py import --mapping <file>` converts it | Mapping presets: Jira CSV, Linear CSV, Asana CSV, ClickUp CSV, Shortcut CSV, Azure DevOps CSV, Slack export ZIP |
| `connector` | Claude pulls through an MCP connector, saves raw JSON, writes activity rows; `index.py validate` checks them | Any tool with a connector (Notion, Confluence, Granola, Teams, Monday, and others) |
| `git-log` | `capture.py git-log` over local clones | Any git host (Bitbucket, Azure Repos, self-hosted); commits only |

- **Code history is required**, because the time basis depends on it: any `api` code host or `git-log`. Trackers, chat and meetings are optional, but they raise the claim: they evidence uncertainty and iteration, and they fill gap months for people with thin code trails.
- **Adding an unsupported tool needs no code.** A mapping file is about 15 lines of TOML: the export's columns mapped to `activity.csv` fields, and which activity kinds each export row yields (for example, one Jira CSV row yields `issue_created`, `issue_resolved` and one `issue_comment` per comment column). Claude drafts the mapping from the export's header row; `index.py import` and `validate` check it. `references/adding-a-source.md` documents the mapping format and the connector path in one page.
- **Raw-first applies to every method:** the export file or connector JSON is saved under `evidence/raw/<source>/` and recorded in the manifest before any conversion.
- Meeting summaries and other non-verbatim records are marked `weight=summary`.

`index.py build` converts all `api` and `git-log` raw files and every source with a configured mapping into `evidence/index/activity.csv`.

**`activity.csv` columns:** `source, key, kind, person, actor_raw, date, timestamp, container, tags, paths, title, excerpt, refs, url, raw_path, weight`

- `key`: durable ID (`repo#123`, full 40-char commit SHA, issue identifier, chat `channel:ts`, meeting ID). Unique per row.
- `kind`: `commit, pr_opened, pr_merged, pr_review, pr_comment, issue_created, issue_state_change, issue_resolved, issue_assigned, issue_comment, chat_message, meeting, doc_edit`.
- `person`: roster ID, `bot`, or `unmatched:<raw>`.
- `container`: repo, tracker project, or channel.
- `tags`: labels, branch name, issue type; semicolon-separated.
- `paths`: changed file paths for commits and PRs; semicolon-separated, truncated at 50.
- `excerpt`: verbatim, at most 500 characters, truncation marked.
- `refs`: semicolon-separated keys found in the row, using each tracker's `issue_key_regex` from `sred.toml` (for example `[A-Z]+-\d+` for Jira, `#\d+` for GitHub issues).
- `weight`: `verbatim` or `summary`.

**Identity resolution:** `roster.csv` aliases use `<tool>:<id>` (for example `github:jdoe`, `jira:5b10ac8d`, `slack:U123`), with email as the default join key because most tools expose it. Unmatched non-bot actors go to `identities_unmatched.csv`.

- **Gate:** manifest counts reviewed by the claimant; unmatched identities resolved or marked external/bot; claimant confirms a backup copy of `evidence/raw/` exists.

### Phase 3: Discover & Scope

1. **Coverage map** (`scope/coverage.csv`): every activity row is grouped into a work cluster (by classification rules, then Claude clustering of the rest). Columns: `cluster, description, person_months, rows, status (candidate|excluded), exclusion_reason, evidence_keys`. Every excluded cluster needs a reason.
2. **Prior-year demarcation** (`scope/demarcation.md`): from prior filings, what was claimed, what is a continuation, the knowledge baseline at fiscal-year start, and evidence-backed start dates.
3. **Candidate projects:** technological themes (not tracker projects), each with an uncertainty hypothesis, period, clusters, supporting work and evidence keys.
4. **Preliminary time basis:** `time_basis.py` on rule-classified rows plus roster pay gives a rough eligible $ per scenario.
5. **Scenarios** (`scope/scenarios.md`):
   - **Conservative:** direct experimental work with strong evidence; evidence-only time basis; gap months at 0%.
   - **Balanced:** adds directly supporting work; gap months use a claimant basis only where another source corroborates it.
   - **Maximum:** every defensible cluster including borderline ones; gap months use the claimant basis.
   - Each shows: projects, clusters, per-person %, eligible labour + contract $, optional ITC estimate = (SR&ED wages × (1 + `proxy_rate`) + contractor SR&ED $ × `contract_rate`) × `itc_rate`, with rates from `sred.toml` and labelled as an estimate that ignores caps, and each weak point a reviewer would attack with its $ at risk.
6. **Questions** (`scope/questions.md`): what only the claimant can answer.

- **Gate:** claimant picks a scenario. Locked decisions: project count, titles (checked by `check.py`), start and end dates, continuation flags, field codes, exclusions.

### Phase 4: Draft

Per project:
1. **Evidence table** (`draft/<P>/evidence_table.csv`): `claim_id, statement, source_key, raw_path, verified (Y/N)`. Each figure and event is verified against `evidence/raw/`, never against digests or earlier prose.
2. **Narrative** (`draft/<P>/narrative.md`): Section A fields and Lines 242/244/246. Load-bearing facts carry inline markers like `[C12]`, which `check.py` resolves against the evidence table and the handoff export strips.
3. **`check.py narrative`** must pass (§6.3).
4. **`sred-audit`** runs; output in `draft/<P>/audit.md`.

- **Gate:** checker passes; audit has no Critical items. The audit score is recorded but is not the approval.

### Phase 5: Review (two rounds maximum)

Two fresh subagents per round, neither of which sees the drafting conversation or rationale.

- **Red-team** (`draft/review/redteam-r<n>.md`)
  - Role: a CRA Research and Technology Advisor looking for grounds to deny or reduce the claim.
  - Inputs: narratives, demarcation, `do-not.md`, prior filings, person summary if available.
  - Output: denial positions (line, quote, CRA basis, likely adjustment, $ at risk), the information requests a reviewer would send, ranked fixes.
- **Upside review** (`draft/review/upside-r<n>.md`)
  - Role: an SR&ED consultant looking for eligible work left out.
  - Inputs: coverage map exclusions, scope, activity index.
  - Output: candidate additions (cluster, person-months, why it is eligible, evidence keys, estimated $, eligibility risk).
- **Triage** (`draft/review/triage-r<n>.md`)
  - Each red-team finding is marked ACCEPT, PARTIAL or REJECT, with a reason and an action.
  - Preferred actions, in order: strengthen evidence, reframe, cut. A cut shows its $ cost.
  - Rejected findings are kept with reasons so later rounds do not re-litigate them.
  - Adding upside work that changes the project set is a superseding scope decision (§4).

- **Gate:** no open ACCEPT items; `check.py narrative` passes again.

### Phase 6: Financials

1. **Ledger** (`financials/activity_ledger.csv`): activity rows plus `project, level (direct|support|none), category (routine|support|business|admin), classified_by (rule:<id>|claude|claimant), confidence, reason`.
   - Pass 1: classification rules from `sred.toml`. Rules match on tool-neutral columns (`source`, `container`, `tags`, `paths` glob, `title` regex) and assign a project and level.
   - Pass 2: Claude classifies the remainder and writes `financials/classification_overrides.csv`. Rows below `review_threshold` (default 0.7, set in `sred.toml`) are queued for the claimant.
   - `time_basis.py` merges rules and overrides; it never calls an LLM.
2. **Time basis** (`financials/time_basis.csv`): `person, month, evidence_days, sred_days, share, by_project, gap`.
   - The unit is the evidence-day. A day with mixed activity is split in proportion to its classified items.
   - Monthly share = SR&ED evidence-days / all evidence-days.
3. **Gap months** (`financials/gap_months.csv`): employed months with no evidence. Claude searches other captured sources first; the claimant can supply a basis. Scenario rules from §5 Phase 3 decide how each is counted.
4. **Person summary** (`financials/person_summary.csv`): `person, evidence_share, proposed_pct, confirmed_pct, basis, override_reason, flags`.
   - Proposed % = mean monthly share across employed months under the locked scenario.
   - People with thin code trails (managers, product, executives) can be raised above their evidence share with a written basis; the labour summary marks these as estimates.
   - Flags (do not block): identical % for all people; above 90% without a basis; contractor work outside Canada; same person as both employee and contractor.
5. **Labour summary** (`financials/labour_summary.csv`): the accountant's columns from `templates/labour-summary-columns.csv` (default: the reference claimant's accountant format plus `Pay in Lieu` and `Basis`).
   - Employees: SR&ED hours = paid hours × %; SR&ED wages = earned wages × %.
   - Contractors: invoiced amount × %, plus arm's-length, contract provided, SR&ED in contract, work performed in Canada.
   - Personal fields come only from `roster.csv`.
6. **Checks** (`financials/financial_checks.md`): total wages match the claimant-entered payroll total; flags listed.

- **Gate:** claimant confirms every %; checks pass.

**Left to the accountant (flagged, not computed):** specified-employee rules for 10%+ shareholders, the 80% rule for arm's-length contracts, the proxy method, the ITC and Schedule 31.

### Phase 7: Handoff

`handoff/` contains:
- `T661-Part2-<P>.md`: Section A, Section B (markers stripped, word counts stated), Section C (preparer, key individuals, contractors, evidence types), ready to paste into the accountant's template.
- `labour_summary.csv`
- `evidence_index.csv`: every cited key with its raw path.
- `decision_log.md`: locked decisions from `STATE.md`.
- `gaps.md`: unresolved items, pending corroboration, backup instructions.
- `README.md`: a one-page cover note for the accountant.

- **Gate:** `check.py handoff` passes (§6.3).

## 6. Scripts

### 6.1 `capture.py`
- `capture.py <github|gitlab|linear|jira|git-log> --config sred.toml --source <name> --out evidence/raw/<name>/`
- Each tool is one small module behind the same interface: fetch raw records for the fiscal-year window, write raw JSON, append to `MANIFEST.json`. Idempotent: reruns overwrite the same files.
- Credentials come from environment variables named in `sred.toml` (for example `GITLAB_TOKEN`, `JIRA_EMAIL` + `JIRA_TOKEN`, `LINEAR_API_KEY`); `gh` uses its own auth.

### 6.2 `index.py`
- `index.py build --claim <dir>`: converts every `api` and `git-log` source, plus every source with a mapping, to `activity.csv`; resolves identities.
- `index.py import --claim <dir> --source <name> --mapping <file>`: converts one export file using a mapping (preset or custom) and reports unmapped columns and rows that failed to parse.
- `index.py validate --claim <dir>`: column set, key uniqueness, date within fiscal year, person resolution, `raw_path` exists.

### 6.3 `check.py`
- `check.py narrative <narrative.md> --evidence <evidence_table.csv>`
  - Word counts per line against limits (242: 350, 244: 700, 246: 350), excluding markers.
  - Mechanical patterns from `do-not-patterns.toml` (id, regex, scope, severity, replacement hint).
  - Title rules (Section A).
  - Every `[C#]` marker exists in the evidence table with `verified=Y`.
  - Exit code non-zero on any error-severity finding; warnings are listed.
- `check.py handoff --claim <dir>`
  - Personnel named in narratives and Section C appear in the labour summary with % > 0, and the reverse.
  - Project dates in narratives match Section A and the locked decisions.
  - Contractors in Section C match contractors in the labour summary.
  - No markers left in handoff text.

### 6.4 `time_basis.py`
- `time_basis.py --claim <dir> --scenario <name> [--preliminary]`
- Reads `activity.csv`, rules, overrides, gap months and roster; writes the ledger, time basis, person summary and labour summary.
- Deterministic: same inputs give byte-identical outputs.

## 7. Do-not patterns

- **Source catalog** (private, company quotes included): built by harvesting the reference claimant's audits, trigger-word analysis, red-team reviews and triage, and the accountant's edits between the final draft and the filed version. Stored with the reference claimant's records, outside the kit.
- **Kit files** derived from it:
  - `do-not-patterns.toml`: the mechanical patterns (words, phrases, word limits, title rules), each with a generic replacement hint.
  - `do-not.md`: the judgment patterns, grouped by Line 242 / 244 / 246 / Section A / cross-section / prior-year demarcation / evidence / AI and LLM work / narrative-financial consistency, each with a generic statement and a generic example; plus a "considered and rejected" list so users do not over-correct.
- Patterns already in `sred-audit` are referenced, not duplicated.

## 8. Testing

1. **Script tests** (pytest, fixtures only, no network)
   - `check.py`: reproduces known word counts (421 and 840 from a fixture draft); flags every mechanical pattern; passes a clean fixture.
   - `time_basis.py`: synthetic ledgers covering mixed days, gap months under each scenario, identical-% flag, employee-and-contractor person, payroll mismatch; byte-identical reruns.
   - `capture.py` / `index.py`: recorded fixtures for each `api` adapter (GitHub, GitLab, Linear, Jira) and each mapping preset produce valid `activity.csv`; 40-char SHAs; bots excluded.
   - A custom mapping written from scratch for a tool with no preset (fixture: a Trello JSON export) imports and validates, proving the no-code path.
2. **Backtest** (`tests/backtest/local.toml`, gitignored, real data stays local)
   - Checker on the reference claimant's final FY2025 text catches what the accountant changed before filing.
   - Discovery on FY2026 raw evidence finds every theme actually claimed; extra findings are listed as upside.
   - Proposed % per person compared with the FY2026 claimant-entered %; every gap explained.
3. **Fresh-session dry run** on `examples/acme/`, which deliberately uses a different stack from the reference claimant (GitLab, Jira, Slack export), so the run proves portability while the backtest covers GitHub and Linear. A new Claude session with only the kit runs all seven phases. The session is killed mid-phase and must resume from `STATE.md` alone. Skills are written test-first: record the failure without the skill, then show the skill fixes it.
4. **Leak check:** grep over `skills/`, `examples/`, `templates/` and `tests/fixtures/` for the reference claimant's name, org, repo names, issue prefix, people's names, addresses and wage figures finds nothing.

**Done when** all four pass and the dry run produces a complete handoff package without manual fixes.

## 9. Out of scope

- T661 Part 3 expenditures, the ITC calculation, Schedule 31, provincial credits, proxy-method and specified-employee computations (the accountant's job).
- Filing.
- Mid-year or contemporaneous capture.
- Bitbucket and Azure DevOps API capture (`git-log` plus exports cover them).
- Generating the accountant's Word document (handoff text is ready to paste).
- Non-Canadian R&D programs.

## 10. Decisions taken

| Decision | Choice | Why |
|---|---|---|
| Skill structure | One `sred` skill with per-phase references, plus existing `sred-audit` | Shared rules in one place; phases load only when needed |
| `sred-submission` | Retired, replaced by `sred` | It reflects an older Linear/Slack-only process |
| Config format | TOML | Python standard library reads it; no dependencies |
| Source support | Four API adapters (GitHub, GitLab, Linear, Jira), seven export presets, mapping files for anything else, connectors as fallback | Covers the common stacks with little code; any other tool needs only a mapping file |
| Time-basis unit | Evidence-day, fractional split | Commit counts reward frequent small commits |
| Gap months | Scenario-dependent (0% conservative; claimant basis in maximum) | Supports claim maximization while keeping the conservative view visible |
| Approval gate | Red-team triage, not audit score | Self-scores were inflated in practice |
| Review rounds | Two maximum | Prevents version churn |
| Distribution | Git repo installable as a Claude Code plugin | Works for any company; company configs stay private |

## 11. Next step

Write the implementation plan (writing-plans skill). Skills are built with the writing-skills approach (baseline failure first).
