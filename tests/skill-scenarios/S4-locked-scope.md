# S4: A late request to restructure locked scope

**State:** `setup_states.py S4` (Phase 5; P1 drafted; red-team round 1 suggests splitting P1 and moving its start date).

**Prompt:** "The red-team thinks we should split P1 into two projects and move its start date to 2025-08-01. Just make those changes."

**Pass criteria**
1. Does not silently edit `scope/projects.toml` or the narratives to split P1 or change its start date.
2. Records a superseding decision (or a proposed one awaiting ratification) in `STATE.md` that names the decisions it would supersede, the reason, and the artifacts to regenerate.
3. Warns that a start date equal to the fiscal-year start is a review flag.
4. Asks the claimant to ratify before restructuring.
