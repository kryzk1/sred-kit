# sred-kit Engine Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic engine of sred-kit: capture adapters, export mappings, the shared activity table, the narrative/setup/handoff checkers, and the evidence-day time basis that produces the accountant's labour summary.

**Architecture:** Five small CLI scripts in `skills/sred/scripts/` (`capture.py`, `index.py`, `check.py`, `time_basis.py`, `handoff.py`) sit on a shared package `sredlib/`. Every source (API adapter, export mapping, connector rows) converts into one CSV format, `evidence/index/activity.csv`; everything downstream reads only that table. Scripts never call an LLM, use only the Python standard library, and produce byte-identical output for identical input.

**Tech Stack:** Python 3.11+ standard library (`tomllib`, `csv`, `json`, `urllib`, `zoneinfo`, `decimal`), `gh` CLI for the GitHub token, `git` for the git-log adapter, pytest (tests only, in a local `.venv`).

**Spec:** `docs/specs/2026-10-04-sred-kit-design.md` (read §5, §6 and §12 before starting).

**Scope of this plan:** everything in the spec that is code. **Plan 2** (`docs/plans/2026-10-04-sred-kit-skills.md`, written after this one) covers the skill content (`SKILL.md`, phase references, onboarding question bank, `do-not.md`, `t661-fields.md`, `adding-a-source.md`), the vendored `sred-audit` copy, the `examples/acme` claim folder, the onboarding test, the backtest, the fresh-session dry run, and retiring the old `sred-submission` skill.

## Global Constraints

- Python `>=3.11`. Code under `skills/sred/scripts/` imports only the standard library. pytest is used only by `tests/`.
- Run tests with `.venv/bin/pytest` from the repo root (`/Users/kryz/Developer/sred-kit`).
- Scripts are run as `python3 skills/sred/scripts/<name>.py …` and import `sredlib` from their own directory.
- `activity.csv` columns, exactly and in this order: `source,key,kind,person,actor_raw,date,timestamp,container,tags,paths,title,excerpt,refs,url,raw_path,weight`.
- Activity kinds: `commit, pr_opened, pr_merged, pr_review, pr_comment, issue_created, issue_state_change, issue_resolved, issue_assigned, issue_comment, chat_message, meeting, doc_edit`. Weights: `verbatim`, `summary`.
- `person` is a roster id, `bot`, or `unmatched:<raw>`.
- Commit keys are full 40-character SHAs.
- `excerpt` is verbatim, at most 500 characters, then `…[truncated]`. `paths` holds at most 50 entries, then `;…[truncated]`.
- `timestamp` is UTC ISO 8601 ending in `Z`; `date` is the company-local date (`[company] timezone`, default UTC).
- Narrative limits default to words `242: 350, 244: 700, 246: 350` and lines `242: 50, 244: 100, 246: 50` at 78 characters. `[limits] mode` is `words` or `lines`.
- Filing deadline = fiscal year end + 18 months.
- Output files are deterministic: rows sorted, no run timestamps (only `MANIFEST.json` records `captured_at`).
- No real company data anywhere under `skills/`, `examples/`, or `tests/fixtures/`. Fixtures use only the fictional Acme Robotics Inc., Alice Chen, Bob Roy and Carol Diaz, `@acme.test` / `@diaz.test` emails, and no postal codes.
- Never create or commit `tests/backtest/local.toml`; the controller creates it locally (it is gitignored).
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

Inputs the spec implies but would otherwise go untested, most likely first. Each has a test in the owning task.

1. **A real export whose headers differ from a preset (or that Excel saved with a byte-order mark).** Expected: a missing required column stops the import with the column names listed; a missing optional column is reported; a BOM is ignored. Tests in Task 3.
2. **API rate limits on a large GitHub org.** Expected: on HTTP 403 with `X-RateLimit-Remaining: 0` or HTTP 429, the client waits (`Retry-After` or reset time) and retries instead of crashing. Test in Task 5.
3. **The claimant hand-edits `person_summary.csv` (`75%` with a percent sign, a basis, an override reason) and reruns.** Expected: the edits survive the rerun and parse. Test in Task 14.
4. **A late-evening commit on the last day of the fiscal year.** Expected: with `[company] timezone` set, it lands in this fiscal year even though it is the next day in UTC. Tests in Tasks 1 and 2.
5. **A source configured but never captured.** Expected: `index.py build` stops with a message naming the source and the exact `capture.py` command, not a stack trace. Test in Task 10.

## File Structure

```
sred-kit/
  pyproject.toml                         pytest config (testpaths, pythonpath)
  .gitignore
  README.md                              install, quick start, scripts, tests, privacy
  .claude-plugin/plugin.json             plugin manifest
  .claude-plugin/marketplace.json        lets `claude plugin marketplace add` install from the repo
  skills/sred/
    mappings/                            export presets (TOML)
      jira-csv.toml linear-csv.toml asana-csv.toml clickup-csv.toml
      shortcut-csv.toml azure-devops-csv.toml slack-export.toml
    references/do-not-patterns.toml      mechanical patterns read by check.py
    templates/
      sred.toml roster.csv STATE.md labour-summary-columns.csv
    scripts/
      capture.py index.py check.py time_basis.py handoff.py
      sredlib/
        __init__.py
        config.py        load sred.toml; fiscal year, sources, limits, rates, timezone
        roster.py        roster.csv; Resolver (aliases, email, name, bots)
        dates.py         timestamp parsing (iso, js, epoch, strptime formats)
        activity.py      activity schema, make_row, refs, read/write, validate
        manifest.py      evidence/raw/MANIFEST.json
        mapping.py       export mapping engine (csv, json)
        slack_export.py  Slack workspace export (zip or folder)
        indexing.py      import one export, build activity.csv, validate
        http.py          JSON-over-HTTP with retries
        adapters/
          __init__.py    Context, CaptureError, get_adapter, adapter_key
          github.py gitlab.py linear.py jira.py gitlog.py
        setupcheck.py    check.py setup
        narrative.py     narrative parsing, counts, check.py narrative
        timebasis.py     ledger, monthly shares, gaps, person summary, labour summary
        handoff.py       handoff build + check.py handoff
  tests/
    conftest.py          fixtures path, FakeHttp, make_claim
    fixtures/exports/    jira.csv linear.csv asana.csv clickup.csv shortcut.csv azure.csv
                         trello.json trello-mapping.toml
    test_*.py
    backtest/README.md   what local.toml holds (local.toml itself is gitignored)
```

---

### Task 1: Scaffold, config, roster, dates

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `skills/sred/scripts/sredlib/__init__.py`, `skills/sred/scripts/sredlib/config.py`, `skills/sred/scripts/sredlib/roster.py`, `skills/sred/scripts/sredlib/dates.py`, `skills/sred/templates/sred.toml`, `skills/sred/templates/roster.csv`, `tests/conftest.py`
- Test: `tests/test_config.py`, `tests/test_roster.py`, `tests/test_dates.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `config.load_config(path: Path) -> dict` (adds `_path`, `_dir`); `config.ConfigError(ValueError)`; `config.fiscal_year(cfg) -> tuple[date, date]`; `config.sources(cfg) -> list[dict]`; `config.source(cfg, name) -> dict`; `config.limits(cfg) -> dict` with keys `mode`, `words`, `lines`, `line_width` (line keys are strings `"242"`…); `config.issue_key_regexes(cfg) -> list[str]`; `config.classification(cfg) -> {"review_threshold": float, "rules": list[dict]}`; `config.rates(cfg) -> dict | None`; `config.kind_weights(cfg) -> dict[str, float]`; `config.timezone_of(cfg) -> tzinfo`; `config.resolve_path(cfg, p: str) -> Path`; constants `VALID_KINDS`, `VALID_METHODS`, `API_TOOLS`.
  - `roster.ROSTER_COLUMNS: list[str]`; `roster.load_roster(path) -> list[dict]`; `roster.parse_aliases(text) -> list[tuple[str, str]]`; `roster.Resolver(roster, extra_bots=None)` with `.resolve(tool, actor, email="", name="") -> str` and `.is_bot(actor) -> bool`.
  - `dates.parse_iso(value) -> datetime`; `dates.iso(ts) -> str`; `dates.parse_datetime(value, formats: list[str]) -> datetime | None`.
  - `tests/conftest.py` fixtures: `fixtures` (Path to `tests/fixtures`), `fake_http` (the `FakeHttp` class), `make_claim(extra_toml="", roster=None) -> Path`.

- [ ] **Step 1: Create the project skeleton and test harness**

`pyproject.toml`:
```toml
[project]
name = "sred-kit"
version = "0.1.0"
description = "Turn a finished fiscal year into an SR&ED handoff package"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["skills/sred/scripts"]
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
tests/backtest/local.toml
```

`skills/sred/scripts/sredlib/__init__.py`:
```python
"""Shared library for the sred-kit scripts. Standard library only."""
```

`tests/conftest.py`:
```python
import csv
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

BASE_TOML = """
[company]
name = "Acme Robotics Inc."

[fiscal_year]
start = 2026-08-01
end = 2027-07-31
"""


class FakeHttp:
    """Answers requests from canned routes: (method, url_prefix, payload, headers).

    The first route whose method matches and whose prefix starts the URL wins, so list
    more specific prefixes first. A callable payload receives the request body.
    """

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, url, headers=None, body=None):
        self.calls.append((method, url, body))
        for m, prefix, payload, hdrs in self.routes:
            if m == method and url.startswith(prefix):
                data = payload(body) if callable(payload) else payload
                return data, {k.lower(): v for k, v in (hdrs or {}).items()}
        raise AssertionError(f"unexpected request {method} {url}")

    def get(self, url, headers=None):
        return self.request("GET", url, headers)

    def post(self, url, body, headers=None):
        return self.request("POST", url, headers, body)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def fake_http():
    return FakeHttp


@pytest.fixture
def make_claim(tmp_path):
    def _make(extra_toml: str = "", roster=None) -> Path:
        (tmp_path / "sred.toml").write_text(BASE_TOML + extra_toml, encoding="utf-8")
        if roster is not None:
            from sredlib.roster import ROSTER_COLUMNS

            with (tmp_path / "roster.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=ROSTER_COLUMNS, lineterminator="\n")
                writer.writeheader()
                for row in roster:
                    writer.writerow({c: row.get(c, "") for c in ROSTER_COLUMNS})
        return tmp_path

    return _make
```

Create the venv:
```bash
cd /Users/kryz/Developer/sred-kit && python3 -m venv .venv && .venv/bin/pip install --quiet pytest
```

- [ ] **Step 2: Write the failing tests**

`tests/test_config.py`:
```python
from datetime import date, datetime, timezone

import pytest

from sredlib import config


def test_fiscal_year_reads_toml_dates(make_claim):
    cfg = config.load_config(make_claim() / "sred.toml")
    assert config.fiscal_year(cfg) == (date(2026, 8, 1), date(2027, 7, 31))


def test_fiscal_year_rejects_quoted_dates(tmp_path):
    (tmp_path / "sred.toml").write_text('[fiscal_year]\nstart = "2026-08-01"\nend = "2027-07-31"\n')
    cfg = config.load_config(tmp_path / "sred.toml")
    with pytest.raises(config.ConfigError, match="TOML dates"):
        config.fiscal_year(cfg)


def test_limits_default_to_form_word_maximums(make_claim):
    lim = config.limits(config.load_config(make_claim() / "sred.toml"))
    assert lim["mode"] == "words"
    assert lim["words"] == {"242": 350, "244": 700, "246": 350}
    assert lim["lines"] == {"242": 50, "244": 100, "246": 50}
    assert lim["line_width"] == 78


def test_limits_override_mode_and_values(make_claim):
    claim = make_claim('[limits]\nmode = "lines"\n[limits.lines]\n244 = 90\n')
    lim = config.limits(config.load_config(claim / "sred.toml"))
    assert lim["mode"] == "lines" and lim["lines"]["244"] == 90 and lim["lines"]["242"] == 50


def test_source_lookup_and_issue_regexes(make_claim):
    claim = make_claim("""
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
issue_key_regex = '[A-Z]+-\\d+'
""")
    cfg = config.load_config(claim / "sred.toml")
    assert config.source(cfg, "jira")["tool"] == "jira"
    assert config.issue_key_regexes(cfg) == [r"[A-Z]+-\d+"]
    with pytest.raises(config.ConfigError):
        config.source(cfg, "nope")


def test_timezone_defaults_to_utc_and_rejects_unknown(make_claim, tmp_path):
    cfg = config.load_config(make_claim() / "sred.toml")
    assert config.timezone_of(cfg) == timezone.utc
    cfg["company"]["timezone"] = "America/Vancouver"
    late = datetime(2027, 8, 1, 5, tzinfo=timezone.utc)
    assert late.astimezone(config.timezone_of(cfg)).date() == date(2027, 7, 31)
    cfg["company"]["timezone"] = "Mars/Olympus"
    with pytest.raises(config.ConfigError, match="time zone"):
        config.timezone_of(cfg)


def test_classification_rates_and_kind_weights(make_claim):
    claim = make_claim("""
[classification]
review_threshold = 0.8
[[classification.rules]]
id = "r1"
project = "P1"
level = "direct"
[rates]
itc_rate = 0.35
[time_basis.kind_weights]
chat_message = 0.5
""")
    cfg = config.load_config(claim / "sred.toml")
    assert config.classification(cfg) == {"review_threshold": 0.8, "rules": [{"id": "r1", "project": "P1", "level": "direct"}]}
    assert config.rates(cfg) == {"itc_rate": 0.35}
    assert config.kind_weights(cfg) == {"chat_message": 0.5}
    assert config.resolve_path(cfg, "prior/a.pdf") == claim / "prior/a.pdf"
```

`tests/test_roster.py`:
```python
from sredlib.roster import Resolver, load_roster, parse_aliases

ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "github:achen;slack:U01;email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac;email:bob@acme.test"},
]


def test_parse_aliases_lowercases_and_skips_junk():
    assert parse_aliases("GitHub:AChen; nonsense ;email:A@x.io") == [("github", "achen"), ("email", "a@x.io")]


def test_resolve_by_tool_alias_email_name_and_angle_form():
    r = Resolver(ROSTER)
    assert r.resolve("github", "AChen") == "alice"
    assert r.resolve("git", "whoever", email="ALICE@acme.test") == "alice"
    assert r.resolve("linear", "u-123", name="Bob Roy") == "bob"
    assert r.resolve("azure-devops", "Bob Roy <bob@acme.test>") == "bob"


def test_bots_and_unmatched():
    r = Resolver(ROSTER, extra_bots=["build-robot"])
    assert r.resolve("github", "dependabot[bot]") == "bot"
    assert r.resolve("github", "build-robot") == "bot"
    assert r.resolve("github", "stranger") == "unmatched:stranger"
    assert r.resolve("github", "") == "unmatched:"


def test_load_roster_fills_missing_columns(tmp_path):
    (tmp_path / "roster.csv").write_text("id,name\nalice, Alice Chen \n")
    rows = load_roster(tmp_path / "roster.csv")
    assert rows[0]["name"] == "Alice Chen" and rows[0]["wages_earned"] == ""
```

`tests/test_dates.py`:
```python
from datetime import datetime, timezone

import pytest

from sredlib.dates import iso, parse_datetime, parse_iso

UTC = timezone.utc


def test_iso_roundtrip_and_offsets():
    assert parse_iso("2026-09-01T10:00:00Z") == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert parse_iso("2026-09-01T12:00:00.000+0200") == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert iso(datetime(2026, 9, 1, 10, tzinfo=UTC)) == "2026-09-01T10:00:00Z"


def test_parse_formats_in_order():
    assert parse_datetime("Fri Sep 27 2024 22:10:24 GMT+0000 (GMT+00:00)", ["js"]) == datetime(2024, 9, 27, 22, 10, 24, tzinfo=UTC)
    assert parse_datetime("07/Mar/26 2:15 PM", ["iso", "%d/%b/%y %I:%M %p"]) == datetime(2026, 3, 7, 14, 15, tzinfo=UTC)
    assert parse_datetime("1767225600000", ["epoch_ms"]) == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_datetime("", ["iso"]) is None


def test_parse_failure_names_value():
    with pytest.raises(ValueError, match="nonsense"):
        parse_datetime("nonsense", ["iso"])
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_config.py tests/test_roster.py tests/test_dates.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'sredlib.config'` (and `roster`, `dates`).

- [ ] **Step 4: Implement `dates.py`, `config.py`, `roster.py`**

`skills/sred/scripts/sredlib/dates.py`:
```python
"""Timestamp parsing shared by every adapter and mapping."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")


def parse_iso(value: str) -> datetime:
    """Parse ISO 8601, accepting a trailing Z and +HHMM offsets. Naive values are UTC."""
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    v = _OFFSET_RE.sub(r"\1:\2", v)
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(ts: datetime) -> str:
    """UTC ISO 8601 with a trailing Z."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str, formats: list[str]) -> datetime | None:
    """Try each format in order. Special formats: iso, epoch, epoch_ms, js (Linear CSV).

    Returns None for an empty value; raises ValueError naming the value if nothing parses.
    """
    v = (value or "").strip()
    if not v:
        return None
    for fmt in formats:
        try:
            if fmt == "iso":
                return parse_iso(v)
            if fmt == "epoch":
                return datetime.fromtimestamp(float(v), tz=timezone.utc)
            if fmt == "epoch_ms":
                return datetime.fromtimestamp(float(v) / 1000, tz=timezone.utc)
            if fmt == "js":
                core = re.sub(r"\s*\(.*\)$", "", v)
                return datetime.strptime(core, "%a %b %d %Y %H:%M:%S GMT%z")
            dt = datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, OverflowError, OSError):
            continue
    raise ValueError(f"could not parse date {value!r} with formats {formats}")
```

`skills/sred/scripts/sredlib/config.py`:
```python
"""Load and query sred.toml."""
from __future__ import annotations

import tomllib
from datetime import date, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VALID_KINDS = {"code", "tracker", "chat", "meetings", "docs"}
VALID_METHODS = {"api", "export", "connector", "git-log"}
API_TOOLS = {"github", "gitlab", "linear", "jira"}
DEFAULT_LIMITS = {
    "mode": "words",
    "words": {"242": 350, "244": 700, "246": 350},
    "lines": {"242": 50, "244": 100, "246": 50},
    "line_width": 78,
}


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> dict:
    path = Path(path)
    with path.open("rb") as fh:
        cfg = tomllib.load(fh)
    cfg["_path"] = path
    cfg["_dir"] = path.parent
    return cfg


def fiscal_year(cfg: dict) -> tuple[date, date]:
    fy = cfg.get("fiscal_year") or {}
    start, end = fy.get("start"), fy.get("end")
    if not isinstance(start, date) or not isinstance(end, date):
        raise ConfigError("fiscal_year.start and fiscal_year.end must be TOML dates (YYYY-MM-DD, unquoted)")
    if end <= start:
        raise ConfigError("fiscal_year.end must be after fiscal_year.start")
    return start, end


def sources(cfg: dict) -> list[dict]:
    return list(cfg.get("sources") or [])


def source(cfg: dict, name: str) -> dict:
    for s in sources(cfg):
        if s.get("name") == name:
            return s
    raise ConfigError(f"no source named {name!r} in sred.toml")


def limits(cfg: dict) -> dict:
    user = cfg.get("limits") or {}
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_LIMITS.items()}
    for key in ("words", "lines"):
        for line, val in (user.get(key) or {}).items():
            out[key][str(line)] = int(val)
    if "mode" in user:
        out["mode"] = user["mode"]
    if "line_width" in user:
        out["line_width"] = int(user["line_width"])
    if out["mode"] not in ("words", "lines"):
        raise ConfigError("limits.mode must be 'words' or 'lines'")
    return out


def issue_key_regexes(cfg: dict) -> list[str]:
    return [s["issue_key_regex"] for s in sources(cfg) if s.get("issue_key_regex")]


def classification(cfg: dict) -> dict:
    c = cfg.get("classification") or {}
    return {"review_threshold": float(c.get("review_threshold", 0.7)), "rules": list(c.get("rules") or [])}


def rates(cfg: dict) -> dict | None:
    r = cfg.get("rates") or {}
    out = {k: float(r[k]) for k in ("itc_rate", "proxy_rate", "contract_rate") if k in r}
    return out or None


def kind_weights(cfg: dict) -> dict[str, float]:
    weights = (cfg.get("time_basis") or {}).get("kind_weights") or {}
    return {k: float(v) for k, v in weights.items()}


def timezone_of(cfg: dict) -> tzinfo:
    name = (cfg.get("company") or {}).get("timezone")
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"company.timezone {name!r} is not a known time zone (e.g. America/Toronto)") from exc


def resolve_path(cfg: dict, p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else Path(cfg["_dir"]) / path
```

`skills/sred/scripts/sredlib/roster.py`:
```python
"""Roster loading and identity resolution across tools."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROSTER_COLUMNS = [
    "id", "name", "classification", "company", "title", "start", "end", "in_canada", "specified_employee",
    "aliases", "paid_hours", "wages_paid", "wages_earned", "bonus", "taxable_benefits", "pay_in_lieu",
    "arms_length", "contract_provided", "sred_in_contract", "street", "city", "province", "postal", "country",
]
DEFAULT_BOT_RE = re.compile(r"(\[bot\]$|^(dependabot|renovate|github-actions|slackbot|vercel|codecov)\b|[-_]bot$)", re.I)
ANGLE_RE = re.compile(r"^(.*?)\s*<([^<>@\s]+@[^<>\s]+)>$")


def load_roster(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ROSTER_COLUMNS:
            r[k] = (r.get(k) or "").strip()
    return rows


def parse_aliases(text: str) -> list[tuple[str, str]]:
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        tool, value = part.split(":", 1)
        out.append((tool.strip().lower(), value.strip().lower()))
    return out


class Resolver:
    """Maps a tool's actor (handle, id, email, display name) to a roster id."""

    def __init__(self, roster: list[dict], extra_bots: list[str] | None = None):
        self.index: dict[tuple[str, str], str] = {}
        self.email: dict[str, str] = {}
        self.names: dict[str, str] = {}
        for r in roster:
            pid = r["id"]
            for tool, value in parse_aliases(r.get("aliases", "")):
                if tool == "email":
                    self.email[value] = pid
                else:
                    self.index[(tool, value)] = pid
            if r.get("name"):
                self.names[r["name"].strip().lower()] = pid
        self.extra_bots = {b.lower() for b in (extra_bots or [])}

    def is_bot(self, actor: str) -> bool:
        a = (actor or "").strip()
        return bool(a) and (a.lower() in self.extra_bots or bool(DEFAULT_BOT_RE.search(a)))

    def resolve(self, tool: str, actor: str, email: str = "", name: str = "") -> str:
        actor, email, name = (actor or "").strip(), (email or "").strip().lower(), (name or "").strip()
        m = ANGLE_RE.match(actor)
        if m:
            name = name or m.group(1).strip()
            email = email or m.group(2).lower()
            actor = m.group(1).strip() or email
        if not actor and not email and not name:
            return "unmatched:"
        if self.is_bot(actor) or (name and self.is_bot(name)):
            return "bot"
        key = (tool.lower(), actor.lower())
        if key in self.index:
            return self.index[key]
        if email and email in self.email:
            return self.email[email]
        if "@" in actor and actor.lower() in self.email:
            return self.email[actor.lower()]
        for candidate in (name, actor):
            if candidate and candidate.lower() in self.names:
                return self.names[candidate.lower()]
        return f"unmatched:{actor or email or name}"
```

- [ ] **Step 5: Add the config and roster templates**

`skills/sred/templates/sred.toml`:
```toml
# sred.toml: one claim folder per company per fiscal year.
# Dates are TOML dates: write them unquoted, e.g. 2026-08-01.

[company]
name = ""                 # legal name
ccpc = true               # Canadian-controlled private corporation
provinces = []            # e.g. ["BC"]
timezone = ""             # IANA name, e.g. "America/Toronto"; blank = UTC

[fiscal_year]
start = 2026-08-01
end = 2027-07-31

[claim]
first_claim = false       # true if the company has never claimed SR&ED
prior_filings = []        # prior T661 Part 2 PDFs, e.g. ["prior/FY2026-T661-Part2.pdf"]
prior_titles = []         # project titles exactly as filed before (Line 200)
field_codes = []          # field-of-science codes filed before (Line 206)
scenario = ""             # locked in Phase 3: conservative | balanced | maximum
# [[claim.prior_projects]]
# title = ""
# end = 2026-07-31

[preparer]
accountant = ""
firm = ""
labour_template = ""      # optional CSV (column,field) replacing templates/labour-summary-columns.csv
third_party_preparer = false
ratifier = ""             # who approves locked decisions, e.g. "CEO"
# handoff_target = 2027-10-31

[eligibility]             # answer each one; "none" is a valid answer
government_assistance = ""
client_contract_work = ""
funded_by_others = ""
work_outside_canada = ""

[payroll]
total_wages_earned = 0.0  # payroll total for the fiscal year; reconciles roster.csv

[limits]
mode = ""                 # "words" (form maximums) or "lines" (the preparer's line budget)
# [limits.words]
# 242 = 350
# [limits.lines]
# 244 = 100

[classification]
review_threshold = 0.7
# [[classification.rules]]
# id = "r1"
# project = "P1"
# level = "direct"        # direct | support | borderline | none
# container = "acme/vision*"
# paths = "models/*"

[rates]                   # optional, for the scenario ITC estimate only; verify current rates
itc_rate = 0.35
proxy_rate = 0.55
contract_rate = 0.80

[identity]
bots = []                 # extra bot account names

# One [[sources]] block per tool. method: api | export | connector | git-log
# [[sources]]
# name = "github"
# kind = "code"
# tool = "github"
# method = "api"
# org = "acme"
# repos = []              # empty = every repo in the org
# subscription_end = 2027-12-31
# issue_key_regex = '#\d+'
```

`skills/sred/templates/roster.csv`:
```
id,name,classification,company,title,start,end,in_canada,specified_employee,aliases,paid_hours,wages_paid,wages_earned,bonus,taxable_benefits,pay_in_lieu,arms_length,contract_provided,sred_in_contract,street,city,province,postal,country
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_config.py tests/test_roster.py tests/test_dates.py -v`
Expected: PASS (14 tests).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore skills tests
git commit -m "feat: scaffold sred-kit with config, roster and date parsing

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Activity table and manifest

**Files:**
- Create: `skills/sred/scripts/sredlib/activity.py`, `skills/sred/scripts/sredlib/manifest.py`
- Test: `tests/test_activity.py`, `tests/test_manifest.py`

**Interfaces:**
- Consumes: `dates.iso`.
- Produces:
  - `activity.COLUMNS`, `activity.KINDS`, `activity.WEIGHTS`, `activity.TRUNC`, `activity.EXCERPT_MAX`, `activity.PATHS_MAX`.
  - `activity.make_row(*, source, key, kind, person, actor_raw, ts: datetime, container="", tags=(), paths=(), title="", excerpt="", refs=(), url="", raw_path="", weight="verbatim", tz=None) -> dict`.
  - `activity.in_window(ts, start: date, end: date, tz=None) -> bool`.
  - `activity.extract_refs(text, regexes: list[str], own_key="") -> list[str]`; `activity.join(values) -> str`; `activity.split(value) -> list[str]`; `activity.truncate(text, limit=500) -> str`; `activity.first_line(text) -> str`.
  - `activity.write_rows(path, rows)`; `activity.read_rows(path) -> tuple[list[str], list[dict]]` (header, rows).
  - `activity.validate_rows(rows, header, start, end, claim_dir, roster_ids=None) -> list[str]`.
  - `manifest.record(claim_dir, source, *, method, files, counts, date_range=None, notes=None, now=None) -> dict`; `manifest.sha256(path) -> str`; `manifest.manifest_path(claim_dir) -> Path`.

- [ ] **Step 1: Write the failing tests**

`tests/test_activity.py`:
```python
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sredlib import activity

TS = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
FY = (date(2026, 8, 1), date(2027, 7, 31))


def row(**kw):
    base = dict(source="gh", key="acme/vision#1", kind="pr_opened", person="alice", actor_raw="achen", ts=TS, raw_path="evidence/raw/gh/x.json")
    base.update(kw)
    return activity.make_row(**base)


def test_make_row_truncates_and_joins():
    r = row(excerpt="x" * 600, tags=["a", "b", "a", ""], paths=[f"p{i}" for i in range(60)], title="\n  First line\nsecond")
    assert r["excerpt"].endswith(activity.TRUNC) and len(r["excerpt"]) == 500 + len(activity.TRUNC)
    assert r["tags"] == "a;b"
    assert r["paths"].count(";") == 50 and r["paths"].endswith(activity.TRUNC)
    assert r["title"] == "First line"
    assert r["date"] == "2026-09-01" and r["timestamp"] == "2026-09-01T10:00:00Z"


def test_local_date_and_window_follow_company_timezone():
    van = ZoneInfo("America/Vancouver")
    late = datetime(2027, 8, 1, 5, tzinfo=timezone.utc)  # 22:00 on July 31 in Vancouver
    r = row(ts=late, tz=van)
    assert r["date"] == "2027-07-31" and r["timestamp"] == "2027-08-01T05:00:00Z"
    assert activity.in_window(late, *FY, van)
    assert not activity.in_window(late, *FY)


def test_extract_refs_finds_keys_and_pr_urls_but_not_self():
    text = "Fixes ACME-12 and ACME-12, see https://github.com/acme/vision/pull/7 and https://gitlab.com/acme/ml/core/-/merge_requests/3"
    assert activity.extract_refs(text, [r"[A-Z]+-\d+"], own_key="ACME-99") == ["ACME-12", "acme/vision#7", "acme/ml/core!3"]
    assert activity.extract_refs("ACME-1", [r"[A-Z]+-\d+"], own_key="ACME-1") == []


def test_write_read_roundtrip_is_sorted(tmp_path):
    rows = [row(key="b", ts=datetime(2026, 9, 2, tzinfo=timezone.utc)), row(key="a")]
    activity.write_rows(tmp_path / "a.csv", rows)
    header, back = activity.read_rows(tmp_path / "a.csv")
    assert header == activity.COLUMNS
    assert [r["key"] for r in back] == ["a", "b"]


def test_validate_catches_each_problem(tmp_path):
    raw = tmp_path / "evidence/raw/gh/x.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}")
    good = row()
    bad = dict(good, key="k2", kind="nope", weight="loud", person="Not Valid!", date="2025-01-01", raw_path="missing.json")
    problems = activity.validate_rows([good, dict(good), bad], activity.COLUMNS, *FY, tmp_path, roster_ids={"alice"})
    text = "\n".join(problems)
    for needle in ["duplicate source+key", "unknown kind", "weight must be", "person must be", "outside the fiscal year", "does not exist"]:
        assert needle in text
    assert activity.validate_rows([good], ["wrong"], *FY, tmp_path) == ["columns must be exactly: " + ",".join(activity.COLUMNS)]


def test_validate_flags_person_not_in_roster(tmp_path):
    raw = tmp_path / "evidence/raw/gh/x.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}")
    problems = activity.validate_rows([row(person="zed")], activity.COLUMNS, *FY, tmp_path, roster_ids={"alice"})
    assert problems == ["line 2 (gh:acme/vision#1): person 'zed' is not in roster.csv"]
```

`tests/test_manifest.py`:
```python
import json
from datetime import datetime, timezone

from sredlib import manifest


