"""P0 membership evaluation, tag rules, heuristic signals, and candidate report."""

from dataclasses import dataclass
import hashlib
import importlib.metadata
import importlib.resources
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Sequence
import uuid
import jsonschema
from aimx_recipes.cli.output import (
    ERR_REVIEWED_LIST_INVALID,
    ERR_REVIEWED_LIST_SLUG_MISMATCH,
    ERR_REVIEWED_LIST_UNKNOWN_COMPETITION,
    ERR_RULE_FILE_INVALID,
    WARN_P0_PROVISIONAL,
    WARN_REVIEWED_LIST_NOT_CANDIDATE,
    WARN_WRITER_VERSION_DIFFERS,
)
from aimx_recipes.sources.kaggle.normalize import membership_id
from aimx_recipes.sources.kaggle.snapshot import (
    SnapshotConflictError,
    atomic_publish,
    canonical_json_line,
    content_sha256,
    get_environment_metadata,
    open_session,
    write_parquet,
)
from aimx_recipes.yaml_strict import StrictYAMLError, load_strict_yaml


class MembershipError(Exception):
    """Raised when rule files, reviewed lists, or membership evaluation fail."""

    def __init__(
        self,
        code: str,
        message: str,
        file: str | None = None,
        line: int | None = None,
        record_id: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.file = file
        self.line = line
        self.record_id = record_id


def load_rule_file_text() -> str:
    """Read the packaged p0-rule.yaml text."""
    ref = importlib.resources.files("aimx_recipes._curation").joinpath(
        "kaggle", "p0-rule.yaml"
    )
    return ref.read_text(encoding="utf-8")


def load_reviewed_list_text() -> str:
    """Read the packaged p0-reviewed.yaml text."""
    ref = importlib.resources.files("aimx_recipes._curation").joinpath(
        "kaggle", "p0-reviewed.yaml"
    )
    return ref.read_text(encoding="utf-8")


def load_rule_schema() -> dict[str, Any]:
    """Read the packaged p0-rule.schema.json."""
    ref = importlib.resources.files("aimx_recipes._curation").joinpath(
        "kaggle", "p0-rule.schema.json"
    )
    return json.loads(ref.read_text(encoding="utf-8"))


def load_reviewed_schema() -> dict[str, Any]:
    """Read the packaged p0-reviewed.schema.json."""
    ref = importlib.resources.files("aimx_recipes._curation").joinpath(
        "kaggle", "p0-reviewed.schema.json"
    )
    return json.loads(ref.read_text(encoding="utf-8"))


def load_and_validate_rule_file(
    text_or_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate p0-rule.yaml."""
    if text_or_path is None:
        content = load_rule_file_text()
    elif isinstance(text_or_path, Path):
        content = text_or_path.read_text(encoding="utf-8")
    else:
        content = text_or_path

    try:
        data = load_strict_yaml(content)
    except StrictYAMLError as e:
        raise MembershipError(
            code=ERR_RULE_FILE_INVALID,
            message=str(e),
            file="p0-rule.yaml",
            line=e.line,
        ) from e

    schema = load_rule_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise MembershipError(
            code=ERR_RULE_FILE_INVALID,
            message=f"Rule file schema validation failed: {e.message}",
            file="p0-rule.yaml",
        ) from e

    return data


def load_and_validate_reviewed_list(
    text_or_path: str | Path | None = None,
    known_competitions: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Load and validate p0-reviewed.yaml against schema and snapshot competitions."""
    if text_or_path is None:
        content = load_reviewed_list_text()
    elif isinstance(text_or_path, Path):
        content = text_or_path.read_text(encoding="utf-8")
    else:
        content = text_or_path

    try:
        data = load_strict_yaml(content)
    except StrictYAMLError as e:
        raise MembershipError(
            code=ERR_REVIEWED_LIST_INVALID,
            message=str(e),
            file="p0-reviewed.yaml",
            line=e.line,
        ) from e

    schema = load_reviewed_schema()
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise MembershipError(
            code=ERR_REVIEWED_LIST_INVALID,
            message=f"Reviewed list schema validation failed: {e.message}",
            file="p0-reviewed.yaml",
        ) from e

    entries = data.get("entries") or []
    seen_ids: set[str] = set()
    for entry in entries:
        cid_str = entry["competition_id"]
        if cid_str in seen_ids:
            raise MembershipError(
                code=ERR_REVIEWED_LIST_INVALID,
                message=f"Duplicate competition_id '{cid_str}' in reviewed list",
                file="p0-reviewed.yaml",
                record_id=cid_str,
            )
        seen_ids.add(cid_str)

        reason = str(entry.get("reason", "")).strip()
        reviewed_by = str(entry.get("reviewed_by", "")).strip()
        if not reason or not reviewed_by:
            raise MembershipError(
                code=ERR_REVIEWED_LIST_INVALID,
                message=f"Reviewed list entry for competition '{cid_str}' has blank reason or reviewed_by",
                file="p0-reviewed.yaml",
                record_id=cid_str,
            )

        if known_competitions is not None:
            cid = int(cid_str)
            if cid not in known_competitions:
                raise MembershipError(
                    code=ERR_REVIEWED_LIST_UNKNOWN_COMPETITION,
                    message=f"Competition id '{cid}' in reviewed list is not found in snapshot",
                    file="p0-reviewed.yaml",
                    record_id=cid_str,
                )
            expected_slug = known_competitions[cid]
            if entry["slug"] != expected_slug:
                raise MembershipError(
                    code=ERR_REVIEWED_LIST_SLUG_MISMATCH,
                    message=f"Slug mismatch for competition {cid}: '{entry['slug']}' != '{expected_slug}'",
                    file="p0-reviewed.yaml",
                    record_id=cid_str,
                )

    return data


def compute_tag_class(tag_ids: Sequence[str], rule_tags: dict[str, set[str]]) -> str:
    """Compute tag class from tag ids."""
    tag_set = set(str(t) for t in tag_ids)
    has_modality = bool(tag_set & rule_tags["modality_exclude"])
    has_in = bool(tag_set & rule_tags["include"])

    if has_modality:
        return "modality_excluded"
    if has_in:
        return "tag_in"
    if tag_set:
        return "other_tags"
    return "untagged"


def strip_dataset_description(
    s: str | None, strip_patterns: Sequence[str] | None = None
) -> str:
    """Strip images and URLs from dataset description before S2/S3 checks."""
    if not s:
        return ""
    if strip_patterns is None:
        strip_patterns = [r"<img[^>]*>", r"!\[[^\]]*\]\([^)]*\)", r"https?://\S+"]
    res = s
    for pat in strip_patterns:
        res = re.sub(pat, "", res, flags=re.I)
    return res


def compute_signals(
    abbr: str | None,
    name: str | None,
    dataset_desc: str | None,
    title: str | None,
    subtitle: str | None,
    tag_ids: Sequence[str],
    rule: dict[str, Any] | None = None,
) -> list[str]:
    """Compute signals S1-S5 for a competition."""
    if rule is None:
        rule = load_and_validate_rule_file()

    sig_def = rule["heuristic"]["signals"]
    s1_metric_pats = [re.compile(p) for p in sig_def["S1"]["metric_families"]]
    s1_name_pats = [re.compile(p, re.I) for p in sig_def["S1"]["name_patterns"]]
    s5_neg_metric_pats = [
        re.compile(p, re.I) for p in sig_def["S5"]["negative_metric_patterns"]
    ]

    s4_pos_tag_ids = {t["id"] for t in sig_def["S4"]["positive_tag_ids"]}
    s4_neg_tag_ids = {t["id"] for t in sig_def["S4"]["negative_tag_ids"]}
    s5_neg_tag_ids = {t["id"] for t in sig_def["S5"]["negative_tag_ids"]}

    s2_tabfile_pats = [re.compile(p, re.I) for p in sig_def["S2"]["file_patterns"]]
    s2_media_pats = [re.compile(p, re.I) for p in sig_def["S2"]["media_patterns"]]
    s2_strip_patterns = sig_def["S2"].get("strip_patterns")

    s3_media_pats = [re.compile(p, re.I) for p in sig_def["S3"]["media_patterns"]]
    kw_pats = {k: re.compile(v, re.I) for k, v in sig_def["S3"]["keywords"].items()}
    kw_thresh = int(sig_def["S3"]["keyword_threshold"])

    abbr_clean = (abbr or "").strip()
    name_clean = (name or "").strip()
    metric = abbr_clean if abbr_clean and not abbr_clean.isdigit() else name_clean

    dd = strip_dataset_description(dataset_desc, s2_strip_patterns)
    head = f"{title or ''} \n {subtitle or ''}"
    curr_tags = set(str(t) for t in tag_ids)

    # Check S5 negative metric
    m_neg = any(p.search(abbr_clean) for p in s5_neg_metric_pats) or any(
        p.search(name_clean) for p in s5_neg_metric_pats
    )

    # S1
    s1 = not m_neg and (
        any(p.match(metric) for p in s1_metric_pats)
        or any(p.search(name_clean) for p in s1_name_pats)
    )

    # S2
    tf_count = sum(len(p.findall(dd)) for p in s2_tabfile_pats)
    s2_mext_count = sum(len(p.findall(dd)) for p in s2_media_pats)
    s2 = tf_count > 0 and s2_mext_count == 0

    # S3
    s3_mext_count = sum(len(p.findall(dd)) for p in s3_media_pats)
    media_kw_triggered = False
    for k, p in kw_pats.items():
        if len(p.findall(dd)) >= kw_thresh or len(p.findall(head)) > 0:
            media_kw_triggered = True
            break
    s3 = s3_mext_count == 0 and not media_kw_triggered

    # S4
    s4 = bool(curr_tags & s4_pos_tag_ids) and not bool(curr_tags & s4_neg_tag_ids)

    # S5
    s5 = m_neg or bool(curr_tags & s5_neg_tag_ids)

    fired: list[str] = []
    if s1:
        fired.append("S1")
    if s2:
        fired.append("S2")
    if s3:
        fired.append("S3")
    if s4:
        fired.append("S4")
    if s5:
        fired.append("S5")

    return fired


def compute_review_flags(
    dataset_desc: str | None,
    title: str | None,
    subtitle: str | None,
    tag_ids: Sequence[str],
    rule: dict[str, Any] | None = None,
) -> list[str]:
    """Compute review flags: bioseq, non_english, thin_dataset_desc, signal."""
    if rule is None:
        rule = load_and_validate_rule_file()

    flags_def = rule["heuristic"]["review_flags"]
    bioseq_pat = re.compile(flags_def["bioseq"]["pattern"], re.I)
    bioseq_thresh = int(flags_def["bioseq"]["threshold"])

    ascii_thresh = float(flags_def["non_english"]["ascii_ratio_threshold"])
    min_desc_len = int(flags_def["thin_dataset_desc"]["min_length"])

    aud_kw_key = flags_def["signal"].get("audio_keyword", "aud")
    aud_kw_regex = rule["heuristic"]["signals"]["S3"]["keywords"].get(
        aud_kw_key, r"\baudio\b"
    )
    aud_kw_pat = re.compile(aud_kw_regex, re.I)
    signal_sp_id = flags_def["signal"]["signal_processing_tag_id"]
    aud_thresh = int(flags_def["signal"]["threshold"])

    s2_strip_patterns = rule["heuristic"]["signals"]["S2"].get("strip_patterns")
    dd = strip_dataset_description(dataset_desc, s2_strip_patterns)
    head = f"{title or ''} \n {subtitle or ''}"
    curr_tags = set(str(t) for t in tag_ids)

    flags: list[str] = []

    # 1. bioseq
    if len(bioseq_pat.findall(dd + " " + head)) >= bioseq_thresh:
        flags.append("bioseq")

    # 2. non_english
    head_trimmed = head.strip()
    if head_trimmed:
        ascii_chars = sum(1 for c in head_trimmed if ord(c) < 128)
        if (ascii_chars / len(head_trimmed)) < ascii_thresh:
            flags.append("non_english")

    # 3. thin_dataset_desc
    if not dataset_desc or len(dd) < min_desc_len:
        flags.append("thin_dataset_desc")

    # 4. signal
    if signal_sp_id in curr_tags or len(aud_kw_pat.findall(dd)) >= aud_thresh:
        flags.append("signal")

    return sorted(flags)


# Candidate expression AST and recursive descent parser
@dataclass
class AstNode:
    op: str
    children: list[Any]


def tokenize(expr: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        if expr[i] in "()":
            tokens.append(expr[i])
            i += 1
            continue
        # Identifier or keyword
        match = re.match(r"[A-Za-z0-9_]+", expr[i:])
        if match:
            tokens.append(match.group(0))
            i += len(match.group(0))
            continue
        raise ValueError(f"Unknown token at index {i}: '{expr[i]}'")
    return tokens


def parse_candidate_expression(expr: str) -> AstNode:
    """Parse candidate boolean expression (S1..S5, and, or, not, parens) without eval."""
    tokens = tokenize(expr)
    pos = 0

    def current() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def match_token(expected: str) -> bool:
        nonlocal pos
        if current() == expected:
            pos += 1
            return True
        return False

    def parse_primary() -> AstNode:
        nonlocal pos
        tok = current()
        if tok == "(":
            pos += 1
            node = parse_or()
            if not match_token(")"):
                raise ValueError("Expected ')'")
            return node
        if tok in ("S1", "S2", "S3", "S4", "S5"):
            pos += 1
            return AstNode(op="var", children=[tok])
        raise ValueError(f"Unexpected token in candidate expression: '{tok}'")

    def parse_not() -> AstNode:
        if match_token("not"):
            return AstNode(op="not", children=[parse_not()])
        return parse_primary()

    def parse_and() -> AstNode:
        node = parse_not()
        while match_token("and"):
            right = parse_not()
            node = AstNode(op="and", children=[node, right])
        return node

    def parse_or() -> AstNode:
        node = parse_and()
        while match_token("or"):
            right = parse_and()
            node = AstNode(op="or", children=[node, right])
        return node

    tree = parse_or()
    if pos < len(tokens):
        raise ValueError(f"Unconsumed tokens at index {pos}: {tokens[pos:]}")
    return tree


def evaluate_candidate_expression(node: AstNode, active_signals: set[str]) -> bool:
    """Evaluate candidate expression AST given active signals set."""
    if node.op == "var":
        return node.children[0] in active_signals
    if node.op == "not":
        return not evaluate_candidate_expression(node.children[0], active_signals)
    if node.op == "and":
        return evaluate_candidate_expression(
            node.children[0], active_signals
        ) and evaluate_candidate_expression(node.children[1], active_signals)
    if node.op == "or":
        return evaluate_candidate_expression(
            node.children[0], active_signals
        ) or evaluate_candidate_expression(node.children[1], active_signals)
    raise ValueError(f"Unknown AST op: {node.op}")


REQUIRED_MEMBERSHIP_OUTPUTS = {"membership.parquet", "candidate-report.md"}


def verify_existing_membership(
    final_mem_dir: Path,
    expected_snapshot_id: str | None = None,
    expected_rule_sha256: str | None = None,
    expected_list_sha256: str | None = None,
    expected_membership_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify existing membership outputs and hashes, returning (membership_details, warnings)."""
    manifest_file = final_mem_dir / "manifest.json"
    if not manifest_file.exists():
        raise SnapshotConflictError(
            f"Missing manifest.json in membership directory {final_mem_dir}"
        )

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise SnapshotConflictError(
            f"Corrupt manifest.json in membership directory: {e}"
        ) from e

    warnings = list(manifest.get("warnings") or [])
    outputs = manifest.get("outputs", [])
    if not outputs or not isinstance(outputs, list):
        raise SnapshotConflictError("Membership manifest has no outputs recorded")

    for o in outputs:
        if not isinstance(o, dict) or "path" not in o or not isinstance(o["path"], str):
            raise SnapshotConflictError("Membership manifest contains malformed output entry")

    output_paths = [o.get("path") for o in outputs]
    if len(output_paths) != len(set(output_paths)):
        raise SnapshotConflictError(
            "Membership manifest contains duplicate output paths"
        )

    for p_str in output_paths:
        if not p_str or ".." in p_str or p_str.startswith("/"):
            raise SnapshotConflictError(
                f"Membership manifest contains invalid output path: {p_str}"
            )

    missing_required = REQUIRED_MEMBERSHIP_OUTPUTS - set(output_paths)
    if missing_required:
        raise SnapshotConflictError(
            f"Membership manifest is missing required outputs: {sorted(missing_required)}"
        )

    if expected_membership_id is not None and manifest.get("membership_id") != expected_membership_id:
        raise SnapshotConflictError(
            f"Membership identity mismatch: expected membership_id '{expected_membership_id}', got '{manifest.get('membership_id')}'"
        )
    if expected_snapshot_id is not None and manifest.get("snapshot_id") != expected_snapshot_id:
        raise SnapshotConflictError(
            f"Membership identity mismatch: expected snapshot_id '{expected_snapshot_id}', got '{manifest.get('snapshot_id')}'"
        )
    if expected_rule_sha256 is not None and manifest.get("rule_sha256") != expected_rule_sha256:
        raise SnapshotConflictError("Membership identity mismatch: rule_sha256 does not match")
    if expected_list_sha256 is not None and manifest.get("list_sha256") != expected_list_sha256:
        raise SnapshotConflictError("Membership identity mismatch: list_sha256 does not match")

    details_raw = manifest.get("membership_details")
    if not isinstance(details_raw, dict):
        raise SnapshotConflictError(
            "Membership manifest is missing membership_details object"
        )
    for req_field in ("membership_id", "rule_version", "status", "p0_in", "p0_out", "candidates", "unreviewed"):
        if req_field not in details_raw:
            raise SnapshotConflictError(
                f"Membership details is missing required field: '{req_field}'"
            )

    if expected_membership_id is not None and details_raw.get("membership_id") != expected_membership_id:
        raise SnapshotConflictError(
            f"Membership details identity mismatch: expected membership_id '{expected_membership_id}', got '{details_raw.get('membership_id')}'"
        )
    if manifest.get("membership_id") != details_raw.get("membership_id"):
        raise SnapshotConflictError(
            f"Membership manifest membership_id '{manifest.get('membership_id')}' does not match membership_details '{details_raw.get('membership_id')}'"
        )

    status_val = details_raw.get("status")
    unreviewed_val = details_raw.get("unreviewed")
    candidates_val = details_raw.get("candidates")

    if not isinstance(unreviewed_val, int) or unreviewed_val < 0:
        raise SnapshotConflictError(
            f"Invalid unreviewed count in membership details: {unreviewed_val}"
        )
    if not isinstance(candidates_val, int) or candidates_val < 0:
        raise SnapshotConflictError(
            f"Invalid candidates count in membership details: {candidates_val}"
        )
    if status_val not in ("final", "provisional"):
        raise SnapshotConflictError(
            f"Invalid status in membership details: '{status_val}'"
        )
    if manifest.get("p0_status") != status_val:
        raise SnapshotConflictError(
            f"Membership manifest p0_status '{manifest.get('p0_status')}' does not match membership_details status '{status_val}'"
        )

    p0_in_raw = details_raw.get("p0_in")
    p0_out_raw = details_raw.get("p0_out")
    if not isinstance(p0_in_raw, dict) or not isinstance(p0_out_raw, dict):
        raise SnapshotConflictError(
            "Membership details p0_in and p0_out must be mappings"
        )
    for rule_k, rule_v in list(p0_in_raw.items()) + list(p0_out_raw.items()):
        if not isinstance(rule_v, int) or rule_v < 0:
            raise SnapshotConflictError(
                f"Count for rule '{rule_k}' in membership details must be a non-negative integer"
            )

    session_temp = final_mem_dir / f".tmp-memverify-{uuid.uuid4().hex}"
    session_temp.mkdir(parents=True, exist_ok=True)
    try:
        for outp in outputs:
            p = final_mem_dir / outp["path"]
            if not p.exists():
                raise SnapshotConflictError(
                    f"Missing membership output file: '{outp['path']}'"
                )

            try:
                file_bytes = p.read_bytes()
            except Exception as e:
                raise SnapshotConflictError(f"Cannot read '{outp['path']}': {e}") from e

            actual_file_sha = hashlib.sha256(file_bytes).hexdigest()

            if outp["path"].endswith(".parquet"):
                try:
                    con = open_session(temp_dir=session_temp)
                    escaped_p = "'" + p.as_posix().replace("'", "''") + "'"
                    rows_data = con.execute(
                        f"SELECT * FROM read_parquet({escaped_p})"
                    ).fetchall()
                    cols = [desc[0] for desc in con.description]
                    rows_dicts = [dict(zip(cols, r)) for r in rows_data]
                    con.close()
                except SnapshotConflictError:
                    raise
                except Exception:
                    raise SnapshotConflictError(
                        f"Corrupt or unreadable parquet file in membership: '{outp['path']}'"
                    ) from None
                actual_content_sha = content_sha256(rows_dicts, key="competition_id")
                if outp.get("rows") is not None and outp["rows"] != len(rows_dicts):
                    raise SnapshotConflictError(
                        f"Membership conflict: manifest output '{outp['path']}' recorded rows {outp['rows']} does not match actual {len(rows_dicts)}"
                    )
                actual_unreviewed = sum(1 for r in rows_dicts if r.get("review_status") == "unreviewed")
                if status_val == "final" and actual_unreviewed > 0:
                    raise SnapshotConflictError(
                        f"Membership details claims status 'final' but table contains {actual_unreviewed} unreviewed candidates"
                    )
                if actual_unreviewed != unreviewed_val:
                    raise SnapshotConflictError(
                        f"Membership details unreviewed count {unreviewed_val} does not match table count {actual_unreviewed}"
                    )
            else:
                actual_content_sha = actual_file_sha

            if actual_content_sha != outp.get("content_sha256"):
                raise SnapshotConflictError(
                    f"Membership conflict: content hash mismatch for '{outp['path']}'"
                )

            if actual_file_sha != outp.get("file_sha256"):
                warnings.append(
                    {
                        "code": WARN_WRITER_VERSION_DIFFERS,
                        "file": outp["path"],
                        "message": f"Writer version differs for '{outp['path']}'",
                    }
                )
    finally:
        shutil.rmtree(session_temp, ignore_errors=True)

    details = dict(details_raw)
    details["state"] = "existing"
    details["candidate_report"] = str(final_mem_dir / "candidate-report.md")
    return details, warnings


def evaluate_and_write_membership(
    data_dir: Path | str,
    snapshot_id: str,
    competitions: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    rule_data: dict[str, Any] | None = None,
    reviewed_data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Evaluate P0 membership, write membership directory, and return membership details and warnings."""
    if rule_data is None:
        rule_data = load_and_validate_rule_file()

    known_comps = {c["competition_id"]: c["slug"] for c in competitions}
    if reviewed_data is None:
        reviewed_data = load_and_validate_reviewed_list(known_competitions=known_comps)

    rule_text = json.dumps(rule_data, sort_keys=True)
    list_text = json.dumps(reviewed_data, sort_keys=True)
    rule_sha = hashlib.sha256(rule_text.encode("utf-8")).hexdigest()
    list_sha = hashlib.sha256(list_text.encode("utf-8")).hexdigest()

    mem_id = membership_id(rule_sha, list_sha, snapshot_id)
    snapshot_dir = Path(data_dir) / "raw" / "kaggle" / snapshot_id
    final_mem_dir = snapshot_dir / "membership" / mem_id

    # If already exists, thoroughly verify contents and return existing
    if final_mem_dir.exists():
        return verify_existing_membership(
            final_mem_dir,
            expected_snapshot_id=snapshot_id,
            expected_rule_sha256=rule_sha,
            expected_list_sha256=list_sha,
            expected_membership_id=mem_id,
        )

    rule_tags = {
        "include": {t["id"] for t in rule_data["tag_rule"]["include"]},
        "modality_exclude": {
            t["id"] for t in rule_data["tag_rule"]["modality_exclude"]
        },
    }
    heuristic_pool = set(
        rule_data.get("heuristic", {}).get("pool", ["other_tags", "untagged"])
    )
    cand_ast = parse_candidate_expression(rule_data["heuristic"]["candidate"])

    # Map dataset descriptions by competition
    doc_map: dict[str, str] = {}
    for d in documents:
        if d["section"] == "competition_dataset_description":
            doc_map[d["source_id"]] = d["text"]

    reviewed_by_id = {
        int(e["competition_id"]): e for e in (reviewed_data.get("entries") or [])
    }

    membership_rows: list[dict[str, Any]] = []
    report_rows: list[dict[str, Any]] = []

    p0_in = {"reviewed_list": 0, "tag": 0}
    p0_out = {"reviewed_list": 0, "tag": 0, "default_exclude": 0}
    candidates_count = 0
    unreviewed_count = 0
    warnings: list[dict[str, Any]] = []

    for comp in competitions:
        cid = comp["competition_id"]
        slug = comp["slug"]
        c_source_id = comp["source_id"]
        tag_ids = comp.get("tag_ids") or []
        t_class = compute_tag_class(tag_ids, rule_tags)

        dd_text = doc_map.get(c_source_id, "")
        signals = compute_signals(
            abbr=comp.get("metric_abbreviation"),
            name=comp.get("metric_name"),
            dataset_desc=dd_text,
            title=comp.get("title"),
            subtitle=comp.get("subtitle"),
            tag_ids=tag_ids,
            rule=rule_data,
        )
        is_candidate = evaluate_candidate_expression(cand_ast, set(signals))
        flags = compute_review_flags(
            dataset_desc=dd_text,
            title=comp.get("title"),
            subtitle=comp.get("subtitle"),
            tag_ids=tag_ids,
            rule=rule_data,
        )

        in_pool = t_class in heuristic_pool
        if in_pool and is_candidate:
            candidates_count += 1

        # Decision precedence:
        # 1. Reviewed list
        # 2. Tag in -> in
        # 3. Modality excluded -> out
        # 4. Default exclude -> out
        reviewed_entry = reviewed_by_id.get(cid)
        if reviewed_entry is not None:
            deciding_rule = "reviewed_list"
            rev_dec = reviewed_entry["decision"]
            rev_reason = reviewed_entry["reason"]
            p0 = "in" if rev_dec == "include" else "out"
            review_status = (
                "reviewed_include" if rev_dec == "include" else "reviewed_exclude"
            )
            if p0 == "in":
                p0_in["reviewed_list"] += 1
            else:
                p0_out["reviewed_list"] += 1

            if not is_candidate:
                warnings.append(
                    {
                        "code": WARN_REVIEWED_LIST_NOT_CANDIDATE,
                        "record_id": str(cid),
                        "message": f"Competition {cid} ({slug}) reviewed but was not a heuristic candidate",
                    }
                )
        elif t_class == "tag_in":
            deciding_rule = "tag"
            rev_dec = None
            rev_reason = None
            p0 = "in"
            p0_in["tag"] += 1
            review_status = "not_candidate"
        elif t_class == "modality_excluded":
            deciding_rule = "tag"
            rev_dec = None
            rev_reason = None
            p0 = "out"
            p0_out["tag"] += 1
            review_status = "not_candidate"
        else:
            deciding_rule = "default_exclude"
            rev_dec = None
            rev_reason = None
            p0 = "out"
            p0_out["default_exclude"] += 1
            if in_pool and is_candidate:
                review_status = "unreviewed"
                unreviewed_count += 1
            else:
                review_status = "not_candidate"

        row = {
            "competition_id": cid,
            "slug": slug,
            "p0": p0,
            "deciding_rule": deciding_rule,
            "tag_class": t_class,
            "reviewed_decision": rev_dec,
            "reviewed_reason": rev_reason,
            "heuristic_pool": in_pool,
            "signals": signals,
            "candidate": is_candidate,
            "review_flags": flags,
            "review_status": review_status,
        }
        membership_rows.append(row)

        # Candidate report includes: pool competitions that are candidates or match S1 without S5
        year = ""
        en_at = comp.get("enabled_at")
        if en_at:
            year = str(en_at.year) if hasattr(en_at, "year") else str(en_at)[:4]

        if in_pool and (is_candidate or ("S1" in signals and "S5" not in signals)):
            report_rows.append(
                {
                    "slug": slug,
                    "competition_id": cid,
                    "year": year,
                    "tag_class": t_class,
                    "metric": comp.get("metric_label") or "",
                    "writeups": comp.get("writeup_refs", 0),
                    "signals": ",".join(signals),
                    "review_flags": ",".join(flags),
                    "review_status": review_status,
                    "deciding_rule": deciding_rule,
                    "p0": p0,
                }
            )

    membership_rows.sort(key=lambda x: x["competition_id"])

    # Candidate report sorting:
    # unreviewed first, then writeups descending, then competition_id
    status_order = {
        "unreviewed": 0,
        "reviewed_include": 1,
        "reviewed_exclude": 2,
        "not_candidate": 3,
    }
    report_rows.sort(
        key=lambda x: (
            status_order.get(x["review_status"], 99),
            -int(x["writeups"]),
            int(x["competition_id"]),
        )
    )

    report_lines = [
        "# P0 Candidate Report",
        "",
        "| slug | competition_id | year | tag_class | metric | writeups | signals | review_flags | review_status | deciding_rule | p0 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report_rows:
        report_lines.append(
            f"| {r['slug']} | {r['competition_id']} | {r['year']} | {r['tag_class']} | "
            f"{r['metric']} | {r['writeups']} | {r['signals']} | {r['review_flags']} | "
            f"{r['review_status']} | {r['deciding_rule']} | {r['p0']} |"
        )
    report_text = "\n".join(report_lines) + "\n"

    # Status
    p0_status = "final" if unreviewed_count == 0 else "provisional"
    if p0_status == "provisional":
        warnings.append(
            {
                "code": WARN_P0_PROVISIONAL,
                "message": f"{unreviewed_count} heuristic candidates are unreviewed",
            }
        )

    # Write to tmp directory
    mem_base = snapshot_dir / "membership"
    mem_base.mkdir(parents=True, exist_ok=True)
    tmp_mem = mem_base / f".tmp-{uuid.uuid4().hex}"
    tmp_mem.mkdir(parents=True, exist_ok=True)

    try:
        # 1. membership.parquet
        mem_cols = {
            "competition_id": "BIGINT",
            "slug": "VARCHAR",
            "p0": "VARCHAR",
            "deciding_rule": "VARCHAR",
            "tag_class": "VARCHAR",
            "reviewed_decision": "VARCHAR",
            "reviewed_reason": "VARCHAR",
            "heuristic_pool": "BOOLEAN",
            "signals": "VARCHAR[]",
            "candidate": "BOOLEAN",
            "review_flags": "VARCHAR[]",
            "review_status": "VARCHAR",
        }
        tmp_ndjson = tmp_mem / f".tmp-membership-{uuid.uuid4().hex}.ndjson"
        with open(tmp_ndjson, "w", encoding="utf-8") as f:
            for r in membership_rows:
                f.write(canonical_json_line(r) + "\n")

        spill_dir = tmp_mem / ".duckdb_temp"
        spill_dir.mkdir(parents=True, exist_ok=True)
        try:
            con = open_session(temp_dir=spill_dir)
            col_defs = ", ".join(
                [f"'{k.replace('\'', '\'\'')}': '{v}'" for k, v in mem_cols.items()]
            )
            escaped_ndjson = "'" + tmp_ndjson.as_posix().replace("'", "''") + "'"
            write_parquet(
                con,
                f"SELECT * FROM read_json({escaped_ndjson}, columns={{{col_defs}}})",
                "competition_id",
                tmp_mem / "membership.parquet",
            )
            con.close()
        finally:
            if tmp_ndjson.exists():
                tmp_ndjson.unlink(missing_ok=True)
            shutil.rmtree(spill_dir, ignore_errors=True)

        mem_pq_bytes = (tmp_mem / "membership.parquet").read_bytes()
        mem_file_sha = hashlib.sha256(mem_pq_bytes).hexdigest()
        mem_content_sha = content_sha256(membership_rows, key="competition_id")

        # 2. candidate-report.md
        report_file = tmp_mem / "candidate-report.md"
        report_file.write_text(report_text, encoding="utf-8")
        rep_file_sha = hashlib.sha256(report_text.encode("utf-8")).hexdigest()

        # 3. manifest.json (store relative path for byte determinism across locations)
        manifest_mem_details = {
            "membership_id": mem_id,
            "state": "created",
            "rule_version": rule_data.get("rule_version", "1.0.0"),
            "p0_in": p0_in,
            "p0_out": p0_out,
            "candidates": candidates_count,
            "unreviewed": unreviewed_count,
            "status": p0_status,
            "candidate_report": "candidate-report.md",
        }

        outputs = [
            {
                "path": "candidate-report.md",
                "rows": len(report_rows),
                "file_sha256": rep_file_sha,
                "content_sha256": rep_file_sha,
            },
            {
                "path": "membership.parquet",
                "rows": len(membership_rows),
                "file_sha256": mem_file_sha,
                "content_sha256": mem_content_sha,
            },
        ]

        env_meta = get_environment_metadata(con, tmp_mem / "membership.parquet")

        manifest_data = {
            "membership_id": mem_id,
            "snapshot_id": snapshot_id,
            "rule_sha256": rule_sha,
            "list_sha256": list_sha,
            "rule_version": rule_data.get("rule_version", "1.0.0"),
            "p0_status": p0_status,
            "counts": {
                "candidates": candidates_count,
                "unreviewed": unreviewed_count,
                "p0_in": p0_in,
                "p0_out": p0_out,
            },
            "outputs": sorted(outputs, key=lambda x: x["path"]),
            "environment": env_meta,
            "membership_details": manifest_mem_details,
            "warnings": warnings,
        }
        (tmp_mem / "manifest.json").write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        atomic_publish(tmp_mem, final_mem_dir)

        # Return details with resolved runtime candidate_report path
        ret_details = dict(manifest_mem_details)
        ret_details["candidate_report"] = str(final_mem_dir / "candidate-report.md")
        return ret_details, warnings
    except Exception:
        shutil.rmtree(tmp_mem, ignore_errors=True)
        raise
