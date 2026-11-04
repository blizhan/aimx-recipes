"""Meta Kaggle source adapter and corpus normalization."""

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any
import uuid
from aimx_recipes import ValidationContext, validate_bundle
from aimx_recipes.cli.output import ERR_BUNDLE_INVALID, build_envelope
from aimx_recipes.sources.kaggle import normalize as norm_mod
from aimx_recipes.sources.kaggle.inputs import (
    create_input_views,
    verify_inputs,
    verify_stat_after,
)
from aimx_recipes.sources.kaggle.membership import (
    evaluate_and_write_membership,
    load_and_validate_reviewed_list,
    load_and_validate_rule_file,
)
from aimx_recipes.sources.kaggle.resolve import (
    resolve_competition_context,
    resolve_writeup_references,
)
from aimx_recipes.sources.kaggle.snapshot import (
    open_session,
    verify_existing_snapshot,
    write_snapshot,
)

ADAPTER_VERSION = norm_mod.ADAPTER_VERSION
CONTRACT_SCHEMA_VERSION = norm_mod.CONTRACT_SCHEMA_VERSION
NORMALIZATION_VERSION = norm_mod.NORMALIZATION_VERSION


def membership_id(
    arg1: str,
    arg2: str | None = None,
    arg3: str | None = None,
) -> str:
    """Compute deterministic membership_id.

    Supports both:
      - membership_id(snapshot_id) -> computes sha256 from current packaged rules
      - membership_id(rule_sha256, list_sha256, snapshot_id) -> raw hashing helper
    """
    if arg2 is None and arg3 is None:
        snapshot_id_val = arg1
        rule_dict = load_and_validate_rule_file()
        list_dict = load_and_validate_reviewed_list()
        import hashlib, json

        rule_sha = hashlib.sha256(
            json.dumps(rule_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()
        list_sha = hashlib.sha256(
            json.dumps(list_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return norm_mod.membership_id(rule_sha, list_sha, snapshot_id_val)
    return norm_mod.membership_id(arg1, arg2 or "", arg3 or "")


__all__ = [
    "ADAPTER_VERSION",
    "CONTRACT_SCHEMA_VERSION",
    "NORMALIZATION_VERSION",
    "IngestResult",
    "ingest",
    "membership_id",
]


@dataclass
class IngestResult:
    snapshot: dict[str, Any]
    counts: dict[str, Any]
    membership: dict[str, Any] | None = None
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_envelope(self, run_started_at: str) -> dict[str, Any]:
        return build_envelope(
            command="ingest kaggle",
            status="ok" if not self.errors else "error",
            run_started_at=run_started_at,
            snapshot=self.snapshot,
            counts=self.counts,
            membership=self.membership,
            warnings=self.warnings,
            errors=self.errors,
        )


class IngestError(Exception):
    """Raised when Kaggle ingestion fails."""

    def __init__(
        self, code: str, message: str, diagnostics: list[dict[str, Any]] | None = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.diagnostics = diagnostics or []


def ingest(
    meta_kaggle: Path | str,
    data_dir: Path | str = "data",
    label: str | None = None,
    threads: int = 4,
    memory_limit: str = "4GB",
) -> IngestResult:
    """Orchestrate Meta Kaggle ingestion."""
    meta_path = Path(meta_kaggle)
    inputs = verify_inputs(meta_path)
    snap_id = norm_mod.snapshot_id(inputs)

    raw_kaggle_dir = Path(data_dir) / "raw" / "kaggle"
    raw_kaggle_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = raw_kaggle_dir / snap_id
    warnings: list[dict[str, Any]] = []

    def _quoted(p: Path) -> str:
        return "'" + p.as_posix().replace("'", "''") + "'"

    if snapshot_dir.exists() and (snapshot_dir / "manifest.json").exists():
        # Reuse existing snapshot after verifying content hashes and outputs
        session_temp = raw_kaggle_dir / f".tmp-verify-{uuid.uuid4().hex}"
        session_temp.mkdir(parents=True, exist_ok=True)
        try:
            con = open_session(threads=threads, memory_limit=memory_limit, temp_dir=session_temp)
            try:
                manifest_data, verify_warnings = verify_existing_snapshot(
                    snapshot_dir, con, expected_snapshot_id=snap_id
                )
                warnings.extend(verify_warnings)

                c_rows_raw = con.execute(
                    f"SELECT * FROM read_parquet({_quoted(snapshot_dir / 'competitions.parquet')})"
                ).fetchall()
                c_cols = [desc[0] for desc in con.description]
                competitions_rows = [dict(zip(c_cols, r)) for r in c_rows_raw]

                d_rows_raw = con.execute(
                    f"SELECT * FROM read_parquet({_quoted(snapshot_dir / 'documents.parquet')})"
                ).fetchall()
                d_cols = [desc[0] for desc in con.description]
                documents_rows = [dict(zip(d_cols, r)) for r in d_rows_raw]
            finally:
                con.close()
        finally:
            shutil.rmtree(session_temp, ignore_errors=True)

        snap_res = {
            "snapshot_id": snap_id,
            "state": "existing",
            "path": str(snapshot_dir),
            "label": manifest_data.get("label"),
            "counts": manifest_data.get("counts"),
        }
    else:
        # Full ingest: resolve and normalize
        session_temp = raw_kaggle_dir / f".tmp-resolve-{uuid.uuid4().hex}"
        session_temp.mkdir(parents=True, exist_ok=True)
        try:
            con = open_session(threads=threads, memory_limit=memory_limit, temp_dir=session_temp)
            try:
                create_input_views(con, meta_path, inputs)
                refs_raw = resolve_writeup_references(con)
                comps_raw = resolve_competition_context(con)
            finally:
                con.close()
        finally:
            shutil.rmtree(session_temp, ignore_errors=True)

        verify_stat_after(inputs)

        competitions_rows, writeup_refs_rows, writeups_rows, documents_rows = (
            norm_mod.build_adapter_tables(refs_raw, comps_raw)
        )

        # Build and validate 001 contract records
        sources_recs, docs_recs, problems_recs = norm_mod.build_contract_records(
            snapshot_id=snap_id,
            competitions_rows=competitions_rows,
            writeup_refs_rows=writeup_refs_rows,
            writeups_rows=writeups_rows,
            documents_rows=documents_rows,
        )

        doc_texts = {d["document_id"]: d["text"] for d in documents_rows}
        ctx = ValidationContext(document_texts=doc_texts)
        bundle_res = validate_bundle(
            sources_recs + docs_recs + problems_recs, context=ctx
        )
        if bundle_res.status != "valid":
            diags = [
                {"code": d.code, "record_id": d.record_id, "message": d.message}
                for d in bundle_res.diagnostics
            ]
            raise IngestError(
                code=ERR_BUNDLE_INVALID,
                message=f"Bundle validation failed: {len(diags)} errors",
                diagnostics=diags,
            )

        # Pre-validate rule file and reviewed list against normalized competitions
        # BEFORE any files or directories are written to disk (ensures exit 1 guarantee).
        rule_data = load_and_validate_rule_file()
        known_comps = {c["competition_id"]: c["slug"] for c in competitions_rows}
        reviewed_data = load_and_validate_reviewed_list(known_competitions=known_comps)

        snap_res = write_snapshot(
            data_dir=data_dir,
            inputs=inputs,
            competitions_rows=competitions_rows,
            writeup_refs_rows=writeup_refs_rows,
            writeups_rows=writeups_rows,
            documents_rows=documents_rows,
            sources_records=sources_recs,
            documents_records=docs_recs,
            problems_records=problems_recs,
            label=label,
            threads=threads,
            memory_limit=memory_limit,
        )

    # Always compute membership. If evaluating membership fails on a freshly created snapshot,
    # clean up the snapshot directory to honor the exit 1 contract guarantee ("nothing new was written").
    try:
        mem_details, mem_warnings = evaluate_and_write_membership(
            data_dir=data_dir,
            snapshot_id=snap_id,
            competitions=competitions_rows,
            documents=documents_rows,
            rule_data=rule_data if "rule_data" in locals() else None,
            reviewed_data=reviewed_data if "reviewed_data" in locals() else None,
        )
    except Exception:
        if snap_res.get("state") == "created" and snapshot_dir.exists():
            shutil.rmtree(snapshot_dir, ignore_errors=True)
        raise

    warnings.extend(mem_warnings)

    return IngestResult(
        snapshot=snap_res,
        counts=snap_res["counts"],
        membership=mem_details,
        warnings=warnings,
        errors=[],
    )
