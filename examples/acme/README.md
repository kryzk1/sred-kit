# Acme Robotics: example claim folder

A fictional claim for Acme Robotics Inc., fiscal year 2025-08-01 to 2026-07-31. Every person, number and event is invented. It runs on a different stack from most teams' defaults on purpose: GitLab, Jira (CSV export) and Slack (export folder).

| Path | What it is |
|---|---|
| `sred.toml`, `roster.csv` | A completed onboarding: company, fiscal year, sources, people and pay |
| `prior/FY2025-T661-Part2.md` | The prior year's filing for the continuing project |
| `evidence/raw/gitlab/` | GitLab merge requests and commits in the shape `capture.py gitlab` writes. They are pre-captured: the API is never called |
| `exports/jira.csv`, `exports/slack/` | Tool exports, converted by the `jira-csv` and `slack-export` presets |
| `generate.py` | Regenerates the raw files and exports deterministically |

What the year contains:

- **P1, Adaptive Grasp Planning Under Occlusion** (continuing): visibility-weighted sampling, a depth prior that overfits on transparent parts, a hybrid sampler, retry policy.
- **P2, Tactile Slip Detection** (new): spectral slip prediction, sensor drift, an abandoned fixed-threshold branch, adaptive baseline compensation.
- **Routine work** that should not be claimed: the marketing website, CI tweaks, dependency bumps, a customer demo.

Try it on a copy:

```bash
cp -r examples/acme /tmp/acme
python3 skills/sred/scripts/check.py setup --claim /tmp/acme --phase 7
python3 skills/sred/scripts/index.py build --claim /tmp/acme
python3 skills/sred/scripts/time_basis.py --claim /tmp/acme --scenario balanced --preliminary
```