def test_record_writes_checksums_and_replaces_source_entry(tmp_path):
    f = tmp_path / "evidence/raw/gh/a.json"
    f.parent.mkdir(parents=True)
    f.write_text("abc")
    now = datetime(2027, 8, 2, 9, tzinfo=timezone.utc)
    manifest.record(tmp_path, "gh", method="api", files=[f], counts={"pulls": 1}, date_range=("2026-08-01", "2027-07-31"), now=now)
    manifest.record(tmp_path, "gh", method="api", files=[f], counts={"pulls": 2}, now=now)
    entry = json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]["gh"]
    assert entry["counts"] == {"pulls": 2}
    assert entry["files"][0] == {"path": "evidence/raw/gh/a.json", "bytes": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}
    assert entry["captured_at"] == "2027-08-02T09:00:00+00:00"
    assert entry["date_range"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_activity.py tests/test_manifest.py -v`
Expected: FAIL with `ImportError: cannot import name 'activity'`.

- [ ] **Step 3: Implement `activity.py` and `manifest.py`**

`skills/sred/scripts/sredlib/activity.py`:
```python
"""The shared activity table that every phase after capture reads."""
from __future__ import annotations

import csv
import re
from datetime import date, datetime, timezone
from pathlib import Path

from .dates import iso

COLUMNS = ["source", "key", "kind", "person", "actor_raw", "date", "timestamp", "container", "tags", "paths",
           "title", "excerpt", "refs", "url", "raw_path", "weight"]
KINDS = {"commit", "pr_opened", "pr_merged", "pr_review", "pr_comment", "issue_created", "issue_state_change",
         "issue_resolved", "issue_assigned", "issue_comment", "chat_message", "meeting", "doc_edit"}
WEIGHTS = {"verbatim", "summary"}
EXCERPT_MAX = 500
PATHS_MAX = 50
TRUNC = "…[truncated]"
PR_URL_RE = re.compile(r"https?://(?:www\.)?github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)")
MR_URL_RE = re.compile(r"https?://[\w.-]+/([\w.-]+(?:/[\w.-]+)+)/-/merge_requests/(\d+)")
PERSON_RE = re.compile(r"[\w.-]+")


def truncate(text: str, limit: int = EXCERPT_MAX) -> str:
    text = (text or "").replace("\r\n", "\n")
    return text if len(text) <= limit else text[:limit] + TRUNC


def join(values) -> str:
    out: list[str] = []
    for v in values:
        v = (v or "").strip()
        if v and v not in out:
            out.append(v)
    return ";".join(out)


def split(value: str) -> list[str]:
    return [v for v in (value or "").split(";") if v]


def first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()[:300]
    return ""


def extract_refs(text: str, regexes: list[str], own_key: str = "") -> list[str]:
    """Issue keys (configured regexes, no capture groups needed) plus GitHub PR and GitLab MR URLs."""
    text = text or ""
    found: list[str] = []
    for rx in regexes:
        found += [m.group(0) for m in re.finditer(rx, text)]
    found += [f"{repo}#{num}" for repo, num in PR_URL_RE.findall(text)]
    found += [f"{path}!{num}" for path, num in MR_URL_RE.findall(text)]
    return [f for f in dict.fromkeys(found) if f and f != own_key]


def local_date(ts: datetime, tz=None) -> date:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(tz or timezone.utc).date()


def in_window(ts: datetime, start: date, end: date, tz=None) -> bool:
    return start <= local_date(ts, tz) <= end


def make_row(*, source, key, kind, person, actor_raw, ts: datetime, container="", tags=(), paths=(), title="",
             excerpt="", refs=(), url="", raw_path="", weight="verbatim", tz=None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if weight not in WEIGHTS:
        raise ValueError(f"unknown weight {weight!r}")
    paths = [p for p in paths if p]
    path_str = join(paths[:PATHS_MAX])
    if len(paths) > PATHS_MAX:
        path_str += ";" + TRUNC
    return {
        "source": source, "key": key, "kind": kind, "person": person, "actor_raw": actor_raw or "",
        "date": local_date(ts, tz).isoformat(), "timestamp": iso(ts), "container": container or "",
        "tags": join(tags), "paths": path_str, "title": first_line(title), "excerpt": truncate(excerpt),
        "refs": join(refs), "url": url or "", "raw_path": raw_path, "weight": weight,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r["timestamp"], r["source"], r["key"]))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in ordered:
            writer.writerow({c: r.get(c, "") for c in COLUMNS})


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def validate_rows(rows: list[dict], header: list[str], start: date, end: date, claim_dir: Path,
                  roster_ids: set[str] | None = None) -> list[str]:
    if header != COLUMNS:
        return ["columns must be exactly: " + ",".join(COLUMNS)]
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for i, r in enumerate(rows, start=2):
        where = f"line {i} ({r['source']}:{r['key']})"
        if not r["source"] or not r["key"]:
            problems.append(f"{where}: source and key are required")
        if (r["source"], r["key"]) in seen:
            problems.append(f"{where}: duplicate source+key")
        seen.add((r["source"], r["key"]))
        if r["kind"] not in KINDS:
            problems.append(f"{where}: unknown kind {r['kind']!r}")
        if r["weight"] not in WEIGHTS:
            problems.append(f"{where}: weight must be 'verbatim' or 'summary'")
        person = r["person"]
        if person != "bot" and not person.startswith("unmatched:"):
            if not PERSON_RE.fullmatch(person or ""):
                problems.append(f"{where}: person must be a roster id, 'bot' or 'unmatched:<raw>'")
            elif roster_ids is not None and person not in roster_ids:
                problems.append(f"{where}: person {person!r} is not in roster.csv")
        try:
            d = date.fromisoformat(r["date"])
            if not start <= d <= end:
                problems.append(f"{where}: date {d} is outside the fiscal year {start}..{end}")
        except ValueError:
            problems.append(f"{where}: date must be YYYY-MM-DD")
        if not r["raw_path"] or not (Path(claim_dir) / r["raw_path"]).exists():
            problems.append(f"{where}: raw_path {r['raw_path']!r} does not exist")
    return problems
```

`skills/sred/scripts/sredlib/manifest.py`:
```python
"""evidence/raw/MANIFEST.json: what was captured, when, how, with checksums."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path(claim_dir: Path) -> Path:
    return Path(claim_dir) / "evidence" / "raw" / "MANIFEST.json"


def record(claim_dir, source, *, method, files, counts, date_range=None, notes=None, now=None) -> dict:
    claim_dir = Path(claim_dir)
    path = manifest_path(claim_dir)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sources": {}}
    root = claim_dir.resolve()
    entry = {
        "method": method,
        "captured_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "files": [{"path": str(Path(f).resolve().relative_to(root)), "sha256": sha256(f), "bytes": Path(f).stat().st_size}
                  for f in sorted(map(Path, files))],
        "counts": dict(counts),
        "date_range": list(date_range) if date_range else None,
        "notes": list(notes or []),
    }
    data["sources"][source] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_activity.py tests/test_manifest.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/activity.py skills/sred/scripts/sredlib/manifest.py tests/test_activity.py tests/test_manifest.py
git commit -m "feat: add the shared activity table and capture manifest

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Export mapping engine, `index.py import`, Jira and Linear presets

**Files:**
- Create: `skills/sred/scripts/sredlib/mapping.py`, `skills/sred/scripts/sredlib/indexing.py`, `skills/sred/scripts/index.py`, `skills/sred/mappings/jira-csv.toml`, `skills/sred/mappings/linear-csv.toml`, `tests/fixtures/exports/jira.csv`, `tests/fixtures/exports/linear.csv`, `tests/fixtures/exports/trello.json`, `tests/fixtures/exports/trello-mapping.toml`
- Test: `tests/test_mapping.py`

**Interfaces:**
- Consumes: `activity.make_row`, `activity.in_window`, `activity.extract_refs`, `activity.write_rows`, `dates.parse_datetime`, `roster.Resolver`, `roster.load_roster`, `config.*`, `manifest.record`.
- Produces:
  - `mapping.PRESET_DIR: Path`; `mapping.MappingError(ValueError)`; `mapping.ImportResult` dataclass (`rows`, `unmapped_columns`, `missing_columns`, `failures`, `warnings`, `skipped_outside_fy`).
  - `mapping.load_mapping(spec: str, claim_dir: Path) -> dict` (`spec` is a preset name like `"jira-csv"` or a path ending in `.toml`, relative to the claim folder).
  - `mapping.import_export(mapping, export_path, *, source, resolver, regexes, claim_dir, fy, tz=None) -> ImportResult`.
  - `indexing.parts_dir(claim_dir) -> Path`; `indexing.resolver_for(cfg, claim_dir) -> Resolver`; `indexing.stage_export(claim_dir, src) -> Path`; `indexing.import_source(cfg, claim_dir, name, mapping_spec=None) -> ImportResult` (writes `evidence/index/parts/<name>.csv`, records the manifest).
  - CLI: `index.py import --claim DIR --source NAME [--mapping SPEC]` (exit 0 with report; exit 2 on a fatal mapping/config error).

**Mapping file format** (documented here; Plan 2 documents it for users in `adding-a-source.md`):
```toml
tool = "jira"              # used for roster alias lookup (aliases like jira:<id>)
kind = "tracker"
format = "csv"             # csv | json | slack-export
verified = false           # false = built from documentation; a warning is printed on import
weight = "verbatim"        # optional; "summary" for non-verbatim records
date_formats = ["iso"]     # tried in order: iso, epoch, epoch_ms, js, or strptime patterns
key = "Issue key"          # column (csv) or dotted path (json) holding the record id
container = "Project key"  # optional; a list means "first non-empty"
title = "Summary"          # optional; same rules
url = ""                   # optional
tags = ["Labels"]          # every column with these names, repeated columns included
records = ""               # json only: dotted path to the list of records

[[events]]                 # each record can yield several activity rows
kind = "issue_created"
key_suffix = ""            # default ":<kind>"; repeat events get ":<kind>:<n>"
date = "Created"
actor = "Reporter"
actor_email = ""           # optional column
actor_name = ""            # optional column
actor_strip = ""           # optional: characters stripped from the actor, e.g. "[]"
actor_split = ""           # optional: keep the first actor when the field lists several
excerpt = "Description"    # optional
when = { field = "type", equals = "createCard" }  # optional filter

[[events]]
kind = "issue_comment"
repeat = "Comment"         # one row per non-empty column with this name
split = ";"                # each value is split into split_fields
split_fields = ["date", "actor", "excerpt"]
```

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/exports/jira.csv`:
```
Summary,Issue key,Issue id,Issue Type,Status,Project key,Assignee,Reporter,Created,Resolved,Labels,Labels,Description,Comment,Comment
Test grasp planner under occlusion,ACME-12,10012,Story,Done,ACME,Bob Roy,Alice Chen,03/Sep/26 9:05 AM,20/Sep/26 4:30 PM,research,vision,Hypothesis: occlusion-aware sampling beats ACME-7 baseline,05/Sep/26 11:00 AM;5b10ac;First run failed at 40% occlusion,06/Sep/26 2:00 PM;Alice Chen;Retrying with depth prior
Old ticket,ACME-3,10003,Bug,Done,ACME,Bob Roy,Bob Roy,01/Jun/26 9:00 AM,02/Jun/26 9:00 AM,,,Before the fiscal year,,
```

`tests/fixtures/exports/linear.csv` (header copied from a real Linear export; one data row):
```
"ID","Team","Title","Description","Status","Estimate","Priority","Project ID","Project","Creator","Assignee","Labels","Cycle Number","Cycle Name","Cycle Start","Cycle End","Created","Updated","Started","Triaged","Completed","Canceled","Archived","Due Date","Parent issue","Initiatives","Project Milestone ID","Project Milestone","SLA Status","UUID","Time in status (minutes)","Related to","Blocked by","Duplicate of"
"ACME-40","Robotics","Compare depth priors","Follow-up to ACME-12","Done","3","High","p1","Perception","alice@acme.test","bob@acme.test","Research","","","","","Fri Oct 02 2026 17:00:00 GMT+0000 (GMT+00:00)","Mon Oct 12 2026 09:00:00 GMT+0000 (GMT+00:00)","Sat Oct 03 2026 09:00:00 GMT+0000 (GMT+00:00)","","Mon Oct 12 2026 09:00:00 GMT+0000 (GMT+00:00)","","","","","","","","","u1","","","",""
```

`tests/fixtures/exports/trello.json`:
```json
{
  "name": "Grasping",
  "actions": [
    {"id": "a1", "type": "createCard", "date": "2026-09-10T15:00:00.000Z", "memberCreator": {"username": "achen"},
     "data": {"board": {"name": "Grasping"}, "card": {"name": "Test suction cup on porous parts"}}},
    {"id": "a2", "type": "commentCard", "date": "2026-09-11T15:00:00.000Z", "memberCreator": {"username": "achen"},
     "data": {"board": {"name": "Grasping"}, "card": {"name": "Test suction cup on porous parts"}, "text": "Seal failed on foam at 0.4 bar"}},
    {"id": "a3", "type": "updateBoard", "date": "2026-09-12T15:00:00.000Z", "memberCreator": {"username": "achen"},
     "data": {"board": {"name": "Grasping"}}}
  ]
}
```

`tests/fixtures/exports/trello-mapping.toml`:
```toml
tool = "trello"
kind = "tracker"
format = "json"
verified = true
records = "actions"
key = "id"
container = "data.board.name"
title = "data.card.name"
date_formats = ["iso"]

[[events]]
kind = "issue_created"
when = { field = "type", equals = "createCard" }
date = "date"
actor = "memberCreator.username"

[[events]]
kind = "issue_comment"
when = { field = "type", equals = "commentCard" }
date = "date"
actor = "memberCreator.username"
excerpt = "data.text"
```

- [ ] **Step 2: Write the failing tests**

`tests/test_mapping.py`:
```python
from datetime import date

import pytest

import index
from sredlib import config
from sredlib.mapping import MappingError, import_export, load_mapping
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "jira:alice chen;email:alice@acme.test;trello:achen"},
    {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac;email:bob@acme.test"},
]


def stage(tmp_path, fixtures, name):
    target = tmp_path / "evidence/raw/src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((fixtures / "exports" / name).read_bytes())
    return target


def run(mapping, path, tmp_path, regexes=(r"[A-Z]+-\d+",)):
    return import_export(mapping, path, source="src", resolver=Resolver(ROSTER), regexes=list(regexes), claim_dir=tmp_path, fy=FY)


def test_jira_preset_yields_created_resolved_and_each_comment(tmp_path, fixtures):
    res = run(load_mapping("jira-csv", tmp_path), stage(tmp_path, fixtures, "jira.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert set(by_key) == {"ACME-12", "ACME-12:issue_resolved", "ACME-12:issue_comment:1", "ACME-12:issue_comment:2"}
    created = by_key["ACME-12"]
    assert created["kind"] == "issue_created" and created["person"] == "alice"
    assert created["timestamp"] == "2026-09-03T09:05:00Z"
    assert created["tags"] == "Story;Done;research;vision"
    assert created["refs"] == "ACME-7"
    assert by_key["ACME-12:issue_comment:1"]["person"] == "bob"
    assert by_key["ACME-12:issue_comment:2"]["excerpt"] == "Retrying with depth prior"
    assert res.skipped_outside_fy == 2
    assert res.warnings and "not been verified" in res.warnings[0]


def test_linear_preset_parses_js_dates_and_email_actor(tmp_path, fixtures):
    res = run(load_mapping("linear-csv", tmp_path), stage(tmp_path, fixtures, "linear.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "ACME-40")
    assert created["person"] == "alice" and created["date"] == "2026-10-02"
    assert created["container"] == "Perception"
    assert {r["kind"] for r in res.rows} == {"issue_created", "issue_state_change", "issue_resolved"}
    assert not res.warnings


def test_missing_required_column_is_fatal(tmp_path):
    path = tmp_path / "evidence/raw/src/bad.csv"
    path.parent.mkdir(parents=True)
    path.write_text("Summary,Created\nx,03/Sep/26 9:05 AM\n")
    with pytest.raises(MappingError, match="Issue key"):
        run(load_mapping("jira-csv", tmp_path), path, tmp_path)


def test_bad_date_is_reported_not_fatal(tmp_path):
    path = tmp_path / "evidence/raw/src/d.csv"
    path.parent.mkdir(parents=True)
    path.write_text("Issue key,Summary,Created,Resolved,Reporter\nACME-1,x,yesterday,,Alice Chen\n")
    res = run(load_mapping("jira-csv", tmp_path), path, tmp_path)
    assert res.rows == [] and "yesterday" in res.failures[0]
    assert "Assignee" in res.missing_columns


def test_excel_bom_header_is_tolerated(tmp_path):
    path = tmp_path / "evidence/raw/src/bom.csv"
    path.parent.mkdir(parents=True)
    path.write_bytes("﻿Issue key,Summary,Created,Resolved,Reporter\nACME-5,x,03/Sep/26 9:05 AM,,Alice Chen\n".encode("utf-8"))
    res = run(load_mapping("jira-csv", tmp_path), path, tmp_path)
    assert [r["key"] for r in res.rows] == ["ACME-5"]


def test_custom_json_mapping_for_tool_without_preset(tmp_path, fixtures):
    path = stage(tmp_path, fixtures, "trello.json")
    (tmp_path / "trello-mapping.toml").write_text((fixtures / "exports" / "trello-mapping.toml").read_text())
    res = run(load_mapping("trello-mapping.toml", tmp_path), path, tmp_path)
    assert sorted((r["kind"], r["person"]) for r in res.rows) == [("issue_comment", "alice"), ("issue_created", "alice")]
    assert {r["container"] for r in res.rows} == {"Grasping"}


def test_unknown_preset_lists_available(tmp_path):
    with pytest.raises(MappingError, match="jira-csv"):
        load_mapping("nope", tmp_path)


def test_index_import_cli_stages_raw_copy_and_writes_part(make_claim, fixtures, capsys):
    claim = make_claim("""
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"
issue_key_regex = '[A-Z]+-\\d+'
""", roster=[{"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "jira:alice chen"}])
    (claim / "exports").mkdir()
    (claim / "exports/jira.csv").write_bytes((fixtures / "exports/jira.csv").read_bytes())
    assert index.main(["import", "--claim", str(claim), "--source", "jira"]) == 0
    out = capsys.readouterr().out
    assert "jira: 4 rows, 2 outside the fiscal year" in out
    assert "Unmatched people" in out and "Bob Roy" in out
    assert (claim / "evidence/raw/jira/jira.csv").exists()
    assert (claim / "evidence/index/parts/jira.csv").exists()
    assert "jira" in (claim / "evidence/raw/MANIFEST.json").read_text()


def test_index_import_cli_reports_fatal_error(make_claim, capsys):
    claim = make_claim('[[sources]]\nname = "x"\nkind = "tracker"\ntool = "jira"\nmethod = "export"\nexport_path = "missing.csv"\nmapping = "jira-csv"\n')
    assert index.main(["import", "--claim", str(claim), "--source", "x"]) == 2
    assert "export file not found" in capsys.readouterr().err
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'index'` / `sredlib.mapping`.

- [ ] **Step 4: Implement `mapping.py`**

`skills/sred/scripts/sredlib/mapping.py`:
```python
"""Convert a tool's export file into activity rows using a small TOML mapping."""
from __future__ import annotations

import csv
import json
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import activity
from .dates import parse_datetime
from .roster import Resolver

PRESET_DIR = Path(__file__).resolve().parent.parent.parent / "mappings"
FORMATS = {"csv", "json", "slack-export"}


class MappingError(ValueError):
    pass


@dataclass
class ImportResult:
    rows: list[dict] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_outside_fy: int = 0


def load_mapping(spec: str, claim_dir: Path) -> dict:
    path = Path(spec)
    if path.suffix != ".toml":
        path = PRESET_DIR / f"{spec}.toml"
    elif not path.is_absolute():
        path = Path(claim_dir) / path
    if not path.exists():
        presets = sorted(p.stem for p in PRESET_DIR.glob("*.toml"))
        raise MappingError(f"mapping {spec!r} not found; presets: {', '.join(presets)}")
    mapping = tomllib.loads(path.read_text(encoding="utf-8"))
    mapping["_path"] = str(path)
    _check_structure(mapping)
    return mapping


def _check_structure(m: dict) -> None:
    fmt = m.get("format", "csv")
    if fmt not in FORMATS:
        raise MappingError(f"format must be one of {sorted(FORMATS)}")
    if fmt == "slack-export":
        return
    for req in ("tool", "key", "events"):
        if not m.get(req):
            raise MappingError(f"mapping is missing {req!r}")
    for ev in m["events"]:
        if ev.get("kind") not in activity.KINDS:
            raise MappingError(f"event kind {ev.get('kind')!r} is not a known activity kind")
        if ev.get("repeat"):
            if "date" not in (ev.get("split_fields") or []):
                raise MappingError("repeat events need split_fields including 'date'")
        elif not ev.get("date"):
            raise MappingError(f"event {ev['kind']!r} needs a 'date' column")


class CsvRecord:
    def __init__(self, header: list[str], values: list[str]):
        self.pairs = list(zip(header, values))

    def get(self, name: str) -> str:
        for h, v in self.pairs:
            if h == name and v.strip():
                return v.strip()
        return ""

    def get_all(self, name: str) -> list[str]:
        return [v.strip() for h, v in self.pairs if h == name and v.strip()]


class JsonRecord:
    """Dotted paths into one JSON record; `a.b[].c` maps over the list at `b`."""

    def __init__(self, data):
        self.data = data

    def _walk(self, node, parts):
        if not parts:
            return node
        head, rest = parts[0], parts[1:]
        if head.endswith("[]"):
            items = node.get(head[:-2]) if isinstance(node, dict) else None
            if not isinstance(items, list):
                return []
            out = []
            for item in items:
                v = self._walk(item, rest)
                out.extend(v if isinstance(v, list) else [v])
            return out
        return self._walk(node.get(head), rest) if isinstance(node, dict) else None

    def get_all(self, name: str) -> list[str]:
        v = self._walk(self.data, name.split("."))
        values = v if isinstance(v, list) else [v]
        return [str(x).strip() for x in values if x is not None and not isinstance(x, (dict, list)) and str(x).strip()]

    def get(self, name: str) -> str:
        values = self.get_all(name)
        return values[0] if values else ""


def _first(rec, spec) -> str:
    if not spec:
        return ""
    for name in ([spec] if isinstance(spec, str) else spec):
        v = rec.get(name)
        if v:
            return v
    return ""


def _load_csv(path: Path) -> tuple[list[str], list[CsvRecord]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = [h.strip() for h in next(reader, [])]
        records = [CsvRecord(header, row) for row in reader if any(c.strip() for c in row)]
    return header, records


def _load_json(path: Path, records_path: str) -> list[JsonRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if records_path:
        for part in records_path.split("."):
            data = data.get(part, []) if isinstance(data, dict) else []
    if not isinstance(data, list):
        raise MappingError(f"records path {records_path!r} does not point at a list")
    return [JsonRecord(item) for item in data]


def _referenced(m: dict) -> list[str]:
    names: list[str] = []

    def add(spec):
        if isinstance(spec, str) and spec:
            names.append(spec)
        elif isinstance(spec, list):
            names.extend(s for s in spec if s)

    for k in ("key", "container", "title", "url"):
        add(m.get(k))
    add(m.get("tags", []))
    for ev in m["events"]:
        for k in ("date", "actor", "actor_email", "actor_name", "excerpt", "repeat"):
            add(ev.get(k))
        if ev.get("when"):
            add(ev["when"].get("field"))
    return list(dict.fromkeys(names))


def _event_items(ev: dict, rec) -> list[tuple[str, dict]]:
    if ev.get("repeat"):
        fields_ = ev["split_fields"]
        items = []
        for i, value in enumerate(rec.get_all(ev["repeat"]), start=1):
            parts = value.split(ev.get("split", ";"), len(fields_) - 1)
            items.append((f":{ev['kind']}:{i}", dict(zip(fields_, parts))))
        return items
    return [(ev.get("key_suffix", f":{ev['kind']}"), {
        "date": rec.get(ev["date"]),
        "actor": rec.get(ev["actor"]) if ev.get("actor") else "",
        "actor_email": rec.get(ev["actor_email"]) if ev.get("actor_email") else "",
        "actor_name": rec.get(ev["actor_name"]) if ev.get("actor_name") else "",
        "excerpt": rec.get(ev["excerpt"]) if ev.get("excerpt") else "",
    })]


def _clean_actor(ev: dict, actor: str) -> str:
    actor = (actor or "").strip()
    if ev.get("actor_strip"):
        actor = actor.strip(ev["actor_strip"]).strip()
    if ev.get("actor_split"):
        actor = actor.split(ev["actor_split"])[0].strip()
    return actor


def import_export(mapping: dict, export_path: Path, *, source: str, resolver: Resolver, regexes: list[str],
                  claim_dir: Path, fy: tuple[date, date], tz=None) -> ImportResult:
    fmt = mapping.get("format", "csv")
    if fmt == "slack-export":
        from .slack_export import import_slack

        return import_slack(export_path, source=source, resolver=resolver, regexes=regexes, claim_dir=claim_dir, fy=fy, tz=tz)
    result = ImportResult()
    if not mapping.get("verified", False):
        result.warnings.append(f"mapping {Path(mapping['_path']).name} has not been verified against a real export: "
                               "check the column report and the first rows before relying on it")
    if fmt == "csv":
        header, records = _load_csv(export_path)
        referenced = _referenced(mapping)
        result.missing_columns = [c for c in referenced if c not in header]
        result.unmapped_columns = [c for c in dict.fromkeys(header) if c and c not in referenced]
        required = [mapping["key"]] + [ev["date"] for ev in mapping["events"] if not ev.get("repeat")]
        fatal = [c for c in dict.fromkeys(required) if c not in header]
        if fatal:
            raise MappingError(f"export is missing required columns: {', '.join(fatal)}")
    else:
        records = _load_json(export_path, mapping.get("records", ""))
    raw_path = str(Path(export_path).resolve().relative_to(Path(claim_dir).resolve()))
    formats = mapping.get("date_formats", ["iso"])
    start, end = fy
    seen: set[str] = set()
    for n, rec in enumerate(records, start=1):
        base = rec.get(mapping["key"])
        if not base:
            result.failures.append(f"record {n}: empty key {mapping['key']!r}")
            continue
        container, title, url = _first(rec, mapping.get("container")), _first(rec, mapping.get("title")), _first(rec, mapping.get("url"))
        tags = [t for col in mapping.get("tags", []) for t in rec.get_all(col)]
        for ev in mapping["events"]:
            when = ev.get("when")
            if when and rec.get(when["field"]) != when["equals"]:
                continue
            for suffix, f in _event_items(ev, rec):
                if not (f.get("date") or "").strip():
                    continue
                key = f"{base}{suffix}"
                try:
                    ts = parse_datetime(f["date"], formats)
                except ValueError as exc:
                    result.failures.append(f"record {n} ({key}): {exc}")
                    continue
                if not activity.in_window(ts, start, end, tz):
                    result.skipped_outside_fy += 1
                    continue
                if key in seen:
                    result.failures.append(f"record {n}: duplicate key {key!r} skipped")
                    continue
                seen.add(key)
                actor = _clean_actor(ev, f.get("actor", ""))
                excerpt = (f.get("excerpt") or "").strip()
                result.rows.append(activity.make_row(
                    source=source, key=key, kind=ev["kind"],
                    person=resolver.resolve(mapping["tool"], actor, email=f.get("actor_email", ""), name=f.get("actor_name", "")),
                    actor_raw=actor, ts=ts, container=container, tags=tags, title=title, excerpt=excerpt,
                    refs=activity.extract_refs(f"{title}\n{excerpt}", regexes, own_key=base), url=url,
                    raw_path=raw_path, weight=mapping.get("weight", "verbatim"), tz=tz,
                ))
    return result
```

- [ ] **Step 5: Implement `indexing.py` (import part) and `index.py`**

`skills/sred/scripts/sredlib/indexing.py`:
```python
"""Build evidence/index from raw captures."""
from __future__ import annotations

import shutil
from pathlib import Path

from . import activity, config, manifest
from .mapping import ImportResult, import_export, load_mapping
from .roster import Resolver, load_roster


def parts_dir(claim_dir: Path) -> Path:
    return Path(claim_dir) / "evidence" / "index" / "parts"


def resolver_for(cfg: dict, claim_dir: Path) -> Resolver:
    roster_path = Path(claim_dir) / "roster.csv"
    roster = load_roster(roster_path) if roster_path.exists() else []
    return Resolver(roster, extra_bots=(cfg.get("identity") or {}).get("bots", []))


def stage_export(claim_dir: Path, src: dict) -> Path:
    """Raw-first: make sure the export lives under evidence/raw/<name>/ before converting it."""
    claim_dir = Path(claim_dir)
    if not src.get("export_path"):
        raise config.ConfigError(f"source {src['name']!r} has no export_path")
    given = Path(src["export_path"])
    given = given if given.is_absolute() else claim_dir / given
    if not given.exists():
        raise FileNotFoundError(f"export file not found: {given}")
    raw_dir = claim_dir / "evidence" / "raw" / src["name"]
    if raw_dir.resolve() in given.resolve().parents:
        return given
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / given.name
    if given.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(given, target)
    else:
        shutil.copy2(given, target)
    return target


def import_source(cfg: dict, claim_dir: Path, name: str, mapping_spec: str | None = None) -> ImportResult:
    claim_dir = Path(claim_dir)
    src = config.source(cfg, name)
    staged = stage_export(claim_dir, src)
    spec = mapping_spec or src.get("mapping")
    if not spec:
        raise config.ConfigError(f'source {name!r} needs mapping = "<preset or path>"')
    result = import_export(load_mapping(spec, claim_dir), staged, source=name, resolver=resolver_for(cfg, claim_dir),
                           regexes=config.issue_key_regexes(cfg), claim_dir=claim_dir, fy=config.fiscal_year(cfg),
                           tz=config.timezone_of(cfg))
    files = [staged] if staged.is_file() else sorted(p for p in staged.rglob("*") if p.is_file())
    dates = sorted(r["date"] for r in result.rows)
    manifest.record(claim_dir, name, method="export", files=files,
                    counts={"rows": len(result.rows), "skipped_outside_fy": result.skipped_outside_fy, "failures": len(result.failures)},
                    date_range=(dates[0], dates[-1]) if dates else None, notes=result.warnings)
    activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", result.rows)
    return result
```

`skills/sred/scripts/index.py`:
```python
#!/usr/bin/env python3
"""Build and check evidence/index/activity.csv.

  index.py import   --claim DIR --source NAME [--mapping PRESET_OR_PATH]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sredlib import config, indexing
from sredlib.mapping import MappingError


def cmd_import(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        res = indexing.import_source(cfg, claim, args.source, args.mapping)
    except (MappingError, config.ConfigError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{args.source}: {len(res.rows)} rows, {res.skipped_outside_fy} outside the fiscal year")
    for kind, n in sorted(Counter(r["kind"] for r in res.rows).items()):
        print(f"  {kind}: {n}")
    unmatched = Counter(r["actor_raw"] for r in res.rows if r["person"].startswith("unmatched:") and r["actor_raw"])
    if unmatched:
        print("Unmatched people (add aliases to roster.csv): " + ", ".join(f"{a} ({n})" for a, n in unmatched.most_common()))
    if res.missing_columns:
        print("Columns named in the mapping but absent from the export: " + ", ".join(res.missing_columns))
    if res.unmapped_columns:
        print("Export columns not used: " + ", ".join(res.unmapped_columns))
    for w in res.warnings:
        print(f"WARNING: {w}")
    for f in res.failures[:20]:
        print(f"FAILED: {f}")
    if len(res.failures) > 20:
        print(f"... and {len(res.failures) - 20} more failures")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="convert one export file using a mapping")
    imp.add_argument("--claim", default=".")
    imp.add_argument("--source", required=True)
    imp.add_argument("--mapping")
    imp.set_defaults(func=cmd_import)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Add the Jira and Linear presets**

`skills/sred/mappings/jira-csv.toml`:
```toml
# Jira Cloud: Filters > Export > "Export CSV (all fields)".
tool = "jira"
kind = "tracker"
format = "csv"
verified = false
date_formats = ["%d/%b/%y %I:%M %p", "%d/%b/%Y %I:%M %p", "%Y-%m-%d %H:%M", "iso"]
key = "Issue key"
container = "Project key"
title = "Summary"
tags = ["Issue Type", "Status", "Labels"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "Created"
actor = "Reporter"
excerpt = "Description"

[[events]]
kind = "issue_resolved"
date = "Resolved"
actor = "Assignee"

[[events]]
kind = "issue_comment"
repeat = "Comment"
split = ";"
split_fields = ["date", "actor", "excerpt"]
```

`skills/sred/mappings/linear-csv.toml`:
```toml
# Linear: Settings > Workspace > Import/Export > Export CSV. Has no comments: prefer capture.py linear while the API is live.
tool = "linear"
kind = "tracker"
format = "csv"
verified = true
date_formats = ["js", "iso"]
key = "ID"
container = ["Project", "Team"]
title = "Title"
tags = ["Status", "Labels", "Team"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "Created"
actor = "Creator"
excerpt = "Description"

[[events]]
kind = "issue_state_change"
key_suffix = ":started"
date = "Started"
actor = "Assignee"

[[events]]
kind = "issue_resolved"
date = "Completed"
actor = "Assignee"

[[events]]
kind = "issue_state_change"
key_suffix = ":canceled"
date = "Canceled"
actor = "Assignee"
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_mapping.py -v`
Expected: PASS (9 tests).

- [ ] **Step 8: Commit**

```bash
git add skills/sred/scripts/sredlib/mapping.py skills/sred/scripts/sredlib/indexing.py skills/sred/scripts/index.py skills/sred/mappings tests/fixtures tests/test_mapping.py
git commit -m "feat: add export mapping engine with Jira and Linear presets

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Slack export and the remaining presets

**Files:**
- Create: `skills/sred/scripts/sredlib/slack_export.py`, `skills/sred/mappings/slack-export.toml`, `skills/sred/mappings/asana-csv.toml`, `skills/sred/mappings/clickup-csv.toml`, `skills/sred/mappings/shortcut-csv.toml`, `skills/sred/mappings/azure-devops-csv.toml`, `tests/fixtures/exports/asana.csv`, `tests/fixtures/exports/clickup.csv`, `tests/fixtures/exports/shortcut.csv`, `tests/fixtures/exports/azure.csv`
- Test: `tests/test_slack_and_presets.py`

**Interfaces:**
- Consumes: `mapping.ImportResult`, `mapping.load_mapping`, `mapping.import_export`, `activity.make_row`, `activity.in_window`, `activity.extract_refs`, `roster.Resolver`.
- Produces: `slack_export.import_slack(export_path, *, source, resolver, regexes, claim_dir, fy, tz=None) -> ImportResult` (called by `mapping.import_export` when `format = "slack-export"`); presets `slack-export`, `asana-csv`, `clickup-csv`, `shortcut-csv`, `azure-devops-csv`.

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/exports/asana.csv`:
```
Task ID,Created At,Completed At,Last Modified,Name,Section/Column,Assignee,Assignee Email,Start Date,Due Date,Tags,Notes,Projects,Parent task
1203,2026-09-14,2026-09-30,2026-09-30,Measure slip on wet parts,Experiments,Alice Chen,alice@acme.test,,,research,Friction model failed above 60% humidity,Grasping,
```

`tests/fixtures/exports/clickup.csv`:
```
Task ID,Task Name,Task Content,Status,Date Created,Date Closed,Assignees,Tags,List Name,Folder Name,Space Name
86b1x,Tune gripper force loop,PID gains oscillated at 5 kHz,complete,1789052400000,,"[Alice Chen, Bob Roy]",research,Control,R&D,Robotics
```

`tests/fixtures/exports/shortcut.csv`:
```
id,name,type,requester,owners,description,created_at,started_at,completed_at,labels,epic,state,project,workflow
512,Evaluate tactile sensor drift,feature,Bob Roy,"Alice Chen, Bob Roy",Drift exceeded spec after 2h,2026-11-03T16:00:00Z,2026-11-04T16:00:00Z,,research,Tactile,In Progress,Sensing,Engineering
```

`tests/fixtures/exports/azure.csv`:
```
ID,Work Item Type,Title,Assigned To,State,Tags,Created Date,Created By,Changed Date,Closed Date,Area Path,Iteration Path
4411,Task,Benchmark path planner on cluttered bins,Alice Chen <alice@acme.test>,Closed,research,12/01/2026 9:15:00 AM,Bob Roy <bob@acme.test>,12/09/2026 3:00:00 PM,12/09/2026 3:00:00 PM,Robotics\Planning,Sprint 9
```

- [ ] **Step 2: Write the failing tests**

`tests/test_slack_and_presets.py`:
```python
import json
import zipfile
from datetime import date

import pytest

from sredlib.mapping import PRESET_DIR, import_export, load_mapping
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "email:bob@acme.test"},
]
# 2026-09-01T10:00:00Z = 1788256800; 2026-06-01T08:00:00Z = 1780300800


def make_export(tmp_path):
    zpath = tmp_path / "evidence/raw/slack/export.zip"
    zpath.parent.mkdir(parents=True)
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("users.json", json.dumps([
            {"id": "U01", "profile": {"email": "alice@acme.test", "real_name": "Alice Chen"}},
            {"id": "U02", "profile": {"real_name": "Bob Roy"}},
        ]))
        zf.writestr("channels.json", "[]")
        zf.writestr("dev/2026-09-01.json", json.dumps([
            {"type": "message", "user": "U01", "text": "Occlusion test failed, see ACME-12 and https://github.com/acme/vision/pull/7",
             "ts": "1788256800.000100", "thread_ts": "1788256800.000100", "reply_count": 1},
            {"type": "message", "user": "U02", "text": "Try the depth prior", "ts": "1788257000.000200", "thread_ts": "1788256800.000100"},
            {"type": "message", "subtype": "channel_join", "user": "U02", "text": "joined", "ts": "1788257100.000300"},
            {"type": "message", "bot_id": "B1", "text": "Deploy finished", "ts": "1788257200.000400"},
        ]))
        zf.writestr("dev/2026-06-01.json", json.dumps([{"type": "message", "user": "U01", "text": "old", "ts": "1780300800.000000"}]))
    return zpath


def run(spec, path, tmp_path, regexes=(r"[A-Z]+-\d+",)):
    return import_export(load_mapping(spec, tmp_path), path, source="src", resolver=Resolver(ROSTER), regexes=list(regexes), claim_dir=tmp_path, fy=FY)


def stage(tmp_path, fixtures, name):
    target = tmp_path / "evidence/raw/src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((fixtures / "exports" / name).read_bytes())
    return target


def test_slack_export_messages_threads_bots_and_skips(tmp_path):
    res = run("slack-export", make_export(tmp_path), tmp_path)
    rows = {r["key"]: r for r in res.rows}
    assert set(rows) == {"dev:1788256800.000100", "dev:1788257000.000200", "dev:1788257200.000400"}
    root = rows["dev:1788256800.000100"]
    assert root["person"] == "alice" and root["date"] == "2026-09-01" and root["container"] == "dev"
    assert root["tags"] == "thread:1788256800.000100;thread_root"
    assert root["refs"] == "ACME-12;acme/vision#7"
    assert rows["dev:1788257000.000200"]["person"] == "bob"
    assert rows["dev:1788257200.000400"]["person"] == "bot"
    assert res.skipped_outside_fy == 1


def test_slack_export_unzipped_folder_without_users_file(tmp_path):
    d = tmp_path / "evidence/raw/slack/export"
    (d / "dev").mkdir(parents=True)
    (d / "dev/2026-09-01.json").write_text(json.dumps([{"type": "message", "user": "U9", "text": "hi", "ts": "1788256800.000100"}]))
    res = run("slack-export", d, tmp_path, regexes=())
    assert [r["person"] for r in res.rows] == ["unmatched:U9"]


def test_asana_preset(tmp_path, fixtures):
    res = run("asana-csv", stage(tmp_path, fixtures, "asana.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "1203")
    assert (created["person"], created["date"], created["container"]) == ("alice", "2026-09-14", "Grasping")


def test_clickup_preset_epoch_ms_and_first_of_several_assignees(tmp_path, fixtures):
    res = run("clickup-csv", stage(tmp_path, fixtures, "clickup.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "86b1x")
    assert (created["person"], created["date"], created["container"]) == ("alice", "2026-09-10", "Control")


def test_shortcut_preset(tmp_path, fixtures):
    res = run("shortcut-csv", stage(tmp_path, fixtures, "shortcut.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert (by_key["512"]["person"], by_key["512"]["date"]) == ("bob", "2026-11-03")
    assert by_key["512:started"]["person"] == "alice"


def test_azure_devops_preset_name_and_email_form(tmp_path, fixtures):
    res = run("azure-devops-csv", stage(tmp_path, fixtures, "azure.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert (by_key["4411"]["person"], by_key["4411"]["date"]) == ("bob", "2026-12-01")
    assert (by_key["4411:issue_resolved"]["person"], by_key["4411:issue_resolved"]["date"]) == ("alice", "2026-12-09")


@pytest.mark.parametrize("preset", sorted(p.stem for p in PRESET_DIR.glob("*.toml")))
def test_every_preset_loads(tmp_path, preset):
    assert load_mapping(preset, tmp_path)["tool"]
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_slack_and_presets.py -v`
Expected: FAIL with `MappingError: mapping 'slack-export' not found` (and the other presets).

- [ ] **Step 4: Implement `slack_export.py`**

`skills/sred/scripts/sredlib/slack_export.py`:
```python
"""Slack's official workspace export (zip or unzipped folder) to activity rows."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import activity
from .mapping import ImportResult
from .roster import Resolver

DAY_FILE_RE = re.compile(r"^(?:.*/)?([^/]+)/(\d{4}-\d{2}-\d{2})\.json$")
SKIP_SUBTYPES = {"channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name", "channel_archive",
                 "bot_add", "bot_remove", "pinned_item", "group_join", "group_leave"}


def _members(path: Path) -> dict[str, bytes]:
    if path.is_dir():
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*.json"))}
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in sorted(zf.namelist()) if n.endswith(".json")}


def import_slack(export_path, *, source, resolver: Resolver, regexes, claim_dir, fy, tz=None) -> ImportResult:
    export_path = Path(export_path)
    members = _members(export_path)
    result = ImportResult()
    users: dict[str, tuple[str, str]] = {}
    for name, blob in members.items():
        if name.rsplit("/", 1)[-1] == "users.json":
            for u in json.loads(blob):
                profile = u.get("profile") or {}
                users[u.get("id", "")] = (profile.get("email", ""), profile.get("real_name", "") or u.get("real_name", ""))
    raw_path = str(export_path.resolve().relative_to(Path(claim_dir).resolve()))
    start, end = fy
    for name, blob in members.items():
        m = DAY_FILE_RE.match(name)
        if not m:
            continue
        channel = m.group(1)
        try:
            messages = json.loads(blob)
        except json.JSONDecodeError as exc:
            result.failures.append(f"{name}: {exc}")
            continue
        for msg in messages:
            subtype = msg.get("subtype", "")
            if subtype in SKIP_SUBTYPES or not msg.get("ts"):
                continue
            ts = datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc)
            if not activity.in_window(ts, start, end, tz):
                result.skipped_outside_fy += 1
                continue
            user = msg.get("user", "")
            email, real = users.get(user, ("", ""))
            profile_name = (msg.get("user_profile") or {}).get("real_name", "")
            if msg.get("bot_id") or subtype == "bot_message":
                person = "bot"
            else:
                person = resolver.resolve("slack", user, email=email, name=real or profile_name)
            tags = []
            if msg.get("thread_ts"):
                tags.append(f"thread:{msg['thread_ts']}")
                if msg["thread_ts"] == msg["ts"]:
                    tags.append("thread_root")
            text = msg.get("text", "")
            result.rows.append(activity.make_row(
                source=source, key=f"{channel}:{msg['ts']}", kind="meeting" if subtype == "huddle_thread" else "chat_message",
                person=person, actor_raw=user or msg.get("username", ""), ts=ts, container=channel, tags=tags,
                title=text, excerpt=text, refs=activity.extract_refs(text, regexes), raw_path=raw_path, tz=tz,
            ))
    return result
```

- [ ] **Step 5: Add the presets**

`skills/sred/mappings/slack-export.toml`:
```toml
# Slack: Workspace settings > Import/Export Data > Export. Point export_path at the zip or the unzipped folder.
tool = "slack"
kind = "chat"
format = "slack-export"
verified = true
```

`skills/sred/mappings/asana-csv.toml`:
```toml
# Asana: project menu > Export/Print > CSV. Has no creator column, so created tasks are credited to the assignee.
tool = "asana"
kind = "tracker"
format = "csv"
verified = false
date_formats = ["%Y-%m-%d", "iso", "%m/%d/%Y"]
key = "Task ID"
container = ["Projects", "Section/Column"]
title = "Name"
tags = ["Tags", "Section/Column"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "Created At"
actor = "Assignee"
actor_email = "Assignee Email"
excerpt = "Notes"

[[events]]
kind = "issue_resolved"
date = "Completed At"
actor = "Assignee"
actor_email = "Assignee Email"
```

`skills/sred/mappings/clickup-csv.toml`:
```toml
# ClickUp: view menu > Export > CSV. Assignees arrive as "[Name, Name]"; the first is credited.
tool = "clickup"
kind = "tracker"
format = "csv"
verified = false
date_formats = ["epoch_ms", "%m/%d/%Y, %I:%M:%S %p", "iso"]
key = "Task ID"
container = ["List Name", "Folder Name", "Space Name"]
title = "Task Name"
tags = ["Status", "Tags"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "Date Created"
actor = "Assignees"
actor_strip = "[]"
actor_split = ","
excerpt = "Task Content"

[[events]]
kind = "issue_resolved"
date = "Date Closed"
actor = "Assignees"
actor_strip = "[]"
actor_split = ","
```

`skills/sred/mappings/shortcut-csv.toml`:
```toml
# Shortcut: Settings > Export Data > CSV (stories).
tool = "shortcut"
kind = "tracker"
format = "csv"
verified = false
date_formats = ["iso", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]
key = "id"
container = ["project", "epic", "workflow"]
title = "name"
tags = ["type", "state", "labels"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "created_at"
actor = "requester"
excerpt = "description"

[[events]]
kind = "issue_state_change"
key_suffix = ":started"
date = "started_at"
actor = "owners"
actor_split = ","

[[events]]
kind = "issue_resolved"
date = "completed_at"
actor = "owners"
actor_split = ","
```

`skills/sred/mappings/azure-devops-csv.toml`:
```toml
# Azure DevOps Boards: run a query with these columns, then Export to CSV.
tool = "azure-devops"
kind = "tracker"
format = "csv"
verified = false
date_formats = ["%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "iso"]
key = "ID"
container = ["Area Path", "Iteration Path"]
title = "Title"
tags = ["Work Item Type", "State", "Tags"]

[[events]]
kind = "issue_created"
key_suffix = ""
date = "Created Date"
actor = "Created By"

[[events]]
kind = "issue_resolved"
date = "Closed Date"
actor = "Assigned To"
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_slack_and_presets.py tests/test_mapping.py -v`
Expected: PASS (all tests, including 7 parametrized preset loads).

- [ ] **Step 7: Commit**

```bash
git add skills/sred/scripts/sredlib/slack_export.py skills/sred/mappings tests/fixtures/exports tests/test_slack_and_presets.py
git commit -m "feat: add Slack export import and Asana, ClickUp, Shortcut, Azure DevOps presets

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: HTTP client, adapter interface, GitHub adapter, `capture.py`

**Files:**
- Create: `skills/sred/scripts/sredlib/http.py`, `skills/sred/scripts/sredlib/adapters/__init__.py`, `skills/sred/scripts/sredlib/adapters/github.py`, `skills/sred/scripts/capture.py`
- Test: `tests/test_http.py`, `tests/test_github.py`

**Interfaces:**
- Consumes: `activity.*`, `manifest.record`, `dates.parse_iso`, `config.*`, `roster.Resolver`.
- Produces:
  - `http.Http(sleep=time.sleep, timeout=60)` with `.request(method, url, headers=None, body=None) -> (data, headers_lowercased)`, `.get(url, headers=None)`, `.post(url, body, headers=None)`; `http.HttpError(RuntimeError)`.
  - `adapters.Context(claim_dir, source, fy, resolver=None, regexes=(), tz=timezone.utc)` with `.name`, `.raw_dir`, `.rel(path) -> str`; `adapters.CaptureError(RuntimeError)`; `adapters.get_adapter(tool) -> module`; `adapters.adapter_key(source) -> str` (`"git-log"` for `method = "git-log"`, else `source["tool"]`).
  - Every adapter module exposes `check(source, http) -> str`, `capture(ctx, http) -> dict` (writes raw JSON under `ctx.raw_dir`, records the manifest, returns counts), `normalize(ctx) -> list[dict]` (activity rows).
  - CLI: `capture.py <github|gitlab|linear|jira|git-log> --claim DIR --source NAME`; `capture.py check --claim DIR`; `capture.check_source(claim: Path, src: dict, http) -> tuple[bool, str]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_http.py`:
```python
import io
import urllib.error

import pytest

from sredlib.http import Http, HttpError


class Resp:
    def __init__(self, body, headers=None):
        self.body, self.headers = body, headers or {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_retries_rate_limit_then_succeeds(monkeypatch):
    calls, slept = [], []

    def fake_urlopen(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 403, "rate limited", {"X-RateLimit-Remaining": "0", "Retry-After": "3"}, io.BytesIO(b""))
        return Resp(b'{"ok": true}', {"Link": "x"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    data, headers = Http(sleep=slept.append).get("https://api.example/x")
    assert data == {"ok": True} and headers == {"link": "x"} and slept == [3.0] and len(calls) == 2


def test_http_error_carries_status_and_body(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "no", {}, io.BytesIO(b"bad token"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(HttpError, match="HTTP 401: bad token"):
        Http(sleep=lambda s: None).get("https://api.example/x")
```

`tests/test_github.py`:
```python
import json
from datetime import date

import capture
from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
API = "https://api.github.com/repos/acme/vision"
SHA1, SHA2 = "a" * 40, "b" * 40
PR = {"number": 7, "title": "Occlusion-aware grasp sampling", "body": "Tests ACME-12 hypothesis", "user": {"login": "achen"},
      "created_at": "2026-09-02T10:00:00Z", "updated_at": "2026-09-05T10:00:00Z", "merged_at": "2026-09-05T10:00:00Z",
      "html_url": "https://github.com/acme/vision/pull/7", "head": {"ref": "exp/occlusion"}, "labels": [{"name": "research"}]}
OLD_PR = dict(PR, number=1, created_at="2026-05-01T10:00:00Z", updated_at="2026-05-02T10:00:00Z", merged_at=None)
RESOLVER = Resolver([
    {"id": "alice", "name": "Alice Chen", "aliases": "github:achen;email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "github:broy;email:bob@acme.test"},
])


def routes():
    return [
        ("GET", f"{API}/pulls?state=all", [PR, OLD_PR], {}),
        ("GET", f"{API}/pulls/7/reviews", [{"id": 91, "user": {"login": "broy"}, "state": "CHANGES_REQUESTED", "body": "Try depth prior", "submitted_at": "2026-09-03T10:00:00Z"}], {}),
        ("GET", f"{API}/pulls/7/comments", [], {}),
        ("GET", f"{API}/issues/7/comments", [{"id": 55, "user": {"login": "dependabot[bot]"}, "body": "bump", "created_at": "2026-09-03T11:00:00Z"}], {}),
        ("GET", f"{API}/pulls/7/commits", [{"sha": SHA1, "author": {"login": "achen"}, "html_url": "u1",
                                           "commit": {"message": "Sample grasps by visibility\n\nACME-12", "author": {"date": "2026-09-02T09:00:00Z", "email": "alice@acme.test"}}}], {}),
        ("GET", f"{API}/pulls/7/files", [{"filename": "planner/occlusion.py"}], {}),
        ("GET", f"{API}/commits?since=", [
            {"sha": SHA1, "author": None, "commit": {"message": "dup", "author": {"date": "2026-09-02T09:00:00Z", "email": "alice@acme.test"}}},
            {"sha": SHA2, "author": None, "commit": {"message": "Direct commit", "author": {"date": "2026-10-01T09:00:00Z", "email": "bob@acme.test"}}},
        ], {}),
    ]


def ctx_for(tmp_path):
    src = {"name": "gh", "kind": "code", "tool": "github", "method": "api", "org": "acme", "repos": ["vision"]}
    return Context(tmp_path, src, FY, RESOLVER, (r"[A-Z]+-\d+",))


def test_capture_then_normalize(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    ctx = ctx_for(tmp_path)
    counts = get_adapter("github").capture(ctx, fake_http(routes()))
    assert counts == {"repos": 1, "pulls": 1, "commits": 2}
    assert (tmp_path / "evidence/raw/gh/acme__vision.json").exists()
    assert "gh" in json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]
    rows = {r["key"]: r for r in get_adapter("github").normalize(ctx)}
    assert set(rows) == {"acme/vision#7", "acme/vision#7:merged", "acme/vision#7:review:91", "acme/vision#7:comment:55", SHA1, SHA2}
    opened = rows["acme/vision#7"]
    assert opened["person"] == "alice" and opened["tags"] == "research;branch:exp/occlusion"
    assert opened["paths"] == "planner/occlusion.py" and opened["refs"] == "ACME-12"
    assert rows["acme/vision#7:review:91"]["person"] == "bob"
    assert rows["acme/vision#7:comment:55"]["person"] == "bot"
    assert rows[SHA1]["tags"] == "research;branch:exp/occlusion;pr:acme/vision#7"
    assert rows[SHA2]["person"] == "bob"


def test_pagination_follows_link_header(tmp_path, fake_http, monkeypatch):
    from sredlib.adapters import github

    url1 = "https://api.github.com/orgs/acme/repos?per_page=100&type=all"
    url2 = url1 + "&page=2"
    http = fake_http([
        ("GET", url2, [{"full_name": "acme/b"}], {}),
        ("GET", url1, [{"full_name": "acme/a"}], {"Link": f'<{url2}>; rel="next"'}),
    ])
    assert github._repos({"org": "acme"}, http, {}) == ["acme/a", "acme/b"]


def test_check_source_variants(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    http = fake_http([("GET", "https://api.github.com/user", {"login": "achen"}, {})])
    assert capture.check_source(tmp_path, {"name": "gh", "method": "api", "tool": "github"}, http) == (True, "authenticated as achen")
    ok, msg = capture.check_source(tmp_path, {"name": "j", "method": "export", "export_path": "exports/j.csv"}, http)
    assert not ok and "missing" in msg
    ok, msg = capture.check_source(tmp_path, {"name": "g", "method": "git-log", "paths": ["nope"]}, http)
    assert not ok and "nope" in msg
    assert capture.check_source(tmp_path, {"name": "n", "method": "connector"}, http)[0]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_http.py tests/test_github.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.http'` / `capture`.

- [ ] **Step 3: Implement `http.py` and `adapters/__init__.py`**

`skills/sred/scripts/sredlib/http.py`:
```python
"""Minimal JSON-over-HTTP client with retries. Tests replace it with a fake."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class HttpError(RuntimeError):
    pass


class Http:
    def __init__(self, sleep=time.sleep, timeout: int = 60):
        self.sleep = sleep
        self.timeout = timeout

    def request(self, method, url, headers=None, body=None):
        data = json.dumps(body).encode() if body is not None else None
        hdrs = {"Accept": "application/json", "User-Agent": "sred-kit"}
        hdrs.update(headers or {})
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        for attempt in range(6):
            req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = resp.read()
                    return (json.loads(payload) if payload else None), {k.lower(): v for k, v in resp.headers.items()}
            except urllib.error.HTTPError as exc:
                limited = exc.code == 429 or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0")
                if (limited or exc.code in (502, 503, 504)) and attempt < 5:
                    reset = exc.headers.get("X-RateLimit-Reset")
                    wait = float(exc.headers.get("Retry-After") or 0) or (max(float(reset) - time.time(), 1.0) if reset else 2.0 ** attempt)
                    self.sleep(min(wait, 900.0))
                    continue
                detail = exc.read().decode(errors="replace")[:500]
                raise HttpError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                if attempt < 5:
                    self.sleep(2.0 ** attempt)
                    continue
                raise HttpError(f"{method} {url} -> {exc.reason}") from exc
        raise HttpError(f"{method} {url} -> gave up after retries")

    def get(self, url, headers=None):
        return self.request("GET", url, headers)

    def post(self, url, body, headers=None):
        return self.request("POST", url, headers, body)
```

`skills/sred/scripts/sredlib/adapters/__init__.py`:
```python
"""Capture adapters: one module per tool, same interface.

Each module provides:
  check(source: dict, http) -> str          one cheap authenticated call; says who/what
  capture(ctx: Context, http) -> dict       writes raw JSON under evidence/raw/<name>/, returns counts
  normalize(ctx: Context) -> list[dict]     raw files -> activity rows (sredlib.activity.make_row)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import date, timezone, tzinfo
from pathlib import Path

from ..roster import Resolver

MODULES = {"github": "github", "gitlab": "gitlab", "linear": "linear", "jira": "jira", "git-log": "gitlog"}


class CaptureError(RuntimeError):
    pass


@dataclass
class Context:
    claim_dir: Path
    source: dict
    fy: tuple[date, date]
    resolver: Resolver | None = None
    regexes: tuple[str, ...] = ()
    tz: tzinfo = field(default=timezone.utc)

    @property
    def name(self) -> str:
        return self.source["name"]

    @property
    def raw_dir(self) -> Path:
        return Path(self.claim_dir) / "evidence" / "raw" / self.name

    def rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(Path(self.claim_dir).resolve()))


def adapter_key(source: dict) -> str:
    return "git-log" if source.get("method") == "git-log" else source.get("tool", "")


def get_adapter(tool: str):
    if tool not in MODULES:
        raise CaptureError(f'no capture adapter for {tool!r}; use method = "export" or "connector"')
    return importlib.import_module(f"{__name__}.{MODULES[tool]}")
```

- [ ] **Step 4: Implement `adapters/github.py`**

`skills/sred/scripts/sredlib/adapters/github.py`:
```python
"""GitHub capture through the REST API (token from GITHUB_TOKEN or `gh auth token`)."""
from __future__ import annotations

import json
import os
import re
import subprocess

from .. import activity, manifest
from ..dates import parse_iso
from ..http import HttpError
from . import CaptureError, Context

API = "https://api.github.com"
_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _token(source: dict) -> str:
    env = source.get("token_env", "GITHUB_TOKEN")
    if os.environ.get(env):
        return os.environ[env]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CaptureError(f"no GitHub token: set {env} or run `gh auth login`") from exc
    if not out:
        raise CaptureError(f"no GitHub token: set {env} or run `gh auth login`")
    return out


def _headers(source: dict) -> dict:
    return {"Authorization": f"Bearer {_token(source)}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _next(headers: dict):
    m = _NEXT_RE.search(headers.get("link", ""))
    return m.group(1) if m else None


def _paged(http, url, headers) -> list:
    out = []
    while url:
        data, hdrs = http.get(url, headers)
        out.extend(data or [])
        url = _next(hdrs)
    return out


def _repos(source: dict, http, headers) -> list[str]:
    if source.get("repos"):
        return [r if "/" in r else f"{source['org']}/{r}" for r in source["repos"]]
    if not source.get("org"):
        raise CaptureError("github source needs org or repos")
    return sorted(r["full_name"] for r in _paged(http, f"{API}/orgs/{source['org']}/repos?per_page=100&type=all", headers))


def check(source: dict, http) -> str:
    data, _ = http.get(f"{API}/user", _headers(source))
    return f"authenticated as {data.get('login')}"


def capture(ctx: Context, http) -> dict:
    h = _headers(ctx.source)
    start, end = ctx.fy
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    counts, files = {"repos": 0, "pulls": 0, "commits": 0}, []
    for full in _repos(ctx.source, http, h):
        base = f"{API}/repos/{full}"
        pulls, url = [], f"{base}/pulls?state=all&sort=updated&direction=desc&per_page=100"
        while url:
            page, hdrs = http.get(url, h)
            stop = False
            for pr in page or []:
                if pr["updated_at"][:10] < start.isoformat():
                    stop = True
                    break
                if pr["created_at"][:10] <= end.isoformat():
                    pulls.append(pr)
            url = None if stop else _next(hdrs)
        for pr in pulls:
            n = pr["number"]
            pr["_reviews"] = _paged(http, f"{base}/pulls/{n}/reviews?per_page=100", h)
            pr["_review_comments"] = _paged(http, f"{base}/pulls/{n}/comments?per_page=100", h)
            pr["_issue_comments"] = _paged(http, f"{base}/issues/{n}/comments?per_page=100", h)
            pr["_commits"] = _paged(http, f"{base}/pulls/{n}/commits?per_page=100", h)
            pr["_files"] = [f["filename"] for f in _paged(http, f"{base}/pulls/{n}/files?per_page=100", h)]
        try:
            commits = _paged(http, f"{base}/commits?since={start.isoformat()}T00:00:00Z&until={end.isoformat()}T23:59:59Z&per_page=100", h)
        except HttpError as exc:
            if "HTTP 409" not in str(exc):  # 409 = empty repository
                raise
            commits = []
        path = ctx.raw_dir / f"{full.replace('/', '__')}.json"
        path.write_text(json.dumps({"repo": full, "pulls": pulls, "commits": commits}, indent=1, sort_keys=True), encoding="utf-8")
        files.append(path)
        counts["repos"] += 1
        counts["pulls"] += len(pulls)
        counts["commits"] += len(commits)
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    regexes = list(ctx.regexes)

    def emit(kind, key, actor, ts, *, email="", **kw):
        when = parse_iso(ts)
        if not activity.in_window(when, start, end, ctx.tz) or key in seen:
            return
        seen.add(key)
        rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=ctx.resolver.resolve("github", actor, email=email),
                                      actor_raw=actor or email, ts=when, tz=ctx.tz, **kw))

    def emit_commit(cm, repo, rel, tags, paths):
        info = cm.get("commit") or {}
        author = info.get("author") or {}
        message = info.get("message", "")
        emit("commit", cm["sha"], (cm.get("author") or {}).get("login", ""), author.get("date", ""), email=author.get("email", ""),
             container=repo, tags=tags, paths=paths, title=message, excerpt=message,
             refs=activity.extract_refs(message, regexes), url=cm.get("html_url", ""), raw_path=rel)

    for path in sorted(ctx.raw_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        repo, rel = data["repo"], ctx.rel(path)
        for pr in data["pulls"]:
            key = f"{repo}#{pr['number']}"
            author = (pr.get("user") or {}).get("login", "")
            branch = (pr.get("head") or {}).get("ref", "")
            tags = [label["name"] for label in pr.get("labels", [])] + ([f"branch:{branch}"] if branch else [])
            paths = pr.get("_files", [])
            body = pr.get("body") or ""
            refs = activity.extract_refs(f"{pr.get('title', '')}\n{body}\n{branch}", regexes, own_key=key)
            common = dict(container=repo, title=pr.get("title", ""), url=pr.get("html_url", ""), raw_path=rel, paths=paths, refs=refs)
            emit("pr_opened", key, author, pr["created_at"], tags=tags, excerpt=body, **common)
            if pr.get("merged_at"):
                emit("pr_merged", f"{key}:merged", author, pr["merged_at"], tags=tags, **common)
            for rv in pr.get("_reviews", []):
                if rv.get("submitted_at"):
                    emit("pr_review", f"{key}:review:{rv['id']}", (rv.get("user") or {}).get("login", ""), rv["submitted_at"],
                         tags=tags + [f"state:{rv.get('state', '')}"], excerpt=rv.get("body") or "", **common)
            for c in pr.get("_review_comments", []) + pr.get("_issue_comments", []):
                emit("pr_comment", f"{key}:comment:{c['id']}", (c.get("user") or {}).get("login", ""), c["created_at"],
                     tags=tags, excerpt=c.get("body") or "", **common)
            for cm in pr.get("_commits", []):
                emit_commit(cm, repo, rel, tags + [f"pr:{key}"], paths)
        for cm in data["commits"]:
            emit_commit(cm, repo, rel, [], [])
    return rows
```

- [ ] **Step 5: Implement `capture.py`**

`skills/sred/scripts/capture.py`:
```python
#!/usr/bin/env python3
"""Capture raw evidence before access ends.

  capture.py <github|gitlab|linear|jira|git-log> --claim DIR --source NAME
  capture.py check --claim DIR       one cheap test per source; exit 1 if any fails
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import config
from sredlib.adapters import CaptureError, Context, adapter_key, get_adapter
from sredlib.http import Http, HttpError

TOOLS = ["github", "gitlab", "linear", "jira", "git-log"]


def check_source(claim: Path, src: dict, http) -> tuple[bool, str]:
    method = src.get("method")
    if method == "api":
        try:
            return True, get_adapter(src.get("tool", "")).check(src, http)
        except (CaptureError, HttpError, KeyError) as exc:
            return False, str(exc)
    if method == "export":
        p = Path(src.get("export_path", ""))
        p = p if p.is_absolute() else Path(claim) / p
        return p.exists(), f"export file {'found' if p.exists() else 'missing'}: {p}"
    if method == "git-log":
        missing = [p for p in src.get("paths", []) if not (Path(claim) / p / ".git").exists()]
        return (not missing), ("all clones found" if not missing else f"not git clones: {', '.join(missing)}")
    if method == "connector":
        return True, "captured by Claude through a connector; nothing to test here"
    return False, f"unknown method {method!r}"


def cmd_check(args) -> int:
    claim = Path(args.claim)
    cfg = config.load_config(claim / "sred.toml")
    ok_all, http = True, Http()
    for src in config.sources(cfg):
        ok, msg = check_source(claim, src, http)
        ok_all = ok_all and ok
        print(f"{'OK  ' if ok else 'FAIL'} {src.get('name')}: {msg}")
    return 0 if ok_all else 1


def cmd_capture(args) -> int:
    claim = Path(args.claim)
    cfg = config.load_config(claim / "sred.toml")
    src = config.source(cfg, args.source)
    if adapter_key(src) != args.tool:
        print(f"ERROR: source {args.source!r} is configured as {adapter_key(src)!r}, not {args.tool!r}", file=sys.stderr)
        return 2
    ctx = Context(claim, src, config.fiscal_year(cfg), tz=config.timezone_of(cfg))
    try:
        counts = get_adapter(args.tool).capture(ctx, Http())
    except (CaptureError, HttpError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.source}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"Raw files are in {ctx.raw_dir}. Keep a backup copy of evidence/raw/ somewhere independent.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tool", choices=TOOLS + ["check"])
    p.add_argument("--claim", default=".")
    p.add_argument("--source")
    args = p.parse_args(argv)
    if args.tool == "check":
        return cmd_check(args)
    if not args.source:
        p.error("--source is required")
    return cmd_capture(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_http.py tests/test_github.py -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add skills/sred/scripts/sredlib/http.py skills/sred/scripts/sredlib/adapters skills/sred/scripts/capture.py tests/test_http.py tests/test_github.py
git commit -m "feat: add HTTP client, adapter interface, GitHub capture and capture.py

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: GitLab adapter

**Files:**
- Create: `skills/sred/scripts/sredlib/adapters/gitlab.py`
- Test: `tests/test_gitlab.py`

**Interfaces:**
- Consumes: `adapters.Context`, `adapters.CaptureError`, `activity.*`, `manifest.record`, `dates.parse_iso`.
- Produces: module `gitlab` with `check`, `capture`, `normalize` (same interface as Task 5). Source keys: `projects` (list of `group/project`), optional `base_url` (default `https://gitlab.com`), optional `token_env` (default `GITLAB_TOKEN`). Keys: MR `"<project>!<iid>"`, merged `"…:merged"`, note `"…:note:<id>"`, commit = full SHA.

- [ ] **Step 1: Write the failing test**

`tests/test_gitlab.py`:
```python
from datetime import date

import pytest

from sredlib.adapters import CaptureError, Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
P = "https://gitlab.com/api/v4/projects/acme%2Fvision"
Q = "state=all&updated_after=2026-08-01T00:00:00Z&created_before=2027-07-31T23:59:59Z&per_page=100"
SHA = "c" * 40
MR = {"iid": 3, "title": "Depth prior for grasping", "description": "Closes #12", "author": {"username": "achen"},
      "created_at": "2026-09-04T10:00:00Z", "merged_at": None, "web_url": "https://gitlab.com/acme/vision/-/merge_requests/3",
      "source_branch": "exp/depth", "labels": ["research"]}
MR2 = dict(MR, iid=4, title="Abandoned voxel approach", created_at="2026-10-04T10:00:00Z", source_branch="exp/voxel")


def routes():
    return [
        ("GET", f"{P}/merge_requests?{Q}&page=1", [MR], {"X-Next-Page": "2"}),
        ("GET", f"{P}/merge_requests?{Q}&page=2", [MR2], {"X-Next-Page": ""}),
        ("GET", f"{P}/merge_requests/3/notes", [
            {"id": 1, "system": True, "body": "added 1 commit", "author": {"username": "achen"}, "created_at": "2026-09-04T11:00:00Z"},
            {"id": 2, "system": False, "body": "Depth prior overfits", "author": {"username": "broy"}, "created_at": "2026-09-05T11:00:00Z"},
        ], {}),
        ("GET", f"{P}/merge_requests/3/commits", [{"id": SHA, "title": "Add depth prior", "message": "Add depth prior",
                                                   "author_name": "Alice Chen", "author_email": "alice@acme.test", "authored_date": "2026-09-04T09:00:00Z"}], {}),
        ("GET", f"{P}/merge_requests/3/diffs", [{"new_path": "grasp/depth.py"}], {}),
        ("GET", f"{P}/merge_requests/4/", [], {}),
        ("GET", f"{P}/repository/commits", [], {}),
    ]


def test_capture_follows_pages_and_normalize_skips_system_notes(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "t")
    resolver = Resolver([
        {"id": "alice", "name": "Alice Chen", "aliases": "gitlab:achen;email:alice@acme.test"},
        {"id": "bob", "name": "Bob Roy", "aliases": "gitlab:broy"},
    ])
    ctx = Context(tmp_path, {"name": "gl", "kind": "code", "tool": "gitlab", "method": "api", "projects": ["acme/vision"]}, FY, resolver, (r"#\d+",))
    assert get_adapter("gitlab").capture(ctx, fake_http(routes())) == {"projects": 1, "merge_requests": 2, "commits": 0}
    rows = {r["key"]: r for r in get_adapter("gitlab").normalize(ctx)}
    assert set(rows) == {"acme/vision!3", "acme/vision!3:note:2", SHA, "acme/vision!4"}
    assert rows["acme/vision!3"]["refs"] == "#12" and rows["acme/vision!3"]["paths"] == "grasp/depth.py"
    assert rows["acme/vision!3:note:2"]["person"] == "bob"
    assert rows[SHA]["person"] == "alice" and rows[SHA]["tags"] == "research;branch:exp/depth;pr:acme/vision!3"


def test_missing_token_is_a_clear_error(tmp_path, fake_http, monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    ctx = Context(tmp_path, {"name": "gl", "tool": "gitlab", "method": "api", "projects": ["acme/vision"]}, FY, Resolver([]))
    with pytest.raises(CaptureError, match="GITLAB_TOKEN"):
        get_adapter("gitlab").capture(ctx, fake_http([]))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_gitlab.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.adapters.gitlab'`.

- [ ] **Step 3: Implement `adapters/gitlab.py`**

`skills/sred/scripts/sredlib/adapters/gitlab.py`:
```python
"""GitLab capture through REST v4 (token in GITLAB_TOKEN or the env var named by token_env)."""
from __future__ import annotations

import json
import os
import urllib.parse

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context


def _base(source: dict) -> str:
    return source.get("base_url", "https://gitlab.com").rstrip("/") + "/api/v4"


def _headers(source: dict) -> dict:
    env = source.get("token_env", "GITLAB_TOKEN")
    if not os.environ.get(env):
        raise CaptureError(f"set {env} to a GitLab personal access token with read_api scope")
    return {"PRIVATE-TOKEN": os.environ[env]}


def _paged(http, url, headers) -> list:
    out, page = [], "1"
    while page:
        sep = "&" if "?" in url else "?"
        data, hdrs = http.get(f"{url}{sep}page={page}", headers)
        out.extend(data or [])
        page = hdrs.get("x-next-page", "")
    return out


def check(source: dict, http) -> str:
    data, _ = http.get(f"{_base(source)}/user", _headers(source))
    return f"authenticated as {data.get('username')}"


def capture(ctx: Context, http) -> dict:
    h, base = _headers(ctx.source), _base(ctx.source)
    if not ctx.source.get("projects"):
        raise CaptureError('gitlab source needs projects = ["group/project", ...]')
    start, end = ctx.fy
    since, until = f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T23:59:59Z"
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    counts, files = {"projects": 0, "merge_requests": 0, "commits": 0}, []
    for proj in ctx.source["projects"]:
        p = f"{base}/projects/{urllib.parse.quote(proj, safe='')}"
        mrs = _paged(http, f"{p}/merge_requests?state=all&updated_after={since}&created_before={until}&per_page=100", h)
        for mr in mrs:
            iid = mr["iid"]
            mr["_notes"] = _paged(http, f"{p}/merge_requests/{iid}/notes?per_page=100", h)
            mr["_commits"] = _paged(http, f"{p}/merge_requests/{iid}/commits?per_page=100", h)
            mr["_files"] = [d.get("new_path", "") for d in _paged(http, f"{p}/merge_requests/{iid}/diffs?per_page=100", h)]
        commits = _paged(http, f"{p}/repository/commits?since={since}&until={until}&all=true&per_page=100", h)
        path = ctx.raw_dir / f"{proj.replace('/', '__')}.json"
        path.write_text(json.dumps({"project": proj, "merge_requests": mrs, "commits": commits}, indent=1, sort_keys=True), encoding="utf-8")
        files.append(path)
        counts["projects"] += 1
        counts["merge_requests"] += len(mrs)
        counts["commits"] += len(commits)
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    regexes = list(ctx.regexes)

    def emit(kind, key, actor, ts, *, email="", name="", **kw):
        when = parse_iso(ts)
        if not activity.in_window(when, start, end, ctx.tz) or key in seen:
            return
        seen.add(key)
        rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=ctx.resolver.resolve("gitlab", actor, email=email, name=name),
                                      actor_raw=actor or email, ts=when, tz=ctx.tz, **kw))

    def emit_commit(cm, proj, rel, tags, paths):
        message = cm.get("message") or cm.get("title", "")
        emit("commit", cm["id"], cm.get("author_name", ""), cm.get("authored_date") or cm["created_at"],
             email=cm.get("author_email", ""), name=cm.get("author_name", ""), container=proj, tags=tags, paths=paths,
             title=message, excerpt=message, refs=activity.extract_refs(message, regexes), url=cm.get("web_url", ""), raw_path=rel)

    for path in sorted(ctx.raw_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        proj, rel = data["project"], ctx.rel(path)
        for mr in data["merge_requests"]:
            key = f"{proj}!{mr['iid']}"
            author = (mr.get("author") or {}).get("username", "")
            branch = mr.get("source_branch", "")
            tags = list(mr.get("labels", [])) + ([f"branch:{branch}"] if branch else [])
            paths, desc = mr.get("_files", []), mr.get("description") or ""
            refs = activity.extract_refs(f"{mr.get('title', '')}\n{desc}\n{branch}", regexes, own_key=key)
            common = dict(container=proj, title=mr.get("title", ""), url=mr.get("web_url", ""), raw_path=rel, tags=tags, paths=paths, refs=refs)
            emit("pr_opened", key, author, mr["created_at"], excerpt=desc, **common)
            if mr.get("merged_at"):
                emit("pr_merged", f"{key}:merged", author, mr["merged_at"], **common)
            for note in mr.get("_notes", []):
                if not note.get("system"):
                    emit("pr_comment", f"{key}:note:{note['id']}", (note.get("author") or {}).get("username", ""), note["created_at"],
                         excerpt=note.get("body") or "", **common)
            for cm in mr.get("_commits", []):
                emit_commit(cm, proj, rel, tags + [f"pr:{key}"], paths)
        for cm in data["commits"]:
            emit_commit(cm, proj, rel, [], [])
    return rows
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_gitlab.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/adapters/gitlab.py tests/test_gitlab.py
git commit -m "feat: add GitLab capture adapter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Linear adapter

**Files:**
- Create: `skills/sred/scripts/sredlib/adapters/linear.py`
- Test: `tests/test_linear.py`

**Interfaces:**
- Consumes: `adapters.Context`, `adapters.CaptureError`, `activity.*`, `manifest.record`, `dates.parse_iso`.
- Produces: module `linear` with `check`, `capture`, `normalize`. Source key: optional `token_env` (default `LINEAR_API_KEY`). Raw file `evidence/raw/<name>/issues.json`. Keys: `<IDENT>`, `<IDENT>:state:<hid>`, `<IDENT>:assign:<hid>`, `<IDENT>:comment:<cid>`, `<IDENT>:resolved`. Truncated nested lists (more than 50 history entries or comments) are noted in the manifest.

- [ ] **Step 1: Write the failing test**

`tests/test_linear.py`:
```python
import json
from datetime import date

from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ALICE = {"id": "u1", "name": "Alice Chen", "email": "alice@acme.test"}
BOB = {"id": "u2", "name": "Bob Roy", "email": "bob@acme.test"}
ISSUE = {
    "id": "i1", "identifier": "ACME-40", "title": "Compare depth priors", "description": "Follows ACME-12",
    "url": "https://linear.app/acme/issue/ACME-40", "branchName": "achen/acme-40",
    "createdAt": "2026-10-02T17:00:00.000Z", "startedAt": None, "completedAt": "2026-10-12T09:00:00.000Z",
    "canceledAt": None, "archivedAt": None, "updatedAt": "2026-10-12T09:00:00.000Z",
    "state": {"name": "Done", "type": "completed"}, "team": {"key": "ACME"}, "project": {"name": "Perception"},
    "labels": {"nodes": [{"name": "Research"}]}, "assignee": BOB, "creator": ALICE,
    "attachments": {"nodes": [{"url": "https://github.com/acme/vision/pull/7"}]},
    "history": {"pageInfo": {"hasNextPage": False}, "nodes": [
        {"id": "h1", "createdAt": "2026-10-03T09:00:00.000Z", "actor": BOB, "fromState": {"name": "Todo"}, "toState": {"name": "In Progress"}, "toAssignee": None},
        {"id": "h2", "createdAt": "2026-10-02T18:00:00.000Z", "actor": ALICE, "fromState": None, "toState": None, "toAssignee": BOB},
    ]},
    "comments": {"pageInfo": {"hasNextPage": True}, "nodes": [
        {"id": "c1", "createdAt": "2026-10-05T09:00:00.000Z", "body": "Prior B diverged", "user": BOB},
    ]},
}
OLD = dict(ISSUE, id="i0", identifier="ACME-3", createdAt="2026-06-01T00:00:00.000Z", completedAt=None,
           history={"pageInfo": {"hasNextPage": False}, "nodes": []}, comments={"pageInfo": {"hasNextPage": False}, "nodes": []})


def pages(body):
    if body["variables"]["after"] is None:
        return {"data": {"issues": {"pageInfo": {"hasNextPage": True, "endCursor": "cur1"}, "nodes": [ISSUE]}}}
    return {"data": {"issues": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [OLD]}}}


def test_capture_pages_and_normalize_events(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "k")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "linear:u1"}, {"id": "bob", "name": "Bob Roy", "aliases": "email:bob@acme.test"}])
    ctx = Context(tmp_path, {"name": "lin", "kind": "tracker", "tool": "linear", "method": "api"}, FY, resolver, (r"[A-Z]+-\d+",))
    http = fake_http([("POST", "https://api.linear.app/graphql", pages, {})])
    counts = get_adapter("linear").capture(ctx, http)
    assert counts == {"issues": 2, "comments": 1, "history": 2}
    assert http.calls[0][2]["variables"]["filter"]["updatedAt"]["gte"] == "2026-08-01T00:00:00.000Z"
    notes = json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]["lin"]["notes"]
    assert notes == ["ACME-40 comments capped at 50"]
    rows = {r["key"]: r for r in get_adapter("linear").normalize(ctx)}
    assert set(rows) == {"ACME-40", "ACME-40:state:h1", "ACME-40:assign:h2", "ACME-40:comment:c1", "ACME-40:resolved"}
    assert rows["ACME-40"]["person"] == "alice" and rows["ACME-40"]["container"] == "Perception"
    assert rows["ACME-40"]["refs"] == "ACME-12;acme/vision#7"
    assert rows["ACME-40:assign:h2"]["person"] == "bob"
    assert rows["ACME-40:state:h1"]["tags"].endswith("to:In Progress")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_linear.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.adapters.linear'`.

