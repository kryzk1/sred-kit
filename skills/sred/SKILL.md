---
name: sred
description: Use when preparing or resuming a Canadian SR&ED claim (CRA Form T661) after a fiscal year ends - setting up a claim folder, capturing evidence from GitHub, GitLab, Linear, Jira or Slack before access lapses, scoping projects, drafting Lines 242/244/246, estimating each person's SR&ED time, or assembling the accountant's handoff.
---

# SR&ED claim

Builds the largest SR&ED claim the evidence supports: T661 Part 2 per project and the accountant's labour summary. One claim folder per company per fiscal year holds everything.

`<skill-dir>` below is the base directory printed when this skill loaded. Templates are in `<skill-dir>/templates/`.

## Start here

1. In the claim folder, if `STATE.md` exists, read it first and continue from `phase:` and `## Next action`. Otherwise begin Phase 1.
2. At the start of every phase run `python3 <skill-dir>/scripts/check.py setup --claim . --phase N`. Resolve, or log as an open question, anything that blocks phase N.
3. Read the reference file for the current phase (table below) before doing that phase's work.
4. After every step, update `STATE.md`: `phase:`, phase log, open questions tagged `(blocks phase N)` (move answered ones to the log), `## Next action`.

## Phases

| # | Phase | Read | Gate before moving on |
|---|---|---|---|
| 1 | Onboarding | `references/01-setup.md` | `check.py setup` shows nothing blocking phase 2; claimant approves the summary |
| 2 | Capture | `references/02-capture.md` | manifest reviewed; unmatched identities resolved; backup confirmed |
| 3 | Discover & scope | `references/03-discover-scope.md` | claimant picks a scenario; decisions locked; `scope/projects.toml` written |
| 4 | Draft | `references/04-draft.md` | `check.py narrative` 0 errors per project; `sred-audit` no Critical items |
| 5 | Review | `references/05-review.md` | no open ACCEPT items; at most two rounds |
| 6 | Financials | `references/06-financials.md` | every % confirmed; `financial_checks.md` clean |
| 7 | Handoff | `references/07-handoff.md` | `check.py handoff` 0 errors |

Phase 6 may run alongside 4 and 5 after Phase 3.

## Rules

- **Evidence** is a raw record under `evidence/raw/` and its key. Summaries, drafts and memory (the claimant's included) are leads to verify.
- **Evidence table before prose.** Every figure or event in a narrative carries a `[C#]` marker that resolves to a verified row.
- **Only the claimant decides.** Onboarding records facts and preferences. A preferred scenario or a list of "not SR&ED" work goes under `## Preferences`; the scenario is chosen in Phase 3 after comparing all three, and exclusions are decided in the coverage map.
- **Locked decisions change only by a superseding decision**: a new D-number naming what it supersedes, the reason, the artifacts to regenerate, and ratification. Nothing changes until it is ratified.
- **Continuing projects** keep the prior filing's Line 200 title and Line 202 start date exactly.
- **Scripts do the mechanical checks** (lengths, patterns, markers, dates, arithmetic); run them rather than eyeballing.
- **Approval** comes from red-team triage, not the `sred-audit` score.
- **Percentages** come from the time basis; the claimant confirms each, with a basis for overrides. Never one % for everyone.
- **Maximize defensibly**: include directly supporting work, give every exclusion a reason, claim nothing unevidenced.

## Scripts (each has `--help`)

| Command | Does |
|---|---|
| `python3 <skill-dir>/scripts/capture.py <tool> --source NAME` or `check` | Raw capture; test every source |
| `python3 <skill-dir>/scripts/index.py import\|build\|validate` | The shared `evidence/index/activity.csv` |
| `python3 <skill-dir>/scripts/check.py setup\|narrative\|handoff` | Phase gates |
| `python3 <skill-dir>/scripts/time_basis.py [--scenario S] [--preliminary]` | Time basis, person summary, labour summary |
| `python3 <skill-dir>/scripts/handoff.py build` | The folder for the accountant |

## Required skill

Phase 4 uses `sred-audit` (installed with this plugin as `sred-kit:sred-audit`).
