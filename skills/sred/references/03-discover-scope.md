# Phase 3: Discover and scope

Find every piece of eligible work in the year, decide what the projects are, and lock those decisions with the claimant. An SR&ED project is a technological line of inquiry, not a tracker project or a repo.

## 1. Coverage map (`scope/coverage.csv`)

Group every row of `evidence/index/activity.csv` into work clusters: first by obvious signals (container, paths, labels, branch names, issue links in `refs`), then by reading titles and excerpts for the rest. Columns:

`cluster,description,person_months,rows,status,exclusion_reason,evidence_keys`

- `status` is `candidate` or `excluded`. Every `excluded` row has a reason (routine development, bot maintenance, sales or demo, prior project's tail work, business planning, and so on).
- Treat `scope/claimant_context.md` and the claimant's "not SR&ED" preferences as leads: check each against the evidence before excluding or including.
- Keep **directly supporting work** with the experiment it served: harnesses, data collection, test rigs, instrumentation built for an experiment. This is the work claims most often miss.

## 2. Prior-year demarcation (`scope/demarcation.md`)

Read every filing in `prior/`. For each candidate project:

- **Continuation or new.** If it continues a prior project: Line 208 is marked, and the Line 200 title and Line 202 start date are copied exactly from the prior filing. The first evidence in this year is recorded as supporting detail, not as the start date. A new title does not turn a continuation into a first claim.
- **New project.** Its start date is the earliest record that shows the hypothesis or the recognized uncertainty, never the fiscal-year start by default. If it begins soon after a related prior project ended, write a short demarcation note showing the uncertainty sets differ.
- **Baseline.** State concretely what prior years established (with figures), and tie each new uncertainty to the finding it grew from. Knowledge already claimed is now baseline: do not claim it again in new words.

## 3. Candidate projects

For each: title, Line 202/204 dates with their evidence keys, continuation or new, field code (keep the prior code unless the technology changed), the uncertainty hypothesis in one sentence, the clusters it covers (direct and supporting), and the main evidence keys. Unrelated lines of inquiry are separate projects; one project needs one shared technological question.

## 4. Scenarios (`scope/scenarios.md`)

Write classification rules into `sred.toml` (`[[classification.rules]]`: `id`, `project`, `level`, and match fields `container`, `paths`, `tags`, `title`, `kind`, `source`) so rows map to projects. `level` is `direct`, `support`, `borderline` or `none`. Then run, for each scenario:

`python3 <skill-dir>/scripts/time_basis.py --claim . --scenario <conservative|balanced|maximum> --preliminary`

| Scenario | Counts |
|---|---|
| conservative | `direct` only; ignores `weight=summary` rows; gap months at 0% |
| balanced | adds `support`; gap months only with a corroborated basis |
| maximum | adds `borderline`; gap months with any claimant basis |

`scope/scenarios.md` shows for each: the projects and clusters, per-person proposed % (from `scope/preliminary/<scenario>/person_summary.csv`), eligible employee wages and contractor amounts and the ITC estimate (from `scenario_<name>.json`), and each weak point a reviewer would attack with the dollars at risk. Recommend one and say why.

## 5. Lock

The claimant picks the scenario and approves the project set. Then:

- Set `claim.scenario` in `sred.toml`.
- Write `scope/projects.toml`: one `[[project]]` per project with `id`, `title`, `start`, `end`, `continuation`, `field_code`.
- Add locked decisions to `STATE.md`, each with date, ratifier and evidence: scenario, project set, each project's dates and continuation status, exclusions.
- Move resolved preferences out of `## Preferences`.
- Set `phase: 4-draft`.

## Changing a locked decision later

Anyone (claimant, reviewer, you) can propose a change; only the claimant ratifies it. Record it in `STATE.md` as a proposed decision:

```
- D7 (proposed, awaiting <ratifier>): supersedes D2. Change: <what>. Reason: <why>.
  Risks: <e.g. a start date equal to the fiscal-year start is a review flag; a continuation's title and start must match the prior filing>.
  Regenerate if ratified: scope/projects.toml, draft/P1/*, time basis (time_basis.py), handoff/.
```

Do not edit `scope/projects.toml`, narratives or financials for it until it is ratified. When ratified, mark it locked, regenerate the listed artifacts, and log it.
