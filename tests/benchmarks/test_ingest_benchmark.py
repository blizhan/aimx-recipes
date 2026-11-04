"""Benchmark and resource bounds test for Meta Kaggle ingestion."""

import json
import time
from aimx_recipes.cli import main


def test_ingest_fixture_time_and_memory(kaggle_fixture_dir, tmp_path, capsys):
    data_dir = tmp_path / "data_bench"
    argv = [
        "ingest",
        "kaggle",
        "--meta-kaggle",
        str(kaggle_fixture_dir),
        "--data-dir",
        str(data_dir),
        "--memory-limit",
        "2GB",
        "--threads",
        "2",
        "--json",
    ]

    t0 = time.perf_counter()
    ret = main(argv)
    elapsed = time.perf_counter() - t0

    captured = capsys.readouterr()
    assert ret == 0, f"Benchmark ingest failed:\n{captured.err}"
    envelope = json.loads(captured.out)
    assert envelope["status"] == "ok"
    assert elapsed < 5.0, (
        f"Ingest on mini fixture took too long: {elapsed:.2f}s (must be < 5s)"
    )
