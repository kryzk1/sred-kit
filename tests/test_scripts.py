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
