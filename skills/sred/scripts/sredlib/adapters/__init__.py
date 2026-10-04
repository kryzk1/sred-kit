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
