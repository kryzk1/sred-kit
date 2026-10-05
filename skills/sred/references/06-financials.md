# Phase 6: Financials

From activity to each person's confirmed SR&ED %, then the accountant's labour summary. Can run alongside Phases 4 and 5 once scope is locked.

## 1. Classify the activity

1. Run `python3 <skill-dir>/scripts/time_basis.py --claim .` (uses `claim.scenario`). It writes `financials/activity_ledger.csv` and `financials/review_queue.csv`: rows no rule matched, plus your own low-confidence calls.
2. For rows no rule matches, add rules to `sred.toml` where a pattern exists. Classify the rest yourself in `financials/classification_overrides.csv`:

   `source,key,project,level,category,classified_by,confidence,reason`

   - `level`: `direct` (the experiment itself), `support` (directly supporting it), `borderline` (defensible, counted only in the maximum scenario) or `none` (with `category`: routine, support, business, admin).
   - `classified_by = claude`, `confidence` 0 to 1, and a one-line reason grounded in the row's content.
   - The claimant's own corrections use `classified_by = claimant`; they beat every rule.
3. Re-run `time_basis.py`. Rows below `classification.review_threshold` (default 0.7) stay in the review queue for the claimant.

## 2. Gap months

`financials/gap_months.csv` lists every employed month with no evidence. Before asking the claimant, search the other captured sources for that person and month (chat, meeting notes, documents). Then the claimant may give a basis:

`person,month,basis,basis_source,corroborated,basis_share`

`basis_share` is 0 to 100. `corroborated = Y` only when another record supports the basis. Conservative ignores gap bases; balanced uses corroborated ones; maximum uses any basis. Entries that stop matching (a month that now has evidence, an id that changed, a month Excel rewrote) are kept in `gap_months_unmatched.csv` and flagged in `financial_checks.md`; resolve them.

## 3. Confirm each person

`financials/person_summary.csv` shows `evidence_share`, `proposed_pct` and the flags. For each person the claimant fills `confirmed_pct` (0 to 100), and `basis` and `override_reason` when it differs from the proposal. Rerunning keeps those columns.

| Flag | Meaning | Usual fix |
|---|---|---|
| `UNCONFIRMED` | no confirmed % yet | the claimant confirms |
| `IDENTICAL_PCT` | everyone claimed has the same % | per-person bases; a uniform % is a review trigger |
| `OVER_90_NO_BASIS` | above 90% with no basis | write the basis or lower it |
| `OVERRIDE_NO_REASON` | confirmed differs from proposed by more than 15 points with no reason | write the reason |
| `THIN_EVIDENCE` | fewer than 3 months with evidence | basis from other records, or accept a lower % |
| `OUTSIDE_CANADA` | claimed work outside Canada | usually not eligible; tell the accountant |
| `DUAL_ROLE` | the same person is both employee and contractor | make sure no time is costed twice |

People with thin code trails (executives, managers, product) can be raised above their evidence share only with a written basis tied to records, such as experiment reviews they ran.

## 4. Labour summary and checks

`time_basis.py` writes `financials/labour_summary.csv` in the accountant's columns (`templates/labour-summary-columns.csv`, or `preparer.labour_template`) and `financials/financial_checks.md`:

- Payroll reconciliation compares `payroll.total_wages_earned` with employees' earned wages in `roster.csv`. A mismatch means the roster or the payroll figure is wrong; fix the source, don't edit the output.
- The scenario totals and ITC estimate are estimates for choosing a scenario, not the filed numbers.

What the accountant computes, not the kit: specified-employee limits for 10%+ shareholders, the 80% rule for arm's-length contracts, the proxy method, and the ITC on Schedule 31. Flag anything unusual in `handoff/gaps.md`.

## Gate

Every person has a `confirmed_pct`, flags are resolved or explained, payroll reconciles, and no unmatched entries are left. Set `phase: 7-handoff` (after Phase 5 is also done).
