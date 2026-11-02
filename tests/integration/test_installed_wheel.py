"""Integration tests for installed-wheel packaging, resource byte fidelity, and isolated execution."""

from pathlib import Path
import subprocess
import tempfile
import zipfile
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_installed_wheel_resources_and_isolated_validation():
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td)
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Build fresh wheel
        build_res = subprocess.run(
            ["uv", "build", "--wheel", "-o", str(dist_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert build_res.returncode == 0, f"uv build failed: {build_res.stderr}"

        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1, f"Expected exactly 1 wheel, found: {wheels}"
        wheel_path = wheels[0]

        # 1. Compare packaged schema resource bytes with source schemas byte-for-byte
        source_schemas_dir = REPO_ROOT / "schemas"
        with zipfile.ZipFile(wheel_path, "r") as z:
            wheel_files = {name: z.read(name) for name in z.namelist()}

            for src_file in source_schemas_dir.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(source_schemas_dir)
                    packaged_name = f"aimx_recipes/_schemas/{rel_path.as_posix()}"
                    assert (
                        packaged_name in wheel_files
                    ), f"Source file {rel_path} not packaged in wheel as {packaged_name}"
                    source_bytes = src_file.read_bytes()
                    packaged_bytes = wheel_files[packaged_name]
                    assert (
                        source_bytes == packaged_bytes
                    ), f"Byte mismatch for {packaged_name}"

        # 2. Provision isolated virtual environment outside checkout
        venv_dir = tmp_path / "test_venv"
        venv_res = subprocess.run(
            ["uv", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        assert venv_res.returncode == 0, f"uv venv failed: {venv_res.stderr}"

        python_bin = venv_dir / "bin" / "python"
        assert python_bin.exists(), f"Python binary not found at {python_bin}"

        # 3. Install wheel offline using provisioned cache
        install_res = subprocess.run(
            [
                "uv",
                "pip",
                "install",
                str(wheel_path),
                "--python",
                str(python_bin),
                "--offline",
            ],
            capture_output=True,
            text=True,
        )
        assert install_res.returncode == 0, f"Wheel installation failed: {install_res.stderr}"

        # 4. Invoke library in an isolated working directory outside checkout with network blocked
        test_script = """
import socket
def fail_net(*a, **kw): raise RuntimeError("Network access forbidden")
socket.socket.connect = fail_net

import aimx_recipes
from aimx_recipes import validate_record

record = {
    "schema_version": "2.0.0",
    "entity_type": "problem",
    "problem_id": "prob:wheel-isolation-test",
    "kind": "competition",
    "title": "Wheel Isolation Test",
    "source_ids": [],
}
res = validate_record(record)
assert res.status == "valid", f"Status expected valid, got {res.status}: {res.diagnostics}"
assert res.structurally_valid is True
print("WHEEL_ISOLATION_TEST_PASS")
"""
        exec_res = subprocess.run(
            [str(python_bin), "-c", test_script],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert exec_res.returncode == 0, f"Execution failed in isolated venv: {exec_res.stderr}"
        assert "WHEEL_ISOLATION_TEST_PASS" in exec_res.stdout
