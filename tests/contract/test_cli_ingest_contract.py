"""Contract tests for aimx-recipes CLI and ingest kaggle envelope."""

import json
from aimx_recipes.cli import main


def test_cli_usage_error_no_args(capsys):
    ret = main([])
    captured = capsys.readouterr()
    assert ret == 2
    assert "usage:" in captured.err.lower() or "error:" in captured.err.lower()
    assert captured.out == ""


def test_cli_usage_error_json(capsys):
    ret = main(["ingest", "kaggle", "--json"])  # missing --meta-kaggle
    captured = capsys.readouterr()
    assert ret == 2
    # When --json is supplied, stdout has the error envelope
    out_json = json.loads(captured.out)
    assert out_json["command"] == "ingest kaggle"
    assert out_json["output_version"] == "1.0.0"
    assert out_json["status"] == "error"
    assert len(out_json["errors"]) > 0
    assert out_json["errors"][0]["code"] == "usage_error"
    # Keys should be sorted in output
    assert list(out_json.keys()) == sorted(out_json.keys())


def test_cli_unknown_flag_json(capsys):
    ret = main(
        ["ingest", "kaggle", "--meta-kaggle", "/tmp", "--unknown-flag", "--json"]
    )
    captured = capsys.readouterr()
    assert ret == 2
    out_json = json.loads(captured.out)
    assert out_json["status"] == "error"
    assert out_json["errors"][0]["code"] == "usage_error"


def test_cli_not_implemented_maps_to_error_envelope(capsys, monkeypatch):
    # Until implemented, ingest kaggle raises NotImplementedError or returns error
    ret = main(["ingest", "kaggle", "--meta-kaggle", "/tmp/nonexistent", "--json"])
    captured = capsys.readouterr()
    assert ret == 1
    out_json = json.loads(captured.out)
    assert out_json["status"] == "error"
    assert out_json["command"] == "ingest kaggle"
    assert out_json["output_version"] == "1.0.0"
    assert "run_started_at" in out_json
    assert out_json["snapshot"] is None
    assert out_json["membership"] is None
    assert len(out_json["errors"]) > 0
    # No ANSI escapes
    assert "\033[" not in captured.out


def test_cli_item_sorting():
    from aimx_recipes.cli.output import sort_diagnostics

    items = [
        {
            "code": "b_code",
            "file": "f2.csv",
            "line": 10,
            "record_id": "r2",
            "message": "msg",
        },
        {
            "code": "a_code",
            "file": "f2.csv",
            "line": 5,
            "record_id": "r1",
            "message": "msg",
        },
        {
            "code": "a_code",
            "file": "f1.csv",
            "line": 20,
            "record_id": "r3",
            "message": "msg",
        },
        {
            "code": "a_code",
            "file": "f1.csv",
            "line": 5,
            "record_id": "r4",
            "message": "msg",
        },
    ]
    sorted_items = sort_diagnostics(items)
    assert [x["record_id"] for x in sorted_items] == ["r4", "r3", "r1", "r2"]


