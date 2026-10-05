# Skill scenarios

Tests for the `sred` skill, run with fresh subagents (superpowers:writing-skills). Each scenario file gives the
starting state (built by `setup_states.py`), the prompt, and pass criteria checked against the transcript and
the resulting files.

- `baseline.md`: runs without the `sred` skill (RED).
- `results.md`: runs with the skill (GREEN), and any loophole fixes (REFACTOR).

Build a state: `python3 tests/skill-scenarios/setup_states.py S1 /tmp/sred-S1`
