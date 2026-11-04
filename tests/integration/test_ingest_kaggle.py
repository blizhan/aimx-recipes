"""Integration tests for Meta Kaggle ingest command."""

import json
from pathlib import Path
import duckdb
import pytest
from aimx_recipes.cli import main


@pytest.fixture
def manifest_mini(load_fixture) -> dict:
    return load_fixture("kaggle/manifest.json")


def test_ingest_kaggle_us1_e2e(kaggle_fixture_dir, tmp_path, manifest_mini, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--label",
        "mini-test-run",
        "--json",
    ]
    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 0, f"Command failed with {ret}: {captured.out}\n{captured.err}"

    out_json = json.loads(captured.out)
    assert out_json["status"] == "ok"
    assert out_json["command"] == "ingest kaggle"
    assert out_json["output_version"] == "1.0.0"

    # Snapshot check
    snap = out_json["snapshot"]
    assert snap is not None
    assert snap["state"] == "created"
    assert snap["label"] == "mini-test-run"
    snapshot_id = snap["snapshot_id"]
    snapshot_path = Path(snap["path"])
    assert snapshot_path.is_dir()
    assert snapshot_path == data_dir / "raw" / "kaggle" / snapshot_id

    # Counts check
    counts = out_json["counts"]
    expected_counts = manifest_mini["counts"]
    assert counts["competitions"] == expected_counts["competitions"]
    assert counts["writeup_refs"] == expected_counts["writeup_refs"]
    assert counts["writeups_ingested"] == expected_counts["writeups_ingested"]
    assert counts["writeup_mirrors"] == expected_counts["writeup_mirrors"]
    assert counts["writeups_short"] == expected_counts["writeups_short"]

    total_refs = (
        counts["writeups_ingested"]
        + counts["writeup_mirrors"]
        + sum(counts["writeups_excluded"].values())
    )
    assert total_refs == counts["writeup_refs"]

    # Check Parquet tables exist
    for tbl in [
        "competitions.parquet",
        "writeup_refs.parquet",
        "writeups.parquet",
        "documents.parquet",
        "manifest.json",
    ]:
        assert (snapshot_path / tbl).exists(), f"Missing {tbl} in {snapshot_path}"

    # Check documents exact text roundtrip
    con = duckdb.connect()
    doc_rows = con.execute(
        f"SELECT document_id, text, content_sha256 FROM read_parquet('{snapshot_path}/documents.parquet')"
    ).fetchall()
    import hashlib

    for doc_id, text, expected_hash in doc_rows:
        actual_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for document {doc_id}"
    con.close()


def test_ingest_kaggle_us2_membership(
    kaggle_fixture_dir, tmp_path, manifest_mini, capsys, monkeypatch
):
    data_dir = tmp_path / "data"

    # 1. Run with empty reviewed list
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
    out1 = json.loads(captured.out)

    mem1 = out1["membership"]
    assert mem1 is not None
    assert mem1["state"] == "created"
    assert mem1["status"] == "provisional"
    assert mem1["candidates"] == 1
    assert mem1["unreviewed"] == 1
    assert "tag" in mem1["p0_in"]
    assert "reviewed_list" in mem1["p0_in"]
    assert "tag" in mem1["p0_out"]
    assert "default_exclude" in mem1["p0_out"]
    assert "reviewed_list" in mem1["p0_out"]

    # Candidate report exists
    report_path = Path(mem1["candidate_report"])
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "comp-103-candidate" in report_text
    # No body marker leaks into candidate report
    assert "UNIQUE_MARKER" not in report_text

    # Snapshot directory
    snap1_dir = Path(out1["snapshot"]["path"])
    mem1_dir = snap1_dir / "membership" / mem1["membership_id"]
    assert mem1_dir.exists()
    mem1_bytes = {f.name: f.read_bytes() for f in mem1_dir.glob("*")}

    # 2. Modify reviewed list to review the candidate (include) and exclude tag-in (101)
    from aimx_recipes.sources.kaggle import membership as mem_mod

    custom_reviewed_yaml = """
    entries:
      - competition_id: "101"
        slug: "comp-101-tag-in"
        decision: "exclude"
        reason: "Overriding tag to exclude"
        reviewed_by: "tester"
        reviewed_on: "2026-11-03"
      - competition_id: "103"
        slug: "comp-103-candidate"
        decision: "include"
        reason: "Reviewing candidate as in"
        reviewed_by: "tester"
        reviewed_on: "2026-11-03"
    """
    monkeypatch.setattr(
        mem_mod, "load_reviewed_list_text", lambda: custom_reviewed_yaml
    )

    # Spy on resolve and normalize to verify they are NOT called on rerun!
    import aimx_recipes.sources.kaggle.resolve as res_mod
    import aimx_recipes.sources.kaggle.normalize as norm_mod

    resolve_called = False
    normalize_called = False

    def spy_resolve(*args, **kwargs):
        nonlocal resolve_called
        resolve_called = True
        raise RuntimeError("resolve should not be called!")

    def spy_normalize(*args, **kwargs):
        nonlocal normalize_called
        normalize_called = True
        raise RuntimeError("normalize should not be called!")

    monkeypatch.setattr(res_mod, "resolve_writeup_references", spy_resolve)
    monkeypatch.setattr(norm_mod, "build_adapter_tables", spy_normalize)

    ret2 = main(argv)
    captured2 = capsys.readouterr()
    assert ret2 == 0
    out2 = json.loads(captured2.out)

    assert not resolve_called
    assert not normalize_called

    assert out2["snapshot"]["state"] == "existing"
    assert out2["snapshot"]["snapshot_id"] == out1["snapshot"]["snapshot_id"]

    mem2 = out2["membership"]
    assert mem2["membership_id"] != mem1["membership_id"]
    assert mem2["state"] == "created"
    assert mem2["status"] == "final"  # all candidates reviewed!
    assert mem2["unreviewed"] == 0
    # Old membership directory byte-unchanged
    assert {f.name: f.read_bytes() for f in mem1_dir.glob("*")} == mem1_bytes


