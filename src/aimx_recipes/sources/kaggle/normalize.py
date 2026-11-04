"""Corpus normalization, deduplication, identities, and contract records."""

from datetime import datetime
import hashlib
import json
from typing import Any, Sequence
from aimx_recipes.cli.output import ERR_DATE_UNPARSEABLE, ERR_CSV_MALFORMED
from aimx_recipes.sources.kaggle.inputs import InputError

ADAPTER_VERSION = "1.0.0"
NORMALIZATION_VERSION = "kaggle-text-1"
CONTRACT_SCHEMA_VERSION = "2.0.0"


class DateParseError(Exception):
    """Raised when a date cannot be parsed from Kaggle input format."""

    def __init__(
        self,
        message: str = "Failed to parse date value",
        code: str = ERR_DATE_UNPARSEABLE,
        file: str | None = None,
        line: int | None = None,
        record_id: str | None = None,
        column: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.file = file
        self.line = line
        self.record_id = record_id
        self.column = column


def text_sha256(text: str) -> str:
    """Return full sha256 hex digest of UTF-8 encoded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_hash_12(text: str) -> str:
    """Return first 12 hex characters of text sha256."""
    return text_sha256(text)[:12]


def compute_dedup_key(text: str) -> str:
    """Compute deduplication key: sha256 over trimmed, whitespace-collapsed text."""
    collapsed = " ".join(text.split())
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


def writeup_source_id(topic_id: int | str) -> str:
    """Return canonical Source ID for a writeup."""
    return f"kaggle:writeup:{topic_id}"


def competition_source_id(competition_id: int | str) -> str:
    """Return canonical Source ID for a competition."""
    return f"kaggle:competition:{competition_id}"


def problem_id(competition_id: int | str) -> str:
    """Return canonical Problem ID for a competition."""
    return f"kaggle:problem:{competition_id}"


def writeup_document_id(topic_id: int | str, text: str) -> str:
    """Return canonical Document ID for a writeup body."""
    return f"kaggle:writeup:{topic_id}:body:{text_hash_12(text)}"


def competition_document_id(competition_id: int | str, section: str, text: str) -> str:
    """Return canonical Document ID for a competition context section."""
    return f"kaggle:competition:{competition_id}:{section}:{text_hash_12(text)}"


def snapshot_id(inputs: Sequence[Any]) -> str:
    """Compute deterministic snapshot_id from canonical inputs and version constants."""
    sorted_inputs = sorted(
        [
            {
                "name": str(r.name if hasattr(r, "name") else r["name"]),
                "sha256": str(r.sha256 if hasattr(r, "sha256") else r["sha256"]),
            }
            for r in inputs
        ],
        key=lambda x: x["name"],
    )
    payload = {
        "adapter_version": ADAPTER_VERSION,
        "inputs": sorted_inputs,
        "normalization_version": NORMALIZATION_VERSION,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h16 = hashlib.sha256(raw).hexdigest()[:16]
    return f"meta-kaggle-{h16}"


def membership_id(rule_sha256: str, list_sha256: str, snapshot_id_val: str) -> str:
    """Compute deterministic membership_id from rule, list, and snapshot fingerprints."""
    payload = {
        "list_sha256": list_sha256,
        "rule_sha256": rule_sha256,
        "snapshot_id": snapshot_id_val,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h16 = hashlib.sha256(raw).hexdigest()[:16]
    return f"p0-{h16}"


def parse_kaggle_datetime(
    val: str | None,
    file: str | None = None,
    record_id: str | None = None,
    column: str | None = None,
) -> datetime | None:
    """Parse Kaggle timestamp format (%m/%d/%Y %H:%M:%S) as naive UTC datetime."""
    if val is None or not str(val).strip():
        return None
    s = str(val).strip()
    try:
        return datetime.strptime(s, "%m/%d/%Y %H:%M:%S")
    except ValueError as e:
        msg = f"Failed to parse date in column '{column}'" if column else "Failed to parse date value"
        raise DateParseError(
            message=msg,
            code=ERR_DATE_UNPARSEABLE,
            file=file,
            record_id=record_id,
            column=column,
        ) from None


def to_rfc3339_z(dt: datetime | None) -> str | None:
    """Format datetime as RFC 3339 string with Z suffix."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def map_medal(val: str | None) -> str | None:
    """Map medal value: 1->gold, 2->silver, 3->bronze, 0/empty->None."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "1":
        return "gold"
    if s == "2":
        return "silver"
    if s == "3":
        return "bronze"
    return None


def parse_rank(val: str | None) -> int | None:
    """Parse rank integer or None if absent."""
    if val is None:
        return None
    s = str(val).strip()
    return int(s) if s.isdigit() else None


def normalize_metric_label(eval_abbr: str | None, eval_name: str | None) -> str:
    """Determine metric label: abbreviation unless numeric or empty, else name."""
    abbr = (eval_abbr or "").strip()
    name = (eval_name or "").strip()
    if abbr and not abbr.isdigit():
        return abbr
    return name


def normalize_competition_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a competition context row."""
    cid = int(raw["competition_id"])
    slug = raw["slug"]
    eval_abbr = raw.get("eval_abbr") or ""
    eval_name = raw.get("eval_name") or ""
    metric_label = normalize_metric_label(eval_abbr, eval_name)

    eval_is_max_raw = raw.get("eval_is_max")
    if eval_is_max_raw is None or str(eval_is_max_raw).strip() == "":
        higher_is_better = None
    else:
        norm_bool = str(eval_is_max_raw).strip().lower()
        if norm_bool in ("true", "1", "t"):
            higher_is_better = True
        elif norm_bool in ("false", "0", "f"):
            higher_is_better = False
        else:
            raise DateParseError(
                message="Invalid boolean value in 'EvaluationAlgorithmIsMax'",
                file="Competitions.csv",
                record_id=str(cid),
                column="EvaluationAlgorithmIsMax",
            )

    return {
        "competition_id": cid,
        "slug": slug,
        "source_id": competition_source_id(cid),
        "problem_id": problem_id(cid),
        "title": raw.get("title") or "",
        "subtitle": raw.get("subtitle") or None,
        "url": f"https://www.kaggle.com/competitions/{slug}",
        "host_segment": raw.get("host_segment") or None,
        "enabled_at": parse_kaggle_datetime(
            raw.get("enabled_date"),
            file="Competitions.csv",
            record_id=str(cid),
            column="EnabledDate",
        ),
        "deadline_at": parse_kaggle_datetime(
            raw.get("deadline_date"),
            file="Competitions.csv",
            record_id=str(cid),
            column="DeadlineDate",
        ),
        "metric_abbreviation": eval_abbr,
        "metric_name": eval_name,
        "metric_label": metric_label,
        "higher_is_better": higher_is_better,
        "competition_data_license": raw.get("license_name") or None,
        "tag_ids": list(raw.get("tag_ids") or []),
        "tag_names": list(raw.get("tag_names") or []),
        "writeup_refs": int(raw.get("writeup_refs", 0)),
        "writeups_ingested": int(raw.get("writeups_ingested", 0)),
        # Raw texts for documents
        "overview": raw.get("overview") or None,
        "eval_desc": raw.get("eval_desc") or None,
        "dataset_desc": raw.get("dataset_desc") or None,
    }


def normalize_writeup_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a writeup row with selected body, length, short flag, and outcomes."""
    topic_id = int(raw["topic_id"])
    raw_md = raw.get("raw_markdown") or ""
    msg = raw.get("message") or ""

    if raw_md != "":
        body_format = "markdown"
        text = raw_md
    elif msg != "":
        body_format = "html"
        text = msg
    else:
        body_format = "empty"
        text = ""

    char_count = len(text)
    is_short = char_count < 200

    msg_id_raw = raw.get("message_id")
    if msg_id_raw is not None:
        try:
            msg_id_val = int(msg_id_raw)
        except (ValueError, TypeError):
            raise InputError(
                code=ERR_CSV_MALFORMED,
                file="ForumMessages.csv",
                column="Id",
                record_id=str(topic_id),
                message="Invalid integer in column 'Id' of 'ForumMessages.csv'",
            ) from None
    else:
        msg_id_val = None

    return {
        "source_id": writeup_source_id(topic_id),
        "document_id": writeup_document_id(topic_id, text) if text else "",
        "topic_id": topic_id,
        "message_id": msg_id_val,
        "team_id": int(raw["team_id"]),
        "competition_id": int(raw["competition_id"]),
        "topic_title": raw.get("topic_title") or "",
        "posted_at": parse_kaggle_datetime(
            raw.get("post_date"),
            file="ForumMessages.csv",
            record_id=str(msg_id_val or topic_id),
            column="PostDate",
        ),
        "body_format": body_format,
        "char_count": char_count,
        "is_short": is_short,
        "medal": map_medal(raw.get("medal_raw")),
        "public_rank": parse_rank(raw.get("public_rank_raw")),
        "private_rank": parse_rank(raw.get("private_rank_raw")),
        "dedup_key": compute_dedup_key(text) if text else "",
        "mirror_topic_ids": [],
        "text": text,
    }


def build_writeup_source(
    topic_id: int | str,
    slug: str,
    snapshot_id: str,
    text: str,
    posted_at: datetime | None,
    mirrors: list[str] | None = None,
) -> dict[str, Any]:
    """Build contract Source record for a writeup."""
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "entity_type": "source",
        "source_id": writeup_source_id(topic_id),
        "snapshot_id": snapshot_id,
        "kind": "writeup",
        "canonical_ref": f"https://www.kaggle.com/competitions/{slug}/discussion/{topic_id}",
        "license": {
            "status": "permissive",
            "identifier": "Apache-2.0",
            "attribution": "Meta Kaggle (Kaggle), Apache-2.0",
        },
        "content_sha256": text_sha256(text),
        "published_at": to_rfc3339_z(posted_at),
        "mirrors": sorted(mirrors or []),
    }


def build_writeup_document(
    topic_id: int | str,
    snapshot_id: str,
    text: str,
    title: str,
) -> dict[str, Any]:
    """Build contract Document record for a writeup body."""
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "entity_type": "document",
        "document_id": writeup_document_id(topic_id, text),
        "source_id": writeup_source_id(topic_id),
        "snapshot_id": snapshot_id,
        "section": "writeup_body",
        "content_sha256": text_sha256(text),
        "normalization_version": NORMALIZATION_VERSION,
        "title": title or "Writeup",
    }


def build_competition_source(
    competition_id: int | str,
    slug: str,
    snapshot_id: str,
    section_texts: dict[str, str],
    enabled_at: datetime | None,
) -> dict[str, Any]:
    """Build contract Source record for a competition page."""
    content_map = {sec: text_sha256(txt) for sec, txt in sorted(section_texts.items())}
    c_raw = json.dumps(content_map, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    c_sha = hashlib.sha256(c_raw).hexdigest()

    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "entity_type": "source",
        "source_id": competition_source_id(competition_id),
        "snapshot_id": snapshot_id,
        "kind": "competition_page",
        "canonical_ref": f"https://www.kaggle.com/competitions/{slug}",
        "license": {
            "status": "permissive",
            "identifier": "Apache-2.0",
            "attribution": "Meta Kaggle (Kaggle), Apache-2.0",
        },
        "content_sha256": c_sha,
        "published_at": to_rfc3339_z(enabled_at),
        "mirrors": [],
    }


def build_competition_documents(
    competition_id: int | str,
    snapshot_id: str,
    title: str,
    section_texts: dict[str, str],
) -> list[dict[str, Any]]:
    """Build contract Document records for competition context sections."""
    docs: list[dict[str, Any]] = []
    for sec, txt in sorted(section_texts.items()):
        if txt and txt.strip():
            docs.append(
                {
                    "schema_version": CONTRACT_SCHEMA_VERSION,
                    "entity_type": "document",
                    "document_id": competition_document_id(competition_id, sec, txt),
                    "source_id": competition_source_id(competition_id),
                    "snapshot_id": snapshot_id,
                    "section": sec,
                    "content_sha256": text_sha256(txt),
                    "normalization_version": NORMALIZATION_VERSION,
                    "title": title or "Competition",
                }
            )
    return docs


def build_competition_problem(
    competition_id: int | str,
    title: str,
    subtitle: str | None,
    deadline_at: datetime | None,
    source_ids: Sequence[str],
) -> dict[str, Any]:
    """Build contract Problem record for a competition."""
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "entity_type": "problem",
        "problem_id": problem_id(competition_id),
        "kind": "competition",
        "title": title or f"Competition {competition_id}",
        "source_ids": sorted(list(set(source_ids))),
        "description": subtitle or None,
        "as_of": to_rfc3339_z(deadline_at),
    }


def build_contract_records(
    snapshot_id: str,
    competitions_rows: list[dict[str, Any]],
    writeup_refs_rows: list[dict[str, Any]],
    writeups_rows: list[dict[str, Any]],
    documents_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build canonical 001 contract records: Sources, Documents, Problems."""
    comp_by_id = {c["competition_id"]: c for c in competitions_rows}
    doc_by_id = {d["document_id"]: d for d in documents_rows}

    # Reference map for writeup canonical refs
    ref_by_topic = {r["topic_id"]: r for r in writeup_refs_rows}

    sources: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []

    # 1. Writeup Sources & Documents
    for w in writeups_rows:
        cid = w["competition_id"]
        slug = comp_by_id[cid]["slug"]
        tid = w["topic_id"]
        w_doc = doc_by_id[w["document_id"]]
        w_text = w_doc["text"]

        # Compute mirror canonical refs
        mirrors = []
        for m_tid in w.get("mirror_topic_ids") or []:
            m_ref = ref_by_topic.get(m_tid)
            if m_ref:
                m_slug = comp_by_id[m_ref["competition_id"]]["slug"]
                mirrors.append(
                    f"https://www.kaggle.com/competitions/{m_slug}/discussion/{m_tid}"
                )

        src = build_writeup_source(
            topic_id=tid,
            slug=slug,
            snapshot_id=snapshot_id,
            text=w_text,
            posted_at=w.get("posted_at"),
            mirrors=mirrors,
        )
        sources.append(src)

        doc = build_writeup_document(
            topic_id=tid,
            snapshot_id=snapshot_id,
            text=w_text,
            title=w.get("topic_title") or "Writeup",
        )
        documents.append(doc)

    # 2. Competition Sources, Documents, and Problems
    for c in competitions_rows:
        cid = c["competition_id"]
        slug = c["slug"]
        title = c.get("title") or "Competition"

        # Find all documents belonging to this competition
        c_docs = [d for d in documents_rows if d["source_id"] == c["source_id"]]
        sec_texts = {d["section"]: d["text"] for d in c_docs}

        c_src = build_competition_source(
            competition_id=cid,
            slug=slug,
            snapshot_id=snapshot_id,
            section_texts=sec_texts,
            enabled_at=c.get("enabled_at"),
        )
        sources.append(c_src)

        for d in c_docs:
            documents.append(
                {
                    "schema_version": CONTRACT_SCHEMA_VERSION,
                    "entity_type": "document",
                    "document_id": d["document_id"],
                    "source_id": c["source_id"],
                    "snapshot_id": snapshot_id,
                    "section": d["section"],
                    "content_sha256": d["content_sha256"],
                    "normalization_version": NORMALIZATION_VERSION,
                    "title": title,
                }
            )

        # Problem source_ids: competition source + all writeup sources referenced by this competition
        comp_refs = [
            r
            for r in writeup_refs_rows
            if r["competition_id"] == cid and r.get("source_id")
        ]
        p_sources = [c["source_id"]] + [r["source_id"] for r in comp_refs]

        prob = build_competition_problem(
            competition_id=cid,
            title=title,
            subtitle=c.get("subtitle"),
            deadline_at=c.get("deadline_at"),
            source_ids=p_sources,
        )
        problems.append(prob)

    sources.sort(key=lambda x: x["source_id"])
    documents.sort(key=lambda x: x["document_id"])
    problems.sort(key=lambda x: x["problem_id"])

    return sources, documents, problems


def build_adapter_tables(
    raw_refs: list[dict[str, Any]],
    raw_comps: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Build the four snapshot adapter tables: competitions, writeup_refs, writeups, documents.

    Returns:
        (competitions_rows, writeup_refs_rows, writeups_rows, documents_rows)
    """
    writeup_refs_rows: list[dict[str, Any]] = []
    writeups_rows: list[dict[str, Any]] = []
    documents_rows: list[dict[str, Any]] = []

    # 1. Separate ingested and excluded references
    ingested_raw: list[dict[str, Any]] = []
    for r in raw_refs:
        if r["disposition"] == "excluded":
            writeup_refs_rows.append(
                {
                    "topic_id": r["topic_id"],
                    "team_id": r["team_id"],
                    "competition_id": r["competition_id"],
                    "message_id": r["message_id"],
                    "disposition": "excluded",
                    "exclusion_reason": r["exclusion_reason"],
                    "source_id": None,
                }
            )
        else:
            ingested_raw.append(r)

    # 2. Group ingested writeups by dedup_key
    dedup_groups: dict[str, list[dict[str, Any]]] = {}
    for r in ingested_raw:
        w_norm = normalize_writeup_row(r)
        d_key = w_norm["dedup_key"]
        if d_key not in dedup_groups:
            dedup_groups[d_key] = []
        dedup_groups[d_key].append(w_norm)

    # 3. For each group, canonical is lowest topic_id
    for d_key, group in dedup_groups.items():
        group.sort(key=lambda x: x["topic_id"])
        canonical = group[0]
        canonical_source_id = canonical["source_id"]
        canonical_doc_id = canonical["document_id"]
        mirror_topic_ids = [m["topic_id"] for m in group[1:]]

        canonical["mirror_topic_ids"] = mirror_topic_ids
        canonical_copy = dict(canonical)
        raw_text = canonical_copy.pop("text", "")
        writeups_rows.append(canonical_copy)

        # Add canonical writeup document
        documents_rows.append(
            {
                "document_id": canonical_doc_id,
                "source_id": canonical_source_id,
                "section": "writeup_body",
                "text": raw_text,
                "content_sha256": text_sha256(raw_text),
                "char_count": canonical["char_count"],
            }
        )

        # Add to writeup_refs_rows
        # First is ingested
        writeup_refs_rows.append(
            {
                "topic_id": canonical["topic_id"],
                "team_id": canonical["team_id"],
                "competition_id": canonical["competition_id"],
                "message_id": canonical["message_id"],
                "disposition": "ingested",
                "exclusion_reason": None,
                "source_id": canonical_source_id,
            }
        )
        # Subsequent are mirrors
        for m in group[1:]:
            writeup_refs_rows.append(
                {
                    "topic_id": m["topic_id"],
                    "team_id": m["team_id"],
                    "competition_id": m["competition_id"],
                    "message_id": m["message_id"],
                    "disposition": "mirror",
                    "exclusion_reason": None,
                    "source_id": canonical_source_id,
                }
            )

    # Sort writeup_refs by topic_id, team_id
    writeup_refs_rows.sort(key=lambda x: (x["topic_id"], x["team_id"]))
    writeups_rows.sort(key=lambda x: x["source_id"])

    # 4. Competitions and competition documents
    competitions_rows: list[dict[str, Any]] = []
    for c_raw in raw_comps:
        c_norm = normalize_competition_row(c_raw)
        cid = c_norm["competition_id"]
        c_refs = [r for r in writeup_refs_rows if r["competition_id"] == cid]
        c_norm["writeup_refs"] = len(c_refs)
        c_norm["writeups_ingested"] = sum(
            1 for r in c_refs if r["disposition"] == "ingested"
        )

        overview_text = c_norm.pop("overview", None)
        eval_desc_text = c_norm.pop("eval_desc", None)
        dataset_desc_text = c_norm.pop("dataset_desc", None)

        competitions_rows.append(c_norm)

        c_source_id = c_norm["source_id"]
        if overview_text and overview_text.strip():
            doc_id = competition_document_id(cid, "competition_overview", overview_text)
            documents_rows.append(
                {
                    "document_id": doc_id,
                    "source_id": c_source_id,
                    "section": "competition_overview",
                    "text": overview_text,
                    "content_sha256": text_sha256(overview_text),
                    "char_count": len(overview_text),
                }
            )
        if eval_desc_text and eval_desc_text.strip():
            doc_id = competition_document_id(
                cid, "competition_evaluation_metric", eval_desc_text
            )
            documents_rows.append(
                {
                    "document_id": doc_id,
                    "source_id": c_source_id,
                    "section": "competition_evaluation_metric",
                    "text": eval_desc_text,
                    "content_sha256": text_sha256(eval_desc_text),
                    "char_count": len(eval_desc_text),
                }
            )
        if dataset_desc_text and dataset_desc_text.strip():
            doc_id = competition_document_id(
                cid, "competition_dataset_description", dataset_desc_text
            )
            documents_rows.append(
                {
                    "document_id": doc_id,
                    "source_id": c_source_id,
                    "section": "competition_dataset_description",
                    "text": dataset_desc_text,
                    "content_sha256": text_sha256(dataset_desc_text),
                    "char_count": len(dataset_desc_text),
                }
            )

    competitions_rows.sort(key=lambda x: x["competition_id"])
    documents_rows.sort(key=lambda x: x["document_id"])

    return competitions_rows, writeup_refs_rows, writeups_rows, documents_rows