def test_text_json_agreement(kaggle_fixture_dir, tmp_path, capsys):
    data_dir_json = tmp_path / "data_json"
    data_dir_text = tmp_path / "data_text"

    main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(kaggle_fixture_dir),
            "--data-dir",
            str(data_dir_json),
            "--json",
        ]
    )
    json_out = json.loads(capsys.readouterr().out)

    main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(kaggle_fixture_dir),
            "--data-dir",
            str(data_dir_text),
        ]
    )
    text_out = capsys.readouterr().out

    # 1. Snapshot id and state
    assert json_out["snapshot"]["snapshot_id"] in text_out
    assert json_out["snapshot"]["state"] in text_out

    # 2. Key counts
    assert f"Competitions: {json_out['counts']['competitions']}" in text_out
    assert f"Writeup references: {json_out['counts']['writeup_refs']}" in text_out
    assert f"Writeups ingested: {json_out['counts']['writeups_ingested']}" in text_out
    assert f"Writeup mirrors: {json_out['counts']['writeup_mirrors']}" in text_out
    assert f"Writeups short: {json_out['counts']['writeups_short']}" in text_out
    assert f"sources={json_out['counts']['sources']}" in text_out
    assert f"documents={json_out['counts']['documents']}" in text_out
    assert f"problems={json_out['counts']['problems']}" in text_out

    # 3. Exclusions by reason
    for reason, count in json_out["counts"]["writeups_excluded"].items():
        assert f"{reason}: {count}" in text_out

    # 4. Membership id, state, and status
    mem = json_out["membership"]
    assert mem["membership_id"] in text_out
    assert mem["state"] in text_out
    assert mem["status"] in text_out

    # 5. P0 in / out by deciding rule
    for rule, count in mem["p0_in"].items():
        assert f"{rule}: {count}" in text_out
    for rule, count in mem["p0_out"].items():
        assert f"{rule}: {count}" in text_out

    # 6. Candidates and unreviewed counts
    assert f"Candidates: {mem['candidates']} ({mem['unreviewed']} unreviewed)" in text_out
    assert "candidate-report.md" in text_out

    # 7. Error path text/json agreement: column_missing
    import csv
    import shutil

    src_bad_col = tmp_path / "bad_col"
    shutil.copytree(kaggle_fixture_dir, src_bad_col)
    fm_p = src_bad_col / "ForumMessages.csv"
    with open(fm_p, "r", newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    idx_raw = r[0].index("RawMarkdown")
    r_no_raw = [[col for j, col in enumerate(row) if j != idx_raw] for row in r]
    with open(fm_p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerows(r_no_raw)

    code_col_json = main(
        ["ingest", "kaggle", "--meta-kaggle", str(src_bad_col), "--data-dir", str(tmp_path / "data_col_j"), "--json"]
    )
    cap_col_json = capsys.readouterr()
    assert code_col_json == 1
    err_json_col = json.loads(cap_col_json.out)
    assert any(e["code"] == "column_missing" for e in err_json_col["errors"])

    code_col_text = main(
        ["ingest", "kaggle", "--meta-kaggle", str(src_bad_col), "--data-dir", str(tmp_path / "data_col_t")]
    )
    cap_col_text = capsys.readouterr()
    assert code_col_text == 1
    for err in err_json_col["errors"]:
        assert f"error: [{err['code']}] {err['message']}" in cap_col_text.err

    # 8. Error path text/json agreement: snapshot_conflict
    w_pq = tmp_path / "data_json" / "raw" / "kaggle" / json_out["snapshot"]["snapshot_id"] / "writeups.parquet"
    w_pq.write_bytes(b"corrupted-writeups")

    code_conf_json = main(
        ["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir_json), "--json"]
    )
    cap_conf_json = capsys.readouterr()
    assert code_conf_json == 1
    err_json_conf = json.loads(cap_conf_json.out)
    assert any(e["code"] == "snapshot_conflict" for e in err_json_conf["errors"])

    code_conf_text = main(
        ["ingest", "kaggle", "--meta-kaggle", str(kaggle_fixture_dir), "--data-dir", str(data_dir_json)]
    )
    cap_conf_text = capsys.readouterr()
    assert code_conf_text == 1
    for err in err_json_conf["errors"]:
        assert f"error: [{err['code']}] {err['message']}" in cap_conf_text.err


def test_no_body_text_leaks(kaggle_fixture_dir, tmp_path, capsys):
    import csv
    import shutil

    data_dir = tmp_path / "data_leak"
    main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(kaggle_fixture_dir),
            "--data-dir",
            str(data_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()

    # Marker string from fixture ForumMessages.csv
    leak_target = "First line of long writeup."
    assert leak_target not in captured.out
    assert leak_target not in captured.err

    # Check manifest and candidate-report.md
    snap_dir = list((data_dir / "raw" / "kaggle").glob("meta-kaggle-*"))[0]
    manifest_txt = (snap_dir / "manifest.json").read_text(encoding="utf-8")
    assert leak_target not in manifest_txt

    cand_rep = list(snap_dir.glob("membership/*/candidate-report.md"))[0]
    assert leak_target not in cand_rep.read_text(encoding="utf-8")

    # S-03 leak test on error path: date unparseable with private marker in message
    src_bad = tmp_path / "baddate_leak"
    shutil.copytree(kaggle_fixture_dir, src_bad)
    fm_csv = src_bad / "ForumMessages.csv"
    with open(fm_csv, "r", newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    header = reader[0]
    date_idx = header.index("PostDate")
    reader[1][date_idx] = "PRIVATE_SENSITIVE_TEXT_MARKER"
    with open(fm_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(reader)

    code_err = main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(src_bad),
            "--data-dir",
            str(tmp_path / "data_bad_leak"),
            "--json",
        ]
    )
    err_cap = capsys.readouterr()
    assert code_err == 1
    assert "PRIVATE_SENSITIVE_TEXT_MARKER" not in err_cap.out
    assert "PRIVATE_SENSITIVE_TEXT_MARKER" not in err_cap.err
    err_json = json.loads(err_cap.out)
    assert any(e["code"] == "date_unparseable" for e in err_json["errors"])

    # S-03 numeric leak test: invalid integer with sensitive marker in Teams.csv
    src_bad_num = tmp_path / "badnum_leak"
    shutil.copytree(kaggle_fixture_dir, src_bad_num)
    teams_csv = src_bad_num / "Teams.csv"
    with open(teams_csv, "r", newline="", encoding="utf-8") as f:
        t_reader = list(csv.reader(f))
    t_header = t_reader[0]
    cid_idx = t_header.index("CompetitionId")
    t_reader[1][cid_idx] = "PRIVATE_NUMERIC_BODY_MARKER"
    with open(teams_csv, "w", newline="", encoding="utf-8") as f:
        t_writer = csv.writer(f)
        t_writer.writerows(t_reader)

    # 1. JSON mode test
    code_num = main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(src_bad_num),
            "--data-dir",
            str(tmp_path / "data_bad_num_leak"),
            "--json",
        ]
    )
    num_cap = capsys.readouterr()
    assert code_num == 1
    assert "PRIVATE_NUMERIC_BODY_MARKER" not in num_cap.out
    assert "PRIVATE_NUMERIC_BODY_MARKER" not in num_cap.err
    num_json = json.loads(num_cap.out)
    assert num_json["errors"][0]["code"] == "csv_malformed"
    assert num_json["errors"][0]["file"] == "Teams.csv"
    assert num_json["errors"][0]["column"] == "CompetitionId"
    assert num_json["errors"][0]["record_id"] == "1001"

    # 2. Text / stderr mode test
    code_num_text = main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(src_bad_num),
            "--data-dir",
            str(tmp_path / "data_bad_num_text"),
        ]
    )
    num_text_cap = capsys.readouterr()
    assert code_num_text == 1
    assert "PRIVATE_NUMERIC_BODY_MARKER" not in num_text_cap.out
    assert "PRIVATE_NUMERIC_BODY_MARKER" not in num_text_cap.err


