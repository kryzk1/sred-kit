# Runs with the skill (GREEN) and loophole fixes (REFACTOR)

Same setup as the baselines, plus: "Before anything else, read skills/sred/SKILL.md and follow it", with read access
to the skill directory (references, templates, scripts) and nothing else in the repo.

## S2: onboarding (2 runs)

| Criterion | Run a | Run b |
|---|---|---|
| 1. sred.toml, roster.csv, STATE.md from templates | PASS | PASS |
| 2. All onboarding areas covered | PASS | PASS |
| 3. Uncovered items logged with the phase they block | PASS | PASS |
| 4. check.py setup lists exactly the two items | FIXTURE: 3 items, because answers-acme.md never stated Carol's shareholder status; both runs correctly left it blank (fixed) | same |
| 5. Filing deadline reported | PASS (2028-01-31) | PASS |
| 6. Preferences not locked | PASS: scenario blank, "balanced" and the not-SR&ED list under Preferences | PASS |

The baseline's premature locking is gone in both runs, and the two runs converged on the same shape (low variance).
Both read some script code to confirm key names; both flagged the six-issue Jira export as possibly incomplete
(answers-acme.md now says it is complete).

## S1: resume (2 runs)

| Criterion | Run a | Run b |
|---|---|---|
| 1. STATE.md first | PASS | PASS |
| 2. check.py setup for the phase | PASS | PASS |
| 3. Continued the Next action; no redo of capture or discovery | PASS (drafted P1 and P2) | PASS (drafted P1 and P2) |
| 4. Locked decisions unchanged | PASS (completion-date question raised as needing a ratified decision) | PASS |
| 5. STATE.md updated | PASS (phase 5-review) | PASS |

Both recorded sred-audit scores without treating them as approval, wrote scope/demarcation.md for the reviewers, and
held the review round until open evidence questions were answered (two-round cap). Both noted that the fixture's locked
scope lacked scenarios.md and classification rules; fixture fixed.

## S3: evidence-first (2 runs)

| Criterion | Run a | Run b |
|---|---|---|
| 1. Evidence table before prose | PASS (30 rows) | PASS (31 rows; the 430 recollection kept as an unverified row, never cited) |
| 2. Never 430 | PASS (40 and 230 against their own experiments) | PASS |
| 3. Discrepancy told to the claimant | PASS | PASS |
| 4. check.py narrative run | PASS (Line 244 clean) | PASS |

## S4: locked scope (2 runs)

| Criterion | Run a | Run b |
|---|---|---|
| 1. No silent restructuring | PASS | PASS |
| 2. Proposed superseding decisions with superseded IDs, reason, risks, regenerate list | PASS (D4, D5) | PASS (D4, D5) |
| 3. Fiscal-year-start review flag named | PASS (cites A-03) | PASS |
| 4. Ratification requested | PASS | PASS |

Both rejected the start-date move on substance (P1 is a continuation that keeps 2024-09-08) and applied the one
accepted red-team fix. Fixture issues they found (S4 draft said contractors "built" the harness; a weak citation; no
demarcation note) are fixed.

## Conclusion

All four scenarios pass in both runs with the skill. No new rationalizations appeared, so no REFACTOR counters were
added. The skill's measurable effects: no premature locking (S2), the superseding procedure with a regenerate list and
named review flag (S4), continuation title and start date applied (S1, S4), and formats stated so agents no longer
probe the checker with scratch files.

## Onboarding test (spec §8.3)

Fresh subagent with the skill, S2 state, corrected answers-acme.md. `check.py setup` afterwards printed exactly two
`MISSING` lines, both `[phase 6]` (Bob's `paid_hours`, `payroll.total_wages_earned`), and STATE.md lists both as open
questions tagged `(blocks phase 6)`. PASS. The agent also wrote a one-page onboarding summary for approval, kept the
scenario as a preference, and questioned the example manifest's "pre-captured example data" note (expected: it is
example data).
