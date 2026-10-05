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
