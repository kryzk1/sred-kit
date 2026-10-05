# S1: Resume a half-finished claim

**State:** `setup_states.py S1` (Phase 4; scope locked in D1 to D3; P1 evidence table has C1 to C3).

**Prompt:** "Pick up the Acme SR&ED claim where we left off."

**Pass criteria**
1. Reads `STATE.md` before acting on anything else.
2. Runs `check.py setup` for the current phase and reports the result.
3. Continues the recorded Next action (P1 evidence table, then narrative); does not redo capture, indexing or discovery.
4. Leaves the locked decisions D1 to D3 and `scope/projects.toml` unchanged.
5. Updates `STATE.md` (phase log and Next action) before stopping.
