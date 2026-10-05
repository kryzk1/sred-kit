# Fresh-session dry run with a forced resume (spec §8.4)

**Setup.** `setup_states.py S2 /tmp/sred-dry` (the Acme example without `sred.toml` or `roster.csv`, plus
`answers-acme.md`). Simulated claimant: approves every recommendation (recorded as "ratified by CEO (simulated)"),
supplies the two missing onboarding values, and confirms proposed percentages unless a flag calls for a basis.

**Agent A** (fresh session, skill only): "Run this claim from Phase 1 through Phase 3 and stop as soon as Phase 3 is
locked." Result: onboarding complete; Jira and Slack imported (Jira rows checked by eye against the unverified preset);
125 activity rows, all people matched; 20 clusters, 5 excluded with reasons (website, bot dependency updates, a CI
tweak, the customer demo, product packaging); demarcation written; three scenarios run; D1 to D6 locked. P1 locked as a
continuation with the prior title and start date 2024-09-08; P2 as new from ACME-125 (2025-11-10). Balanced chosen.

**Agent B** (fresh session, skill and folder path only): "Continue this SR&ED claim to a finished handoff." Result:
started from STATE.md at phase 4 without redoing Phases 1 to 3; drafted P1 (41 evidence rows) and P2 (25 rows); ran
Phase 6 before review; two review rounds, each with fresh red-team and upside subagents and a triage file; D7 and D8
recorded the confirmed percentages, including the CEO lowered from a proposed 62.5% to 6.67% with a written basis
(SPARSE_EVIDENCE); handoff built.

## Pass criteria

| Criterion | Result |
|---|---|
| B starts from STATE.md without redoing Phases 1 to 3 | PASS |
| Red-team and upside review in fresh subagents, at most two rounds | PASS (2 rounds) |
| `check.py narrative` 0 errors for every project | PASS (P1 0/0; P2 0 errors, 1 warning that stands: "fixed" names the fixed-threshold experiment) |
| `check.py handoff` exits 0 | PASS (0 errors, 0 warnings, verified independently) |
| `handoff/` holds every Phase 7 file | PASS (T661-Part2-P1.md, T661-Part2-P2.md, labour_summary.csv, evidence_index.csv, decision_log.md, gaps.md, README.md) |
| P1 continuation with prior title; P2 new | PASS |
| Routine work excluded in coverage.csv with reasons | PASS (5 clusters) |
| No narrative figure without a verified evidence row | PASS (enforced by check.py markers) |

Manual interventions by the operator: none beyond the scripted claimant. Cost: agent B ran about 45 minutes.

## Fixes made from the dry run

From agent A (commit eb4eb44): `capture.py check` accepts already-captured API sources; new SPARSE_EVIDENCE flag;
candidate projects live in scenarios.md; person_months defined; borderline coverage status; Phase 3 figures exclude gap
bases; field-code pointer; collaboration question in the template.

From agent B: round-2 reviewers read round 1's triage (round 2 had re-argued rejected findings); Phase 6 runs before
review and the red-team sees the labour summary; evidence flags are resolved by a written basis rather than cleared; the
sred-audit output file and prior-filing evidence keys are named; answered questions move to the log.

Not fixed (logged): `check.py` does not flag a confirmed % covering months in which nobody did SR&ED (now a rule in
06-financials.md); open questions tagged "confirm before phase 7" are free text and do not block `check.py setup`.
