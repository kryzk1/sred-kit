import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACME = ROOT / "examples" / "acme"
SCRIPTS = ROOT / "skills" / "sred" / "scripts"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def same_tree(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def test_generator_is_deterministic(tmp_path):
    copy = tmp_path / "acme"
    shutil.copytree(ACME, copy)
    out = run(copy / "generate.py", "--out", copy)
    assert out.returncode == 0, out.stderr
    assert same_tree(ACME, copy)


def test_example_builds_and_passes_setup(tmp_path):
    copy = tmp_path / "acme"
    shutil.copytree(ACME, copy)
    setup = run(SCRIPTS / "check.py", "setup", "--claim", copy, "--phase", "7")
    assert setup.returncode == 0, setup.stdout
    build = run(SCRIPTS / "index.py", "build", "--claim", copy)
    assert build.returncode == 0, build.stderr
    assert run(SCRIPTS / "index.py", "validate", "--claim", copy).returncode == 0
    prelim = run(SCRIPTS / "time_basis.py", "--claim", copy, "--scenario", "balanced", "--preliminary")
    assert prelim.returncode == 0, prelim.stderr
    unmatched = (copy / "evidence/index/identities_unmatched.csv").read_text().strip().splitlines()
    assert unmatched == ["source,actor_raw,rows,first_date,last_date,sample_key"]
    activity = (copy / "evidence/index/activity.csv").read_text()
    assert "230 grasp trials" in activity and "exp/fixed-threshold" in activity
