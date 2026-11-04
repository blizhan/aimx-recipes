"""Reference dataset integration test for full Meta Kaggle dump."""

import hashlib
import json
import os
from pathlib import Path
import time
import pytest
from aimx_recipes.cli import main

ENV_REF = os.environ.get("AIMX_RECIPES_META_KAGGLE")
REF_DIR = Path(ENV_REF) if ENV_REF else Path("data/reference/meta-kaggle")


@pytest.mark.kaggle_ref
@pytest.mark.skipif(
    not REF_DIR.exists(),
    reason="Reference Meta Kaggle dataset not found (set AIMX_RECIPES_META_KAGGLE)",
)
def test_ingest_kaggle_reference_dataset(tmp_path, capsys):
    data_dir = tmp_path / "data"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(REF_DIR),
        "--data-dir",
        str(data_dir),
        "--json",
    ]

    t0 = time.perf_counter()
    ret = main(argv)
    elapsed = time.perf_counter() - t0

    captured = capsys.readouterr()
    assert ret == 0, f"Reference ingest failed: {captured.err}"
    assert elapsed < 1800, f"Wall time exceeded 30 minutes: {elapsed:.1f}s"

    envelope = json.loads(captured.out)
    assert envelope["status"] == "ok"
    assert envelope["snapshot"]["state"] == "created"

    counts = envelope["counts"]
    assert counts["writeup_refs"] == 6276
    assert counts["writeups_excluded"].get("empty_text") == 3
    assert counts["writeup_mirrors"] == 1
    assert counts["writeups_short"] == 107
    assert counts["competitions"] == 618

    mem = envelope["membership"]
    assert mem is not None
    assert mem["status"] == "provisional"
    assert mem["candidates"] == 101, (
        f"Candidate count {mem['candidates']} differs from 101; see research-heuristic-v0.md"
    )
    assert mem["unreviewed"] == 101
    assert mem["p0_in"]["tag"] == 178
    assert mem["p0_out"]["tag"] == 173
    assert mem["p0_out"]["default_exclude"] == 267

    # Verify exclusions: exactly 3 empty_text, all other exclusion categories zero
    assert sum(counts["writeups_excluded"].values()) == 3

    # Check tag class distribution from membership.parquet
    import duckdb
    snap_dir = Path(envelope["snapshot"]["path"])
    mem_dir = Path(mem["candidate_report"]).parent
    con = duckdb.connect()
    tag_counts = dict(
        con.execute(
            f"SELECT tag_class, count(*) FROM read_parquet('{(mem_dir / 'membership.parquet').as_posix()}') GROUP BY tag_class"
        ).fetchall()
    )
    con.close()
    assert tag_counts.get("tag_in") == 178
    assert tag_counts.get("modality_excluded") == 173
    assert tag_counts.get("other_tags") == 113
    assert tag_counts.get("untagged") == 154

    # Independent bundle validation outside of ingest
    from aimx_recipes import ValidationContext, validate_bundle
    con2 = duckdb.connect()
    doc_rows = con2.execute(
        f"SELECT document_id, text FROM read_parquet('{(snap_dir / 'documents.parquet').as_posix()}')"
    ).fetchall()
    con2.close()
    doc_texts = {r[0]: r[1] for r in doc_rows}

    records = []
    for fname in ["sources.jsonl", "documents.jsonl", "problems.jsonl"]:
        for line in (snap_dir / "records" / fname).read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))

    ctx = ValidationContext(document_texts=doc_texts)
    bundle_res = validate_bundle(records, context=ctx)
    assert bundle_res.status == "valid", f"Independent bundle validation failed: {bundle_res.diagnostics}"

    # Snapshot hashes before rerun
    files1 = {
        p.relative_to(snap_dir): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in snap_dir.rglob("*")
        if p.is_file()
    }

    # Rerun determinism check
    main(argv)
    out2 = json.loads(capsys.readouterr().out)
    assert out2["snapshot"]["state"] == "existing"
    assert out2["membership"]["state"] == "existing"

    files2 = {
        p.relative_to(snap_dir): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in snap_dir.rglob("*")
        if p.is_file()
    }
    assert files1 == files2, "Snapshot files mutated or differed on rerun"
