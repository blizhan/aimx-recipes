"""Unit tests for Unicode quote span verification, limits, and hash verification."""

import hashlib
from aimx_recipes.models import ValidationContext
from aimx_recipes.contextual import validate_bundle


def test_quote_exact_500_chars_passes_501_fails():
    doc_text = "A" * 501
    doc_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()

    doc_record = {
        "schema_version": "2.0.0",
        "entity_type": "document",
        "document_id": "doc:1",
        "source_id": "src:1",
        "snapshot_id": "snap:1",
        "section": "body",
        "content_sha256": doc_hash,
        "normalization_version": "2.0.0",
    }
    src_record = {
        "schema_version": "2.0.0",
        "entity_type": "source",
        "source_id": "src:1",
        "kind": "writeup",
        "canonical_ref": "https://example.com",
        "license": {"status": "unknown", "identifier": None, "attribution": None},
        "snapshot_id": "snap:1",
        "content_sha256": doc_hash,
    }
    prob_record = {
        "schema_version": "2.0.0",
        "entity_type": "problem",
        "problem_id": "prob:1",
        "kind": "competition",
        "title": "Tabular Problem",
        "source_ids": ["src:1"],
    }
    attempt_record = {
        "schema_version": "2.0.0",
        "entity_type": "attempt",
        "attempt_id": "att:1",
        "problem_id": "prob:1",
        "document_id": "doc:1",
        "recipe_id": None,
        "raw_method_name": "Lags",
        "baseline_method": None,
        "candidate_method": "Hourly Lags",
        "configuration": {},
        "validation_protocol": None,
        "evaluation_scope": None,
        "metric_name": None,
        "metric_direction": None,
        "baseline_value": None,
        "candidate_value": None,
        "reported_delta": None,
        "joint_change": False,
        "joint_changes": [],
        "outcome": "positive",
        "confounders": [],
        "provenance": {
            "origin": "synthetic",
            "source_content_sha256": doc_hash,
            "fixture_id": "fix:1",
        },
    }

    # 500 chars quote
    ev_500 = {
        "schema_version": "2.0.0",
        "entity_type": "evidence",
        "evidence_id": "ev:500",
        "attempt_id": "att:1",
        "document_id": "doc:1",
        "type": "reported_gain",
        "outcome": "positive",
        "quote": "A" * 500,
        "char_start": 0,
        "char_end": 500,
        "uncertainty": [],
        "comparison": None,
        "provenance": {
            "origin": "synthetic",
            "source_content_sha256": doc_hash,
            "fixture_id": "fix:1",
        },
    }

    ctx = ValidationContext(document_texts={"doc:1": doc_text})
    res_500 = validate_bundle(
        [src_record, doc_record, prob_record, attempt_record, ev_500], context=ctx
    )
    assert res_500.status == "valid"

    # 501 chars quote
    ev_501 = dict(ev_500)
    ev_501["evidence_id"] = "ev:501"
    ev_501["quote"] = "A" * 501
    ev_501["char_end"] = 501
    res_501 = validate_bundle(
        [src_record, doc_record, prob_record, attempt_record, ev_501], context=ctx
    )
    assert res_501.status == "invalid"
    assert any(d.code == "quote.too_long" for d in res_501.diagnostics)


def test_quote_mismatch_and_no_search_or_repair():
    doc_text = "The quick brown fox jumps over the lazy dog."
    doc_hash = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()

    records = [
        {
            "schema_version": "2.0.0",
            "entity_type": "source",
            "source_id": "src:1",
            "kind": "writeup",
            "canonical_ref": "https://example.com",
            "license": {"status": "unknown", "identifier": None, "attribution": None},
            "snapshot_id": "snap:1",
            "content_sha256": doc_hash,
        },
        {
            "schema_version": "2.0.0",
            "entity_type": "document",
            "document_id": "doc:1",
            "source_id": "src:1",
            "snapshot_id": "snap:1",
            "section": "body",
            "content_sha256": doc_hash,
            "normalization_version": "2.0.0",
        },
        {
            "schema_version": "2.0.0",
            "entity_type": "problem",
            "problem_id": "prob:1",
            "kind": "competition",
            "title": "Fox Problem",
            "source_ids": ["src:1"],
        },
        {
            "schema_version": "2.0.0",
            "entity_type": "attempt",
            "attempt_id": "att:1",
            "problem_id": "prob:1",
            "document_id": "doc:1",
            "recipe_id": None,
            "raw_method_name": "Fox Method",
            "baseline_method": None,
            "candidate_method": "Fast Fox",
            "configuration": {},
            "validation_protocol": None,
            "evaluation_scope": None,
            "metric_name": None,
            "metric_direction": None,
            "baseline_value": None,
            "candidate_value": None,
            "reported_delta": None,
            "joint_change": False,
            "joint_changes": [],
            "outcome": "positive",
            "confounders": [],
            "provenance": {
                "origin": "synthetic",
                "source_content_sha256": doc_hash,
                "fixture_id": "fix:1",
            },
        },
        {
            "schema_version": "2.0.0",
            "entity_type": "evidence",
            "evidence_id": "ev:1",
            "attempt_id": "att:1",
            "document_id": "doc:1",
            "type": "reported_gain",
            "outcome": "positive",
            # Mismatched quote (different whitespace / punctuation)
            "quote": "brown fox  jumps",
            "char_start": 10,
            "char_end": 26,
            "uncertainty": [],
            "comparison": None,
            "provenance": {
                "origin": "synthetic",
                "source_content_sha256": doc_hash,
                "fixture_id": "fix:1",
            },
        },
    ]

    ctx = ValidationContext(document_texts={"doc:1": doc_text})
    res = validate_bundle(records, context=ctx)
    assert res.status == "invalid"
    assert any(d.code == "quote.mismatch" for d in res.diagnostics)
