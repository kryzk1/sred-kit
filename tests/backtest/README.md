# Backtest data (private)

`local.toml` in this folder is gitignored. It holds:

- `leak_terms`: regexes for the reference claimant's private terms (company, org, repos, issue prefix, people,
  accountant). `tests/test_leak.py` fails if any appears in shipped files.
- `[backtest]`: paths to the reference claimant's real drafts and evidence, used by the Plan 2 backtest.

Never commit it.
