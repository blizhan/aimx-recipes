"""Test packaging, wheel installation, CLI entry point, and embedded resources."""

import subprocess
import venv


def test_wheel_build_and_install(tmp_path, kaggle_fixture_dir):
    dist_dir = tmp_path / "dist"
    # Build sdist and wheel
    res_build = subprocess.run(
        ["uv", "build", "--out-dir", str(dist_dir)],
        capture_output=True,
        text=True,
    )
    assert res_build.returncode == 0, f"uv build failed:\n{res_build.stderr}"

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel, found {wheels}"
    wheel_file = wheels[0]

    # Create a fresh isolated venv
    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True)

    venv_bin = venv_dir / "bin"
    python_bin = venv_bin / "python"
    cli_bin = venv_bin / "aimx-recipes"

    # Install the wheel into the venv using uv pip install
    res_install = subprocess.run(
        ["uv", "pip", "install", "--python", str(python_bin), str(wheel_file)],
        capture_output=True,
        text=True,
    )
    assert res_install.returncode == 0, f"Wheel install failed:\n{res_install.stderr}"

    # Verify aimx-recipes --help
    res_help = subprocess.run([str(cli_bin), "--help"], capture_output=True, text=True)
    assert res_help.returncode == 0
    assert "aimx-recipes" in res_help.stdout

    # Verify aimx-recipes ingest kaggle --help
    res_khelp = subprocess.run(
        [str(cli_bin), "ingest", "kaggle", "--help"], capture_output=True, text=True
    )
    assert res_khelp.returncode == 0
    assert "--meta-kaggle" in res_khelp.stdout

    # Verify packaged curation resources
    res_py = subprocess.run(
        [
            str(python_bin),
            "-c",
            "import importlib.resources as r; f = r.files('aimx_recipes._curation'); assert (f / 'kaggle/p0-rule.yaml').is_file(); assert (f / 'kaggle/p0-reviewed.yaml').is_file(); print('OK')",
        ],
        capture_output=True,
        text=True,
    )
    assert res_py.returncode == 0, f"Resource check failed:\n{res_py.stderr}"
    assert "OK" in res_py.stdout

    # Verify running ingest with fixture
    out_data = tmp_path / "out_data"
    res_ingest = subprocess.run(
        [
            str(cli_bin),
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(kaggle_fixture_dir),
            "--data-dir",
            str(out_data),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert res_ingest.returncode == 0, (
        f"Ingest via installed CLI failed:\n{res_ingest.stderr}"
    )
