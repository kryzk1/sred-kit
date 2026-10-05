# sred-kit

Turns a finished fiscal year into an SR&ED handoff package for your accountant:

- **Written portion:** CRA Form T661 Part 2 for each project (Section A, Lines 242/244/246, Section C).
- **Financial portion:** the Wages & Labour Summary, with each person's SR&ED % backed by an evidence-day time basis.

The goal is the largest claim the evidence supports: it looks back across everything done in the year, including directly supporting work, and every claimed number traces to a raw record.

## Install

Requires Claude Code, Python 3.11+, and `gh` (for GitHub capture).

```bash
claude plugin marketplace add <path-or-git-url-of-this-repo>
claude plugin install sred-kit@sred-kit
```

Or copy `skills/sred` (and `skills/sred-audit` if you don't already have it) into `~/.claude/skills/`.

## Use

In an empty folder for the claim (one per company per fiscal year), ask Claude to "set up a new SR&ED claim" or run `/sred setup`. Onboarding asks for everything the later phases need, then the skill walks seven phases: setup, capture, discover and scope, draft, review, financials, handoff. `STATE.md` in the claim folder is the resume point.

**Capture before access ends.** Subscriptions that lapse take their history with them, and free Slack plans hide messages older than 90 days.

## Scripts

All in `skills/sred/scripts/`, standard library only, deterministic:

| Script | Does |
|---|---|
| `capture.py` | Raw capture from GitHub, GitLab, Linear, Jira, or local `git log`; `check` tests every source |
| `index.py` | `import` an export with a mapping, `build` the shared `activity.csv`, `validate` it |
| `check.py` | `setup` completeness, `narrative` lengths and do-not patterns, `handoff` consistency |
| `time_basis.py` | Evidence-day time basis, person summary, labour summary, scenario totals |
| `handoff.py` | `build` the folder you send to the accountant |

Tools without a built-in adapter work through their export file and a short mapping (`skills/sred/mappings/`), or through a Claude connector.

## Develop

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/pytest
```

## Privacy

Claim folders hold payroll and personal data: keep them out of this repo and back them up privately. The kit itself contains no company data; `tests/test_leak.py` enforces that.