def test_no_writes_outside_data_dir(kaggle_fixture_dir, tmp_path, monkeypatch, capsys):
    from pathlib import Path
    import tempfile
    from unittest.mock import patch

    repo_curation = Path("curation").resolve()
    curation_mtimes = {
        p: p.stat().st_mtime_ns for p in repo_curation.rglob("*") if p.is_file()
    }
    repo_schemas = Path("schemas").resolve()
    schemas_mtimes = {
        p: p.stat().st_mtime_ns for p in repo_schemas.rglob("*") if p.is_file()
    }

    # Isolate current working directory to test DuckDB native .tmp creation
    isolated_cwd = tmp_path / "isolated_cwd"
    isolated_cwd.mkdir()
    sibling_unrelated = isolated_cwd / "sibling_unrelated"
    sibling_unrelated.mkdir()
    monkeypatch.chdir(isolated_cwd)

    data_dir = isolated_cwd / "data_isolated"

    # S-01: Track any NamedTemporaryFile calls to ensure no files are created in /tmp
    seen_system_temps = []
    orig_tempfile = tempfile.NamedTemporaryFile

    def _track_named_temp(*args, **kwargs):
        f = orig_tempfile(*args, **kwargs)
        seen_system_temps.append(f.name)
        return f

    with patch.object(tempfile, "NamedTemporaryFile", side_effect=_track_named_temp):
        main(
            [
                "ingest",
                "kaggle",
                "--meta-kaggle",
                str(kaggle_fixture_dir),
                "--data-dir",
                str(data_dir),
                "--memory-limit",
                "32MB",
                "--json",
            ]
        )
    capsys.readouterr()

    assert (
        len(seen_system_temps) == 0
    ), f"Temporary files leaked into system: {seen_system_temps}"

    # Verify no native DuckDB spill files were written to cwd outside data_dir
    cwd_files = [p for p in isolated_cwd.rglob("*") if p.is_file() and not str(p).startswith(str(data_dir))]
    assert cwd_files == [], f"Files leaked outside data_dir in cwd: {cwd_files}"

    # Assert repo curation and schemas files were untouched
    curation_mtimes_after = {
        p: p.stat().st_mtime_ns for p in repo_curation.rglob("*") if p.is_file()
    }
    assert curation_mtimes == curation_mtimes_after
    schemas_mtimes_after = {
        p: p.stat().st_mtime_ns for p in repo_schemas.rglob("*") if p.is_file()
    }
    assert schemas_mtimes == schemas_mtimes_after
    assert list(sibling_unrelated.rglob("*")) == []