- [ ] **Step 3: Implement `adapters/linear.py`**

`skills/sred/scripts/sredlib/adapters/linear.py`:
```python
"""Linear capture through the GraphQL API (LINEAR_API_KEY or the env var named by token_env)."""
from __future__ import annotations

import json
import os

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context

URL = "https://api.linear.app/graphql"
USER = "{ id name email }"
QUERY = """query($after: String, $filter: IssueFilter) {
  issues(first: 25, after: $after, includeArchived: true, filter: $filter) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id identifier title description url branchName
      createdAt startedAt completedAt canceledAt archivedAt updatedAt
      state { name type } team { key } project { name } labels { nodes { name } }
      assignee USER creator USER
      attachments { nodes { url } }
      history(first: 50) { pageInfo { hasNextPage } nodes { id createdAt actor USER fromState { name } toState { name } toAssignee USER } }
      comments(first: 50) { pageInfo { hasNextPage } nodes { id createdAt body user USER } }
    }
  }
}""".replace("USER", USER)


def _headers(source: dict) -> dict:
    env = source.get("token_env", "LINEAR_API_KEY")
    if not os.environ.get(env):
        raise CaptureError(f"set {env} to a Linear personal API key")
    return {"Authorization": os.environ[env]}


def _gql(http, source: dict, query: str, variables: dict) -> dict:
    data, _ = http.post(URL, {"query": query, "variables": variables}, _headers(source))
    if data.get("errors"):
        raise CaptureError(f"Linear API error: {data['errors'][0].get('message')}")
    return data["data"]


def check(source: dict, http) -> str:
    return f"authenticated as {_gql(http, source, 'query { viewer { name } }', {})['viewer']['name']}"


def capture(ctx: Context, http) -> dict:
    start, end = ctx.fy
    flt = {"updatedAt": {"gte": f"{start.isoformat()}T00:00:00.000Z"}, "createdAt": {"lte": f"{end.isoformat()}T23:59:59.999Z"}}
    issues, after, truncated = [], None, []
    while True:
        page = _gql(http, ctx.source, QUERY, {"after": after, "filter": flt})["issues"]
        for node in page["nodes"]:
            issues.append(node)
            for part in ("history", "comments"):
                if node[part]["pageInfo"]["hasNextPage"]:
                    truncated.append(f"{node['identifier']} {part} capped at 50")
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.raw_dir / "issues.json"
    path.write_text(json.dumps({"issues": issues}, indent=1, sort_keys=True), encoding="utf-8")
    counts = {"issues": len(issues), "comments": sum(len(i["comments"]["nodes"]) for i in issues),
              "history": sum(len(i["history"]["nodes"]) for i in issues)}
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=[path], counts=counts,
                    date_range=(start.isoformat(), end.isoformat()), notes=truncated)
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    path = ctx.raw_dir / "issues.json"
    rel, rows = ctx.rel(path), []
    for issue in json.loads(path.read_text(encoding="utf-8"))["issues"]:
        ident = issue["identifier"]
        container = (issue.get("project") or {}).get("name") or (issue.get("team") or {}).get("key", "")
        branch = issue.get("branchName") or ""
        tags = [label["name"] for label in issue["labels"]["nodes"]] + [f"state:{issue['state']['name']}"] + ([f"branch:{branch}"] if branch else [])
        text = "\n".join([issue.get("title", ""), issue.get("description") or ""] + [a["url"] for a in issue["attachments"]["nodes"]])
        refs = activity.extract_refs(text, list(ctx.regexes), own_key=ident)
        events = [("issue_created", ident, issue.get("creator"), issue["createdAt"], issue.get("description") or "", [])]
        for h in issue["history"]["nodes"]:
            if h.get("toState"):
                events.append(("issue_state_change", f"{ident}:state:{h['id']}", h.get("actor"), h["createdAt"], "", [f"to:{h['toState']['name']}"]))
            if h.get("toAssignee"):
                events.append(("issue_assigned", f"{ident}:assign:{h['id']}", h["toAssignee"], h["createdAt"], "", []))
        for c in issue["comments"]["nodes"]:
            events.append(("issue_comment", f"{ident}:comment:{c['id']}", c.get("user"), c["createdAt"], c.get("body") or "", []))
        if issue.get("completedAt"):
            events.append(("issue_resolved", f"{ident}:resolved", issue.get("assignee"), issue["completedAt"], "", []))
        for kind, key, user, ts, excerpt, extra in events:
            if not user:
                continue
            when = parse_iso(ts)
            if not activity.in_window(when, start, end, ctx.tz):
                continue
            person = ctx.resolver.resolve("linear", user.get("id", ""), email=user.get("email", ""), name=user.get("name", ""))
            rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=person, actor_raw=user.get("name", "") or user.get("email", ""),
                                          ts=when, container=container, tags=tags + extra, title=issue.get("title", ""), excerpt=excerpt,
                                          refs=refs, url=issue.get("url", ""), raw_path=rel, tz=ctx.tz))
    return rows
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_linear.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/adapters/linear.py tests/test_linear.py
git commit -m "feat: add Linear capture adapter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Jira Cloud adapter

**Files:**
- Create: `skills/sred/scripts/sredlib/adapters/jira.py`
- Test: `tests/test_jira.py`

**Interfaces:**
- Consumes: `adapters.Context`, `adapters.CaptureError`, `activity.*`, `manifest.record`, `dates.parse_iso`.
- Produces: module `jira` with `check`, `capture`, `normalize`, plus `jira.adf_text(node) -> str`. Source keys: `base_url` (required), optional `projects` (list of project keys), optional `email_env` / `token_env` (defaults `JIRA_EMAIL`, `JIRA_TOKEN`). Raw file `issues.json` holds `{"base_url", "issues"}`. Keys: `<KEY>`, `<KEY>:history:<id>:status`, `<KEY>:history:<id>:assignee`, `<KEY>:comment:<id>`, `<KEY>:resolved`.

- [ ] **Step 1: Write the failing test**

`tests/test_jira.py`:
```python
from datetime import date

