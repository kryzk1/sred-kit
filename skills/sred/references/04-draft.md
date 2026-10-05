# Phase 4: Draft

One narrative per project in `draft/<P>/`. Evidence first, prose second, checks last.

## 1. Evidence table (`draft/<P>/evidence_table.csv`)

Columns: `claim_id,statement,source_key,raw_path,verified`

- One row per fact a narrative will rely on: each figure, result, failed approach, hypothesis, date and person.
- `source_key` is the durable key from `activity.csv` (`repo#123`, `group/project!12`, a full commit SHA, `ACME-118:issue_comment:1`, `channel:ts`) or a prior filing.
- Open the raw file and confirm the statement says what the record says before setting `verified=Y`. A figure that cannot be found in a raw record does not go in the narrative.
- A figure the claimant remembers is a lead: search for it, and if the evidence differs, use the evidence and tell the claimant both numbers.

## 2. Narrative (`draft/<P>/narrative.md`)

```markdown
# P1: <title exactly as in scope/projects.toml>

## Section A
- 200 Project title: <title>
- 202 Start date: YYYY-MM-DD
- 204 Completion date: YYYY-MM-DD
- 206 Field of science code: 2.02.09
- 208 Continuation: yes|no
- 210 First claim: yes|no

## Line 242
<plain prose>

## Line 244
<plain prose>

## Line 246
<plain prose>

## Section C
- Key individuals: Name (role); Name (role)
- Contractors: Name (company); or none
- Prepared by: <name, role>
- Evidence: <evidence types retained, e.g. design of experiments, records of trial runs, progress reports>
```

- Lines 242/244/246 are plain prose: no bullets, bold, headings or tables.
- Put each `[C#]` marker before the sentence's closing punctuation: `... across 230 trials [C7].`
- Section A and C must match `scope/projects.toml` and the people the time basis claims.

What each line holds (the rubric is in `sred-audit`; the judgment patterns are in `do-not.md`):

- **242, uncertainties.** One or two sentences on what the company does, the concrete baseline from prior work, then each uncertainty: "It was uncertain whether [approach] could [measurable property] under [conditions], because [the standard method] [why it did not settle the question]." What was unknown at the outset, not results.
- **244, work.** In technical order, per uncertainty: hypothesis, method, variables and counts, result (including failures), and what it established. Name contractors' role in one sentence when contractors are claimed. Supporting work gets one bridge sentence.
- **246, advancements.** What was learned, for a class of systems and within the tested bounds, including negative and boundary findings, and why it was not established in the knowledge base at the outset.

## 3. Check and audit

1. `python3 <skill-dir>/scripts/check.py narrative draft/<P>/narrative.md` until it reports 0 errors. Read every warning: each is a pattern from `do-not-patterns.toml` or a mechanical rule. Fix it or note why it stands.
2. Run the `sred-audit` skill on the narrative. Fix every Critical item. Record the score in the phase log; it is a quality floor, not approval.
3. Log the project as drafted. After every project: `phase: 5-review`.
