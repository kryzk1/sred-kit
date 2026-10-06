# Phase 7: Handoff

Assemble what goes to the accountant and check it.

1. Re-run `python3 <skill-dir>/scripts/time_basis.py --claim .` if anything changed since the last run, so the labour summary matches the confirmed percentages.
2. `python3 <skill-dir>/scripts/handoff.py build --claim .` writes into `handoff/`:
   - `T661-Part2-<P>.md` per project: claim markers stripped, word and line counts stated, ready to paste into the accountant's template
   - `evidence_index.csv`: every cited marker with its source key and raw path
   - `labour_summary.csv`
   - `decision_log.md`: the locked decisions from `STATE.md`
   - `gaps.md`: anything you wrote there earlier (review findings carried past round 2, eligibility answers other than "none", contractor documents still outstanding) is kept, and a generated block of open questions and financial flags is refreshed on every build.
3. Write `handoff/README.md`, one page for the accountant:
   - what each file is
   - the fiscal year, the projects (continuation or new) and the scenario chosen
   - the length-limit mode the narratives were checked against
   - the people claimed and how the percentages were derived (evidence-day time basis, confirmed by the claimant)
   - what they still need to compute (specified-employee limits, 80% contract rule, proxy method, ITC)
   - the open gaps
4. `python3 <skill-dir>/scripts/check.py handoff --claim .` until it reports 0 errors. Errors mean the handoff disagrees with scope or financials: a stale labour summary, a Section A field that differs from `scope/projects.toml`, someone named in Section C with no confirmed %, or claim markers left in the text.
5. Log the handoff in `STATE.md`, set `phase: 7-handoff (complete)`, and remind the claimant to keep `evidence/raw/` and `handoff/` backed up.