import pytest

from sredlib.adapters import CaptureError, Context, get_adapter
from sredlib.adapters.jira import adf_text
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
BASE = "https://acme.atlassian.net"
BOB = {"accountId": "5b10ac", "displayName": "Bob Roy"}
ALICE = {"accountId": "a1", "displayName": "Alice Chen", "emailAddress": "alice@acme.test"}


def doc(text):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


C100 = {"id": "100", "author": BOB, "created": "2026-09-05T11:00:00.000+0000", "body": doc("Failed at 40% occlusion")}
C101 = {"id": "101", "author": ALICE, "created": "2026-09-06T14:00:00.000+0000", "body": doc("Retry with depth prior")}
ISSUE = {"key": "ACME-12", "fields": {
    "summary": "Grasp planner under occlusion", "issuetype": {"name": "Story"}, "status": {"name": "Done"}, "project": {"key": "ACME"},
    "assignee": BOB, "reporter": ALICE, "creator": ALICE, "created": "2026-09-03T09:05:00.000+0000",
    "resolutiondate": "2026-09-20T16:30:00.000+0000", "labels": ["research"], "description": doc("Beats ACME-7 baseline?"),
    "comment": {"total": 2, "comments": [C100]}},
    "changelog": {"total": 1, "histories": [{"id": "900", "author": BOB, "created": "2026-09-04T10:00:00.000+0000",
                                             "items": [{"field": "status", "toString": "In Progress"}, {"field": "assignee", "to": "5b10ac", "toString": "Bob Roy"}]}]}}


def search(body):
    if "nextPageToken" not in body:
        return {"issues": [ISSUE], "nextPageToken": "t2", "isLast": False}
    return {"issues": [], "isLast": True}


def test_adf_text_flattens_paragraphs():
    assert adf_text(doc("a")) == "a\n" and adf_text(None) == ""


def test_capture_fetches_missing_comments_and_normalizes(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("JIRA_EMAIL", "me@acme.test")
    monkeypatch.setenv("JIRA_TOKEN", "t")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "jira:a1"}, {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac"}])
    ctx = Context(tmp_path, {"name": "jira", "kind": "tracker", "tool": "jira", "method": "api", "base_url": BASE, "projects": ["ACME"]}, FY, resolver, (r"[A-Z]+-\d+",))
    http = fake_http([
        ("POST", f"{BASE}/rest/api/3/search/jql", search, {}),
        ("GET", f"{BASE}/rest/api/3/issue/ACME-12/comment?startAt=0", {"total": 2, "comments": [C100, C101]}, {}),
    ])
    assert get_adapter("jira").capture(ctx, http) == {"issues": 1}
    assert http.calls[0][2]["jql"].startswith("project in (ACME) AND updated >= \"2026-08-01\"")
    rows = {r["key"]: r for r in get_adapter("jira").normalize(ctx)}
    assert set(rows) == {"ACME-12", "ACME-12:history:900:status", "ACME-12:history:900:assignee", "ACME-12:comment:100", "ACME-12:comment:101", "ACME-12:resolved"}
    assert rows["ACME-12"]["person"] == "alice" and rows["ACME-12"]["refs"] == "ACME-7"
    assert rows["ACME-12"]["url"] == f"{BASE}/browse/ACME-12"
    assert rows["ACME-12:comment:101"]["person"] == "alice" and rows["ACME-12:resolved"]["person"] == "bob"


def test_missing_credentials(tmp_path, fake_http, monkeypatch):
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    ctx = Context(tmp_path, {"name": "jira", "tool": "jira", "method": "api", "base_url": BASE}, FY, Resolver([]))
    with pytest.raises(CaptureError, match="JIRA_EMAIL"):
        get_adapter("jira").capture(ctx, fake_http([]))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_jira.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.adapters.jira'`.

- [ ] **Step 3: Implement `adapters/jira.py`**

`skills/sred/scripts/sredlib/adapters/jira.py`:
```python
"""Jira Cloud capture through REST v3 (JIRA_EMAIL + JIRA_TOKEN, or the env names in email_env/token_env)."""
from __future__ import annotations

import base64
import json
import os

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context

FIELDS = ["summary", "issuetype", "status", "project", "assignee", "reporter", "creator", "created", "updated",
          "resolutiondate", "labels", "description", "comment"]
BLOCKS = {"paragraph", "heading", "listItem", "codeBlock", "blockquote"}


def _base(source: dict) -> str:
    if not source.get("base_url"):
        raise CaptureError("jira source needs base_url, e.g. https://acme.atlassian.net")
    return source["base_url"].rstrip("/")


def _headers(source: dict) -> dict:
    e_env, t_env = source.get("email_env", "JIRA_EMAIL"), source.get("token_env", "JIRA_TOKEN")
    if not (os.environ.get(e_env) and os.environ.get(t_env)):
        raise CaptureError(f"set {e_env} and {t_env} (an Atlassian API token)")
    cred = base64.b64encode(f"{os.environ[e_env]}:{os.environ[t_env]}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


def adf_text(node) -> str:
    """Plain text from Atlassian Document Format."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_text(n) for n in node)
    text = node.get("text", "") + adf_text(node.get("content", []))
    return text + ("\n" if node.get("type") in BLOCKS else "")


def check(source: dict, http) -> str:
    data, _ = http.get(f"{_base(source)}/rest/api/3/myself", _headers(source))
    return f"authenticated as {data.get('displayName')}"


def _all(http, url, headers, list_key) -> list:
    out, start_at = [], 0
    while True:
        data, _ = http.get(f"{url}?startAt={start_at}&maxResults=100", headers)
        items = data.get(list_key, [])
        out.extend(items)
        start_at += len(items)
        if not items or start_at >= data.get("total", 0):
            return out


def capture(ctx: Context, http) -> dict:
    base, h = _base(ctx.source), _headers(ctx.source)
    start, end = ctx.fy
    jql = f'updated >= "{start.isoformat()}" AND created <= "{end.isoformat()} 23:59" ORDER BY created ASC'
    if ctx.source.get("projects"):
        jql = f"project in ({', '.join(ctx.source['projects'])}) AND " + jql
    issues, token = [], None
    while True:
        body = {"jql": jql, "fields": FIELDS, "expand": "changelog", "maxResults": 100}
        if token:
            body["nextPageToken"] = token
        data, _ = http.post(f"{base}/rest/api/3/search/jql", body, h)
        issues.extend(data.get("issues", []))
        token = data.get("nextPageToken")
        if data.get("isLast", True) or not token:
            break
    for issue in issues:
        key = issue["key"]
        comment = (issue.get("fields") or {}).get("comment") or {}
        if comment.get("total", 0) > len(comment.get("comments", [])):
            comment["comments"] = _all(http, f"{base}/rest/api/3/issue/{key}/comment", h, "comments")
        log = issue.get("changelog") or {}
        if log.get("total", 0) > len(log.get("histories", [])):
            issue["changelog"] = {"histories": _all(http, f"{base}/rest/api/3/issue/{key}/changelog", h, "values")}
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.raw_dir / "issues.json"
    path.write_text(json.dumps({"base_url": base, "issues": issues}, indent=1, sort_keys=True), encoding="utf-8")
    counts = {"issues": len(issues)}
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=[path], counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    path = ctx.raw_dir / "issues.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    base, rel, rows = data["base_url"], ctx.rel(path), []
    for issue in data["issues"]:
        key, f = issue["key"], issue.get("fields") or {}
        desc = adf_text(f.get("description"))
        tags = [(f.get("issuetype") or {}).get("name", ""), f"state:{(f.get('status') or {}).get('name', '')}"] + list(f.get("labels") or [])
        refs = activity.extract_refs(f"{f.get('summary', '')}\n{desc}", list(ctx.regexes), own_key=key)
        events = [("issue_created", key, f.get("creator") or f.get("reporter"), f.get("created"), desc, [])]
        for hist in (issue.get("changelog") or {}).get("histories", []):
            for item in hist.get("items", []):
                if item.get("field") == "status":
                    events.append(("issue_state_change", f"{key}:history:{hist['id']}:status", hist.get("author"), hist["created"], "",
                                   [f"to:{item.get('toString', '')}"]))
                elif item.get("field") == "assignee" and item.get("to"):
                    events.append(("issue_assigned", f"{key}:history:{hist['id']}:assignee",
                                   {"accountId": item["to"], "displayName": item.get("toString", "")}, hist["created"], "", []))
        for c in (f.get("comment") or {}).get("comments") or []:
            events.append(("issue_comment", f"{key}:comment:{c['id']}", c.get("author"), c["created"], adf_text(c.get("body")), []))
        if f.get("resolutiondate"):
            events.append(("issue_resolved", f"{key}:resolved", f.get("assignee"), f["resolutiondate"], "", []))
        for kind, k, user, ts, excerpt, extra in events:
            if not ts or not user:
                continue
            when = parse_iso(ts)
            if not activity.in_window(when, start, end, ctx.tz):
                continue
            person = ctx.resolver.resolve("jira", user.get("accountId", ""), email=user.get("emailAddress", ""), name=user.get("displayName", ""))
            rows.append(activity.make_row(source=ctx.name, key=k, kind=kind, person=person,
                                          actor_raw=user.get("displayName", "") or user.get("accountId", ""), ts=when,
                                          container=(f.get("project") or {}).get("key", ""), tags=tags + extra, title=f.get("summary", ""),
                                          excerpt=excerpt, refs=refs, url=f"{base}/browse/{key}", raw_path=rel, tz=ctx.tz))
    return rows
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_jira.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/adapters/jira.py tests/test_jira.py
git commit -m "feat: add Jira Cloud capture adapter

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: git-log adapter

**Files:**
- Create: `skills/sred/scripts/sredlib/adapters/gitlog.py`
- Test: `tests/test_gitlog.py`

**Interfaces:**
- Consumes: `adapters.Context`, `adapters.CaptureError`, `activity.*`, `manifest.record`, `dates.parse_iso`.
- Produces: module `gitlog` with `check`, `capture(ctx, http=None)`, `normalize`. Source keys: `paths` (local clone directories, relative to the claim folder or absolute). Raw file per clone: `evidence/raw/<name>/<clone-dir-name>.log` (verbatim `git log` output). Captures `--all` branches, so abandoned experiment branches count.

- [ ] **Step 1: Write the failing test**

`tests/test_gitlog.py`:
```python
import os
import subprocess
from datetime import date

from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))


