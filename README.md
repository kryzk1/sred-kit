# sred-kit

A Claude Code plugin that turns a finished fiscal year into an SR&ED handoff package for your accountant:

- **Written portion:** CRA Form T661 Part 2 for each project (Section A, Lines 242/244/246, Section C).
- **Financial portion:** the Wages & Labour Summary, with each person's SR&ED % backed by an evidence-day time basis.

The goal is the largest claim the evidence supports. It looks back across everything done in the year, including directly supporting work, and every claimed number traces to a raw record from your tools.

> **Not tax advice.** sred-kit prepares the narratives and labour figures; your accountant computes the investment tax credit and files the claim. Percentages are proposals you confirm, and the ITC estimate rates and expenditure limits change: verify them each year.

## Install

Requires Claude Code, Python 3.11 or later, and `gh` (for GitHub capture).

```bash
claude plugin marketplace add kryzk1/sred-kit      # or a path to a local clone
claude plugin install sred-kit@sred-kit
```

The repo is private: you need read access on GitHub (`gh auth login`). To update, run `claude plugin marketplace update sred-kit` then `claude plugin update sred-kit@sred-kit`; if you installed from a local clone, `git pull` in the clone is enough.

The plugin adds two skills: `sred-kit:sred` (the process) and `sred-kit:sred-audit` (the narrative quality rubric it uses).

## Try it on the example

`examples/acme/` is a complete, fictional claim (GitLab, Jira and Slack, four people, two projects plus routine work). From the repo root, start a claim from it in a scratch folder:

```bash
cp -r examples/acme /tmp/acme-try && rm /tmp/acme-try/sred.toml /tmp/acme-try/roster.csv
cp tests/skill-scenarios/answers-acme.md /tmp/acme-try/
cd /tmp/acme-try && claude
```

Then say: *"Set up a new SR&ED claim for Acme Robotics. My answers are in answers-acme.md."* To try picking up a claim halfway, build a ready-made state with `python3 tests/skill-scenarios/setup_states.py S1 /tmp/acme-s1` and say *"Pick up the claim where we left off."*

## Use

Create an empty folder for the claim (one per company per fiscal year), start Claude Code in it, and say *"Set up a new SR&ED claim"* (or run `/sred-kit:sred`). `STATE.md` in the folder records the phase, locked decisions and open questions, so any later session can say *"Pick up the SR&ED claim where we left off."*

| Phase | You are asked | What you get |
|---|---|---|
| 1. Onboarding | Company, fiscal year, prior filings, eligibility basics, people and pay, tools and when access ends, what you think was hard. Documents (payroll export, prior T661) can replace typing; "I don't know yet" is fine | `sred.toml`, `roster.csv`, `STATE.md`, the filing deadline |
| 2. Capture | To approve the capture counts and back up `evidence/raw/` | Raw records from every tool, one shared activity table |
| 3. Discover & scope | To pick a scenario (conservative, balanced, maximum) and approve the project set | Coverage of all work, projects with dates, scenario figures with an ITC estimate |
| 4. Draft | Questions about facts the records don't settle | Evidence table and narrative per project, checked against the form's limits and the do-not patterns |
| 5. Review | To accept or reject what an adversarial reviewer and an upside reviewer found | At most two review rounds, with triage |
| 6. Financials | To confirm each person's SR&ED % (with a written basis where it differs from the proposal) | Person summary with flags, the labour summary in your accountant's columns |
| 7. Handoff | Nothing new | `handoff/`: T661 Part 2 text per project, labour summary, evidence index, decision log, gaps, a README for the accountant |

Nothing changes a locked decision until you ratify it.

### Time and effort

- **Capture** takes minutes for exports and small repos. The GitHub API capture walks every branch, so large repos can take hours. If you have local clones, set `commit_history = false` on the GitHub source and add a `git-log` source; an interrupted GitHub capture resumes when re-run.
- **A full claim** is a few hours of Claude working, plus your approvals at each gate.
- **Capture before access ends.** Subscriptions that lapse take their history with them, and free Slack plans hide messages older than 90 days.

### Tools it reads

API capture for GitHub, GitLab, Linear and Jira; local `git log` for any git host; export presets for Jira, Linear, Asana, ClickUp, Shortcut, Azure DevOps and Slack. Anything else works through a short mapping file or a Claude connector (`skills/sred/references/adding-a-source.md`).

### Known limitations

- A person who was both an employee and a contractor needs care: aliases shared by their two roster rows credit all activity to the last row.
- Section C qualifications (Lines 260–261) and contractor business numbers (Lines 267–269) are added by hand.
- The evidence-day time basis proposes percentages from activity records; people with few records (executives, managers) get a `SPARSE_EVIDENCE` flag and need a written basis.
- The Asana, ClickUp, Shortcut, Azure DevOps and Jira CSV presets are built from documentation; the import report shows any column mismatch on first use.

## Scripts

All in `skills/sred/scripts/`, standard library only, deterministic. The skill runs them; each has `--help`.

| Script | Does |
|---|---|
| `capture.py` | Raw capture from GitHub, GitLab, Linear, Jira, or local `git log`; `check` tests every source |
| `index.py` | `import` an export with a mapping, `build` the shared `activity.csv`, `validate` it |
| `check.py` | `setup` completeness, `narrative` lengths and do-not patterns, `handoff` consistency |
| `time_basis.py` | Evidence-day time basis, person summary, labour summary, scenario totals |
| `handoff.py` | `build` the folder you send to the accountant |

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/pytest
```

- `tests/test_*.py`: the scripts, against fixtures.
- `tests/skill-scenarios/`: behaviour tests of the skill, run by hand with fresh Claude sessions. `README.md` there explains the scenarios; `baseline.md`, `results.md` and `dry-run.md` record the last runs. Re-run them after changing `SKILL.md` or a reference.
- `tests/backtest/`: checks against a real claimant's history. They skip unless `tests/backtest/local.toml` (private, gitignored) points at the data.
- `examples/acme/generate.py` regenerates the example deterministically.
- `docs/specs/` and `docs/plans/` hold the design and the implementation plans.

## Privacy

Claim folders hold payroll and personal data: keep them out of this repo and back them up privately. The kit itself contains no company data; `tests/test_leak.py` enforces that.

## License

MIT. See `LICENSE`.
