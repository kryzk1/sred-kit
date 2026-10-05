# S2: Onboard a new claim with partial answers

**State:** `setup_states.py S2` (exports, pre-captured GitLab data and the prior filing; no `sred.toml` or `roster.csv`).

**Prompt:** "Set up a new SR&ED claim for Acme Robotics, fiscal year ending 2026-07-31. My answers are in answers-acme.md; for anything not covered there, I don't know yet."

**Pass criteria**
1. Creates `sred.toml`, `roster.csv` and `STATE.md` (from the kit's templates or equivalent structure).
2. Covers every onboarding area: company and claim, eligibility, people and pay, tools, context and preferences.
3. Logs the two uncovered items (payroll total, Bob's paid hours) as open questions, each tagged with the phase it blocks (6).
4. `check.py setup --claim <dir>` afterwards lists exactly those two items.
5. Reports the filing deadline, 2028-01-31.
6. Records the claimant's scenario preference and their not-SR&ED list as preferences or leads, without locking them: the scenario is chosen in Phase 3 after the three scenarios are compared, and exclusions are decided in the coverage map. (Added after the baseline locked both during onboarding.)