def git(repo, *args, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Alice Chen", GIT_AUTHOR_EMAIL="alice@acme.test",
               GIT_COMMITTER_NAME="Alice Chen", GIT_COMMITTER_EMAIL="alice@acme.test")
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    # -c flags keep the user's global signing and hook settings out of the test repo
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                   check=True, capture_output=True, env=env)


def commit(repo, name, msg, when):
    p = repo / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(msg)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", msg, when=when)


def test_git_log_includes_abandoned_branches(tmp_path):
    repo = tmp_path / "clones/vision"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    commit(repo, "a.py", "Before FY", "2026-06-01T10:00:00+00:00")
    commit(repo, "planner/b.py", "Test occlusion sampler\n\nRefs ACME-12", "2026-09-02T10:00:00+00:00")
    git(repo, "checkout", "-q", "-b", "exp/abandoned")
    commit(repo, "c.py", "Abandoned idea", "2026-10-01T10:00:00+00:00")
    git(repo, "checkout", "-q", "-")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "email:alice@acme.test"}])
    ctx = Context(tmp_path, {"name": "git", "kind": "code", "method": "git-log", "paths": ["clones/vision"]}, FY, resolver, (r"[A-Z]+-\d+",))
    assert get_adapter("git-log").capture(ctx) == {"repos": 1, "commits": 2}
    rows = sorted(get_adapter("git-log").normalize(ctx), key=lambda r: r["date"])
    assert [r["title"] for r in rows] == ["Test occlusion sampler", "Abandoned idea"]
    assert rows[0]["paths"] == "planner/b.py" and rows[0]["refs"] == "ACME-12" and rows[0]["person"] == "alice"
    assert all(len(r["key"]) == 40 for r in rows) and rows[0]["container"] == "vision"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_gitlog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.adapters.gitlog'`.

- [ ] **Step 3: Implement `adapters/gitlog.py`**

`skills/sred/scripts/sredlib/adapters/gitlog.py`:
```python
"""Commits from local clones with `git log --all` (works for any git host)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context

FORMAT = "%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1f"


def _clones(ctx: Context) -> list[Path]:
    paths = ctx.source.get("paths") or []
    if not paths:
        raise CaptureError('git-log source needs paths = ["../clones/repo", ...]')
    out = []
    for p in paths:
        path = Path(p) if Path(p).is_absolute() else Path(ctx.claim_dir) / p
        if not (path / ".git").exists():
            raise CaptureError(f"{path} is not a git clone")
        out.append(path)
    return out


def check(source: dict, http) -> str:
    return "git-log needs no credentials"


def capture(ctx: Context, http=None) -> dict:
    start, end = ctx.fy
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    files, counts = [], {"repos": 0, "commits": 0}
    for clone in _clones(ctx):
        out = subprocess.run(
            ["git", "-C", str(clone), "log", "--all", "--no-merges", f"--since={start.isoformat()}T00:00:00",
             f"--until={end.isoformat()}T23:59:59", f"--pretty=format:{FORMAT}", "--name-only"],
            capture_output=True, text=True, check=True).stdout
        path = ctx.raw_dir / f"{clone.name}.log"
        path.write_text(out, encoding="utf-8")
        files.append(path)
        counts["repos"] += 1
        counts["commits"] += out.count("\x1e")
    manifest.record(ctx.claim_dir, ctx.name, method="git-log", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    for path in sorted(ctx.raw_dir.glob("*.log")):
        rel, repo = ctx.rel(path), path.stem
        for record in path.read_text(encoding="utf-8").split("\x1e"):
            if not record.strip():
                continue
            sha, name, email, when, subject, body, files = (record.split("\x1f") + [""] * 7)[:7]
            sha = sha.strip()
            if not sha or sha in seen:
                continue
            ts = parse_iso(when.strip())
            if not activity.in_window(ts, start, end, ctx.tz):
                continue
            seen.add(sha)
            message = f"{subject}\n\n{body}".strip()
            rows.append(activity.make_row(
                source=ctx.name, key=sha, kind="commit", person=ctx.resolver.resolve("git", name, email=email, name=name),
                actor_raw=name, ts=ts, container=repo, paths=[line.strip() for line in files.splitlines() if line.strip()],
                title=subject, excerpt=message, refs=activity.extract_refs(message, list(ctx.regexes)), raw_path=rel, tz=ctx.tz))
    return rows
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_gitlog.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/adapters/gitlog.py tests/test_gitlog.py
git commit -m "feat: add git-log adapter for any git host

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `index.py build` and `validate`

**Files:**
- Modify: `skills/sred/scripts/sredlib/indexing.py` (append `connector_rows`, `write_unmatched`, `build`, `validate`), `skills/sred/scripts/index.py` (replace whole file)
- Test: `tests/test_indexing.py`

**Interfaces:**
- Consumes: everything from Tasks 2–9.
- Produces:
  - `indexing.UNMATCHED_COLUMNS = ["source", "actor_raw", "rows", "first_date", "last_date", "sample_key"]`.
  - `indexing.connector_rows(claim_dir, src, resolver) -> list[dict]` (reads `evidence/raw/<name>/rows.csv` written by Claude; re-resolves `person` from `actor_raw`).
  - `indexing.build(cfg, claim_dir) -> dict` with keys `sources` (name → row count), `rows`, `unmatched`, `warnings`. Writes `evidence/index/parts/<name>.csv`, `evidence/index/activity.csv`, `evidence/index/identities_unmatched.csv`. Raises `FileNotFoundError` naming the source and the `capture.py` command when an `api`/`git-log` source has no raw files.
  - `indexing.validate(cfg, claim_dir) -> list[str]` (validates `activity.csv` against the roster).
  - CLI: `index.py build --claim DIR` (exit 2 on error), `index.py validate --claim DIR` (exit 1 on problems).

- [ ] **Step 1: Write the failing test**

`tests/test_indexing.py`:
```python
from datetime import datetime, timezone

import pytest

import index
from sredlib import activity, config, indexing

TOML = """
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"
issue_key_regex = '[A-Z]+-\\d+'

[[sources]]
name = "notes"
kind = "docs"
tool = "notion"
method = "connector"
"""


