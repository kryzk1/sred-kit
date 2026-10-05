"""Backtest against the reference claimant's real history. Skips unless tests/backtest/local.toml (private,
gitignored) has a [backtest] table pointing at the files."""
import tomllib
from pathlib import Path

import pytest

from sredlib import config
from sredlib.narrative import check_narrative, load_patterns, parse_narrative, word_count

LOCAL = Path(__file__).resolve().parent / "local.toml"
# Patterns behind the mechanical edits an accountant made to a real draft before filing.
ACCOUNTANT_EDITS = {"M-L05", "M-S01", "M-W23", "M-S08", "M-W01", "M-W25", "M-S05", "M-W24", "M-L14", "M-W03",
                    "M-S10", "M-S06", "M-S07", "M-S12", "M-S03", "M-S04", "M-W15b"}


def setting(key: str) -> Path:
    if not LOCAL.exists():
        pytest.skip("tests/backtest/local.toml absent (private)")
    value = (tomllib.loads(LOCAL.read_text()).get("backtest") or {}).get(key)
    if not value or not Path(value).exists():
        pytest.skip(f"[backtest].{key} not configured or missing")
    return Path(value)


def findings_for(narrative_key: str) -> set[str]:
    cfg = config.load_config(setting("fy2025_claim") / "sred.toml")
    n = parse_narrative(setting(narrative_key).read_text())
    return {f.rule for f in check_narrative(n, [], cfg, load_patterns())[0]}


def test_v9_word_counts_match_the_manual_review():
    n = parse_narrative(setting("fy2025_v9_draft").read_text())
    assert {k: word_count(v) for k, v in n.lines.items()} == {"242": 421, "244": 840, "246": 327}


def test_checker_flags_every_mechanical_edit_the_accountant_made():
    assert ACCOUNTANT_EDITS <= findings_for("fy2025_final_narrative")


def test_checker_flags_the_universalization_the_accountant_added():
    assert "M-W14" in findings_for("fy2025_filed_narrative")
