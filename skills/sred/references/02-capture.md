# Phase 2: Capture

Pull raw records before access ends, then turn them into one table, `evidence/index/activity.csv`.

## Order

Capture the source whose access ends first (`subscription_end`), and Slack free plans immediately, since history older than 90 days is hidden. Code history comes next: the time basis depends on it.

## Per method

| Method | Do |
|---|---|
| `api` | `python3 <skill-dir>/scripts/capture.py <github\|gitlab\|linear\|jira> --claim . --source NAME`. It writes raw JSON under `evidence/raw/NAME/` and records the manifest. Read any `NOTE:` lines it prints (for example capped comment lists). Rate-limit waits are normal on large orgs. |
| `git-log` | `capture.py git-log --claim . --source NAME`. Captures every branch of each local clone, including abandoned experiments. |
| `export` | Save the tool's export where `export_path` points, then `python3 <skill-dir>/scripts/index.py import --claim . --source NAME`. The file is copied into `evidence/raw/NAME/` first. Read the column report: missing columns, unused columns, failed rows, unmatched people. A preset marked unverified needs its first rows checked against the export by eye. |
| `connector` | Pull through the Claude connector, save the raw JSON under `evidence/raw/NAME/`, and write `evidence/raw/NAME/rows.csv` in the activity format (see `adding-a-source.md`). Mark meeting summaries and other non-verbatim records `weight=summary`. |

A tool with no preset: write a mapping file (see `adding-a-source.md`).

Large GitHub repos: the API capture walks every branch (one or more calls per branch). If you have local clones, set `commit_history = false` on the GitHub source and add a `git-log` source for commits; the API then fetches only PR discussions and reviews. An interrupted GitHub capture resumes from its cache when re-run.

## Build and check

1. `python3 <skill-dir>/scripts/index.py build --claim .` converts every source into `evidence/index/activity.csv`. A source that was configured but never captured stops the build with the exact `capture.py` command to run.
2. `python3 <skill-dir>/scripts/index.py validate --claim .` must report no problems.
3. Open `evidence/index/identities_unmatched.csv`. For each person, add the missing alias to their `roster.csv` row (`gitlab:handle`, `jira:Full Name`, `slack:U123`, `email:...`). Mark accounts that are not people as bots (`[identity] bots`) and external people as external in an open question. Rebuild until the file lists no one who worked on the claim.
4. Ask the claimant to copy `evidence/raw/` somewhere independent. Links in tools die when subscriptions end; these files are the record.

## Gate

The claimant has reviewed the counts in `evidence/raw/MANIFEST.json`, unmatched identities are resolved, `validate` is clean, and the backup is confirmed. Log it, set `phase: 3-scope`.