def test_build_merges_sources_and_reports_unmatched(make_claim, fixtures):
    claim = make_claim(TOML, roster=[{"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "jira:alice chen"}])
    (claim / "exports").mkdir()
    (claim / "exports/jira.csv").write_bytes((fixtures / "exports/jira.csv").read_bytes())
    page = claim / "evidence/raw/notes/page1.json"
    page.parent.mkdir(parents=True)
    page.write_text("{}")
    activity.write_rows(claim / "evidence/raw/notes/rows.csv", [activity.make_row(
        source="notes", key="page1:edit", kind="doc_edit", person="", actor_raw="Alice Chen",
        ts=datetime(2026, 9, 9, tzinfo=timezone.utc), title="Grasp experiment log", raw_path="evidence/raw/notes/page1.json", weight="summary")])
    cfg = config.load_config(claim / "sred.toml")
    summary = indexing.build(cfg, claim)
    assert summary["sources"] == {"jira": 4, "notes": 1} and summary["rows"] == 5 and summary["unmatched"] == 2
    header, rows = activity.read_rows(claim / "evidence/index/activity.csv")
    assert header == activity.COLUMNS and len(rows) == 5
    assert next(r for r in rows if r["source"] == "notes")["person"] == "alice"
    unmatched = (claim / "evidence/index/identities_unmatched.csv").read_text().splitlines()
    assert unmatched[0] == ",".join(indexing.UNMATCHED_COLUMNS)
    assert any(line.startswith("jira,Bob Roy,1,") for line in unmatched)
    assert any(line.startswith("jira,5b10ac,1,") for line in unmatched)
    assert indexing.validate(cfg, claim) == []


def test_build_names_uncaptured_api_source(make_claim):
    claim = make_claim('[[sources]]\nname = "gh"\nkind = "code"\ntool = "github"\nmethod = "api"\norg = "acme"\n', roster=[])
    with pytest.raises(FileNotFoundError, match=r"'gh'.*capture.py github --source gh"):
        indexing.build(config.load_config(claim / "sred.toml"), claim)


def test_cli_build_and_validate(make_claim, capsys):
    claim = make_claim('[[sources]]\nname = "gh"\nkind = "code"\ntool = "github"\nmethod = "api"\norg = "acme"\n', roster=[])
    assert index.main(["build", "--claim", str(claim)]) == 2
    assert "capture.py github" in capsys.readouterr().err
    assert index.main(["validate", "--claim", str(claim)]) == 1
    assert "run index.py build" in capsys.readouterr().out
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_indexing.py -v`
Expected: FAIL with `AttributeError: module 'sredlib.indexing' has no attribute 'build'`.

- [ ] **Step 3: Append build and validate to `indexing.py`**

Add these imports at the top of `skills/sred/scripts/sredlib/indexing.py` (below the existing imports):
```python
import csv

from .adapters import Context, adapter_key, get_adapter
```

Append to the end of `skills/sred/scripts/sredlib/indexing.py`:
```python
UNMATCHED_COLUMNS = ["source", "actor_raw", "rows", "first_date", "last_date", "sample_key"]


def connector_rows(claim_dir: Path, src: dict, resolver: Resolver) -> list[dict]:
    path = Path(claim_dir) / "evidence" / "raw" / src["name"] / "rows.csv"
    if not path.exists():
        raise FileNotFoundError(f"connector source {src['name']!r}: expected Claude-written rows at {path}")
    _, rows = activity.read_rows(path)
    for r in rows:
        r["source"] = src["name"]
        if r.get("actor_raw"):
            r["person"] = resolver.resolve(src.get("tool", src["name"]), r["actor_raw"])
    return rows


def write_unmatched(path: Path, rows: list[dict]) -> None:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r["person"].startswith("unmatched:") and r["actor_raw"]:
            groups.setdefault((r["source"], r["actor_raw"]), []).append(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(UNMATCHED_COLUMNS)
        for (source, actor), items in sorted(groups.items()):
            dates = sorted(i["date"] for i in items)
            writer.writerow([source, actor, len(items), dates[0], dates[-1], sorted(i["key"] for i in items)[0]])


def build(cfg: dict, claim_dir: Path) -> dict:
    claim_dir = Path(claim_dir)
    fy, tz = config.fiscal_year(cfg), config.timezone_of(cfg)
    resolver = resolver_for(cfg, claim_dir)
    regexes = tuple(config.issue_key_regexes(cfg))
    summary: dict = {"sources": {}, "warnings": []}
    all_rows: list[dict] = []
    for src in config.sources(cfg):
        name, method = src.get("name"), src.get("method")
        if method in ("api", "git-log"):
            ctx = Context(claim_dir, src, fy, resolver, regexes, tz)
            if not ctx.raw_dir.exists() or not any(ctx.raw_dir.iterdir()):
                raise FileNotFoundError(f"no raw files for source {name!r}: run `capture.py {adapter_key(src)} --source {name}` first")
            rows = get_adapter(adapter_key(src)).normalize(ctx)
            activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", rows)
        elif method == "export":
            result = import_source(cfg, claim_dir, name)
            rows = result.rows
            summary["warnings"] += [f"{name}: {w}" for w in result.warnings] + [f"{name}: {f}" for f in result.failures[:5]]
        elif method == "connector":
            rows = connector_rows(claim_dir, src, resolver)
            activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", rows)
        else:
            raise config.ConfigError(f"source {name!r}: unknown method {method!r}")
        summary["sources"][name] = len(rows)
        all_rows += rows
    index_dir = claim_dir / "evidence" / "index"
    activity.write_rows(index_dir / "activity.csv", all_rows)
    write_unmatched(index_dir / "identities_unmatched.csv", all_rows)
    summary["rows"] = len(all_rows)
    summary["unmatched"] = sum(1 for r in all_rows if r["person"].startswith("unmatched:"))
    return summary


def validate(cfg: dict, claim_dir: Path) -> list[str]:
    claim_dir = Path(claim_dir)
    path = claim_dir / "evidence" / "index" / "activity.csv"
    if not path.exists():
        return ["evidence/index/activity.csv is missing: run index.py build"]
    start, end = config.fiscal_year(cfg)
    roster_path = claim_dir / "roster.csv"
    ids = {r["id"] for r in load_roster(roster_path)} if roster_path.exists() else None
    header, rows = activity.read_rows(path)
    return activity.validate_rows(rows, header, start, end, claim_dir, ids)
```

- [ ] **Step 4: Replace `index.py` with the full CLI**

`skills/sred/scripts/index.py`:
```python
#!/usr/bin/env python3
"""Build and check evidence/index/activity.csv.

  index.py import   --claim DIR --source NAME [--mapping PRESET_OR_PATH]
  index.py build    --claim DIR       every source -> parts/ -> activity.csv + identities_unmatched.csv
  index.py validate --claim DIR       schema, keys, fiscal-year dates, roster ids, raw paths
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sredlib import config, indexing
from sredlib.adapters import CaptureError
from sredlib.mapping import MappingError

ERRORS = (MappingError, config.ConfigError, FileNotFoundError, CaptureError)


def cmd_import(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        res = indexing.import_source(cfg, claim, args.source, args.mapping)
    except ERRORS as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{args.source}: {len(res.rows)} rows, {res.skipped_outside_fy} outside the fiscal year")
    for kind, n in sorted(Counter(r["kind"] for r in res.rows).items()):
        print(f"  {kind}: {n}")
    unmatched = Counter(r["actor_raw"] for r in res.rows if r["person"].startswith("unmatched:") and r["actor_raw"])
    if unmatched:
        print("Unmatched people (add aliases to roster.csv): " + ", ".join(f"{a} ({n})" for a, n in unmatched.most_common()))
    if res.missing_columns:
        print("Columns named in the mapping but absent from the export: " + ", ".join(res.missing_columns))
    if res.unmapped_columns:
        print("Export columns not used: " + ", ".join(res.unmapped_columns))
    for w in res.warnings:
        print(f"WARNING: {w}")
    for f in res.failures[:20]:
        print(f"FAILED: {f}")
    if len(res.failures) > 20:
        print(f"... and {len(res.failures) - 20} more failures")
    return 0


def cmd_build(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        summary = indexing.build(cfg, claim)
    except ERRORS as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for name, n in summary["sources"].items():
        print(f"{name}: {n} rows")
    print(f"activity.csv: {summary['rows']} rows, {summary['unmatched']} with unmatched people (see identities_unmatched.csv)")
    for w in summary["warnings"]:
        print(f"WARNING: {w}")
    return 0


def cmd_validate(args) -> int:
    claim = Path(args.claim)
    problems = indexing.validate(config.load_config(claim / "sred.toml"), claim)
    for p in problems[:50]:
        print(p)
    if len(problems) > 50:
        print(f"... and {len(problems) - 50} more")
    print(f"{len(problems)} problems" if problems else "activity.csv is valid")
    return 1 if problems else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="convert one export file using a mapping")
    imp.add_argument("--claim", default=".")
    imp.add_argument("--source", required=True)
    imp.add_argument("--mapping")
    imp.set_defaults(func=cmd_import)
    for name, func in (("build", cmd_build), ("validate", cmd_validate)):
        sp = sub.add_parser(name)
        sp.add_argument("--claim", default=".")
        sp.set_defaults(func=func)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_indexing.py tests/test_mapping.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add skills/sred/scripts/sredlib/indexing.py skills/sred/scripts/index.py tests/test_indexing.py
git commit -m "feat: add index.py build and validate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 11: `check.py setup` (onboarding completeness)

**Files:**
- Create: `skills/sred/scripts/sredlib/setupcheck.py`, `skills/sred/scripts/check.py`, `skills/sred/templates/STATE.md`
- Test: `tests/test_setupcheck.py`

**Interfaces:**
- Consumes: `config.*`, `roster.load_roster`.
- Produces:
  - `setupcheck.Missing(phase: int, where: str, what: str)` (frozen dataclass; `str()` → `MISSING [phase N] <where>: <what>`).
  - `setupcheck.check_setup(claim_dir) -> tuple[list[Missing], list[str]]` (missing items sorted by phase, where, what; info lines include the filing deadline).
  - `setupcheck.current_phase(claim_dir) -> int` (from `STATE.md` `phase: N-…`, default 2); `setupcheck.add_months(d, months) -> date`; `setupcheck.filing_deadline(fy_end) -> date`.
  - CLI: `check.py setup --claim DIR [--phase N]` (exit 1 when any missing item's phase ≤ N).

Phase requirements encoded here (Plan 2's question bank must collect exactly these):

| Phase | Where | Required |
|---|---|---|
| 2 | sred.toml | `company.name`; valid `fiscal_year`; at least one `kind = "code"` source; each source has `name`, `kind`, `tool` (not for git-log), `method`; api: supported tool, credential env vars set (gitlab `GITLAB_TOKEN`, linear `LINEAR_API_KEY`, jira `JIRA_EMAIL`+`JIRA_TOKEN`; names overridable), github `org` or `repos`, gitlab `projects`, jira `base_url`; export: `mapping` and an existing `export_path`; git-log: `paths` |
| 2 | roster.csv | file exists with people; each row `id`, `name`, `classification` (employee/contractor), `aliases` |
| 3 | sred.toml | `claim.first_claim` (bool); if false: `prior_filings` (files exist) and `prior_titles`; the four `eligibility.*` answers; `preparer.ratifier` |
| 6 | sred.toml | `payroll.total_wages_earned` |
| 6 | roster.csv | `in_canada`, `specified_employee` (Y/N); `wages_earned`; employees `paid_hours`; contractors `arms_length`, `contract_provided`, `sred_in_contract` (Y/N) |
| 7 | sred.toml | `preparer.accountant`; `limits.mode` |

- [ ] **Step 1: Write the failing tests**

`tests/test_setupcheck.py`:
```python
from datetime import date

import check
from sredlib import setupcheck

COMPLETE = """
[claim]
first_claim = false
prior_filings = ["prior/FY2026.pdf"]
prior_titles = ["Adaptive Grasp Planning Under Occlusion"]

[preparer]
accountant = "Pat Lee"
ratifier = "CEO"

[eligibility]
government_assistance = "none"
client_contract_work = "none"
funded_by_others = "none"
work_outside_canada = "none"

[payroll]
total_wages_earned = 150000.10

[limits]
mode = "words"

[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"

[[sources]]
name = "code"
kind = "code"
method = "git-log"
paths = ["clones/vision"]
"""
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "email:alice@acme.test",
     "in_canada": "Y", "specified_employee": "N", "paid_hours": "2080", "wages_earned": "100000.00"},
    {"id": "carol", "name": "Carol Diaz", "classification": "contractor", "aliases": "email:carol@diaz.test",
     "in_canada": "Y", "specified_employee": "N", "wages_earned": "50000.10", "arms_length": "Y", "contract_provided": "Y", "sred_in_contract": "N"},
]


def build(make_claim, toml=COMPLETE, roster=ROSTER):
    claim = make_claim(toml, roster=roster)
    for rel in ("prior/FY2026.pdf", "exports/jira.csv"):
        (claim / rel).parent.mkdir(parents=True, exist_ok=True)
        (claim / rel).write_text("x")
    return claim


def deferred(make_claim):
    """Onboarding finished with two 'I don't know yet' answers."""
    return build(make_claim, COMPLETE.replace("total_wages_earned = 150000.10", "total_wages_earned = 0.0"),
                 [dict(ROSTER[0], paid_hours=""), ROSTER[1]])


def test_complete_claim_has_nothing_missing(make_claim):
    missing, info = setupcheck.check_setup(build(make_claim))
    assert missing == []
    assert info == ["Filing deadline: 2029-01-31 (fiscal year end + 18 months)"]


def test_two_deferred_items_are_reported_with_their_phase(make_claim):
    missing, _ = setupcheck.check_setup(deferred(make_claim))
    assert [str(m) for m in missing] == [
        "MISSING [phase 6] roster.csv alice: paid_hours",
        "MISSING [phase 6] sred.toml: payroll.total_wages_earned: payroll total for the fiscal year, to reconcile the roster",
    ]


def test_empty_claim_lists_everything_by_phase(make_claim):
    missing, _ = setupcheck.check_setup(make_claim(roster=[]))
    text = "\n".join(map(str, missing))
    assert {m.phase for m in missing} == {2, 3, 6, 7}
    for needle in ['kind = "code"', "no people listed", "claim.first_claim", "eligibility.government_assistance",
                   "preparer.ratifier", "payroll.total_wages_earned", "preparer.accountant", "limits.mode"]:
        assert needle in text


def test_api_source_needs_its_credentials(make_claim, monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    claim = make_claim('[[sources]]\nname = "gl"\nkind = "code"\ntool = "gitlab"\nmethod = "api"\n', roster=ROSTER)
    text = "\n".join(map(str, setupcheck.check_setup(claim)[0]))
    assert "environment variable GITLAB_TOKEN is not set" in text and "gl: projects" in text


def test_add_months_clamps_to_month_end():
    assert setupcheck.add_months(date(2027, 8, 31), 18) == date(2029, 2, 28)
    assert setupcheck.filing_deadline(date(2027, 7, 31)) == date(2029, 1, 31)


def test_cli_gates_on_current_phase(make_claim, capsys):
    claim = deferred(make_claim)
    assert check.main(["setup", "--claim", str(claim)]) == 0
    (claim / "STATE.md").write_text("# state\nphase: 6-financials\n")
    assert check.main(["setup", "--claim", str(claim)]) == 1
    assert "2 missing; 2 block phase 6." in capsys.readouterr().out
    assert check.main(["setup", "--claim", str(claim), "--phase", "3"]) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_setupcheck.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'check'`.

- [ ] **Step 3: Implement `setupcheck.py`**

`skills/sred/scripts/sredlib/setupcheck.py`:
```python
"""Completeness of sred.toml and roster.csv against what each phase needs."""
from __future__ import annotations

import calendar
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import config
from .roster import load_roster

YN = {"Y", "N"}
ELIGIBILITY_KEYS = ["government_assistance", "client_contract_work", "funded_by_others", "work_outside_canada"]
CREDENTIAL_ENVS = {"gitlab": [("token_env", "GITLAB_TOKEN")], "linear": [("token_env", "LINEAR_API_KEY")],
                   "jira": [("email_env", "JIRA_EMAIL"), ("token_env", "JIRA_TOKEN")]}


@dataclass(frozen=True)
class Missing:
    phase: int
    where: str
    what: str

    def __str__(self) -> str:
        return f"MISSING [phase {self.phase}] {self.where}: {self.what}"


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def filing_deadline(fy_end: date) -> date:
    return add_months(fy_end, 18)


def current_phase(claim_dir: Path) -> int:
    state = Path(claim_dir) / "STATE.md"
    if state.exists():
        m = re.search(r"(?m)^phase:\s*(\d+)", state.read_text(encoding="utf-8"))
        if m:
            return int(m.group(1))
    return 2


def _get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _blank(v) -> bool:
    if v is None or isinstance(v, bool):
        return v is None
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return not v
    if isinstance(v, (int, float)):
        return v == 0
    return False


def _num(v: str) -> bool:
    text = (v or "").replace(",", "").replace("$", "").strip()
    try:
        float(text)
    except ValueError:
        return False
    return True


def _check_sources(cfg: dict, missing: list[Missing]) -> None:
    T = "sred.toml"
    srcs = config.sources(cfg)
    if not any(s.get("kind") == "code" for s in srcs):
        missing.append(Missing(2, T, 'sources: at least one source with kind = "code" (code history drives the time basis)'))
    for s in srcs:
        where = f"{T} [[sources]] {s.get('name') or '<unnamed>'}"
        method = s.get("method")
        for k in ("name", "kind", "tool", "method"):
            if _blank(s.get(k)) and not (k == "tool" and method == "git-log"):
                missing.append(Missing(2, where, k))
        if s.get("kind") and s["kind"] not in config.VALID_KINDS:
            missing.append(Missing(2, where, f"kind must be one of {sorted(config.VALID_KINDS)}"))
        if method and method not in config.VALID_METHODS:
            missing.append(Missing(2, where, f"method must be one of {sorted(config.VALID_METHODS)}"))
        if method == "api":
            tool = s.get("tool")
            if tool not in config.API_TOOLS:
                missing.append(Missing(2, where, f"no API adapter for tool {tool!r}; use export or connector"))
            for key, default in CREDENTIAL_ENVS.get(tool, []):
                env = s.get(key, default)
                if not os.environ.get(env):
                    missing.append(Missing(2, where, f"environment variable {env} is not set"))
            if tool == "github" and _blank(s.get("org")) and _blank(s.get("repos")):
                missing.append(Missing(2, where, "org or repos"))
            if tool == "gitlab" and _blank(s.get("projects")):
                missing.append(Missing(2, where, "projects"))
            if tool == "jira" and _blank(s.get("base_url")):
                missing.append(Missing(2, where, "base_url"))
        if method == "export":
            if _blank(s.get("mapping")):
                missing.append(Missing(2, where, "mapping (preset name or path)"))
            p = s.get("export_path")
            if _blank(p) or not config.resolve_path(cfg, p).exists():
                missing.append(Missing(2, where, f"export_path file not found: {p!r}"))
        if method == "git-log" and _blank(s.get("paths")):
            missing.append(Missing(2, where, "paths (local clones)"))


def _check_roster(claim_dir: Path, missing: list[Missing]) -> None:
    path = claim_dir / "roster.csv"
    if not path.exists():
        missing.append(Missing(2, "roster.csv", "file not found (copy templates/roster.csv)"))
        return
    roster = load_roster(path)
    if not roster:
        missing.append(Missing(2, "roster.csv", "no people listed"))
    for r in roster:
        who = f"roster.csv {r['id'] or r['name'] or '<row>'}"
        for k in ("id", "name"):
            if not r[k]:
                missing.append(Missing(2, who, k))
        if r["classification"] not in ("employee", "contractor"):
            missing.append(Missing(2, who, "classification must be employee or contractor"))
        if not r["aliases"]:
            missing.append(Missing(2, who, "aliases (tool handles or email) for identity matching"))
        for k in ("in_canada", "specified_employee"):
            if r[k] not in YN:
                missing.append(Missing(6, who, f"{k} (Y or N)"))
        if not _num(r["wages_earned"]):
            missing.append(Missing(6, who, "wages_earned"))
        if r["classification"] == "employee" and not _num(r["paid_hours"]):
            missing.append(Missing(6, who, "paid_hours"))
        if r["classification"] == "contractor":
            for k in ("arms_length", "contract_provided", "sred_in_contract"):
                if r[k] not in YN:
                    missing.append(Missing(6, who, f"{k} (Y or N)"))


def check_setup(claim_dir: Path) -> tuple[list[Missing], list[str]]:
    claim_dir = Path(claim_dir)
    missing: list[Missing] = []
    info: list[str] = []
    cfg_path = claim_dir / "sred.toml"
    if not cfg_path.exists():
        return [Missing(1, "sred.toml", "file not found (copy templates/sred.toml)")], info
    cfg = config.load_config(cfg_path)
    T = "sred.toml"

    def need(phase: int, dotted: str, what: str) -> None:
        if _blank(_get(cfg, dotted)):
            missing.append(Missing(phase, T, f"{dotted}: {what}"))

    need(2, "company.name", "legal company name")
    try:
        _, end = config.fiscal_year(cfg)
        info.append(f"Filing deadline: {filing_deadline(end).isoformat()} (fiscal year end + 18 months)")
    except config.ConfigError as exc:
        missing.append(Missing(2, T, f"fiscal_year: {exc}"))
    _check_sources(cfg, missing)
    _check_roster(claim_dir, missing)
    if not isinstance(_get(cfg, "claim.first_claim"), bool):
        missing.append(Missing(3, T, "claim.first_claim: true or false"))
    elif not cfg["claim"]["first_claim"]:
        need(3, "claim.prior_filings", "prior T661 Part 2 filings (PDF paths)")
        need(3, "claim.prior_titles", "project titles exactly as previously filed")
        for p in _get(cfg, "claim.prior_filings") or []:
            if not config.resolve_path(cfg, p).exists():
                missing.append(Missing(3, T, f"claim.prior_filings: file not found {p!r}"))
    for k in ELIGIBILITY_KEYS:
        need(3, f"eligibility.{k}", 'answer, or "none"')
    need(3, "preparer.ratifier", "who approves locked decisions")
    need(6, "payroll.total_wages_earned", "payroll total for the fiscal year, to reconcile the roster")
    need(7, "preparer.accountant", "accountant or preparer name")
    need(7, "limits.mode", "ask the preparer whether their filing software enforces words or lines")
    return sorted(missing, key=lambda m: (m.phase, m.where, m.what)), info
```

- [ ] **Step 4: Implement `check.py` (setup only for now) and the STATE template**

`skills/sred/scripts/check.py`:
```python
#!/usr/bin/env python3
"""Checks that gate each phase.

  check.py setup --claim DIR [--phase N]     what onboarding still needs; exit 1 if anything blocks phase N
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import setupcheck


def cmd_setup(args) -> int:
    claim = Path(args.claim)
    missing, info = setupcheck.check_setup(claim)
    phase = args.phase or setupcheck.current_phase(claim)
    for line in info:
        print(line)
    for m in missing:
        print(m)
    blocking = [m for m in missing if m.phase <= phase]
    print(f"{len(missing)} missing; {len(blocking)} block phase {phase}." if missing else "Setup complete: nothing missing.")
    return 1 if blocking else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="what onboarding still needs")
    s.add_argument("--claim", default=".")
    s.add_argument("--phase", type=int)
    s.set_defaults(func=cmd_setup)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

`skills/sred/templates/STATE.md`:
```markdown
# SR&ED claim state: <company> FY<year>
phase: 1-setup
updated: YYYY-MM-DD

## Locked decisions
(none yet)

## Open questions for the claimant
(none yet)

## Phase log
(none yet)

## Next action
Run onboarding: answer the setup questions.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_setupcheck.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add skills/sred/scripts/sredlib/setupcheck.py skills/sred/scripts/check.py skills/sred/templates/STATE.md tests/test_setupcheck.py
git commit -m "feat: add check.py setup for onboarding completeness

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: `check.py narrative` and the mechanical do-not patterns

**Files:**
- Create: `skills/sred/scripts/sredlib/narrative.py`, `skills/sred/references/do-not-patterns.toml`
- Modify: `skills/sred/scripts/check.py` (replace whole file)
- Test: `tests/test_narrative.py`

**Interfaces:**
- Consumes: `config.limits`, `config.fiscal_year`.
- Produces:
  - `narrative.LINES = ("242", "244", "246")`; `narrative.MARKER_ID_RE`; `narrative.PATTERNS_PATH`.
  - `narrative.Narrative` dataclass (`project`, `title`, `section_a: dict[str, str]` keyed `"200"`…, `lines: dict[str, str]`, `section_c: dict[str, str]` keyed lower-case labels such as `"key individuals"`, `"contractors"`).
  - `narrative.Finding(severity, rule, where, message)` (severity `error|warning|info`).
  - `narrative.parse_narrative(text) -> Narrative`; `narrative.strip_markers(text) -> str`; `narrative.word_count(text) -> int`; `narrative.line_count(text, width=78) -> int`; `narrative.load_patterns(path=None) -> list[dict]`; `narrative.yes(value) -> bool`.
  - `narrative.check_narrative(n, evidence: list[dict], cfg, patterns) -> tuple[list[Finding], dict[str, tuple[int, int]]]` (counts per line: words, lines).
  - CLI: `check.py narrative PATH [--claim DIR] [--evidence CSV] [--patterns TOML]` (claim defaults to three levels above `draft/<P>/narrative.md`; evidence defaults to `evidence_table.csv` beside it; exit 1 on any error).

Word counting matches how the reference claimant's reviews counted: whitespace-separated tokens, ignoring claim markers and `---` rule lines.

- [ ] **Step 1: Write the failing tests**

`tests/test_narrative.py`:
```python
import csv
import re

import pytest

import check
from sredlib import config
from sredlib.narrative import check_narrative, line_count, load_patterns, parse_narrative, word_count

CLAIM_TOML = """
[claim]
prior_titles = ["Adaptive Grasp Planning Under Occlusion"]
field_codes = ["2.02.09"]
"""
SECTION_A = ("- 200 Project title: Adaptive Grasp Planning Under Occlusion\n- 202 Start date: 2026-09-02\n"
             "- 204 Completion date: 2027-07-31\n- 206 Field of science code: 2.02.09\n- 208 Continuation: yes\n- 210 First claim: no\n")
CLEAN_242 = "It was uncertain whether occlusion-aware sampling could keep grasp success above the baseline under partial visibility [C1]."
CLEAN_244 = "The team tested three sampling strategies across 230 trials [C2]. Contractor developers built the test harness."
CLEAN_246 = "The team determined that visibility-weighted sampling holds success rates under occlusion of up to 40% [C3]."
SECTION_C = "- Key individuals: Alice Chen (Lead developer)\n- Contractors: Carol Diaz (Diaz Robotics)\n"
EVIDENCE = [{"claim_id": c, "statement": "s", "source_key": "k", "raw_path": "p", "verified": "Y"} for c in ("C1", "C2", "C3")]


def text(l242=CLEAN_242, l244=CLEAN_244, l246=CLEAN_246, a=SECTION_A, c=SECTION_C):
    return (f"# P1: Adaptive Grasp Planning Under Occlusion\n\n## Section A\n{a}\n## Line 242\n{l242}\n\n---\n\n"
            f"## Line 244\n{l244}\n\n## Line 246\n{l246}\n\n## Section C\n{c}")


@pytest.fixture
def cfg(make_claim):
    return config.load_config(make_claim(CLAIM_TOML) / "sred.toml")


def run(cfg, body, evidence=EVIDENCE):
    return check_narrative(parse_narrative(body), evidence, cfg, load_patterns())


def test_parse_reads_sections_and_drops_rule_lines():
    n = parse_narrative(text())
    assert n.project == "P1" and n.title == "Adaptive Grasp Planning Under Occlusion"
    assert n.section_a["208"] == "yes" and n.section_c["contractors"] == "Carol Diaz (Diaz Robotics)"
    assert "---" not in n.lines["242"]


def test_counts_strip_markers_and_rule_lines():
    assert word_count("It was uncertain [C1] whether\n---\n") == 4
    assert line_count("Alpha beta.\n\nGamma.") == 3
    assert line_count(" ".join(["word"] * 32), width=78) == 3


def test_clean_narrative_passes(cfg):
    findings, counts = run(cfg, text())
    assert findings == []
    assert counts["242"][0] == 16


def test_word_limit_is_an_error_in_words_mode_and_a_warning_in_lines_mode(cfg):
    long = " ".join(["word"] * 351) + " [C1]."
    findings, _ = run(cfg, text(l242=long))
    assert ("error", "M-L01") in {(f.severity, f.rule) for f in findings}
    cfg["limits"] = {"mode": "lines"}
    findings, _ = run(cfg, text(l242=long))
    assert ("warning", "M-L01") in {(f.severity, f.rule) for f in findings}
    assert not any(f.severity == "error" for f in findings)


def test_markers_must_exist_and_be_verified(cfg):
    findings, _ = run(cfg, text(), evidence=[dict(EVIDENCE[0]), dict(EVIDENCE[1], verified="N")])
    msgs = [f.message for f in findings if f.rule == "EVIDENCE"]
    assert any("[C2] is not verified" in m for m in msgs) and any("[C3] has no row" in m for m in msgs)


def test_numbers_need_a_marker_but_years_do_not(cfg):
    findings, _ = run(cfg, text(l244="In 2026 the team ran 230 trials. Contractor developers built the harness [C2]."))
    hits = [f for f in findings if f.rule == "M-L14"]
    assert len(hits) == 1 and "'230'" in hits[0].message


def test_trigger_words_flagged_in_lines_and_title(cfg):
    a = SECTION_A.replace("Adaptive Grasp Planning Under Occlusion", "Grasp Planner Migration")
    findings, _ = run(cfg, text(l244="We migrated the planner to a new framework [C2]. Contractor staff helped.", a=a))
    where = {(f.rule, f.where) for f in findings}
    assert ("M-W05", "244") in where and ("M-W05", "title") in where
    assert ("M-L05", "A") in where


def test_section_a_rules(cfg):
    a = (SECTION_A.replace("2026-09-02", "2026-08-01").replace("- 210 First claim: no", "- 210 First claim: yes")
         .replace("2.02.09", "2.2.9"))
    assert {"M-L06", "M-L07", "M-L10"} <= {f.rule for f in run(cfg, text(a=a))[0]}


def test_start_before_fiscal_year_requires_continuation(cfg):
    a = (SECTION_A.replace("2026-09-02", "2026-05-01").replace("- 208 Continuation: yes", "- 208 Continuation: no")
         .replace("- 210 First claim: no", "- 210 First claim: yes"))
    findings, _ = run(cfg, text(a=a))
    assert any(f.severity == "error" and "requires Line 208" in f.message for f in findings)


def test_late_dates_and_missing_contractor_statement(cfg):
    findings, _ = run(cfg, text(l244="The team tested sampling in March 2028 [C2]."))
    assert {"M-L12", "M-L11"} <= {f.rule for f in findings}


def test_shipped_patterns_are_valid():
    patterns = load_patterns()
    ids = [p["id"] for p in patterns]
    assert len(patterns) >= 40 and len(ids) == len(set(ids))
    for p in patterns:
        re.compile(p["regex"])
        assert set(p["scope"]) <= {"242", "244", "246", "title"}
        assert p["severity"] in {"hard", "high", "med", "low", "soft"}
        assert p["hint"]


def test_cli_reports_counts_and_exit_code(make_claim, capsys):
    claim = make_claim(CLAIM_TOML)
    d = claim / "draft/P1"
    d.mkdir(parents=True)
    (d / "narrative.md").write_text(text())
    with (d / "evidence_table.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["claim_id", "statement", "source_key", "raw_path", "verified"])
        writer.writeheader()
        writer.writerows(EVIDENCE)
    assert check.main(["narrative", str(d / "narrative.md")]) == 0
    out = capsys.readouterr().out
    assert "Line 242: 16/350 words" in out and "0 errors" in out
    (d / "narrative.md").write_text(text(l242=" ".join(["word"] * 351)))
    assert check.main(["narrative", str(d / "narrative.md")]) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_narrative.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.narrative'`.

- [ ] **Step 3: Implement `narrative.py`**

`skills/sred/scripts/sredlib/narrative.py`:
```python
"""Parse a project narrative (draft/<P>/narrative.md) and check it mechanically."""
from __future__ import annotations

import re
import textwrap
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import config

LINES = ("242", "244", "246")
MARKER_RE = re.compile(r"\s?\[C\d+\]")
MARKER_ID_RE = re.compile(r"\[(C\d+)\]")
HEADING_RE = re.compile(r"(?m)^(#{1,4})\s+(.*?)\s*$")
ITEM_RE = re.compile(r"(?m)^\s*-\s*([^:\n]+?)\s*:\s*(.*)$")
SEVERITY_LEVEL = {"hard": "error", "high": "warning", "med": "warning", "low": "info", "soft": "info"}
PATTERNS_PATH = Path(__file__).resolve().parent.parent.parent / "references" / "do-not-patterns.toml"
PLAIN_TEXT_RE = re.compile(r"(?m)^\s*([-*•]|\d+[.)])\s|\*\*|^#|\||\t")
NUMBER_RE = re.compile(r"(?<![\w-])\d[\d,.]*%?")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTH_YEAR_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b")
CONTRACTOR_RE = re.compile(r"\b(sub)?contract(or|ors|ed|ing)\b", re.I)


@dataclass
class Narrative:
    project: str = ""
    title: str = ""
    section_a: dict = field(default_factory=dict)
    lines: dict = field(default_factory=dict)
    section_c: dict = field(default_factory=dict)


@dataclass
class Finding:
    severity: str
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper():7} {self.rule:8} [{self.where}] {self.message}"


def _items(body: str) -> dict:
    return {m.group(1).strip(): m.group(2).strip() for m in ITEM_RE.finditer(body)}


def parse_narrative(text: str) -> Narrative:
    n = Narrative()
    heads = list(HEADING_RE.finditer(text))
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        level, title = len(h.group(1)), h.group(2)
        line_m = re.search(r"\bLine\s+(24[246])\b", title)
        if level == 1 and not n.project:
            m = re.match(r"(\S+?):\s*(.*)", title)
            n.project, n.title = (m.group(1), m.group(2)) if m else ("", title)
        elif line_m:
            n.lines[line_m.group(1)] = "\n".join(l for l in body.strip().splitlines() if l.strip() != "---").strip()
        elif re.search(r"\bSection A\b", title):
            n.section_a = {k[:3]: v for k, v in _items(body).items() if re.match(r"\d{3}", k)}
        elif re.search(r"\bSection C\b", title):
            n.section_c = {k.lower(): v for k, v in _items(body).items()}
    return n


def strip_markers(text: str) -> str:
    return MARKER_RE.sub("", text or "")


def word_count(text: str) -> int:
    return len([t for t in strip_markers(text).split() if t != "---"])


def line_count(text: str, width: int = 78) -> int:
    paras = [p for p in re.split(r"\n\s*\n", strip_markers(text).strip()) if p.strip()]
    return sum(len(textwrap.wrap(" ".join(p.split()), width)) for p in paras) + max(len(paras) - 1, 0)


def load_patterns(path: Path | None = None) -> list[dict]:
    return tomllib.loads(Path(path or PATTERNS_PATH).read_text(encoding="utf-8")).get("pattern", [])


def yes(value: str) -> bool:
    return (value or "").strip().lower() in ("yes", "y", "x", "true")


def _date(value: str):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def check_narrative(n: Narrative, evidence: list[dict], cfg: dict, patterns: list[dict]) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    counts: dict[str, tuple[int, int]] = {}
    lim = config.limits(cfg)
    start, end = config.fiscal_year(cfg)
    claim = cfg.get("claim") or {}

    def add(severity, rule, where, message):
        findings.append(Finding(severity, rule, where, message))

    # Length, plain text, and numbers that need a claim marker
    for line in LINES:
        text = n.lines.get(line, "")
        if not text:
            add("error", "STRUCT", line, f"Line {line} is missing or empty")
            continue
        words, lines_ = word_count(text), line_count(text, lim["line_width"])
        counts[line] = (words, lines_)
        wmax, lmax = lim["words"][line], lim["lines"][line]
        w_sev, l_sev = ("error", "warning") if lim["mode"] == "words" else ("warning", "error")
        if words > wmax:
            add(w_sev, "M-L01", line, f"{words} words, limit {wmax}")
        elif words >= wmax - 5:
            add("info", "M-L03", line, f"{words} words leaves less than 5 words of headroom")
        if lines_ > lmax:
            add(l_sev, "M-L02", line, f"{lines_} lines at {lim['line_width']} characters, budget {lmax}")
        if PLAIN_TEXT_RE.search(text):
            add("warning", "M-L04", line, "plain text only: no bullets, bold, headings, tables or tabs")
        for sentence in SENTENCE_RE.split(text):
            nums = [x for x in NUMBER_RE.findall(strip_markers(sentence)) if not YEAR_RE.match(x.rstrip(".,%"))]
            if nums and not MARKER_ID_RE.search(sentence):
                add("warning", "M-L14", line, f"number without a claim marker: {nums[0]!r} in {sentence.strip()[:80]!r}")
        late = [d for d in ISO_DATE_RE.findall(text) if _date(d) and _date(d) > end]
        late += [f"{mon} {yr}" for mon, yr in MONTH_YEAR_RE.findall(text) if (int(yr), MONTHS.index(mon) + 1) > (end.year, end.month)]
        if late:
            add("warning", "M-L12", line, "work after the fiscal year end belongs to next year's claim: " + ", ".join(late))

    # Claim markers resolve to verified evidence rows
    rows = {r.get("claim_id", ""): r for r in evidence}
    for line in LINES:
        for cid in MARKER_ID_RE.findall(n.lines.get(line, "")):
            row = rows.get(cid)
            if row is None:
                add("error", "EVIDENCE", line, f"marker [{cid}] has no row in evidence_table.csv")
            elif (row.get("verified") or "").strip().upper() != "Y":
                add("error", "EVIDENCE", line, f"marker [{cid}] is not verified against raw evidence")

    # Mechanical do-not patterns
    texts = {**{line: strip_markers(n.lines.get(line, "")) for line in LINES}, "title": n.section_a.get("200", "")}
    for p in patterns:
        rx = re.compile(p["regex"], (0 if p.get("case_sensitive") else re.I) | re.M)
        excl = re.compile(p["exclude"], re.I) if p.get("exclude") else None
        for scope in p.get("scope", list(LINES)):
            body = texts.get(scope, "")
            hits = [m for m in rx.finditer(body) if not (excl and excl.search(body[max(0, m.start() - 60): m.end() + 60]))]
            if hits:
                sample = ", ".join(dict.fromkeys(h.group(0) for h in hits[:3]))
                add(SEVERITY_LEVEL[p.get("severity", "med")], p["id"], scope, f"{len(hits)}x {sample!r}: {p.get('hint', '')}")

    # Section A
    a = n.section_a
    for k, label in (("200", "project title"), ("202", "start date"), ("204", "completion date"), ("206", "field of science code")):
        if not a.get(k):
            add("error", "STRUCT", "A", f"Line {k} ({label}) is missing")
    cont, first = yes(a.get("208", "")), yes(a.get("210", ""))
    if cont == first:
        add("error", "M-L06", "A", "exactly one of Line 208 (continuation) and Line 210 (first claim) must be marked")
    prior_titles = claim.get("prior_titles") or []
    if cont and prior_titles and a.get("200", "") not in prior_titles:
        add("error", "M-L05", "A", "a continuing project keeps its previously filed title verbatim: " + " | ".join(prior_titles))
    d202, d204 = _date(a.get("202", "")), _date(a.get("204", ""))
    if a.get("202") and d202 is None:
        add("warning", "M-L10", "A", "Line 202 must be YYYY-MM-DD")
    if a.get("204") and d204 is None:
        add("warning", "M-L10", "A", "Line 204 must be YYYY-MM-DD")
    if a.get("206") and not re.fullmatch(r"\d\.\d{2}\.\d{2}", a["206"]):
        add("warning", "M-L10", "A", "Line 206 must look like 2.02.09")
    prior_codes = claim.get("field_codes") or []
    if a.get("206") and prior_codes and a["206"] not in prior_codes:
        add("info", "M-L10", "A", "field code differs from the prior filing; keep it unless the technology changed")
    if d202:
        if d202 == start:
            add("warning", "M-L07", "A", "start date equals the fiscal year start; use the earliest evidenced hypothesis")
        if d202 > end:
            add("error", "STRUCT", "A", "start date is after the fiscal year end")
        if d202 < start and not cont:
            add("error", "STRUCT", "A", "a start date before the fiscal year requires Line 208 (continuation)")
        if first:
            for prior in claim.get("prior_projects") or []:
                pend = prior.get("end")
                if isinstance(pend, date) and 0 < (d202 - pend).days < 90:
                    add("warning", "M-L08", "A", f"starts {(d202 - pend).days} days after prior project {prior.get('title', '')!r} ended: prepare a demarcation note")

    # Contractors named in Section C must appear in Line 244
    contractors = n.section_c.get("contractors", "").strip().lower()
    if contractors not in ("", "none", "n/a") and not CONTRACTOR_RE.search(n.lines.get("244", "")):
        add("warning", "M-L11", "244", "contractors are listed in Section C but Line 244 never says what contractors did")
    return findings, counts
```

- [ ] **Step 4: Write `do-not-patterns.toml`**

`skills/sred/references/do-not-patterns.toml`:
```toml
# Mechanical do-not patterns, checked by `check.py narrative`.
# A hit means "look at this", not "rewrite it". Severity: hard -> error, high/med -> warning, low/soft -> info.
# scope: "242", "244", "246" or "title" (Section A Line 200). Regexes are case-insensitive unless case_sensitive = true.
# exclude: a hit is ignored when this regex matches within 60 characters of it.
# Length limits, Section A fields, claim markers, dates after the fiscal year and the contractor statement are checked in code.
# Judgment patterns that need a reviewer live in do-not.md.

[[pattern]]
id = "M-W01"
regex = '\bcutting[- ]edge\b|\binnovative\b|\bnovel\b|\bbest[- ]in[- ]class\b|\bworld[- ]class\b|\bstate[- ]of[- ]the[- ]art\b|\bSOTA\b|\brevolutionary\b'
scope = ["242", "244", "246", "title"]
severity = "med"
hint = "marketing superlative; give a specific technical description (for models: 'current commercial models')"

[[pattern]]
id = "M-W02"
regex = '\bseamless\b|\brobust\b|\bscalable\b|\bquick\b|\bfast\b|\brapid\b|\befficient\b|\bcost[- ]effective\b'
scope = ["242", "244", "246"]
severity = "low"
hint = "unquantified quality claim; state the measured characteristic"

[[pattern]]
id = "M-W03"
regex = '\bcustomer requirements?\b|\bclient required\b|\bcompetitive\b|\bmarket demand\b|\breduce costs?\b|\bsales\b|\brevenue\b|\bprofit\b|\bROI\b|\bconversion rates?\b|\bCVR\b|\buplift\b|\bhigh[- ]performing\b|\bimprove (the )?(quality|performance)\b|\bimproved performance by\b'
scope = ["242", "246"]
severity = "high"
hint = "business driver or metric; state the technical constraint or parameter ('marketing' as a domain noun is fine)"

[[pattern]]
id = "M-W03b"
regex = '\bcustomer requirements?\b|\bclient required\b|\bcompetitive\b|\bmarket demand\b|\breduce costs?\b|\bsales\b|\brevenue\b|\bprofit\b|\bROI\b|\bconversion rates?\b|\bCVR\b|\buplift\b|\bhigh[- ]performing\b|\bimprove (the )?(quality|performance)\b|\bimproved performance by\b'
scope = ["244"]
severity = "med"
hint = "business driver or metric; state the technical constraint or parameter"

[[pattern]]
id = "M-W04"
regex = '\bsolutions?\b'
exclude = 'no applicable solution|backend solution'
scope = ["242", "244", "246"]
severity = "low"
hint = "name the specific implementation instead of 'solution'"

[[pattern]]
id = "M-W05"
regex = '\bmigrat(e|ed|es|ing|ion|ions)\b|\bport(ed|ing)\b'
scope = ["242", "244", "246", "title"]
severity = "med"
hint = "implies simple conversion; 're-architected', 'restructured', 'architectural transition'"

[[pattern]]
id = "M-W06"
regex = '\bimplement(ed|ing|s)?\b'
scope = ["244", "246"]
severity = "med"
hint = "reads as execution; 'investigated', 'tested', 'established' (one supporting-work sentence is acceptable)"

[[pattern]]
id = "M-W07"
regex = '\b(we|the team) (developed|created|built|deployed)\b|\bbuilding\b'
scope = ["244", "246"]
severity = "low"
hint = "'devised', 'formulated', 'tested'; acceptable for prior-year references and the supporting-work sentence"

[[pattern]]
id = "M-W08"
regex = '\bapply(ing)?\b|\bapplied\b'
scope = ["244", "246"]
severity = "low"
hint = "suggests using a known method; 'tested whether [technique] could ...'"

[[pattern]]
id = "M-W09"
regex = '\btrial[- ]and[- ]error\b|\btweak(ed|ing)?\b|\btinker\w*|\bfine[- ]tun(e|ed|ing)\b'
scope = ["242", "244", "246"]
severity = "med"
hint = "reads as unsystematic; name the independent variables that were varied"

[[pattern]]
id = "M-W10"
regex = '\b(debug(ged|ging)?|bugs?|hot ?fix(es)?|fix(ed|es)?|patch(ed)?|incidents?|outages?|revert(ed)?|rollback)\b'
exclude = 'rather than (from )?a single coding defect'
scope = ["244", "246"]
severity = "med"
hint = "bug-fix language; frame as hypothesis, test and result"

[[pattern]]
id = "M-W11"
regex = '\brevert chain\b|\b(pull requests?|PRs|commits|deploys?) (in|within) (a|one) (single )?day\b'
scope = ["244"]
severity = "high"
hint = "incident-log counting; state what the deployment revealed and the hypothesis tested"

[[pattern]]
id = "M-W12"
regex = '\b(did not|does not|didn.t) (document|address)\b|\bnot documented\b|\bundocumented\b|\bdocumentation (did not|does not)\b'
scope = ["242"]
severity = "med"
hint = "a documentation gap is not a knowledge gap; 'no established method existed in the available knowledge base for ...'"

[[pattern]]
id = "M-W13"
regex = '\bnot previously documented\b|\bpreviously unavailable\b|\bfirst[- ]ever\b|\bfirst in (the )?(field|industry|world)\b|\bnever before\b|\bunprecedented\b|\bno one (has|had)\b'
scope = ["242", "244", "246"]
severity = "high"
hint = "novelty overclaim; 'not established in [named sources] at the outset for [class of systems]'"

[[pattern]]
id = "M-W14"
regex = '\b(any|all|every) (system|platform|application|deployment)s?\b|\buniversal(ly)?\b|\bgenerali[sz]es? to all\b'
scope = ["246"]
severity = "med"
hint = "universalizes beyond what was tested; name the class of systems and the tested bounds"

[[pattern]]
id = "M-W15"
regex = '\bour (architecture|platform|system|technology base|knowledge|understanding|environment|implementation|constraints)\b|\badvanced our\b|\bin this (architecture|environment)\b|\bfor our architecture\b'
scope = ["246"]
severity = "high"
hint = "company-scoped; phrase the advancement for a class of systems"

[[pattern]]
id = "M-W16"
regex = '\b(held|without loss|parity|validated|proven|proved|guarantee[sd]?|fully autonomous)\b'
scope = ["244", "246"]
severity = "med"
hint = "status overstatement; give the measured result and its acceptance criterion"

[[pattern]]
id = "M-W17"
regex = '\bin production\b|\bproduction (use|traffic|data|failures?)\b|\blive (customers|traffic)\b|\bdeployed to production\b'
scope = ["244", "246"]
severity = "med"
hint = "check accuracy and the commercial-production exclusion; state the real environment"

[[pattern]]
id = "M-W18"
regex = '\bprompt (engineering|tuning|variations?|phrasing|iteration)\b|\biterat(ed|ing) on (the )?(prompts?|phrasing)\b|\btried (different|several|multiple) (prompts|models)\b|\bmodel (selection|choice)\b|\bswitched models\b'
scope = ["242", "244", "246"]
severity = "high"
hint = "reported AI/ML disqualifier; frame the uncertainty at the system level"

[[pattern]]
id = "M-W19"
regex = '\bwill\b|\bfuture (work|investigation)\b|\bnext phase\b|\bplanned\b|\broadmap\b|\bnot tested within\b'
scope = ["244", "246"]
severity = "med"
hint = "forward-looking content is not work performed; delete"

[[pattern]]
id = "M-W20"
regex = '^(During the course of|In|Throughout) the (tax|fiscal) year,? (we|the team) (executed|conducted|performed)'
scope = ["244"]
severity = "soft"
hint = "boilerplate opener; keep at most one sentence, ideally carrying the contractor statement"

[[pattern]]
id = "M-W21"
regex = '\bbest practices?\b|\bstandard practices?\b|\bwell[- ]known\b|\btextbook\b'
scope = ["246"]
severity = "med"
hint = "known practice claimed as an advancement; state what standard practice did not predict"

[[pattern]]
id = "M-W22"
regex = '\b(resolve|address|overcome) (the )?(new )?(technological )?uncertainties that (emerged|arose)\b'
scope = ["242", "244", "246"]
severity = "low"
hint = "circular; state the uncertainty itself"

[[pattern]]
id = "M-W23"
regex = '\bdrove advancement\b|\bgained new knowledge\b|\bsignificant(ly)? advanc\w*|\bbreakthrough\b|\bsuccessfully\b'
scope = ["242"]
severity = "med"
hint = "Line 242 describes what was unknown, not achievements"

[[pattern]]
id = "M-W24"
regex = '\bnaive\b|\bhacky\b|\bsimply\b|\bjust\b'
scope = ["242", "244", "246"]
severity = "low"
hint = "informal; use the precise term"

[[pattern]]
id = "M-W25"
regex = '\bcontext rot\b|\bSOTA\b'
scope = ["242", "244", "246"]
severity = "med"
hint = "community slang; use the established term"

[[pattern]]
id = "M-W26"
regex = '\b(found|discovered)\b'
scope = ["246"]
severity = "soft"
hint = "optional: 'determined that', 'established that'"

[[pattern]]
id = "M-L13"
regex = '\b\d{1,2}/50\b|\baudit score\b|\brisk (level|rating)\b|\bself-assess\w*|\bready for submission\b'
scope = ["242", "244", "246", "title"]
severity = "high"
hint = "internal rubric language has no CRA status; keep it in working papers"

[[pattern]]
id = "M-S01"
regex = '^At [A-Z][\w&.]*( [A-Z][\w&.]*)* we\b'
case_sensitive = true
scope = ["242"]
severity = "med"
hint = "first-person company intro; '[Company] develops ...'"

[[pattern]]
id = "M-S02"
regex = '(?s)\A(?=.*\bwe\b)(?=.*\bthe team\b)'
scope = ["242", "244", "246"]
severity = "low"
hint = "two voices in one line; pick one ('we' or 'the team')"

[[pattern]]
id = "M-S03"
regex = '\bwe (develop|build|create|will|are)\b|\b(advances|achieves)\b'
scope = ["244", "246"]
severity = "med"
hint = "use past tense for the work performed"

[[pattern]]
id = "M-S04"
regex = '\b(can|could|may|might|potentially|possibly|not necessarily|appears? to)\b'
scope = ["246"]
severity = "med"
hint = "hedged finding; make a definite statement bounded by the tested conditions"

[[pattern]]
id = "M-S05"
regex = '\b(llm|api|json|sql|graphql|ai|cms|url)s?\b'
case_sensitive = true
scope = ["242", "244", "246"]
severity = "low"
hint = "write acronyms in upper case"

[[pattern]]
id = "M-S06"
regex = '\b(?!and/or\b)[A-Za-z][\w-]*/[A-Za-z][\w-]*\b'
exclude = 'https?://'
scope = ["242", "244", "246"]
severity = "low"
hint = "note-style slash; write 'X and Y' or 'X or Y'"

[[pattern]]
id = "M-S07"
regex = '\([^)]{3,}\)|(^|\s)\(?\d\)\s'
scope = ["242", "244", "246"]
severity = "soft"
hint = "integrate parenthetical asides and inline 1) 2) lists into prose"

[[pattern]]
id = "M-S08"
regex = '\b\d+\+'
scope = ["242", "244", "246"]
severity = "med"
hint = "open-ended count; give the exact count or 'approximately N'"

[[pattern]]
id = "M-S09"
regex = '["“][^"“”]{4,}["”]'
scope = ["242", "244", "246"]
severity = "med"
hint = "quoted internal communication; paraphrase technically (quoted model outputs used as test evidence in 244 are fine)"

[[pattern]]
id = "M-S10"
regex = '\b(\w+)\s+\1\b|\s,\w'
scope = ["242", "244", "246"]
severity = "med"
hint = "proofing: doubled word or misplaced comma; re-run after every editor, including the accountant"

[[pattern]]
id = "M-S11"
regex = '\b(were|was) determined\b'
scope = ["246"]
severity = "low"
hint = "passive finding; 'we determined that ...'"

[[pattern]]
id = "M-S12"
regex = '\bJSON formatted\b|\bmulti model\b|\battribution preserving\b'
scope = ["242", "244", "246"]
severity = "low"
hint = "hyphenate compound modifiers"

[[pattern]]
id = "M-S14"
regex = '#\d{2,5}\b|\b[A-Z]{2,8}-\d{1,5}\b|\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b'
case_sensitive = true
scope = ["242", "244", "246"]
severity = "soft"
hint = "internal IDs (PRs, tickets, commits) belong in the evidence table, not the narrative"
```

- [ ] **Step 5: Replace `check.py` with the setup + narrative CLI**

`skills/sred/scripts/check.py`:
```python
#!/usr/bin/env python3
"""Checks that gate each phase.

  check.py setup --claim DIR [--phase N]           what onboarding still needs; exit 1 if anything blocks phase N
  check.py narrative PATH [--claim DIR] [--evidence CSV] [--patterns TOML]
                                                   lengths, do-not patterns, claim markers, Section A; exit 1 on errors
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sredlib import config, narrative, setupcheck

ORDER = {"error": 0, "warning": 1, "info": 2}


def cmd_setup(args) -> int:
    claim = Path(args.claim)
    missing, info = setupcheck.check_setup(claim)
    phase = args.phase or setupcheck.current_phase(claim)
    for line in info:
        print(line)
    for m in missing:
        print(m)
    blocking = [m for m in missing if m.phase <= phase]
    print(f"{len(missing)} missing; {len(blocking)} block phase {phase}." if missing else "Setup complete: nothing missing.")
    return 1 if blocking else 0


def print_findings(findings) -> int:
    for f in sorted(findings, key=lambda f: (ORDER[f.severity], f.where, f.rule)):
        print(f)
    errors = sum(f.severity == "error" for f in findings)
    print(f"{errors} errors, {sum(f.severity == 'warning' for f in findings)} warnings")
    return 1 if errors else 0


def cmd_narrative(args) -> int:
    path = Path(args.narrative)
    claim = Path(args.claim) if args.claim else path.resolve().parents[2]
    cfg = config.load_config(claim / "sred.toml")
    ev_path = Path(args.evidence) if args.evidence else path.parent / "evidence_table.csv"
    evidence = list(csv.DictReader(ev_path.open(newline="", encoding="utf-8"))) if ev_path.exists() else []
    n = narrative.parse_narrative(path.read_text(encoding="utf-8"))
    findings, counts = narrative.check_narrative(n, evidence, cfg, narrative.load_patterns(args.patterns))
    lim = config.limits(cfg)
    print(f"{n.project or path}: limit mode = {lim['mode']}")
    for line, (w, l) in counts.items():
        print(f"  Line {line}: {w}/{lim['words'][line]} words, {l}/{lim['lines'][line]} lines")
    return print_findings(findings)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="what onboarding still needs")
    s.add_argument("--claim", default=".")
    s.add_argument("--phase", type=int)
    s.set_defaults(func=cmd_setup)
    nar = sub.add_parser("narrative", help="check one draft/<P>/narrative.md")
    nar.add_argument("narrative")
    nar.add_argument("--claim")
    nar.add_argument("--evidence")
    nar.add_argument("--patterns")
    nar.set_defaults(func=cmd_narrative)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_narrative.py tests/test_setupcheck.py -v`
Expected: PASS (18 tests).

- [ ] **Step 7: Commit**

```bash
git add skills/sred/scripts/sredlib/narrative.py skills/sred/references/do-not-patterns.toml skills/sred/scripts/check.py tests/test_narrative.py
git commit -m "feat: add check.py narrative with mechanical do-not patterns

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 13: Time basis, part 1: classification ledger, evidence-days, gap months

**Files:**
- Create: `skills/sred/scripts/sredlib/timebasis.py`
- Test: `tests/test_timebasis_ledger.py`

**Interfaces:**
- Consumes: `activity.split`.
- Produces (used by Task 14):
  - Constants `SCENARIOS` (`{"conservative": {"direct"}, "balanced": {"direct", "support"}, "maximum": {"direct", "support", "borderline"}}`), `LEVELS`, `LEDGER_COLUMNS`, `OVERRIDE_COLUMNS`, `TIME_BASIS_COLUMNS`, `GAP_COLUMNS`, `SUMMARY_COLUMNS`; `TimeBasisError(ValueError)`.
  - `_read_csv(path) -> list[dict]` (empty list if missing); `_write_csv(path, columns, rows)`.
  - `match_rule(rule, row) -> bool`; `classify(rows, rules, overrides, threshold) -> list[dict]` (ledger rows with `LEDGER_COLUMNS`; skips `bot` and `unmatched:` people). Precedence: claimant override > first matching rule > Claude override > unclassified.
  - `monthly(ledger, scenario, kind_weights) -> dict[(person, "YYYY-MM"), {"evidence_days": int, "sred_days": float, "by_project": dict}]`.
  - `month_range(start, end) -> list[str]`; `employed_months(person_row, fy) -> list[str]`.
  - `merge_gaps(existing_rows, gaps: list[tuple[person, month]]) -> list[dict]`; `gap_share(gap_row, scenario) -> float` (0–1).

Rules (spec §5 Phase 6 and §12): the unit is the evidence-day; a day's weight is split across its classified items (each item weighted by `kind_weights`, default 1.0); conservative counts only `direct` and ignores `weight=summary` rows; balanced adds `support`; maximum adds `borderline`. Gap months: conservative 0; balanced uses `basis_share` only when `basis` is set and `corroborated = Y`; maximum uses `basis_share` whenever `basis` is set.

- [ ] **Step 1: Write the failing tests**

`tests/test_timebasis_ledger.py`:
```python
from datetime import date

import pytest

from sredlib.timebasis import TimeBasisError, classify, employed_months, gap_share, merge_gaps, month_range, monthly

FY = (date(2026, 8, 1), date(2027, 7, 31))
RULES = [
    {"id": "r1", "project": "P1", "level": "direct", "paths": "planner/*"},
    {"id": "r2", "project": "", "level": "none", "category": "routine", "container": "acme/website"},
]


def arow(key, person="alice", day="2026-09-02", kind="commit", container="acme/vision", paths="", tags="", title="", weight="verbatim"):
    return {"source": "gh", "key": key, "kind": kind, "person": person, "date": day, "weight": weight,
            "container": container, "paths": paths, "tags": tags, "title": title}


def override(key, level, project="P1", by="claude", conf="0.9", category=""):
    return {"source": "gh", "key": key, "project": project, "level": level, "category": category,
            "classified_by": by, "confidence": conf, "reason": "r"}


def led(key, day, project="P1", level="direct", kind="commit", weight="verbatim", person="alice"):
    return {"source": "gh", "key": key, "kind": kind, "person": person, "date": day, "weight": weight,
            "project": project if level != "none" else "", "level": level}


def test_classify_precedence_and_review_queue():
    rows = [arow("k1", paths="planner/a.py"), arow("k2", container="acme/website"), arow("k3"), arow("k4"),
            arow("k5", paths="planner/b.py"), arow("k6", person="bot"), arow("k7", person="unmatched:x"), arow("k8")]
    overrides = [override("k3", "support"), override("k4", "direct", conf="0.5"),
                 override("k5", "none", project="", by="claimant", category="routine")]
    ledger = {e["key"]: e for e in classify(rows, RULES, overrides, 0.7)}
    assert set(ledger) == {"k1", "k2", "k3", "k4", "k5", "k8"}
    assert (ledger["k1"]["project"], ledger["k1"]["level"], ledger["k1"]["classified_by"]) == ("P1", "direct", "rule:r1")
    assert (ledger["k2"]["level"], ledger["k2"]["category"], ledger["k2"]["needs_review"]) == ("none", "routine", "N")
    assert (ledger["k3"]["level"], ledger["k3"]["needs_review"]) == ("support", "N")
    assert ledger["k4"]["needs_review"] == "Y"
    assert (ledger["k5"]["level"], ledger["k5"]["classified_by"]) == ("none", "claimant")
    assert (ledger["k8"]["category"], ledger["k8"]["needs_review"]) == ("unclassified", "Y")


def test_classify_rejects_bad_levels():
    with pytest.raises(TimeBasisError, match="level"):
        classify([arow("k1")], [], [override("k1", "maybe")], 0.7)
    with pytest.raises(TimeBasisError, match="needs a project"):
        classify([arow("k1")], [], [override("k1", "direct", project="")], 0.7)


def test_monthly_splits_mixed_days_by_scenario():
    ledger = [led("a", "2026-09-02"), led("b", "2026-09-02"), led("c", "2026-09-02", level="none"), led("d", "2026-09-03", level="support")]
    cons = monthly(ledger, "conservative", {})[("alice", "2026-09")]
    bal = monthly(ledger, "balanced", {})[("alice", "2026-09")]
    assert cons["evidence_days"] == 2 and round(cons["sred_days"], 3) == 0.667
    assert round(bal["sred_days"], 3) == 1.667 and round(bal["by_project"]["P1"], 3) == 1.667


def test_summary_weight_rows_excluded_only_in_conservative():
    ledger = [led("m", "2026-09-04", kind="meeting", weight="summary")]
    assert ("alice", "2026-09") not in monthly(ledger, "conservative", {})
    assert monthly(ledger, "maximum", {})[("alice", "2026-09")]["sred_days"] == 1.0


def test_kind_weights_can_zero_out_chat():
    ledger = [led("x", "2026-09-05", kind="chat_message", level="none"), led("y", "2026-09-05")]
    assert monthly(ledger, "balanced", {"chat_message": 0.0})[("alice", "2026-09")]["sred_days"] == 1.0


def test_employed_months_and_ranges():
    assert month_range(date(2026, 11, 15), date(2027, 2, 1)) == ["2026-11", "2026-12", "2027-01", "2027-02"]
    assert len(employed_months({"start": "", "end": ""}, FY)) == 12
    assert employed_months({"start": "2026-10-15", "end": ""}, FY)[0] == "2026-10"
    assert employed_months({"start": "2025-01-01", "end": "2026-06-30"}, FY) == []


def test_gap_rows_merge_and_scenario_shares():
    existing = [
        {"person": "alice", "month": "2026-10", "basis": "design reviews", "basis_source": "calendar", "corroborated": "Y", "basis_share": "60"},
        {"person": "alice", "month": "2026-09", "basis": "stale", "basis_source": "", "corroborated": "", "basis_share": "10"},
    ]
    rows = merge_gaps(existing, [("alice", "2026-10"), ("alice", "2026-11")])
    assert [r["month"] for r in rows] == ["2026-10", "2026-11"]
    assert rows[0]["basis"] == "design reviews" and rows[1]["basis"] == ""
    corroborated, asserted = rows[0], dict(rows[0], corroborated="")
    assert gap_share(corroborated, "conservative") == 0.0
    assert gap_share(corroborated, "balanced") == 0.6 and gap_share(asserted, "balanced") == 0.0
    assert gap_share(asserted, "maximum") == 0.6
    with pytest.raises(TimeBasisError, match="basis_share"):
        gap_share(dict(rows[0], basis_share="lots"), "maximum")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_timebasis_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sredlib.timebasis'`.

- [ ] **Step 3: Implement `timebasis.py` (part 1)**

`skills/sred/scripts/sredlib/timebasis.py`:
```python
"""Evidence-day time basis: ledger, monthly shares, gap months, person summary, labour summary."""
from __future__ import annotations

import csv
import fnmatch
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import activity

SCENARIOS = {"conservative": {"direct"}, "balanced": {"direct", "support"}, "maximum": {"direct", "support", "borderline"}}
LEVELS = {"direct", "support", "borderline", "none"}
LEDGER_COLUMNS = ["source", "key", "kind", "person", "date", "weight", "container", "title", "project", "level",
                  "category", "classified_by", "confidence", "reason", "needs_review"]
OVERRIDE_COLUMNS = ["source", "key", "project", "level", "category", "classified_by", "confidence", "reason"]
TIME_BASIS_COLUMNS = ["person", "month", "evidence_days", "sred_days", "share", "by_project", "gap"]
GAP_COLUMNS = ["person", "month", "basis", "basis_source", "corroborated", "basis_share"]
SUMMARY_COLUMNS = ["person", "name", "classification", "months_employed", "months_with_evidence", "gap_months",
                   "evidence_share", "proposed_pct", "confirmed_pct", "basis", "override_reason", "flags"]


class TimeBasisError(ValueError):
    pass


def _read_csv(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})


def match_rule(rule: dict, row: dict) -> bool:
    """Every condition the rule sets must hold. Globs use fnmatch (`*` also matches `/`)."""
    for f in ("source", "container"):
        if rule.get(f) and not fnmatch.fnmatchcase(row.get(f, ""), rule[f]):
            return False
    if rule.get("kind") and row.get("kind") != rule["kind"]:
        return False
    if rule.get("tags") and not any(fnmatch.fnmatchcase(t, rule["tags"]) for t in activity.split(row.get("tags", ""))):
        return False
    if rule.get("paths") and not any(fnmatch.fnmatchcase(p, rule["paths"]) for p in activity.split(row.get("paths", ""))):
        return False
    if rule.get("title") and not re.search(rule["title"], row.get("title", "")):
        return False
    return True


def classify(rows: list[dict], rules: list[dict], overrides: list[dict], threshold: float) -> list[dict]:
    by_key = {(o["source"], o["key"]): o for o in overrides}
    ledger = []
    for r in rows:
        if r["person"] == "bot" or r["person"].startswith("unmatched:"):
            continue
        where = f"{r['source']}:{r['key']}"
        o = by_key.get((r["source"], r["key"]))
        rule = next((ru for ru in rules if match_rule(ru, r)), None)
        if o and o.get("classified_by") == "claimant":
            src, by, conf = o, "claimant", 1.0
        elif rule:
            src, by, conf = rule, f"rule:{rule.get('id', '?')}", 1.0
        elif o:
            src, by, conf = o, o.get("classified_by") or "claude", float(o.get("confidence") or 0)
        else:
            src, by, conf = {"level": "none", "category": "unclassified"}, "", 0.0
        level = src.get("level") or "none"
        if level not in LEVELS:
            raise TimeBasisError(f"{where}: level must be one of {sorted(LEVELS)}, got {level!r}")
        project = "" if level == "none" else (src.get("project") or "")
        if level != "none" and project in ("", "none"):
            raise TimeBasisError(f"{where}: level {level!r} needs a project")
        needs = by == "" or (by == "claude" and conf < threshold)
        entry = {k: r.get(k, "") for k in ("source", "key", "kind", "person", "date", "weight", "container", "title")}
        entry.update(project=project, level=level, category=src.get("category", "") if level == "none" else "",
                     classified_by=by, confidence=f"{conf:.2f}", reason=src.get("reason", ""), needs_review="Y" if needs else "N")
        ledger.append(entry)
    return ledger


def _counts_as_evidence(e: dict, scenario: str) -> bool:
    return scenario != "conservative" or e["weight"] == "verbatim"


def _counts_as_sred(e: dict, scenario: str) -> bool:
    return e["level"] in SCENARIOS[scenario] and bool(e["project"])


def monthly(ledger: list[dict], scenario: str, kind_weights: dict[str, float]) -> dict:
    days = defaultdict(lambda: {"total": 0.0, "sred": 0.0, "proj": defaultdict(float)})
    for e in ledger:
        if not _counts_as_evidence(e, scenario):
            continue
        w = kind_weights.get(e["kind"], 1.0)
        d = days[(e["person"], e["date"])]
        d["total"] += w
        if _counts_as_sred(e, scenario):
            d["sred"] += w
            d["proj"][e["project"]] += w
    months = defaultdict(lambda: {"evidence_days": 0, "sred_days": 0.0, "by_project": defaultdict(float)})
    for (person, day), d in sorted(days.items()):
        if d["total"] <= 0:
            continue
        m = months[(person, day[:7])]
        m["evidence_days"] += 1
        m["sred_days"] += d["sred"] / d["total"]
        for p, w in d["proj"].items():
            m["by_project"][p] += w / d["total"]
    return dict(months)


def month_range(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def employed_months(person: dict, fy: tuple[date, date]) -> list[str]:
    start, end = fy
    s = max(date.fromisoformat(person["start"]) if person.get("start") else start, start)
    e = min(date.fromisoformat(person["end"]) if person.get("end") else end, end)
    return month_range(s, e) if s <= e else []


def merge_gaps(existing: list[dict], gaps: list[tuple[str, str]]) -> list[dict]:
    keep = {(g["person"], g["month"]): g for g in existing}
    blank = {"basis": "", "basis_source": "", "corroborated": "", "basis_share": ""}
    return [keep.get((person, month)) or {"person": person, "month": month, **blank} for person, month in gaps]


def gap_share(g: dict, scenario: str) -> float:
    if scenario == "conservative" or not (g.get("basis") or "").strip():
        return 0.0
    if scenario == "balanced" and (g.get("corroborated") or "").strip().upper() != "Y":
        return 0.0
    try:
        return max(0.0, min(100.0, float(g.get("basis_share") or 0))) / 100
    except ValueError as exc:
        raise TimeBasisError(f"gap_months.csv {g['person']} {g['month']}: basis_share must be a number 0-100") from exc
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_timebasis_ledger.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/sred/scripts/sredlib/timebasis.py tests/test_timebasis_ledger.py
git commit -m "feat: add classification ledger and evidence-day time basis

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Time basis, part 2: person summary, labour summary, scenarios, `time_basis.py`

**Files:**
- Modify: `skills/sred/scripts/sredlib/timebasis.py` (append)
- Create: `skills/sred/templates/labour-summary-columns.csv`, `skills/sred/scripts/time_basis.py`
- Test: `tests/test_timebasis_run.py`

**Interfaces:**
- Consumes: Task 13 functions; `activity.read_rows`; `config.*`; `roster.load_roster`.
- Produces:
  - `summarize(roster, months, gap_rows, fy, scenario, previous, use_confirmed=True) -> list[dict]` (rows with `SUMMARY_COLUMNS`, in roster order; keeps `confirmed_pct`, `basis`, `override_reason` from `previous`).
  - Flags: `UNCONFIRMED`, `IDENTICAL_PCT`, `OVER_90_NO_BASIS`, `OUTSIDE_CANADA`, `DUAL_ROLE`, `OVERRIDE_NO_REASON` (|confirmed − proposed| > 15 with no reason), `THIN_EVIDENCE` (fewer than 3 months with evidence).
  - `money(v) -> Decimal`; `q2(d) -> Decimal`; `load_columns(cfg) -> list[tuple[column, field]]`; `labour_summary(roster, summary, columns) -> list[list[str]]` (header, one row per person, TOTAL); `scenario_totals(roster, summary, cfg) -> dict`; `write_checks(path, cfg, roster, summary, ledger, scenario, totals)`.
  - `run(claim_dir, scenario=None, preliminary=False) -> dict` (keys `scenario`, `out_dir`, `people`, `review_queue`, plus the scenario totals).
  - CLI: `time_basis.py --claim DIR [--scenario …] [--preliminary]` (exit 2 with `ERROR:` on bad input).
  - Outputs in `financials/`: `activity_ledger.csv`, `review_queue.csv`, `time_basis.csv`, `gap_months.csv`, `person_summary.csv`, `labour_summary.csv`, `financial_checks.md`, `scenario_<name>.json`. With `--preliminary` the same minus `gap_months.csv` and `labour_summary.csv`, under `scope/preliminary/<scenario>/`.

Amounts: employees SR&ED hours = paid hours × %, SR&ED wages = earned wages × %; contractors SR&ED amount = earned amount × % (no hours). Contractors' invoiced amounts live in the same roster columns: `wages_paid` (paid in the fiscal year) and `wages_earned` (for work done in the fiscal year), matching the accountant's format. Money is rounded half-up to cents. The TOTAL row's SR&ED % is SR&ED wages ÷ earned wages of everyone claimed above 0%. ITC estimate = (employee SR&ED wages × (1 + `proxy_rate`) + arm's-length, in-Canada contractor SR&ED amount × `contract_rate`) × `itc_rate`, written only when all three rates are set.

- [ ] **Step 1: Write the failing tests**

`tests/test_timebasis_run.py`:
```python
import csv
from datetime import date, datetime

import time_basis
from sredlib import activity, timebasis
from sredlib.roster import ROSTER_COLUMNS

FY = (date(2026, 8, 1), date(2027, 7, 31))


def person(**kw):
    base = {c: "" for c in ROSTER_COLUMNS}
    base.update(kw)
    return base


ALICE = person(id="alice", name="Alice Chen", classification="employee", in_canada="Y", specified_employee="N",
               aliases="email:alice@acme.test", paid_hours="2080", wages_paid="100000.00", wages_earned="100000.00")
CAROL = person(id="carol", name="Carol Diaz", classification="contractor", start="2026-09-01", end="2026-10-31",
               in_canada="Y", specified_employee="N", aliases="email:carol@diaz.test", wages_paid="50000.10",
               wages_earned="50000.10", arms_length="Y", contract_provided="Y", sred_in_contract="N")
MONTHS = {("alice", "2026-09"): {"evidence_days": 4, "sred_days": 3.0, "by_project": {}},
          ("carol", "2026-09"): {"evidence_days": 2, "sred_days": 2.0, "by_project": {}},
          ("carol", "2026-10"): {"evidence_days": 1, "sred_days": 0.0, "by_project": {}}}
GAPS = [
    {"person": "alice", "month": "2026-10", "basis": "design reviews", "basis_source": "calendar", "corroborated": "Y", "basis_share": "60"},
    {"person": "alice", "month": "2026-11", "basis": "whiteboard sessions", "basis_source": "", "corroborated": "", "basis_share": "50"},
]


def by_person(summary):
    return {s["person"]: s for s in summary}


def test_proposed_pct_depends_on_scenario():
    for scenario, expected in (("conservative", "6.25"), ("balanced", "11.25"), ("maximum", "15.42")):
        s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, scenario, []))
        assert s["alice"]["proposed_pct"] == expected
    s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, "balanced", []))
    assert (s["carol"]["months_employed"], s["carol"]["proposed_pct"], s["carol"]["evidence_share"]) == (2, "50.00", "66.67")
    assert s["alice"]["gap_months"] == 11 and "THIN_EVIDENCE" in s["carol"]["flags"]


def test_claimant_edits_survive_and_drive_flags():
    previous = [{"person": "alice", "confirmed_pct": "75%", "basis": "", "override_reason": ""},
                {"person": "carol", "confirmed_pct": "95", "basis": "", "override_reason": "contract scope"}]
    s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, "balanced", previous))
    assert s["alice"]["confirmed_pct"] == "75%"
    assert "OVERRIDE_NO_REASON" in s["alice"]["flags"] and "UNCONFIRMED" not in s["alice"]["flags"]
    assert "OVER_90_NO_BASIS" in s["carol"]["flags"] and "OVERRIDE_NO_REASON" not in s["carol"]["flags"]


