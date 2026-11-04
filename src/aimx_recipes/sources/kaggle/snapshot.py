"""DuckDB session management, deterministic writing, and snapshot publishing."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
from typing import Any, Sequence
import uuid
import duckdb
from aimx_recipes.cli.output import (
    ERR_SNAPSHOT_CONFLICT,
    WARN_WRITER_VERSION_DIFFERS,
)
from aimx_recipes.sources.kaggle.normalize import (
    ADAPTER_VERSION,
    CONTRACT_SCHEMA_VERSION,
    NORMALIZATION_VERSION,
    snapshot_id,
)


class SnapshotConflictError(Exception):
    """Raised when an existing snapshot has conflicting content."""

    def __init__(self, message: str, code: str = ERR_SNAPSHOT_CONFLICT):
        super().__init__(message)
        self.code = code
        self.message = message


def sql_quote(val: str | Path) -> str:
    """Escape string or Path for DuckDB SQL literal."""
    s = str(val.as_posix() if isinstance(val, Path) else val)
    return "'" + s.replace("'", "''") + "'"


REQUIRED_SNAPSHOT_OUTPUTS = {
    "competitions.parquet",
    "writeup_refs.parquet",
    "writeups.parquet",
    "documents.parquet",
    "records/sources.jsonl",
    "records/documents.jsonl",
    "records/problems.jsonl",
}


def get_environment_metadata(
    con: duckdb.DuckDBPyConnection, sample_parquet: Path | None = None
) -> dict[str, Any]:
    """Return environment metadata block for snapshot and membership manifests."""
    try:
        pkg_ver = importlib.metadata.version("aimx-recipes")
    except Exception:
        pkg_ver = "0.1.0"
    py_ver = platform.python_version()
    duckdb_ver = duckdb.__version__
    created_by = f"DuckDB version {duckdb_ver}"
    if sample_parquet and sample_parquet.exists():
        try:
            res_meta = con.execute(
                f"SELECT created_by FROM parquet_file_metadata({sql_quote(sample_parquet)})"
            ).fetchall()
            created_by = res_meta[0][0]
        except Exception:
            pass

    # Locate uv.lock only when running within aimx-recipes source repository
    uv_lock_sha = None
    candidate_pkg_root = Path(__file__).resolve().parents[4]
    candidate_lock = candidate_pkg_root / "uv.lock"
    candidate_toml = candidate_pkg_root / "pyproject.toml"
    if candidate_lock.is_file() and candidate_toml.is_file():
        try:
            toml_text = candidate_toml.read_text(encoding="utf-8")
            if 'name = "aimx-recipes"' in toml_text or "name = 'aimx-recipes'" in toml_text:
                uv_lock_sha = hashlib.sha256(candidate_lock.read_bytes()).hexdigest()
        except Exception:
            uv_lock_sha = None

    return {
        "package_version": pkg_ver,
        "python": py_ver,
        "duckdb": duckdb_ver,
        "parquet_created_by": created_by,
        "uv_lock_sha256": uv_lock_sha,
    }


def verify_existing_snapshot(
    final_dir: Path,
    con: duckdb.DuckDBPyConnection,
    expected_snapshot_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify existing snapshot logical and byte hashes against manifest."""
    manifest_file = final_dir / "manifest.json"
    if not manifest_file.exists():
        raise SnapshotConflictError(
            "Existing snapshot directory is missing manifest.json"
        )

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise SnapshotConflictError(
            f"Corrupt manifest.json in snapshot directory: {e}"
        ) from e

    outputs = manifest.get("outputs", [])
    if not outputs or not isinstance(outputs, list):
        raise SnapshotConflictError("Snapshot manifest has no outputs recorded")

    for o in outputs:
        if not isinstance(o, dict) or "path" not in o or not isinstance(o["path"], str):
            raise SnapshotConflictError("Snapshot manifest contains malformed output entry")

    output_paths = [o.get("path") for o in outputs]
    if len(output_paths) != len(set(output_paths)):
        raise SnapshotConflictError("Snapshot manifest contains duplicate output paths")

    for p_str in output_paths:
        if not p_str or ".." in p_str or p_str.startswith("/"):
            raise SnapshotConflictError(
                f"Snapshot manifest contains invalid output path: {p_str}"
            )

    missing_required = REQUIRED_SNAPSHOT_OUTPUTS - set(output_paths)
    if missing_required:
        raise SnapshotConflictError(
            f"Snapshot manifest is missing required outputs: {sorted(missing_required)}"
        )

    if expected_snapshot_id is not None and manifest.get("snapshot_id") != expected_snapshot_id:
        raise SnapshotConflictError(
            f"Snapshot identity mismatch: expected snapshot_id '{expected_snapshot_id}', got '{manifest.get('snapshot_id')}'"
        )

    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise SnapshotConflictError("Snapshot manifest is missing counts object")

    warnings: list[dict[str, Any]] = []

    for outp in outputs:
        file_path = final_dir / outp["path"]
        if not file_path.exists():
            raise SnapshotConflictError(
                f"Missing output file in existing snapshot: {outp['path']}"
            )

        actual_file_bytes = file_path.read_bytes()
        actual_file_sha = hashlib.sha256(actual_file_bytes).hexdigest()

        if outp["path"].endswith(".parquet"):
            key_col = (
                "competition_id"
                if "competitions" in outp["path"]
                else (
                    "source_id"
                    if "writeups" in outp["path"]
                    else ("document_id" if "documents" in outp["path"] else "topic_id")
                )
            )
            try:
                rows_data = con.execute(
                    f"SELECT * FROM read_parquet({sql_quote(file_path)})"
                ).fetchall()
                cols = [desc[0] for desc in con.description]
                rows_dicts = [dict(zip(cols, r)) for r in rows_data]
                if outp.get("rows") is not None and outp["rows"] != len(rows_dicts):
                    raise SnapshotConflictError(
                        f"Snapshot conflict: manifest output '{outp['path']}' recorded rows {outp['rows']} does not match actual {len(rows_dicts)}"
                    )
                if outp["path"] == "competitions.parquet" and counts.get("competitions") != len(rows_dicts):
                    raise SnapshotConflictError(
                        f"Snapshot conflict: manifest competitions count {counts.get('competitions')} does not match actual {len(rows_dicts)}"
                    )
                elif outp["path"] == "writeup_refs.parquet" and counts.get("writeup_refs") != len(rows_dicts):
                    raise SnapshotConflictError(
                        f"Snapshot conflict: manifest writeup_refs count {counts.get('writeup_refs')} does not match actual {len(rows_dicts)}"
                    )
                actual_content_sha = content_sha256(rows_dicts, key=key_col)
            except SnapshotConflictError:
                raise
            except Exception:
                raise SnapshotConflictError(
                    f"Corrupt or unreadable parquet file in snapshot: '{outp['path']}'"
                ) from None
        elif outp["path"].endswith(".jsonl"):
            key_col = (
                "source_id"
                if "sources" in outp["path"]
                else ("document_id" if "documents" in outp["path"] else "problem_id")
            )
            lines = [
                json.loads(line)
                for line in file_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if outp.get("rows") is not None and outp["rows"] != len(lines):
                raise SnapshotConflictError(
                    f"Snapshot conflict: manifest output '{outp['path']}' recorded rows {outp['rows']} does not match actual {len(lines)}"
                )
            if outp["path"] == "records/sources.jsonl" and counts.get("sources") != len(lines):
                raise SnapshotConflictError(
                    f"Snapshot conflict: manifest sources count {counts.get('sources')} does not match actual {len(lines)}"
                )
            elif outp["path"] == "records/documents.jsonl" and counts.get("documents") != len(lines):
                raise SnapshotConflictError(
                    f"Snapshot conflict: manifest documents count {counts.get('documents')} does not match actual {len(lines)}"
                )
            elif outp["path"] == "records/problems.jsonl" and counts.get("problems") != len(lines):
                raise SnapshotConflictError(
                    f"Snapshot conflict: manifest problems count {counts.get('problems')} does not match actual {len(lines)}"
                )
            actual_content_sha = content_sha256(lines, key=key_col)
        else:
            actual_content_sha = actual_file_sha

        if actual_content_sha != outp["content_sha256"]:
            raise SnapshotConflictError(
                f"Snapshot conflict: content hash mismatch for '{outp['path']}'",
                code=ERR_SNAPSHOT_CONFLICT,
            )

        if actual_file_sha != outp["file_sha256"]:
            warnings.append(
                {
                    "code": WARN_WRITER_VERSION_DIFFERS,
                    "file": outp["path"],
                    "message": f"Writer version differs for '{outp['path']}': content is identical but bytes differ",
                }
            )

    return manifest, warnings


COMPETITION_COLUMNS = {
    "competition_id": "BIGINT",
    "slug": "VARCHAR",
    "source_id": "VARCHAR",
    "problem_id": "VARCHAR",
    "title": "VARCHAR",
    "subtitle": "VARCHAR",
    "url": "VARCHAR",
    "host_segment": "VARCHAR",
    "enabled_at": "TIMESTAMP",
    "deadline_at": "TIMESTAMP",
    "metric_abbreviation": "VARCHAR",
    "metric_name": "VARCHAR",
    "metric_label": "VARCHAR",
    "higher_is_better": "BOOLEAN",
    "competition_data_license": "VARCHAR",
    "tag_ids": "VARCHAR[]",
    "tag_names": "VARCHAR[]",
    "writeup_refs": "BIGINT",
    "writeups_ingested": "BIGINT",
}

WRITEUP_REFS_COLUMNS = {
    "topic_id": "BIGINT",
    "team_id": "BIGINT",
    "competition_id": "BIGINT",
    "message_id": "BIGINT",
    "disposition": "VARCHAR",
    "exclusion_reason": "VARCHAR",
    "source_id": "VARCHAR",
}

WRITEUPS_COLUMNS = {
    "source_id": "VARCHAR",
    "document_id": "VARCHAR",
    "topic_id": "BIGINT",
    "message_id": "BIGINT",
    "team_id": "BIGINT",
    "competition_id": "BIGINT",
    "topic_title": "VARCHAR",
    "posted_at": "TIMESTAMP",
    "body_format": "VARCHAR",
    "char_count": "BIGINT",
    "is_short": "BOOLEAN",
    "medal": "VARCHAR",
    "public_rank": "BIGINT",
    "private_rank": "BIGINT",
    "dedup_key": "VARCHAR",
    "mirror_topic_ids": "BIGINT[]",
}

DOCUMENTS_COLUMNS = {
    "document_id": "VARCHAR",
    "source_id": "VARCHAR",
    "section": "VARCHAR",
    "text": "VARCHAR",
    "content_sha256": "VARCHAR",
    "char_count": "BIGINT",
}


def open_session(
    threads: int = 4,
    memory_limit: str = "4GB",
    temp_dir: Path | str | None = None,
) -> duckdb.DuckDBPyConnection:
    """Open an offline DuckDB in-memory session with deterministic UTC settings."""
    con = duckdb.connect(":memory:")
    con.execute("SET TimeZone='UTC'")
    con.execute("SET autoinstall_known_extensions=false")
    con.execute("SET autoload_known_extensions=false")
    con.execute(f"SET threads={threads}")
    con.execute(f"SET max_memory='{memory_limit}'")
    if temp_dir is not None:
        p_td = Path(temp_dir)
        p_td.mkdir(parents=True, exist_ok=True)
        escaped_td = str(p_td.resolve().as_posix()).replace("'", "''")
        con.execute(f"SET temp_directory='{escaped_td}'")
    else:
        # Prevent default fallback to cwd .tmp by disabling disk spill on unnamed sessions
        con.execute("SET temp_directory=''")
    return con


def write_parquet(
    con: duckdb.DuckDBPyConnection,
    query: str,
    order_by: str,
    path: Path | str,
) -> None:
    """Write query results to Parquet deterministically with total order and fixed row groups."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    copy_sql = (
        f"COPY ({query} ORDER BY {order_by}) "
        f"TO {sql_quote(p)} "
        f"(FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880)"
    )
    con.execute(copy_sql)


def canonical_json_line(obj: Any) -> str:
    """Render object as single-line canonical JSON with sorted keys and compact separators."""
    from datetime import date, datetime

    def _default(o: Any) -> str:
        if isinstance(o, (datetime, date)):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")

    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_default
    )


def content_sha256(
    rows: list[dict[str, Any]],
    key: str | Sequence[str] = "id",
) -> str:
    """Compute deterministic sha256 across rows independent of input ordering."""
    if isinstance(key, str):

        def key_fn(r: dict[str, Any]) -> Any:
            return str(r.get(key, ""))
    else:

        def key_fn(r: dict[str, Any]) -> Any:
            return tuple(str(r.get(k, "")) for k in key)

    sorted_rows = sorted(rows, key=key_fn)
    hasher = hashlib.sha256()
    for r in sorted_rows:
        line = canonical_json_line(r) + "\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def is_incomplete_dir(name: str) -> bool:
    """Check if a directory name indicates an incomplete snapshot."""
    return name.startswith(".tmp-")


def fsync_dir(path: Path) -> None:
    """fsync directory descriptor."""
    try:
        dfd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


def atomic_publish(tmp_dir: Path, final_dir: Path) -> None:
    """Atomically publish tmp_dir to final_dir via rename."""
    if final_dir.exists():
        raise FileExistsError(f"Target directory {final_dir} already exists")

    # fsync all files in tmp_dir
    for root, _, files in os.walk(tmp_dir):
        for f in files:
            fp = Path(root) / f
            try:
                fd = os.open(str(fp), os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                pass
        fsync_dir(Path(root))

    os.rename(tmp_dir, final_dir)
    fsync_dir(final_dir.parent)


def serialize_for_ndjson(val: Any) -> Any:
    """Format dates and complex objects for NDJSON."""
    from datetime import date, datetime

    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    return val


def write_table_parquet(
    con: duckdb.DuckDBPyConnection,
    rows: list[dict[str, Any]],
    columns: dict[str, str],
    order_by: str,
    out_path: Path,
) -> tuple[int, str, str]:
    """Write table to Parquet via temporary NDJSON in staging directory and return (row_count, file_sha256, content_sha256)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_json = out_path.parent / f".tmp-ndjson-{uuid.uuid4().hex}.json"
    with open(tmp_json, "w", encoding="utf-8") as f:
        for r in rows:
            clean_r = {k: serialize_for_ndjson(v) for k, v in r.items()}
            f.write(canonical_json_line(clean_r) + "\n")

    try:
        col_defs = ", ".join([f"{sql_quote(k)}: '{v}'" for k, v in columns.items()])
        query = f"SELECT * FROM read_json({sql_quote(tmp_json)}, columns={{{col_defs}}})"
        write_parquet(con, query, order_by, out_path)
    finally:
        if tmp_json.exists():
            tmp_json.unlink(missing_ok=True)

    file_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    # Content hash over rows
    key_col = order_by.split(",")[0].strip()
    content_hash = content_sha256(rows, key=key_col)
    return len(rows), file_hash, content_hash


def write_jsonl_records(
    records: list[dict[str, Any]],
    key: str,
    out_path: Path,
) -> tuple[int, str, str]:
    """Write canonical JSON Lines sorted by key and return (count, file_sha, content_sha)."""
    sorted_records = sorted(records, key=lambda x: str(x.get(key, "")))
    lines = [canonical_json_line(r) for r in sorted_records]
    content = "\n".join(lines) + ("\n" if lines else "")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    file_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    content_sha = content_sha256(records, key=key)
    return len(records), file_sha, content_sha


def write_snapshot(
    data_dir: Path | str,
    inputs: Sequence[Any],
    competitions_rows: list[dict[str, Any]],
    writeup_refs_rows: list[dict[str, Any]],
    writeups_rows: list[dict[str, Any]],
    documents_rows: list[dict[str, Any]],
    sources_records: list[dict[str, Any]] | None = None,
    documents_records: list[dict[str, Any]] | None = None,
    problems_records: list[dict[str, Any]] | None = None,
    label: str | None = None,
    threads: int = 4,
    memory_limit: str = "4GB",
) -> dict[str, Any]:
    """Write snapshot adapter tables, manifest, and return snapshot details."""
    snap_id = snapshot_id(inputs)
    final_dir = Path(data_dir) / "raw" / "kaggle" / snap_id

    # If already exists with equal content, return existing state
    if final_dir.exists():
        manifest_file = final_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r", encoding="utf-8") as f:
                existing_manifest = json.load(f)
            return {
                "snapshot_id": snap_id,
                "state": "existing",
                "path": str(final_dir),
                "label": existing_manifest.get("label"),
                "counts": existing_manifest.get("counts"),
            }

    raw_kaggle_dir = Path(data_dir) / "raw" / "kaggle"
    raw_kaggle_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = raw_kaggle_dir / f".tmp-{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    spill_dir = tmp_dir / ".duckdb_temp"
    spill_dir.mkdir(parents=True, exist_ok=True)

    try:
        con = open_session(
            threads=threads, memory_limit=memory_limit, temp_dir=spill_dir
        )
        outputs: list[dict[str, Any]] = []

        # 1. competitions.parquet
        c_count, c_file_sha, c_content_sha = write_table_parquet(
            con,
            competitions_rows,
            COMPETITION_COLUMNS,
            "competition_id",
            tmp_dir / "competitions.parquet",
        )
        outputs.append(
            {
                "path": "competitions.parquet",
                "rows": c_count,
                "file_sha256": c_file_sha,
                "content_sha256": c_content_sha,
            }
        )

        # 2. writeup_refs.parquet
        r_count, r_file_sha, r_content_sha = write_table_parquet(
            con,
            writeup_refs_rows,
            WRITEUP_REFS_COLUMNS,
            "topic_id, team_id",
            tmp_dir / "writeup_refs.parquet",
        )
        outputs.append(
            {
                "path": "writeup_refs.parquet",
                "rows": r_count,
                "file_sha256": r_file_sha,
                "content_sha256": r_content_sha,
            }
        )

        # 3. writeups.parquet
        w_count, w_file_sha, w_content_sha = write_table_parquet(
            con,
            writeups_rows,
            WRITEUPS_COLUMNS,
            "source_id",
            tmp_dir / "writeups.parquet",
        )
        outputs.append(
            {
                "path": "writeups.parquet",
                "rows": w_count,
                "file_sha256": w_file_sha,
                "content_sha256": w_content_sha,
            }
        )

        # 4. documents.parquet
        d_count, d_file_sha, d_content_sha = write_table_parquet(
            con,
            documents_rows,
            DOCUMENTS_COLUMNS,
            "document_id",
            tmp_dir / "documents.parquet",
        )
        outputs.append(
            {
                "path": "documents.parquet",
                "rows": d_count,
                "file_sha256": d_file_sha,
                "content_sha256": d_content_sha,
            }
        )

        # 5. records/*.jsonl
        rec_dir = tmp_dir / "records"
        src_count = None
        doc_count = None
        prob_count = None

        if sources_records is not None:
            src_count, s_file_sha, s_content_sha = write_jsonl_records(
                sources_records, "source_id", rec_dir / "sources.jsonl"
            )
            outputs.append(
                {
                    "path": "records/sources.jsonl",
                    "rows": src_count,
                    "file_sha256": s_file_sha,
                    "content_sha256": s_content_sha,
                }
            )

        if documents_records is not None:
            doc_count, doc_file_sha, doc_content_sha = write_jsonl_records(
                documents_records, "document_id", rec_dir / "documents.jsonl"
            )
            outputs.append(
                {
                    "path": "records/documents.jsonl",
                    "rows": doc_count,
                    "file_sha256": doc_file_sha,
                    "content_sha256": doc_content_sha,
                }
            )

        if problems_records is not None:
            prob_count, p_file_sha, p_content_sha = write_jsonl_records(
                problems_records, "problem_id", rec_dir / "problems.jsonl"
            )
            outputs.append(
                {
                    "path": "records/problems.jsonl",
                    "rows": prob_count,
                    "file_sha256": p_file_sha,
                    "content_sha256": p_content_sha,
                }
            )

        # Build counts
        ex_counts: dict[str, int] = {}
        for r in writeup_refs_rows:
            if r["disposition"] == "excluded" and r.get("exclusion_reason"):
                reason = r["exclusion_reason"]
                ex_counts[reason] = ex_counts.get(reason, 0) + 1

        counts = {
            "competitions": len(competitions_rows),
            "writeup_refs": len(writeup_refs_rows),
            "writeups_ingested": sum(
                1 for r in writeup_refs_rows if r["disposition"] == "ingested"
            ),
            "writeup_mirrors": sum(
                1 for r in writeup_refs_rows if r["disposition"] == "mirror"
            ),
            "writeups_excluded": ex_counts,
            "writeups_short": sum(1 for w in writeups_rows if w.get("is_short")),
            "sources": src_count,
            "documents": doc_count,
            "problems": prob_count,
        }

        # Environment
        env_meta = get_environment_metadata(con, tmp_dir / "competitions.parquet")

        # Build manifest
        manifest_data = {
            "snapshot_id": snap_id,
            "adapter_version": ADAPTER_VERSION,
            "normalization_version": NORMALIZATION_VERSION,
            "contract_schema_version": CONTRACT_SCHEMA_VERSION,
            "label": label,
            "inputs": [
                {
                    "name": inp.name,
                    "size_bytes": inp.size_bytes,
                    "sha256": inp.sha256,
                    "rows": inp.row_count,
                }
                for inp in inputs
            ],
            "outputs": sorted(outputs, key=lambda x: x["path"]),
            "counts": counts,
            "environment": env_meta,
        }

        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        con.close()
        shutil.rmtree(spill_dir, ignore_errors=True)

        # Publish atomically
        atomic_publish(tmp_dir, final_dir)

        return {
            "snapshot_id": snap_id,
            "state": "created",
            "path": str(final_dir),
            "label": label,
            "counts": counts,
        }
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
