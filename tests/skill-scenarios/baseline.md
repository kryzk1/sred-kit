# Baseline runs (RED): no `sred` skill

Each run: one fresh general-purpose subagent with the scenario prompt, the claim folder, and the scripts directory; no
access to the kit's docs or templates; questions for the claimant go to QUESTIONS.md. Globally installed skills
(e.g. sred-audit, sred-submission) were available, as they are for a real user. Runs were made before the Acme example
was shifted one year earlier (its fiscal year had ended after "today", which two agents flagged).

## Summary

| Scenario | Result | Failures |
|---|---|---|
| S1 resume | PASS (5/5) | none |
| S2 onboarding | PARTIAL (4/5, plus a new failure) | locked the scenario and exclusions during onboarding; could not find the templates |
| S3 evidence-first | PASS (4/4) | none |
| S4 locked scope | PARTIAL (2 pass, 2 partial) | no artifacts-to-regenerate list; date risk not named as a review flag |

**What this means for the skill.** The scripts plus the structure of `STATE.md` (phase, locked decisions with ratification,
Next action) already produce most of the discipline: agents read state first, honour ratified decisions, refuse
unsupported numbers and run the checkers. Following writing-skills, S1 and S3 are dropped from the skill's discipline
scope (no rationalization counters are written for them); they stay as regression checks. The skill must address:

1. **Premature locking (S2).** A preference ("default scenario: balanced") and the claimant's view of what is not SR&ED
   were recorded as locked decisions in onboarding, bypassing the Phase 3 scenario comparison and coverage map.
2. **Superseding procedure (S4).** The regenerate list, and naming a fiscal-year-start date as a review flag.
3. **Formats and locations.** Every agent spent many tool calls reverse-engineering the narrative format, claim markers
   and evidence-table columns by running the checker on scratch files, and wrote templates from the code. The skill
   should state the formats and point at the templates.
4. **Domain rules agents found on their own but inconsistently.** A continuing project keeps the original Line 200 title
   and Line 202 start date from the prior filing (S1, S3 and S4 all raised it; none applied it).

## S1: resume

1. Read STATE.md first: PASS. 2. Ran check.py setup: PASS (also --phase 4 and 6). 3. Continued the Next action without
redoing capture or discovery: PASS (ran index.py validate only). 4. Locked decisions unchanged: PASS (raised the D2
start-date conflict as a question). 5. Updated STATE.md: PASS. Drafted P1 (C4 to C28 added, 0 errors, 0 warnings).

## S2: onboarding

1. Created sred.toml, roster.csv, STATE.md: PASS (sred.toml written from the code's schema; the template was not
found). 2. Covered all areas: PASS. 3. Two uncovered items logged with phase 6: PASS. 4. check.py setup lists exactly
those two: PASS. 5. Filing deadline reported: PASS. New failure: locked "scenario = balanced" in sred.toml and the
claimant's not-SR&ED list as classification rules and locked decisions during onboarding. It also went on to import
and index (beyond onboarding, harmless).

## S3: evidence-first

1. Evidence table before prose: PASS (23 verified rows, quotes checked against raw files). 2. Never 430: PASS (cited
40 and 230 against their own experiments, no total). 3. Told the claimant: PASS (QUESTIONS.md Q2). 4. Ran the
checker: PASS.

## S4: locked scope

1. No silent restructuring: PASS. 2. Superseding decision with IDs, reason, regenerate list: PARTIAL (open questions
naming D1/D2 and "needs CEO"; no regenerate list). 3. Review flag named: PARTIAL (argued the date is unsupported by
evidence). 4. Asked to ratify: PASS. Also caught that a continuing project keeps its original start date, and that
STATE.md claimed a P2 draft that did not exist (fixture fixed).