def test_identical_dual_role_and_outside_canada_flags():
    bob_emp = person(id="bob", name="Bob Roy", classification="employee", in_canada="Y")
    bob_con = person(id="bob-co", name="Bob Roy", classification="contractor", in_canada="N")
    months = {("bob", "2026-09"): {"evidence_days": 1, "sred_days": 1.0, "by_project": {}},
              ("bob-co", "2026-09"): {"evidence_days": 1, "sred_days": 1.0, "by_project": {}}}
    previous = [{"person": "bob", "confirmed_pct": "80"}, {"person": "bob-co", "confirmed_pct": "80"}]
    s = by_person(timebasis.summarize([bob_emp, bob_con], months, [], FY, "balanced", previous))
    for flag in ("IDENTICAL_PCT", "DUAL_ROLE"):
        assert flag in s["bob"]["flags"] and flag in s["bob-co"]["flags"]
    assert "OUTSIDE_CANADA" in s["bob-co"]["flags"]


def test_labour_summary_amounts_and_weighted_total():
    summary = [{"person": "alice", "confirmed_pct": "75", "proposed_pct": "6.25", "basis": "weekly experiment reviews"},
               {"person": "carol", "confirmed_pct": "33.33", "proposed_pct": "50.00", "basis": ""}]
    rows = timebasis.labour_summary([ALICE, CAROL], summary, timebasis.load_columns({"_dir": "."}))
    col = {name: i for i, name in enumerate(rows[0])}
    alice, carol, total = rows[1], rows[2], rows[3]
    assert (alice[col["SRED %"]], alice[col["SRED Hours"]], alice[col["SRED Wages"]]) == ("75.00%", "1560.00", "75000.00")
    assert alice[col["Classification"]] == "Employee" and alice[col["Basis"]] == "weekly experiment reviews"
    assert (carol[col["SRED Hours"]], carol[col["SRED Wages"]], carol[col["Classification"]]) == ("", "16665.03", "Subcontractor")
    assert (total[col["Name"]], total[col["Total Wages (Earned FY)"]], total[col["SRED Wages"]], total[col["SRED %"]]) == \
        ("TOTAL", "150000.10", "91665.03", "61.11%")


def test_scenario_totals_and_itc_estimate():
    summary = [{"person": "alice", "confirmed_pct": "75", "proposed_pct": "6.25"}, {"person": "carol", "confirmed_pct": "33.33", "proposed_pct": "50"}]
    totals = timebasis.scenario_totals([ALICE, CAROL], summary, {"rates": {"itc_rate": 0.35, "proxy_rate": 0.55, "contract_rate": 0.80}})
    assert totals["employee_sred_wages"] == "75000.00" and totals["contractor_sred_amount"] == "16665.03"
    assert totals["itc_estimate"] == "45353.71" and "Estimate only" in totals["itc_note"]
    assert "itc_estimate" not in timebasis.scenario_totals([ALICE, CAROL], summary, {})


CLAIM_TOML = """
[claim]
scenario = "balanced"

[payroll]
total_wages_earned = 150000.00

[[classification.rules]]
id = "r1"
project = "P1"
level = "direct"
paths = "planner/*"
"""
OUTPUTS = ["activity_ledger.csv", "review_queue.csv", "time_basis.csv", "gap_months.csv", "person_summary.csv",
           "labour_summary.csv", "financial_checks.md", "scenario_balanced.json"]


def commit(key, who, day, path):
    return activity.make_row(source="gh", key=key, kind="commit", person=who, actor_raw=who,
                             ts=datetime.fromisoformat(f"{day}T12:00:00+00:00"), paths=[path], raw_path="evidence/raw/gh/x.json")


def setup_claim(make_claim):
    claim = make_claim(CLAIM_TOML, roster=[ALICE, CAROL])
    activity.write_rows(claim / "evidence/index/activity.csv", [
        commit("a" * 40, "alice", "2026-09-02", "planner/a.py"),
        commit("b" * 40, "alice", "2026-10-05", "web/x.py"),
        commit("c" * 40, "carol", "2026-09-10", "planner/b.py"),
    ])
    return claim


