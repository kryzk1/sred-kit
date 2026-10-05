# Phase 5: Review

Two independent reviews per round, at most two rounds. Each reviewer is a fresh subagent that never sees the drafting conversation or your reasons, only the files listed. Run Phase 6 first when you can, so the red-team sees the confirmed percentages and the labour summary.

## Red-team (`draft/review/redteam-r<n>.md`)

Dispatch a fresh subagent with this prompt, filling in the paths:

```
You are a CRA Research and Technology Advisor reviewing an SR&ED claim. Your job is to find every
ground to deny or reduce it. Read only these files:
- Narratives: <claim>/draft/*/narrative.md
- Prior filings: <claim>/prior/*
- Scope: <claim>/scope/projects.toml, <claim>/scope/demarcation.md
- Do-not patterns: <skill-dir>/references/do-not.md
- Per-person percentages and pay, if present: <claim>/financials/person_summary.csv, <claim>/financials/labour_summary.csv
- Round 2 only: <claim>/draft/review/triage-r1.md. Do not repeat a finding rejected there unless the
  narrative changed in a way that revives it; say why if you do.
Do not read evidence tables, STATE.md or any other file.

Write <claim>/draft/review/redteam-r<n>.md with three sections:
1. Denial positions, numbered. Each: line (200 to 282), quoted text, the CRA basis
   (eligibility criterion, T4088 guidance or a do-not pattern ID), the likely adjustment, and an estimate
   of what is at risk (a project, a person's share, or a dollar range).
2. Information requests a reviewer would send the claimant.
3. Fixes ranked by how much claim they protect.
Be specific and adversarial. Don't praise.
```

## Upside review (`draft/review/upside-r<n>.md`)

Dispatch a second fresh subagent:

```
You are an SR&ED consultant looking for eligible work this claim left out. Read only:
- <claim>/scope/coverage.csv (especially excluded clusters and their reasons)
- <claim>/scope/projects.toml and <claim>/scope/scenarios.md
- <claim>/evidence/index/activity.csv
- <skill-dir>/references/do-not.md (sections "Considered and rejected" and "Financial consistency")
Do not read narratives, STATE.md or other files.

Write <claim>/draft/review/upside-r<n>.md listing candidate additions. Each: the cluster or rows,
person-months, why it is eligible (directly supporting work, an experiment the coverage map missed,
a wrongly excluded cluster), evidence keys, an estimated share of whose time, and the eligibility risk.
List nothing the evidence doesn't show.
```

## Triage (`draft/review/triage-r<n>.md`)

One row per red-team finding:

| Finding | Verdict | Reason | Action | Cost |
|---|---|---|---|---|

- Verdict: `ACCEPT`, `PARTIAL` or `REJECT`, with the reason. Check `do-not.md` "Considered and rejected" before accepting: reviewers often over-reach in the same ways.
- Prefer actions in this order: strengthen the evidence, reframe the text, cut. A cut states its cost (project, share or dollars).
- Rejected findings stay in the file so round 2 doesn't re-argue them.
- Upside additions: accept, decline with a reason, or ask the claimant. An addition that changes the project set or a locked decision goes through the superseding procedure in `03-discover-scope.md`; nothing changes until the claimant ratifies.

Apply the accepted actions, re-run `check.py narrative` for every changed project, and log the round.

## Gate

No open ACCEPT items, `check.py narrative` clean, and two rounds at most (if round 2 still finds substantial issues, record them in `handoff/gaps.md` rather than running round 3). Set `phase: 6-financials` (or `7-handoff` if financials are done).
