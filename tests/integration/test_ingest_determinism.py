"""Integration tests for determinism, immutability, manifests, and snapshot conflicts."""

import hashlib
import json
from pathlib import Path
import duckdb
from aimx_recipes.cli import main
from aimx_recipes.cli.output import (
    ERR_SNAPSHOT_CONFLICT,
    WARN_WRITER_VERSION_DIFFERS,
)


def test_determinism_threads_and_rerun(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"

    # First run: threads=1
    argv1 = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--threads",
        "1",
        "--json",
    ]
    ret1 = main(argv1)
    captured1 = capsys.readouterr()
    assert ret1 == 0
    out1 = json.loads(captured1.out)
    assert out1["snapshot"]["state"] == "created"
    assert out1["membership"]["state"] == "created"
    snap_path = Path(out1["snapshot"]["path"])

    # Hashes of all files
    files1 = {
        p.relative_to(snap_path): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in snap_path.rglob("*")
        if p.is_file()
    }

    # Second run: threads=4
    argv2 = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--threads",
        "4",
        "--json",
    ]
    ret2 = main(argv2)
    captured2 = capsys.readouterr()
    assert ret2 == 0
    out2 = json.loads(captured2.out)
    assert out2["snapshot"]["state"] == "existing"
    assert out2["snapshot"]["snapshot_id"] == out1["snapshot"]["snapshot_id"]
    assert out2["membership"]["state"] == "existing"
    assert out2["membership"]["membership_id"] == out1["membership"]["membership_id"]

    files2 = {
        p.relative_to(snap_path): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in snap_path.rglob("*")
        if p.is_file()
    }
    assert files1 == files2, "Snapshot files mutated or differed on rerun"


def test_changed_input_new_snapshot_id(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    main(argv)
    out1 = json.loads(capsys.readouterr().out)
    snap1_id = out1["snapshot"]["snapshot_id"]

    # Append row to Teams.csv in a copy of fixture dir
    copy_dir = tmp_path / "fixture_copy"
    import shutil

    shutil.copytree(kaggle_fixture_dir, copy_dir)

    teams_file = copy_dir / "Teams.csv"
    with open(teams_file, "a", newline="", encoding="utf-8") as f:
        # Append another team writeup reference
        f.write(
            '"99999","101","1","New Team","","","","","0","","","15","15","1001"\r\n'
        )

    argv_changed = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(copy_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    ret = main(argv_changed)
    out2 = json.loads(capsys.readouterr().out)
    assert ret == 0
    snap2_id = out2["snapshot"]["snapshot_id"]
    assert snap2_id != snap1_id
    assert (data_dir / "raw" / "kaggle" / snap1_id).exists()
    assert (data_dir / "raw" / "kaggle" / snap2_id).exists()


def test_snapshot_conflict_aborts(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    main(argv)
    out = json.loads(capsys.readouterr().out)
    snap_path = Path(out["snapshot"]["path"])

    # Tamper with writeups.parquet content: rewrite with different data
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT 'corrupted' AS source_id) TO '{(snap_path / 'writeups.parquet').as_posix()}' (FORMAT parquet)"
    )
    con.close()

    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 1
    out_err = json.loads(captured.out)
    assert out_err["status"] == "error"
    assert any(e["code"] == ERR_SNAPSHOT_CONFLICT for e in out_err["errors"])


def test_writer_version_differs_warning(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    main(argv)
    out = json.loads(capsys.readouterr().out)
    snap_path = Path(out["snapshot"]["path"])

    # Rewrite writeups.parquet with same data but different compression (e.g. snappy instead of zstd)
    w_pq = snap_path / "writeups.parquet"
    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT * FROM read_parquet('{w_pq.as_posix()}')) TO '{w_pq.as_posix()}' (FORMAT parquet, COMPRESSION snappy)"
    )
    con.close()

    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 0
    out_warn = json.loads(captured.out)
    assert out_warn["snapshot"]["state"] == "existing"
    assert any(w["code"] == WARN_WRITER_VERSION_DIFFERS for w in out_warn["warnings"])