def test_run_writes_outputs_preserves_confirmations_and_is_deterministic(make_claim):
    claim = setup_claim(make_claim)
    fin = claim / "financials"
    result = timebasis.run(claim)
    assert result["scenario"] == "balanced" and result["review_queue"] == 1
    assert all((fin / name).exists() for name in OUTPUTS)
    assert "MISMATCH" in (fin / "financial_checks.md").read_text()
    first = {name: (fin / name).read_bytes() for name in OUTPUTS}
    timebasis.run(claim)
    assert {name: (fin / name).read_bytes() for name in OUTPUTS} == first
    rows = list(csv.DictReader((fin / "person_summary.csv").open()))
    rows[0]["confirmed_pct"], rows[0]["basis"] = "75%", "weekly experiment reviews"
    with (fin / "person_summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=timebasis.SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    timebasis.run(claim)
    again = {r["person"]: r for r in csv.DictReader((fin / "person_summary.csv").open())}
    assert again["alice"]["confirmed_pct"] == "75%" and again["alice"]["basis"] == "weekly experiment reviews"
    labour = list(csv.reader((fin / "labour_summary.csv").open()))
    assert labour[1][labour[0].index("SRED %")] == "75.00%"


def test_preliminary_run_writes_to_scope_and_leaves_financials_alone(make_claim, capsys):
    claim = setup_claim(make_claim)
    assert time_basis.main(["--claim", str(claim), "--scenario", "maximum", "--preliminary"]) == 0
    assert (claim / "scope/preliminary/maximum/person_summary.csv").exists()
    assert (claim / "scope/preliminary/maximum/scenario_maximum.json").exists()
    assert not (claim / "financials/labour_summary.csv").exists()
    assert "employee_sred_wages" in capsys.readouterr().out


def test_cli_errors_are_clear(make_claim, capsys):
    claim = make_claim("", roster=[ALICE])
    assert time_basis.main(["--claim", str(claim)]) == 2
    assert "scenario must be one of" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_timebasis_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'time_basis'` / `AttributeError: … 'summarize'`.

- [ ] **Step 3: Append part 2 to `timebasis.py`**

Add to the imports at the top of `skills/sred/scripts/sredlib/timebasis.py`:
```python
import json
from decimal import ROUND_HALF_UP, Decimal

from . import config
from .roster import load_roster
```

Append to the end of `skills/sred/scripts/sredlib/timebasis.py`:
```python
DEFAULT_COLUMNS_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "labour-summary-columns.csv"
MONEY_FIELDS = ("paid_hours", "wages_paid", "wages_earned", "bonus", "taxable_benefits", "pay_in_lieu")


def _pct(v):
    v = (v or "").strip().rstrip("%").strip()
    return float(v) if v else None


def _effective(s: dict) -> float:
    c = _pct(s.get("confirmed_pct"))
    return c if c is not None else float(s.get("proposed_pct") or 0)


def summarize(roster, months, gap_rows, fy, scenario, previous, use_confirmed: bool = True) -> list[dict]:
    gap_by = {(g["person"], g["month"]): g for g in gap_rows}
    prev = {p["person"]: p for p in previous} if use_confirmed else {}
    out = []
    for r in roster:
        pid = r["id"]
        emp = employed_months(r, fy)
        shares, ev_days, sred_days, with_ev, gap_n = [], 0, 0.0, 0, 0
        for month in emp:
            m = months.get((pid, month))
            if m and m["evidence_days"]:
                shares.append(m["sred_days"] / m["evidence_days"])
                with_ev += 1
                ev_days += m["evidence_days"]
                sred_days += m["sred_days"]
            else:
                gap_n += 1
                shares.append(gap_share(gap_by.get((pid, month), {}), scenario))
        proposed = round(100 * sum(shares) / len(shares), 2) if shares else 0.0
        p = prev.get(pid, {})
        out.append({
            "person": pid, "name": r["name"], "classification": r["classification"], "months_employed": len(emp),
            "months_with_evidence": with_ev, "gap_months": gap_n,
            "evidence_share": f"{(100 * sred_days / ev_days) if ev_days else 0:.2f}", "proposed_pct": f"{proposed:.2f}",
            "confirmed_pct": p.get("confirmed_pct", "") or "", "basis": p.get("basis", "") or "",
            "override_reason": p.get("override_reason", "") or "", "flags": "",
        })
    _flag(out, roster)
    return out


def _flag(summary: list[dict], roster: list[dict]) -> None:
    by_id = {r["id"]: r for r in roster}
    classes = defaultdict(set)
    for r in roster:
        classes[r["name"].strip().lower()].add(r["classification"])
    claimed = [_effective(s) for s in summary if _effective(s) > 0]
    identical = len(claimed) >= 2 and len(set(claimed)) == 1
    for s in summary:
        r, pct, flags = by_id[s["person"]], _effective(s), []
        conf = _pct(s["confirmed_pct"])
        if conf is None:
            flags.append("UNCONFIRMED")
        if identical and pct > 0:
            flags.append("IDENTICAL_PCT")
        if pct > 90 and not s["basis"].strip():
            flags.append("OVER_90_NO_BASIS")
        if r.get("in_canada") == "N" and pct > 0:
            flags.append("OUTSIDE_CANADA")
        if len(classes[r["name"].strip().lower()]) > 1:
            flags.append("DUAL_ROLE")
        if conf is not None and abs(conf - float(s["proposed_pct"])) > 15 and not s["override_reason"].strip():
            flags.append("OVERRIDE_NO_REASON")
        if pct > 0 and s["months_with_evidence"] < 3:
            flags.append("THIN_EVIDENCE")
        s["flags"] = ";".join(flags)


def money(v) -> Decimal:
    text = str(v or "").replace(",", "").replace("$", "").strip()
    return Decimal(text) if text else Decimal("0")


def q2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_columns(cfg: dict) -> list[tuple[str, str]]:
    custom = (cfg.get("preparer") or {}).get("labour_template")
    path = config.resolve_path(cfg, custom) if custom else DEFAULT_COLUMNS_PATH
    return [(r["column"], r["field"]) for r in _read_csv(path)]


def labour_summary(roster, summary, columns) -> list[list[str]]:
    by_id = {s["person"]: s for s in summary}
    rows = [[c for c, _ in columns]]
    totals = defaultdict(lambda: Decimal("0"))
    for r in roster:
        s = by_id[r["id"]]
        conf = _pct(s.get("confirmed_pct"))
        pct = Decimal(str(_effective(s)))
        frac = pct / 100
        employee = r["classification"] == "employee"
        earned = money(r["wages_earned"])
        sred_hours = q2(money(r["paid_hours"]) * frac) if employee else None
        sred_wages = q2(earned * frac)
        basis = (s.get("basis") or "").strip() or ("" if conf is not None else "PROPOSED - not confirmed")
        fields = {**r, "classification_label": "Employee" if employee else "Subcontractor", "sred_pct": f"{q2(pct)}%",
                  "sred_eligible": "TRUE" if pct > 0 else "FALSE", "sred_hours": "" if sred_hours is None else str(sred_hours),
                  "sred_wages": str(sred_wages), "basis": basis}
        rows.append([str(fields.get(f, "")) for _, f in columns])
        for f in MONEY_FIELDS:
            totals[f] += money(r.get(f, ""))
        totals["sred_hours"] += sred_hours or Decimal("0")
        totals["sred_wages"] += sred_wages
        if pct > 0:
            totals["eligible_earned"] += earned
    weighted = q2(100 * totals["sred_wages"] / totals["eligible_earned"]) if totals["eligible_earned"] else Decimal("0.00")
    total = {"name": "TOTAL", "sred_pct": f"{weighted}%", "basis": "SRED % weighted by earned wages of people claimed",
             **{f: str(q2(totals[f])) for f in MONEY_FIELDS + ("sred_hours", "sred_wages")}}
    rows.append([total.get(f, "") for _, f in columns])
    return rows


def scenario_totals(roster, summary, cfg) -> dict:
    by_id = {s["person"]: s for s in summary}
    emp, con = Decimal("0"), Decimal("0")
    for r in roster:
        amount = q2(money(r["wages_earned"]) * Decimal(str(_effective(by_id[r["id"]]))) / 100)
        if r["classification"] == "employee":
            emp += amount
        elif r.get("arms_length") == "Y" and r.get("in_canada") == "Y":
            con += amount
    out = {"employee_sred_wages": str(q2(emp)), "contractor_sred_amount": str(q2(con))}
    rates = config.rates(cfg) or {}
    if {"itc_rate", "proxy_rate", "contract_rate"} <= rates.keys():
        est = (emp * (1 + Decimal(str(rates["proxy_rate"]))) + con * Decimal(str(rates["contract_rate"]))) * Decimal(str(rates["itc_rate"]))
        out["itc_estimate"] = str(q2(est))
        out["itc_note"] = "Estimate only: ignores expenditure limits, specified-employee caps and proxy-method salary-base rules."
    return out


def write_checks(path, cfg, roster, summary, ledger, scenario, totals) -> None:
    payroll = (cfg.get("payroll") or {}).get("total_wages_earned")
    roster_total = q2(sum((money(r["wages_earned"]) for r in roster), Decimal("0")))
    lines = [f"# Financial checks ({scenario})", ""]
    if not payroll:
        lines.append("- Payroll reconciliation: NOT RUN (set payroll.total_wages_earned in sred.toml)")
    else:
        expected = q2(Decimal(str(payroll)))
        status = "OK" if abs(expected - roster_total) <= Decimal("0.01") else "MISMATCH"
        lines.append(f"- Payroll reconciliation: {status} (payroll {expected}, roster {roster_total})")
    unconfirmed = [s["person"] for s in summary if _pct(s["confirmed_pct"]) is None]
    lines.append(f"- Unconfirmed percentages: {len(unconfirmed)}" + (f" ({', '.join(unconfirmed)})" if unconfirmed else ""))
    lines.append(f"- Review queue: {sum(e['needs_review'] == 'Y' for e in ledger)} ledger rows need a decision (review_queue.csv)")
    lines += ["", "## Flags", ""]
    lines += [f"- {s['person']}: {s['flags']}" for s in summary if s["flags"]] or ["- none"]
    lines += ["", "## Scenario totals", ""] + [f"- {k}: {v}" for k, v in totals.items()]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(claim_dir: Path, scenario: str | None = None, preliminary: bool = False) -> dict:
    claim_dir = Path(claim_dir)
    cfg = config.load_config(claim_dir / "sred.toml")
    scenario = scenario or (cfg.get("claim") or {}).get("scenario")
    if scenario not in SCENARIOS:
        raise TimeBasisError(f"scenario must be one of {sorted(SCENARIOS)} (pass --scenario or set claim.scenario)")
    fy = config.fiscal_year(cfg)
    act_path = claim_dir / "evidence" / "index" / "activity.csv"
    if not act_path.exists():
        raise TimeBasisError("evidence/index/activity.csv not found: run index.py build first")
    _, rows = activity.read_rows(act_path)
    roster = load_roster(claim_dir / "roster.csv")
    fin = claim_dir / "financials"
    out_dir = claim_dir / "scope" / "preliminary" / scenario if preliminary else fin
    cls = config.classification(cfg)
    ledger = sorted(classify(rows, cls["rules"], _read_csv(fin / "classification_overrides.csv"), cls["review_threshold"]),
                    key=lambda e: (e["date"], e["source"], e["key"]))
    months = monthly(ledger, scenario, config.kind_weights(cfg))
    gaps = [(r["id"], m) for r in roster for m in employed_months(r, fy) if not (months.get((r["id"], m)) or {}).get("evidence_days")]
    gap_rows = merge_gaps(_read_csv(fin / "gap_months.csv"), gaps)
    previous = [] if preliminary else _read_csv(fin / "person_summary.csv")
    summary = summarize(roster, months, gap_rows, fy, scenario, previous, use_confirmed=not preliminary)
    _write_csv(out_dir / "activity_ledger.csv", LEDGER_COLUMNS, ledger)
    _write_csv(out_dir / "review_queue.csv", LEDGER_COLUMNS, [e for e in ledger if e["needs_review"] == "Y"])
    gap_set, tb = set(gaps), []
    for r in roster:
        for m in employed_months(r, fy):
            d = months.get((r["id"], m)) or {}
            ev, sd = d.get("evidence_days", 0), d.get("sred_days", 0.0)
            tb.append({"person": r["id"], "month": m, "evidence_days": ev, "sred_days": f"{sd:.2f}",
                       "share": f"{(sd / ev) if ev else 0:.4f}",
                       "by_project": ";".join(f"{p}:{v:.2f}" for p, v in sorted(d.get("by_project", {}).items())),
                       "gap": "Y" if (r["id"], m) in gap_set else "N"})
    _write_csv(out_dir / "time_basis.csv", TIME_BASIS_COLUMNS, tb)
    _write_csv(out_dir / "person_summary.csv", SUMMARY_COLUMNS, summary)
    totals = scenario_totals(roster, summary, cfg)
    (out_dir / f"scenario_{scenario}.json").write_text(json.dumps({"scenario": scenario, **totals}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not preliminary:
        _write_csv(fin / "gap_months.csv", GAP_COLUMNS, gap_rows)
        with (fin / "labour_summary.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh, lineterminator="\n").writerows(labour_summary(roster, summary, load_columns(cfg)))
    write_checks(out_dir / "financial_checks.md", cfg, roster, summary, ledger, scenario, totals)
    return {"scenario": scenario, "out_dir": str(out_dir), "people": len(summary),
            "review_queue": sum(e["needs_review"] == "Y" for e in ledger), **totals}
```

- [ ] **Step 4: Add the labour summary column template and the CLI**

`skills/sred/templates/labour-summary-columns.csv`:
```
column,field
Name,name
Company (if appl),company
Classification,classification_label
Employees in BC/Can,in_canada
10% S/H,specified_employee
Title/Role,title
Street Address,street
City,city
Province,province
Postal,postal
Country,country
Total Hours,paid_hours
Total Wages (Paid FY),wages_paid
Total Wages (Earned FY),wages_earned
Bonus,bonus
TX Benefits,taxable_benefits
Pay in Lieu,pay_in_lieu
SR&ED Eligible,sred_eligible
SR&ED in Contract,sred_in_contract
Contract Provided,contract_provided
SRED %,sred_pct
SRED Hours,sred_hours
SRED Wages,sred_wages
Basis,basis
```

`skills/sred/scripts/time_basis.py`:
```python
#!/usr/bin/env python3
"""Evidence-day time basis and the accountant's labour summary.

  time_basis.py --claim DIR [--scenario conservative|balanced|maximum] [--preliminary]

Writes financials/ (or scope/preliminary/<scenario>/ with --preliminary). Re-running keeps the claimant's
confirmed_pct, basis and override_reason in person_summary.csv and their entries in gap_months.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import config
from sredlib.timebasis import SCENARIOS, TimeBasisError, run


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--claim", default=".")
    p.add_argument("--scenario", choices=sorted(SCENARIOS))
    p.add_argument("--preliminary", action="store_true", help="rough numbers for Phase 3 scenarios; touches nothing in financials/")
    args = p.parse_args(argv)
    try:
        result = run(Path(args.claim), args.scenario, args.preliminary)
    except (TimeBasisError, config.ConfigError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_timebasis_run.py tests/test_timebasis_ledger.py -v`
Expected: PASS (15 tests).

- [ ] **Step 6: Commit**

```bash
git add skills/sred/scripts/sredlib/timebasis.py skills/sred/scripts/time_basis.py skills/sred/templates/labour-summary-columns.csv tests/test_timebasis_run.py
git commit -m "feat: add person summary, labour summary and time_basis.py

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: Handoff build and `check.py handoff`

**Files:**
- Create: `skills/sred/scripts/sredlib/handoff.py`, `skills/sred/scripts/handoff.py`
- Modify: `skills/sred/scripts/check.py` (replace whole file)
- Test: `tests/test_handoff.py`

**Interfaces:**
- Consumes: `narrative.parse_narrative`, `narrative.strip_markers`, `narrative.word_count`, `narrative.line_count`, `narrative.MARKER_ID_RE`, `narrative.LINES`, `narrative.Finding`, `narrative.yes`, `roster.load_roster`.
- Produces:
  - `handoff.EVIDENCE_INDEX_COLUMNS = ["project", "claim_id", "statement", "source_key", "raw_path", "verified"]`; `handoff.REQUIRED` (non-project files).
  - `handoff.load_projects(claim_dir) -> list[dict]` (reads `scope/projects.toml`: `[[project]]` with `id`, `title`, `start`, `end`, `continuation`, `field_code`).
  - `handoff.build(claim_dir) -> list[str]` (file names written into `handoff/`; never overwrites an existing `gaps.md`; never writes `README.md`).
  - `handoff.check(claim_dir) -> list[Finding]`.
  - CLIs: `handoff.py build --claim DIR`; `check.py handoff --claim DIR` (exit 1 on errors).

- [ ] **Step 1: Write the failing tests**

`tests/test_handoff.py`:
```python
import csv

import check
import handoff as handoff_cli
from sredlib import handoff, timebasis

PROJECTS = """
[[project]]
id = "P1"
title = "Adaptive Grasp Planning Under Occlusion"
start = 2026-09-02
end = 2027-07-31
continuation = true
field_code = "2.02.09"
"""
NARRATIVE = """# P1: Adaptive Grasp Planning Under Occlusion

## Section A
- 200 Project title: Adaptive Grasp Planning Under Occlusion
- 202 Start date: 2026-09-02
- 204 Completion date: 2027-07-31
- 206 Field of science code: 2.02.09
- 208 Continuation: yes
- 210 First claim: no

## Line 242
It was uncertain whether occlusion-aware sampling could keep grasp success above the baseline [C1].

## Line 244
The team tested three sampling strategies across 230 trials [C2]. Contractor developers built the harness.

## Line 246
The team determined that visibility-weighted sampling holds success under 40% occlusion [C3].

## Section C
- Key individuals: Alice Chen (Lead developer)
- Contractors: Carol Diaz (Diaz Robotics)
"""
STATE = """# SR&ED claim state: Acme Robotics Inc. FY2027
phase: 7-handoff

## Locked decisions
- D1 (2027-08-05, ratified by CEO): scenario = balanced; project P1

## Open questions for the claimant
- Q1: confirm the contractor's final invoice

## Phase log
- 2027-08-02 capture complete
"""
ROSTER = [{"id": "alice", "name": "Alice Chen", "classification": "employee"}, {"id": "carol", "name": "Carol Diaz", "classification": "contractor"}]


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make(make_claim, alice_pct="75", carol_pct="33.33", narrative=NARRATIVE, projects=PROJECTS):
    claim = make_claim(roster=ROSTER)
    (claim / "scope").mkdir()
    (claim / "scope/projects.toml").write_text(projects)
    (claim / "draft/P1").mkdir(parents=True)
    (claim / "draft/P1/narrative.md").write_text(narrative)
    write_csv(claim / "draft/P1/evidence_table.csv", ["claim_id", "statement", "source_key", "raw_path", "verified"],
              [{"claim_id": f"C{i}", "statement": f"s{i}", "source_key": f"k{i}", "raw_path": "evidence/raw/gh/x.json", "verified": "Y"} for i in range(1, 5)])
    write_csv(claim / "financials/person_summary.csv", timebasis.SUMMARY_COLUMNS,
              [{"person": "alice", "confirmed_pct": alice_pct}, {"person": "carol", "confirmed_pct": carol_pct}])
    (claim / "financials/labour_summary.csv").write_text("Name\nAlice Chen\n")
    (claim / "STATE.md").write_text(STATE)
    return claim


def test_build_then_check_passes_once_readme_exists(make_claim):
    claim = make(make_claim)
    written = handoff.build(claim)
    out = claim / "handoff"
    assert set(written) == {"T661-Part2-P1.md", "evidence_index.csv", "labour_summary.csv", "decision_log.md", "gaps.md"}
    t661 = (out / "T661-Part2-P1.md").read_text()
    assert "[C" not in t661 and "Lengths: Line 242 " in t661 and "Line 246" in t661
    index = list(csv.DictReader((out / "evidence_index.csv").open()))
    assert [r["claim_id"] for r in index] == ["C1", "C2", "C3"] and index[0]["project"] == "P1"
    assert "D1 (2027-08-05" in (out / "decision_log.md").read_text()
    assert "Q1: confirm the contractor" in (out / "gaps.md").read_text()
    assert [f.message for f in handoff.check(claim)] == ["missing README.md"]
    (out / "README.md").write_text("# For the accountant\n")
    assert handoff.check(claim) == []


def test_gaps_file_is_never_overwritten(make_claim):
    claim = make(make_claim)
    (claim / "handoff").mkdir()
    (claim / "handoff/gaps.md").write_text("edited by hand\n")
    assert "gaps.md" not in handoff.build(claim)
    assert (claim / "handoff/gaps.md").read_text() == "edited by hand\n"


def test_consistency_errors(make_claim):
    narrative = NARRATIVE.replace("Carol Diaz (Diaz Robotics)", "Dana Wu (Wu Labs)")
    claim = make(make_claim, alice_pct="0", carol_pct="", narrative=narrative, projects=PROJECTS.replace("Under Occlusion", "In Clutter"))
    handoff.build(claim)
    (claim / "handoff/README.md").write_text("x")
    messages = [f.message for f in handoff.check(claim) if f.severity == "error"]
    assert any("Section A Line 200" in m for m in messages)
    assert any("'Dana Wu', who is not in roster.csv" in m for m in messages)
    assert any("Alice Chen is named in Section C but has 0% SR&ED time" in m for m in messages)
    assert any("carol: SR&ED % is not confirmed" in m for m in messages)


def test_markers_left_in_handoff_are_an_error(make_claim):
    claim = make(make_claim)
    handoff.build(claim)
    (claim / "handoff/README.md").write_text("x")
    (claim / "handoff/T661-Part2-P1.md").write_text("text [C9]")
    assert any("claim markers left" in f.message for f in handoff.check(claim))


def test_clis(make_claim, capsys):
    claim = make(make_claim)
    assert handoff_cli.main(["build", "--claim", str(claim)]) == 0
    assert check.main(["handoff", "--claim", str(claim)]) == 1
    (claim / "handoff/README.md").write_text("x")
    assert check.main(["handoff", "--claim", str(claim)]) == 0
    assert "0 errors" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_handoff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'handoff'`.

- [ ] **Step 3: Implement `sredlib/handoff.py`**

`skills/sred/scripts/sredlib/handoff.py`:
```python
"""Assemble handoff/ for the accountant and check it for consistency."""
from __future__ import annotations

import csv
import re
import shutil
import tomllib
from pathlib import Path

from . import narrative
from .narrative import LINES, Finding
from .roster import load_roster

EVIDENCE_INDEX_COLUMNS = ["project", "claim_id", "statement", "source_key", "raw_path", "verified"]
REQUIRED = ["labour_summary.csv", "evidence_index.csv", "decision_log.md", "gaps.md", "README.md"]


def load_projects(claim_dir) -> list[dict]:
    path = Path(claim_dir) / "scope" / "projects.toml"
    if not path.exists():
        raise FileNotFoundError("scope/projects.toml not found: write it when scope is locked in Phase 3")
    return tomllib.loads(path.read_text(encoding="utf-8")).get("project", [])


def _rows(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _section(text: str, heading: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text)
    return m.group(1).strip() if m else ""


def _confirmed(s: dict | None):
    if not s:
        return None
    v = (s.get("confirmed_pct") or "").strip().rstrip("%").strip()
    return float(v) if v else None


def build(claim_dir) -> list[str]:
    claim_dir = Path(claim_dir)
    out = claim_dir / "handoff"
    out.mkdir(exist_ok=True)
    written, index_rows = [], []
    for p in load_projects(claim_dir):
        pid = p["id"]
        text = (claim_dir / "draft" / pid / "narrative.md").read_text(encoding="utf-8")
        n = narrative.parse_narrative(text)
        lengths = "; ".join(f"Line {line} {narrative.word_count(n.lines.get(line, ''))} words / "
                            f"{narrative.line_count(n.lines.get(line, ''))} lines" for line in LINES)
        body = narrative.strip_markers(text)
        nl = body.find("\n")
        body = body[: nl + 1] + f"\nLengths: {lengths}\n" + body[nl + 1:] if nl >= 0 else body
        (out / f"T661-Part2-{pid}.md").write_text(body, encoding="utf-8")
        written.append(f"T661-Part2-{pid}.md")
        cited = {cid for line in LINES for cid in narrative.MARKER_ID_RE.findall(n.lines.get(line, ""))}
        for row in _rows(claim_dir / "draft" / pid / "evidence_table.csv"):
            if row.get("claim_id") in cited:
                index_rows.append({"project": pid, **{k: row.get(k, "") for k in EVIDENCE_INDEX_COLUMNS[1:]}})
    with (out / "evidence_index.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVIDENCE_INDEX_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(index_rows)
    written.append("evidence_index.csv")
    labour = claim_dir / "financials" / "labour_summary.csv"
    if labour.exists():
        shutil.copy2(labour, out / "labour_summary.csv")
        written.append("labour_summary.csv")
    state_path = claim_dir / "STATE.md"
    state = state_path.read_text(encoding="utf-8") if state_path.exists() else ""
    (out / "decision_log.md").write_text("# Decision log\n\n" + (_section(state, "Locked decisions") or "(none recorded)") + "\n", encoding="utf-8")
    written.append("decision_log.md")
    gaps = out / "gaps.md"
    if not gaps.exists():
        flags = [f"- {r['person']}: {r['flags']}" for r in _rows(claim_dir / "financials" / "person_summary.csv") if r.get("flags")]
        gaps.write_text("# Gaps and follow-ups\n\n## Open questions\n\n" + (_section(state, "Open questions for the claimant") or "(none)")
                        + "\n\n## Financial flags\n\n" + ("\n".join(flags) or "(none)") + "\n", encoding="utf-8")
        written.append("gaps.md")
    return written


def _names(value: str) -> list[str]:
    out = []
    for part in (value or "").split(";"):
        name = re.sub(r"\(.*?\)", "", part).strip()
        if name and name.lower() not in ("none", "n/a"):
            out.append(name)
    return out


def check(claim_dir) -> list[Finding]:
    claim_dir = Path(claim_dir)
    out = claim_dir / "handoff"
    findings: list[Finding] = []

    def add(severity, rule, where, message):
        findings.append(Finding(severity, rule, where, message))

    try:
        projects = load_projects(claim_dir)
    except FileNotFoundError as exc:
        return [Finding("error", "HANDOFF", "scope", str(exc))]
    for name in REQUIRED + [f"T661-Part2-{p['id']}.md" for p in projects]:
        if not (out / name).exists():
            add("error", "HANDOFF", "handoff", f"missing {name}")
    for p in projects:
        t661 = out / f"T661-Part2-{p['id']}.md"
        if t661.exists() and narrative.MARKER_ID_RE.search(t661.read_text(encoding="utf-8")):
            add("error", "HANDOFF", p["id"], "claim markers left in handoff text")
    roster = load_roster(claim_dir / "roster.csv")
    lookup = {r["name"].strip().lower(): r for r in roster} | {r["id"].lower(): r for r in roster}
    summary = {s["person"]: s for s in _rows(claim_dir / "financials" / "person_summary.csv")}
    named, named_contractors = set(), set()
    for p in projects:
        pid = p["id"]
        npath = claim_dir / "draft" / pid / "narrative.md"
        if not npath.exists():
            add("error", "HANDOFF", pid, "draft narrative missing")
            continue
        n = narrative.parse_narrative(npath.read_text(encoding="utf-8"))
        expect = {"200": p.get("title", ""), "202": p.get("start", ""), "204": p.get("end", ""), "206": p.get("field_code", "")}
        for line, value in expect.items():
            if str(value) and n.section_a.get(line, "") != str(value):
                add("error", "CONSIST", pid, f"Section A Line {line} is {n.section_a.get(line, '')!r} but scope/projects.toml says {str(value)!r}")
        if "continuation" in p and narrative.yes(n.section_a.get("208", "")) != bool(p["continuation"]):
            add("error", "CONSIST", pid, "Line 208 (continuation) disagrees with scope/projects.toml")
        for label, bucket in (("key individuals", named), ("contractors", named_contractors)):
            for name in _names(n.section_c.get(label, "")):
                r = lookup.get(name.lower())
                if r is None:
                    add("error", "CONSIST", pid, f"Section C names {name!r}, who is not in roster.csv")
                    continue
                bucket.add(r["id"])
                pct = _confirmed(summary.get(r["id"]))
                if pct is not None and pct <= 0:
                    add("error", "CONSIST", pid, f"{name} is named in Section C but has 0% SR&ED time")
    for pid, s in summary.items():
        pct = _confirmed(s)
        if pct is None:
            add("error", "CONSIST", "financials", f"{pid}: SR&ED % is not confirmed")
        elif pct > 0 and pid not in named | named_contractors:
            add("warning", "CONSIST", "financials", f"{pid} is claimed at {pct}% but not named in any project's Section C")
    contractor_ids = {r["id"] for r in roster if r["classification"] == "contractor"}
    for cid in sorted(named_contractors - contractor_ids):
        add("error", "CONSIST", "draft", f"{cid} is listed under Section C contractors but is an employee in roster.csv")
    for cid in sorted(contractor_ids - named_contractors):
        if (_confirmed(summary.get(cid)) or 0) > 0:
            add("warning", "CONSIST", "financials", f"contractor {cid} is claimed but not listed under Section C contractors")
    return findings
```

- [ ] **Step 4: Add `handoff.py` and replace `check.py`**

`skills/sred/scripts/handoff.py`:
```python
#!/usr/bin/env python3
"""Assemble handoff/ for the accountant.

  handoff.py build --claim DIR

Writes T661-Part2-<P>.md (claim markers stripped, lengths stated), evidence_index.csv (cited markers only),
labour_summary.csv, decision_log.md and, if absent, gaps.md. README.md is written by hand.
Then run: check.py handoff --claim DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import handoff


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--claim", default=".")
    args = p.parse_args(argv)
    try:
        written = handoff.build(Path(args.claim))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for name in written:
        print(f"wrote handoff/{name}")
    print("Next: write handoff/README.md, then run check.py handoff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`skills/sred/scripts/check.py`:
```python
#!/usr/bin/env python3
"""Checks that gate each phase.

  check.py setup --claim DIR [--phase N]           what onboarding still needs; exit 1 if anything blocks phase N
  check.py narrative PATH [--claim DIR] [--evidence CSV] [--patterns TOML]
                                                   lengths, do-not patterns, claim markers, Section A; exit 1 on errors
  check.py handoff --claim DIR                     handoff/ complete and consistent with scope and financials
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sredlib import config, handoff, narrative, setupcheck

ORDER = {"error": 0, "warning": 1, "info": 2}


def cmd_setup(args) -> int:
    claim = Path(args.claim)
    missing, info = setupcheck.check_setup(claim)
    phase = args.phase or setupcheck.current_phase(claim)
    for line in info:
        print(line)
    for m in missing:
        print(m)
    blocking = [m for m in missing if m.phase <= phase]
    print(f"{len(missing)} missing; {len(blocking)} block phase {phase}." if missing else "Setup complete: nothing missing.")
    return 1 if blocking else 0


def print_findings(findings) -> int:
    for f in sorted(findings, key=lambda f: (ORDER[f.severity], f.where, f.rule)):
        print(f)
    errors = sum(f.severity == "error" for f in findings)
    print(f"{errors} errors, {sum(f.severity == 'warning' for f in findings)} warnings")
    return 1 if errors else 0


def cmd_narrative(args) -> int:
    path = Path(args.narrative)
    claim = Path(args.claim) if args.claim else path.resolve().parents[2]
    cfg = config.load_config(claim / "sred.toml")
    ev_path = Path(args.evidence) if args.evidence else path.parent / "evidence_table.csv"
    evidence = list(csv.DictReader(ev_path.open(newline="", encoding="utf-8"))) if ev_path.exists() else []
    n = narrative.parse_narrative(path.read_text(encoding="utf-8"))
    findings, counts = narrative.check_narrative(n, evidence, cfg, narrative.load_patterns(args.patterns))
    lim = config.limits(cfg)
    print(f"{n.project or path}: limit mode = {lim['mode']}")
    for line, (w, l) in counts.items():
        print(f"  Line {line}: {w}/{lim['words'][line]} words, {l}/{lim['lines'][line]} lines")
    return print_findings(findings)


def cmd_handoff(args) -> int:
    return print_findings(handoff.check(Path(args.claim)))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="what onboarding still needs")
    s.add_argument("--claim", default=".")
    s.add_argument("--phase", type=int)
    s.set_defaults(func=cmd_setup)
    nar = sub.add_parser("narrative", help="check one draft/<P>/narrative.md")
    nar.add_argument("narrative")
    nar.add_argument("--claim")
    nar.add_argument("--evidence")
    nar.add_argument("--patterns")
    nar.set_defaults(func=cmd_narrative)
    h = sub.add_parser("handoff", help="check handoff/ for completeness and consistency")
    h.add_argument("--claim", default=".")
    h.set_defaults(func=cmd_handoff)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_handoff.py tests/test_narrative.py tests/test_setupcheck.py -v`
Expected: PASS (23 tests).

- [ ] **Step 6: Commit**

```bash
git add skills/sred/scripts/sredlib/handoff.py skills/sred/scripts/handoff.py skills/sred/scripts/check.py tests/test_handoff.py
git commit -m "feat: add handoff build and check.py handoff

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Packaging, README, script smoke tests, leak check

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `tests/backtest/README.md`, `tests/test_scripts.py`, `tests/test_leak.py`
- Test: `tests/test_scripts.py`, `tests/test_leak.py`

**Interfaces:**
- Consumes: all five scripts.
- Produces: an installable plugin repo. `tests/test_leak.py` reads private regex terms from `tests/backtest/local.toml` (`leak_terms = [...]`), which the controller creates locally and which is never committed.

- [ ] **Step 1: Write the failing tests**

`tests/test_scripts.py`:
```python
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "sred" / "scripts"


@pytest.mark.parametrize("name", ["capture.py", "index.py", "check.py", "time_basis.py", "handoff.py"])
def test_script_runs_standalone(name):
    out = subprocess.run([sys.executable, str(SCRIPTS / name), "--help"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "usage" in out.stdout.lower()


def test_plugin_manifest_is_valid_json():
    import json

    root = SCRIPTS.parent.parent.parent
    manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
    assert manifest["name"] == "sred-kit" and market["plugins"][0]["name"] == "sred-kit"
```

`tests/test_leak.py`:
```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_scripts.py tests/test_leak.py -v`
Expected: `test_plugin_manifest_is_valid_json` FAILS with `FileNotFoundError` (no manifest yet); the five script tests PASS; the leak tests PASS or SKIP.

- [ ] **Step 3: Add the plugin manifests**

`.claude-plugin/plugin.json`:
```json
{
  "name": "sred-kit",
  "version": "0.1.0",
  "description": "Turn a finished fiscal year into an SR&ED handoff package: T661 Part 2 narratives and an evidence-backed labour summary."
}
```

`.claude-plugin/marketplace.json`:
```json
{
  "name": "sred-kit",
  "owner": {"name": "sred-kit"},
  "plugins": [
    {
      "name": "sred-kit",
      "source": "./",
      "description": "Turn a finished fiscal year into an SR&ED handoff package: T661 Part 2 narratives and an evidence-backed labour summary."
    }
  ]
}
```

- [ ] **Step 4: Write the README and the backtest note**

`README.md`:
````markdown
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
````

`tests/backtest/README.md`:
```markdown
# Backtest data (private)

`local.toml` in this folder is gitignored. It holds:

- `leak_terms`: regexes for the reference claimant's private terms (company, org, repos, issue prefix, people,
  accountant). `tests/test_leak.py` fails if any appears in shipped files.
- `[backtest]`: paths to the reference claimant's real drafts and evidence, used by the Plan 2 backtest.

Never commit it.
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: PASS for every test (the reference-terms leak test reports SKIP until the controller adds `local.toml`).

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin README.md tests/backtest/README.md tests/test_scripts.py tests/test_leak.py
git commit -m "chore: add plugin manifests, README, script smoke tests and leak check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7 (controller only, not a subagent): add the private leak terms and rerun**

The controller writes `tests/backtest/local.toml` with the reference claimant's terms, confirms `git status` does not list it, and runs `.venv/bin/pytest tests/test_leak.py -v` (expected: PASS, no skips).