def test_ingest_kaggle_us3_records_and_validation(
    kaggle_fixture_dir, tmp_path, manifest_mini, capsys
):
    from aimx_recipes import ValidationContext, validate_bundle

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
    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 0
    out = json.loads(captured.out)

    snap_path = Path(out["snapshot"]["path"])
    records_dir = snap_path / "records"
    assert records_dir.exists()

    sources_file = records_dir / "sources.jsonl"
    documents_file = records_dir / "documents.jsonl"
    problems_file = records_dir / "problems.jsonl"

    assert sources_file.exists()
    assert documents_file.exists()
    assert problems_file.exists()

    sources = [
        json.loads(line)
        for line in sources_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    documents = [
        json.loads(line)
        for line in documents_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    problems = [
        json.loads(line)
        for line in problems_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    con = duckdb.connect()
    doc_rows = con.execute(
        f"SELECT document_id, text FROM read_parquet('{(snap_path / 'documents.parquet').as_posix()}')"
    ).fetchall()
    con.close()
    doc_texts = {r[0]: r[1] for r in doc_rows}

    # Validate bundle
    all_records = sources + documents + problems
    ctx = ValidationContext(document_texts=doc_texts)
    res = validate_bundle(all_records, context=ctx)
    assert res.status == "valid", f"Bundle invalid: {res.diagnostics}"

    # Counts
    counts = out["counts"]
    assert counts["sources"] == len(sources)
    assert counts["documents"] == len(documents)
    assert counts["problems"] == len(problems)
    assert counts["writeup_mirrors"] == 1

    # Verify Problem includes writeup source for both competitions of the duplicate pair
    p101 = [p for p in problems if p["problem_id"] == "kaggle:problem:101"][0]
    p102 = [p for p in problems if p["problem_id"] == "kaggle:problem:102"][0]
    assert "kaggle:writeup:1001" in p101["source_ids"]
    assert "kaggle:writeup:1001" in p102["source_ids"]


def test_ingest_kaggle_us3_bundle_invalid_aborts(
    kaggle_fixture_dir, tmp_path, capsys, monkeypatch
):
    import aimx_recipes.sources.kaggle.normalize as norm_mod

    orig_build = norm_mod.build_contract_records

    def corrupt_build(*args, **kwargs):
        sources, docs, problems = orig_build(*args, **kwargs)
        # Corrupt one document content_sha256
        if docs:
            docs[0]["content_sha256"] = (
                "0000000000000000000000000000000000000000000000000000000000000000"
            )
        return sources, docs, problems

    monkeypatch.setattr(norm_mod, "build_contract_records", corrupt_build)

    data_dir = tmp_path / "data_corrupt"
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
    assert ret == 1
    out = json.loads(captured.out)
    assert out["status"] == "error"
    assert any(e["code"] == "bundle_invalid" for e in out["errors"])

    # No snapshot directory published
    raw_dir = data_dir / "raw" / "kaggle"
    if raw_dir.exists():
        assert not any(not p.name.startswith(".tmp-") for p in raw_dir.iterdir())


def test_ingest_kaggle_missing_column_no_dir_created(
    kaggle_fixture_dir, tmp_path, capsys
):
    # Rename required column in Competitions.csv
    comp_path = kaggle_fixture_dir / "Competitions.csv"
    lines = comp_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header = lines[0].replace('"Overview"', '"OverviewBroken"')
    comp_path.write_text(header + "".join(lines[1:]), encoding="utf-8")

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
    ret = main(argv)
    captured = capsys.readouterr()
    assert ret == 1
    out_json = json.loads(captured.out)
    assert out_json["status"] == "error"
    assert any(e["code"] == "column_missing" for e in out_json["errors"])
    # No directory created under raw/kaggle
    kaggle_dir = data_dir / "raw" / "kaggle"
    if kaggle_dir.exists():
        assert list(kaggle_dir.iterdir()) == []


def test_ingest_kaggle_invalid_reviewed_list_leaves_no_snapshot(
    kaggle_fixture_dir, tmp_path, capsys, monkeypatch
):
    """F-02: Reviewed list error must not leave a published snapshot on disk."""
    import aimx_recipes.sources.kaggle.membership as mem_mod

    bad_reviewed_yaml = """
    entries:
      - competition_id: "999999"
        slug: "unknown-competition"
        decision: "include"
        reason: "Manual review"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    monkeypatch.setattr(mem_mod, "load_reviewed_list_text", lambda: bad_reviewed_yaml)

    data_dir = tmp_path / "data_bad_review"
    ret = main(
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
    assert ret == 1
    out_json = json.loads(captured.out)
    assert out_json["status"] == "error"
    assert any(e["code"] == "reviewed_list_unknown_competition" for e in out_json["errors"])

    # Assert no snapshot directory remains published under raw/kaggle
    manifest_files = list(data_dir.rglob("manifest.json"))
    assert len(manifest_files) == 0, f"Snapshot was published despite error: {manifest_files}"


def test_ingest_kaggle_dangling_tag_fails(kaggle_fixture_dir, tmp_path, capsys):
    """F-03: Dangling TagId reference fails with csv_malformed and record_id."""
    import shutil
    import csv

    src_dir = tmp_path / "mini_missing_tag"
    shutil.copytree(kaggle_fixture_dir, src_dir)

    # Remove tag 14102 from Tags.csv
    tags_csv = src_dir / "Tags.csv"
    with open(tags_csv, "r", newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    kept_tags = [r for r in reader if r["Id"] != "14102"]
    with open(tags_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(reader[0].keys()))
        writer.writeheader()
        writer.writerows(kept_tags)

    data_dir = tmp_path / "data_tag_fail"
    ret = main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(src_dir),
            "--data-dir",
            str(data_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 1
    out_json = json.loads(captured.out)
    assert out_json["status"] == "error"
    err = next((e for e in out_json["errors"] if e["code"] == "csv_malformed"), None)
    assert err is not None
    assert err["file"] == "CompetitionTags.csv"
    assert err["record_id"] == "14102"


def test_ingest_kaggle_tag_with_missing_name_succeeds(kaggle_fixture_dir, tmp_path, capsys):
    """R-01: An existing Tag with empty Name must NOT be treated as a dangling TagId."""
    import shutil
    import csv

    src_dir = tmp_path / "mini_blank_tag_name"
    shutil.copytree(kaggle_fixture_dir, src_dir)

    # Clear Name field for tag 14101 in Tags.csv
    tags_csv = src_dir / "Tags.csv"
    with open(tags_csv, "r", newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    for r in reader:
        if r["Id"] == "14101":
            r["Name"] = ""
    with open(tags_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(reader[0].keys()))
        writer.writeheader()
        writer.writerows(reader)

    data_dir = tmp_path / "data_blank_name_ok"
    ret = main(
        [
            "ingest",
            "kaggle",
            "--meta-kaggle",
            str(src_dir),
            "--data-dir",
            str(data_dir),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    out_json = json.loads(captured.out)
    assert out_json["status"] == "ok"
    assert out_json["snapshot"]["state"] == "created"
