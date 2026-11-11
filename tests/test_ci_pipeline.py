"""A failed release gate must prevent both later checks and the image build."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("failed_module", ["", "hotel_cancel.validate", "hotel_cancel.quality_gate"])
def test_ci_is_ordered_and_stops_before_build_on_failure(tmp_path, failed_module):
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "Makefile", tmp_path / "Makefile")
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import os,sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1:2] == ['-c']:\n"
        " print('0.2.0'); sys.exit(0)\n"
        "module = sys.argv[2] if sys.argv[1] == '-m' else 'docker'\n"
        "with open(os.environ['CI_TEST_LOG'], 'a') as f: f.write(module+'\\n')\n"
        "sys.exit(1 if module == os.environ.get('CI_TEST_FAIL') else 0)\n"
    )
    docker = tmp_path / "docker"
    docker.write_text(f"#!{sys.executable}\nexec(open({str(runner)!r}).read())\n")
    docker.chmod(0o755)
    log = tmp_path / "steps.txt"
    env = {
        **os.environ,
        "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "CI_TEST_LOG": str(log),
        "CI_TEST_FAIL": failed_module,
    }
    result = subprocess.run(
        ["make", "-j4", "ci", f"PYTHON={sys.executable} {runner}"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    expected = [
        "ruff",
        "pytest",
        "hotel_cancel.validate",
        "hotel_cancel.knowledge",
        "hotel_cancel.quality_gate",
        "hotel_cancel.briefing",
        "docker",
    ]
    if failed_module:
        expected = expected[: expected.index(failed_module) + 1]
    assert log.read_text().splitlines() == expected, result.stdout + result.stderr
    assert (result.returncode != 0) == bool(failed_module)