def test_manifest_completeness_and_no_timestamps(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    main(argv)
    out = json.loads(capsys.readouterr().out)
    snap_path = Path(out["snapshot"]["path"])

    man_file = snap_path / "manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))

    # Inputs
    assert len(man_data["inputs"]) == 6
    for inp in man_data["inputs"]:
        assert {"name", "size_bytes", "sha256", "rows"}.issubset(inp.keys())

    # Outputs
    for outp in man_data["outputs"]:
        assert {"path", "rows", "file_sha256", "content_sha256"}.issubset(outp.keys())

    # Environment
    env = man_data["environment"]
    assert "package_version" in env
    assert "python" in env
    assert "duckdb" in env
    assert "parquet_created_by" in env
    assert "uv_lock_sha256" in env

    # No wall-clock timestamp key in manifest
    assert "run_started_at" not in man_data
    assert "created_at" not in man_data
    assert "timestamp" not in man_data


def test_temp_directories_ignored(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw" / "kaggle"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Simulate a crash leaving .tmp-orphan
    orphan_tmp = raw_dir / ".tmp-crash123"
    orphan_tmp.mkdir()
    (orphan_tmp / "junk.txt").write_text("junk", encoding="utf-8")

    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--json",
    ]
    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 0
    out = json.loads(captured.out)
    # The orphan tmp dir was ignored and not used as snapshot
    assert out["snapshot"]["state"] == "created"
    assert orphan_tmp.exists()  # still there as orphan, not touched


def test_independent_rebuild_manifest_byte_determinism(kaggle_fixture_dir, tmp_path, capsys):
    """SC-002 / F-04: identical manifests across two distinct fresh data-dir paths."""
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"

    ret_a = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(dir_a), "--json"])
    out_a = json.loads(capsys.readouterr().out)
    assert ret_a == 0

    ret_b = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(dir_b), "--json"])
    out_b = json.loads(capsys.readouterr().out)
    assert ret_b == 0

    assert out_a["membership"]["membership_id"] == out_b["membership"]["membership_id"]

    # Compare snapshot manifests
    snap_man_a = (Path(out_a["snapshot"]["path"]) / "manifest.json").read_bytes()
    snap_man_b = (Path(out_b["snapshot"]["path"]) / "manifest.json").read_bytes()
    assert snap_man_a == snap_man_b, "Snapshot manifest differed between independent data-dirs"

    # Compare membership manifests
    mem_man_a = (Path(out_a["membership"]["candidate_report"]).parent / "manifest.json").read_bytes()
    mem_man_b = (Path(out_b["membership"]["candidate_report"]).parent / "manifest.json").read_bytes()
    assert mem_man_a == mem_man_b, "Membership manifest differed between independent data-dirs"


def test_corrupt_membership_fails_conflict(kaggle_fixture_dir, tmp_path, capsys):
    """F-01: corrupt membership.parquet must cause snapshot_conflict and exit 1."""
    data_dir = tmp_path / "data"
    ret = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret == 0
    out = json.loads(capsys.readouterr().out)

    mem_dir = Path(out["membership"]["candidate_report"]).parent
    (mem_dir / "membership.parquet").write_bytes(b"corrupt")

    ret_corrupt = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret_corrupt == 1
    out_corrupt = json.loads(capsys.readouterr().out)
    assert out_corrupt["status"] == "error"
    assert any(e["code"] == "snapshot_conflict" for e in out_corrupt["errors"])


def test_missing_required_output_in_manifest_fails_conflict(kaggle_fixture_dir, tmp_path, capsys):
    """F-01: manifest missing required outputs must fail conflict check rather than reusing."""
    data_dir = tmp_path / "data_missing_output"
    ret = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret == 0
    out = json.loads(capsys.readouterr().out)

    mem_dir = Path(out["membership"]["candidate_report"]).parent
    manpath = mem_dir / "manifest.json"
    man_data = json.loads(manpath.read_text(encoding="utf-8"))
    man_data["outputs"] = [o for o in man_data["outputs"] if o["path"] != "membership.parquet"]
    manpath.write_text(json.dumps(man_data), encoding="utf-8")
    (mem_dir / "membership.parquet").unlink(missing_ok=True)

    ret_rerun = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret_rerun == 1
    out_rerun = json.loads(capsys.readouterr().out)
    assert out_rerun["status"] == "error"
    assert any(e["code"] == "snapshot_conflict" for e in out_rerun["errors"])


