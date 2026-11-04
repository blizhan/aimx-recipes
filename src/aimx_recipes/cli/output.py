"""CLI output formatting, envelope construction, and exit codes."""

from datetime import datetime, timezone
import json
from typing import Any

OUTPUT_VERSION = "1.0.0"

# Stable Error Codes
ERR_INPUT_MISSING = "input_missing"
ERR_COLUMN_MISSING = "column_missing"
ERR_CSV_MALFORMED = "csv_malformed"
ERR_DATE_UNPARSEABLE = "date_unparseable"
ERR_INPUT_CHANGED = "input_changed_during_run"
ERR_BUNDLE_INVALID = "bundle_invalid"
ERR_SNAPSHOT_CONFLICT = "snapshot_conflict"
ERR_REVIEWED_LIST_INVALID = "reviewed_list_invalid"
ERR_REVIEWED_LIST_UNKNOWN_COMPETITION = "reviewed_list_unknown_competition"
ERR_REVIEWED_LIST_SLUG_MISMATCH = "reviewed_list_slug_mismatch"
ERR_RULE_FILE_INVALID = "rule_file_invalid"
ERR_WRITE_FAILED = "write_failed"
ERR_USAGE_ERROR = "usage_error"

# Stable Warning Codes
WARN_P0_PROVISIONAL = "p0_provisional"
WARN_WRITER_VERSION_DIFFERS = "writer_version_differs"
WARN_REVIEWED_LIST_NOT_CANDIDATE = "reviewed_list_entry_not_candidate"


def sort_diagnostics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort warnings or errors by (code, file, line, record_id)."""
    return sorted(
        items,
        key=lambda x: (
            str(x.get("code") or ""),
            str(x.get("file") or ""),
            int(x.get("line") or 0),
            str(x.get("record_id") or ""),
        ),
    )


def now_utc_iso() -> str:
    """Return current wall-clock time as RFC 3339 UTC string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_envelope(
    command: str,
    status: str,
    run_started_at: str,
    snapshot: dict[str, Any] | None = None,
    counts: dict[str, Any] | None = None,
    membership: dict[str, Any] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct JSON envelope per cli-ingest-kaggle.md."""
    envelope: dict[str, Any] = {
        "command": command,
        "counts": counts,
        "errors": sort_diagnostics(errors or []),
        "membership": membership,
        "output_version": OUTPUT_VERSION,
        "run_started_at": run_started_at,
        "snapshot": snapshot,
        "status": status,
        "warnings": sort_diagnostics(warnings or []),
    }
    return envelope


def render_json(envelope: dict[str, Any]) -> str:
    """Render envelope as canonical JSON with sorted keys."""
    return json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False)


def render_text(envelope: dict[str, Any]) -> str:
    """Render human-readable output in contract order:
    1. snapshot id and state
    2. counts
    3. exclusions by reason
    4. membership id, state, and status
    5. P0 in/out by deciding rule
    6. candidates and unreviewed count, with report path
    7. warnings
    8. errors
    """
    lines: list[str] = []

    # 1. Snapshot
    snapshot = envelope.get("snapshot")
    if snapshot:
        lines.append(
            f"Snapshot: {snapshot.get('snapshot_id')} ({snapshot.get('state')})"
        )
        if snapshot.get("label"):
            lines.append(f"Label: {snapshot.get('label')}")
        lines.append(f"Path: {snapshot.get('path')}")

    # 2. Counts
    counts = envelope.get("counts")
    if counts:
        lines.append("Counts:")
        lines.append(f"  Competitions: {counts.get('competitions', 0)}")
        lines.append(f"  Writeup references: {counts.get('writeup_refs', 0)}")
        lines.append(f"  Writeups ingested: {counts.get('writeups_ingested', 0)}")
        lines.append(f"  Writeup mirrors: {counts.get('writeup_mirrors', 0)}")
        lines.append(f"  Writeups short: {counts.get('writeups_short', 0)}")
        if "sources" in counts and counts["sources"] is not None:
            lines.append(
                f"  Contract records: sources={counts.get('sources')}, documents={counts.get('documents')}, problems={counts.get('problems')}"
            )

    # 3. Exclusions
    if counts and "writeups_excluded" in counts:
        ex = counts["writeups_excluded"]
        lines.append("Exclusions by reason:")
        if isinstance(ex, dict):
            for k in sorted(ex.keys()):
                lines.append(f"  {k}: {ex[k]}")

    # 4. Membership
    membership = envelope.get("membership")
    if membership:
        lines.append(
            f"Membership: {membership.get('membership_id')} ({membership.get('state')}, {membership.get('status')})"
        )
        lines.append(f"Rule version: {membership.get('rule_version')}")

        # 5. P0 in/out by deciding rule
        p0_in = membership.get("p0_in", {})
        p0_out = membership.get("p0_out", {})
        lines.append("P0 decisions:")
        lines.append("  In:")
        for k in sorted(p0_in.keys()):
            lines.append(f"    {k}: {p0_in[k]}")
        lines.append("  Out:")
        for k in sorted(p0_out.keys()):
            lines.append(f"    {k}: {p0_out[k]}")

        # 6. Candidates and unreviewed
        lines.append(
            f"Candidates: {membership.get('candidates', 0)} ({membership.get('unreviewed', 0)} unreviewed)"
        )
        if membership.get("candidate_report"):
            lines.append(f"Candidate report: {membership.get('candidate_report')}")

    # 7. Warnings
    warnings = envelope.get("warnings") or []
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  [{w.get('code')}] {w.get('message')}")

    # 8. Errors
    errors = envelope.get("errors") or []
    if errors:
        lines.append("Errors:")
        for e in errors:
            loc = ""
            if e.get("file"):
                loc = f" in {e.get('file')}"
                if e.get("line"):
                    loc += f":{e.get('line')}"
            lines.append(f"  [{e.get('code')}]{loc} {e.get('message')}")

    return "\n".join(lines)
