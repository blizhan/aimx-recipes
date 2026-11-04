"""Unit tests for contract record builders (001 v2.0.0)."""

from datetime import datetime
from aimx_recipes import validate_record
from aimx_recipes.sources.kaggle.normalize import (
    build_competition_documents,
    build_competition_problem,
    build_competition_source,
    build_writeup_document,
    build_writeup_source,
)


def test_build_writeup_source_and_document():
    topic_id = 1001
    slug = "comp-101-tag-in"
    snap_id = "meta-kaggle-1234567812345678"
    text = "First place solution body text"
    posted_at = datetime(2024, 4, 16, 14, 30, 0)
    mirrors = ["https://www.kaggle.com/competitions/comp-102-modality/discussion/1002"]

    w_src = build_writeup_source(
        topic_id=topic_id,
        slug=slug,
        snapshot_id=snap_id,
        text=text,
        posted_at=posted_at,
        mirrors=mirrors,
    )
    assert w_src["schema_version"] == "2.0.0"
    assert w_src["entity_type"] == "source"
    assert w_src["kind"] == "writeup"
    assert (
        w_src["canonical_ref"]
        == f"https://www.kaggle.com/competitions/{slug}/discussion/{topic_id}"
    )
    assert w_src["license"] == {
        "status": "permissive",
        "identifier": "Apache-2.0",
        "attribution": "Meta Kaggle (Kaggle), Apache-2.0",
    }
    assert w_src["published_at"] == "2024-04-16T14:30:00Z"
    assert w_src["mirrors"] == mirrors

    v_src = validate_record(w_src)
    assert v_src.status == "valid", f"Source invalid: {v_src.diagnostics}"

    w_doc = build_writeup_document(
        topic_id=topic_id,
        snapshot_id=snap_id,
        text=text,
        title="Solution 1001",
    )
    assert w_doc["schema_version"] == "2.0.0"
    assert w_doc["entity_type"] == "document"
    assert w_doc["section"] == "writeup_body"
    assert w_doc["normalization_version"] == "kaggle-text-1"
    assert w_doc["content_sha256"] == w_src["content_sha256"]

    v_doc = validate_record(w_doc)
    assert v_doc.status == "valid", f"Doc invalid: {v_doc.diagnostics}"

    # S-02: Missing posted_at stays None (not masked as 1970) and is valid under 001 contract
    w_src_no_date = build_writeup_source(
        topic_id=topic_id,
        slug=slug,
        snapshot_id=snap_id,
        text=text,
        posted_at=None,
    )
    assert w_src_no_date["published_at"] is None
    v_src_no_date = validate_record(w_src_no_date)
    assert v_src_no_date.status == "valid"


def test_build_competition_source_document_problem():
    cid = 101
    slug = "comp-101-tag-in"
    snap_id = "meta-kaggle-1234567812345678"
    enabled_at = datetime(2024, 1, 15, 10, 0, 0)
    deadline_at = datetime(2024, 4, 15, 23, 59, 0)

    section_texts = {
        "competition_overview": "Overview text",
        "competition_evaluation_metric": "Metric text",
    }

    c_src = build_competition_source(
        competition_id=cid,
        slug=slug,
        snapshot_id=snap_id,
        section_texts=section_texts,
        enabled_at=enabled_at,
    )
    assert c_src["kind"] == "competition_page"
    assert c_src["canonical_ref"] == f"https://www.kaggle.com/competitions/{slug}"
    assert c_src["published_at"] == "2024-01-15T10:00:00Z"
    assert c_src["mirrors"] == []

    v_src = validate_record(c_src)
    assert v_src.status == "valid", f"Comp source invalid: {v_src.diagnostics}"

    # S-02: Missing enabled_at stays None (not masked as 1970) and is valid under 001 contract
    c_src_no_date = build_competition_source(
        competition_id=cid,
        slug=slug,
        snapshot_id=snap_id,
        section_texts=section_texts,
        enabled_at=None,
    )
    assert c_src_no_date["published_at"] is None
    v_src_no_date = validate_record(c_src_no_date)
    assert v_src_no_date.status == "valid"

    c_docs = build_competition_documents(
        competition_id=cid,
        snapshot_id=snap_id,
        title="Comp 101",
        section_texts=section_texts,
    )
    assert len(c_docs) == 2
    for d in c_docs:
        v_d = validate_record(d)
        assert v_d.status == "valid"

    prob = build_competition_problem(
        competition_id=cid,
        title="Comp 101",
        subtitle="Subtitle 101",
        deadline_at=deadline_at,
        source_ids=["kaggle:competition:101", "kaggle:writeup:1001"],
    )
    assert prob["schema_version"] == "2.0.0"
    assert prob["entity_type"] == "problem"
    assert prob["kind"] == "competition"
    assert prob["as_of"] == "2024-04-15T23:59:00Z"
    assert prob["source_ids"] == ["kaggle:competition:101", "kaggle:writeup:1001"]

    v_prob = validate_record(prob)
    assert v_prob.status == "valid", f"Problem invalid: {v_prob.diagnostics}"