def test_installed_layout_lock_is_none(tmp_path, monkeypatch):
    """F-04: in installed layout without project source tree, uv_lock_sha256 must be None."""
    from unittest.mock import patch
    import aimx_recipes.sources.kaggle.snapshot as snap_mod

    unrelated_dir = tmp_path / "unrelated_pkg"
    unrelated_dir.mkdir()
    (unrelated_dir / "uv.lock").write_text("unrelated foreign lock", encoding="utf-8")
    monkeypatch.chdir(unrelated_dir)

    simulated_file = str(tmp_path / "venv/lib/python3.13/site-packages/aimx_recipes/sources/kaggle/snapshot.py")
    with patch.object(snap_mod, "__file__", simulated_file):
        con = snap_mod.open_session()
        try:
            meta = snap_mod.get_environment_metadata(con)
            assert meta["uv_lock_sha256"] is None
        finally:
            con.close()


def test_tampered_membership_details_fails_conflict(kaggle_fixture_dir, tmp_path, capsys):
    """F-01: tampered membership_details fields (identity, false final status, types) must fail conflict."""
    data_dir = tmp_path / "data_tamper_mem"
    ret = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret == 0
    out = json.loads(capsys.readouterr().out)

    mem_dir = Path(out["membership"]["candidate_report"]).parent
    manpath = mem_dir / "manifest.json"
    orig_text = manpath.read_text(encoding="utf-8")

    # 1. Tamper details membership_id
    tampered = json.loads(orig_text)
    tampered["membership_details"]["membership_id"] = "p0-wrong"
    manpath.write_text(json.dumps(tampered), encoding="utf-8")
    assert main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"]) == 1
    err_out = json.loads(capsys.readouterr().out)
    assert any(e["code"] == "snapshot_conflict" for e in err_out["errors"])

    # 2. Tamper details status to final when unreviewed candidates exist
    tampered = json.loads(orig_text)
    tampered["membership_details"]["status"] = "final"
    manpath.write_text(json.dumps(tampered), encoding="utf-8")
    assert main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"]) == 1
    err_out = json.loads(capsys.readouterr().out)
    assert any(e["code"] == "snapshot_conflict" for e in err_out["errors"])


def test_tampered_snapshot_manifest_fails_conflict(kaggle_fixture_dir, tmp_path, capsys):
    """F-01: tampered snapshot_id or counts in snapshot manifest.json must fail conflict."""
    data_dir = tmp_path / "data_tamper_snap"
    ret = main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"])
    assert ret == 0
    out = json.loads(capsys.readouterr().out)

    snap_dir = Path(out["snapshot"]["path"])
    manpath = snap_dir / "manifest.json"
    orig_text = manpath.read_text(encoding="utf-8")

    # 1. Tamper snapshot_id
    tampered = json.loads(orig_text)
    tampered["snapshot_id"] = "meta-kaggle-wrong"
    manpath.write_text(json.dumps(tampered), encoding="utf-8")
    assert main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"]) == 1
    err_out = json.loads(capsys.readouterr().out)
    assert any(e["code"] == "snapshot_conflict" for e in err_out["errors"])

    # 2. Tamper counts
    tampered = json.loads(orig_text)
    tampered["counts"]["writeup_refs"] = 999999
    manpath.write_text(json.dumps(tampered), encoding="utf-8")
    assert main(["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir), "--json"]) == 1
    err_out = json.loads(capsys.readouterr().out)
    assert any(e["code"] == "snapshot_conflict" for e in err_out["errors"])
