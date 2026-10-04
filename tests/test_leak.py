import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = [ROOT / "skills", ROOT / "examples", ROOT / "tests" / "fixtures", ROOT / "README.md", ROOT / ".claude-plugin"]
LOCAL = ROOT / "tests" / "backtest" / "local.toml"
TEXT_SUFFIXES = {".md", ".toml", ".csv", ".json", ".py", ".txt", ".log"}
SIN_RE = re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{3}\b")
POSTAL_RE = re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z] ?\d[ABCEGHJ-NPRSTV-Z]\d\b")


def shipped_files():
    for base in SHIPPED:
        paths = [base] if base.is_file() else (sorted(base.rglob("*")) if base.exists() else [])
        for p in paths:
            if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
                yield p


def test_no_personal_identifiers():
    hits = [f"{p.relative_to(ROOT)}: {m.group(0)}" for p in shipped_files()
            for rx in (SIN_RE, POSTAL_RE) for m in rx.finditer(p.read_text(encoding="utf-8", errors="ignore"))]
    assert hits == []


def test_no_reference_claimant_terms():
    if not LOCAL.exists():
        pytest.skip("tests/backtest/local.toml is absent (it lists private terms and is never committed)")
    terms = tomllib.loads(LOCAL.read_text(encoding="utf-8")).get("leak_terms", [])
    hits = [f"{p.relative_to(ROOT)}: {t}" for p in shipped_files() for t in terms
            if re.search(t, p.read_text(encoding="utf-8", errors="ignore"))]
    assert hits == []
