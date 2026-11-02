"""Integration tests for evidence bundles, reference resolution, and quote verification."""

import copy
import hashlib
from pathlib import Path
import pytest
from aimx_recipes.models import ValidationContext
from aimx_recipes.contextual import validate_bundle
from aimx_recipes.validation import validate_record


def test_valid_evidence_bundle_with_context(load_fixture, fixtures_dir):
    records = load_fixture("us2/evidence_bundle_valid.json")
    doc_path = fixtures_dir / "us2/document_text.txt"
    doc_text = doc_path.read_text(encoding="utf-8")

    ctx = ValidationContext(document_texts={"doc:us2-body": doc_text})
    res = validate_bundle(records, context=ctx)

    assert res.level == "contextual"
    assert res.status == "valid"
    assert res.structurally_valid is True
    assert res.contextual_complete is True
    assert len(res.diagnostics) == 0


def test_missing_document_text_reports_incomplete(load_fixture):
    records = load_fixture("us2/evidence_bundle_valid.json")
    # Empty context: no document text provided
    ctx = ValidationContext(document_texts={})
    res = validate_bundle(records, context=ctx)

    assert res.level == "contextual"
    assert res.status == "incomplete"
    assert res.structurally_valid is True
    assert res.contextual_complete is False
    assert any(d.code == "context.document_text_missing" for d in res.diagnostics)


def test_document_hash_mismatch_fails(load_fixture):
    records = load_fixture("us2/evidence_bundle_valid.json")
    # Wrong text with different hash
    ctx = ValidationContext(document_texts={"doc:us2-body": "Different document body text."})
    res = validate_bundle(records, context=ctx)

    assert res.status == "invalid"
    assert any(d.code == "document.hash_mismatch" for d in res.diagnostics)


def test_attempt_without_evidence_fails(load_fixture, fixtures_dir):
    records = load_fixture("us2/evidence_bundle_valid.json")
    # Remove Evidence record
    records_no_ev = [r for r in records if r["entity_type"] != "evidence"]
    doc_text = (fixtures_dir / "us2/document_text.txt").read_text(encoding="utf-8")

    ctx = ValidationContext(document_texts={"doc:us2-body": doc_text})
    res = validate_bundle(records_no_ev, context=ctx)

    assert res.status == "invalid"
    assert any(d.code == "attempt.evidence_missing" for d in res.diagnostics)


def test_mapped_recipe_reference_in_bundle(load_fixture, fixtures_dir):
    records = copy.deepcopy(load_fixture("us2/evidence_bundle_valid.json"))
    recipe = load_fixture("us1/recipe_valid.json")
    # Set recipe_id on attempt to match recipe
    for r in records:
        if r["entity_type"] == "attempt":
            r["recipe_id"] = recipe["recipe_id"]

    bundle = [*records, recipe]
    doc_text = (fixtures_dir / "us2/document_text.txt").read_text(encoding="utf-8")
    ctx = ValidationContext(document_texts={"doc:us2-body": doc_text})

    res = validate_bundle(bundle, context=ctx)
    assert res.status == "valid"
    assert res.contextual_complete is True


def test_controlled_ablation_requires_comparison_within_quote():
    ev = {
        "schema_version": "2.0.0",
        "entity_type": "evidence",
        "evidence_id": "ev:bad-comp",
        "attempt_id": "att:1",
        "document_id": "doc:1",
        "type": "controlled_ablation",
        "outcome": "positive",
        "quote": "Method A outperforms Method B",
        "char_start": 0,
        "char_end": 29,
        "uncertainty": [],
        "comparison": {
            "baseline": "Nonexistent baseline",
            "candidate": "Method A",
        },
        "provenance": {
            "origin": "synthetic",
            "source_content_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "fixture_id": "fix:1",
        },
    }
    res = validate_record(ev)
    assert res.status == "invalid"
    assert any(d.code == "value.invalid" and "comparison" in d.check for d in res.diagnostics)


def test_attempt_scope_and_metric_conditional_requirements():
    # Candidate value supplied without evaluation scope and metric name must fail
    att = {
        "schema_version": "2.0.0",
        "entity_type": "attempt",
        "attempt_id": "att:bad-scope",
        "problem_id": "prob:1",
        "document_id": "doc:1",
        "recipe_id": None,
        "raw_method_name": "Test",
        "baseline_method": None,
        "candidate_method": "Candidate",
        "configuration": {},
        "validation_protocol": None,
        "evaluation_scope": None,  # Missing when candidate_value is present!
        "metric_name": None,
        "metric_direction": None,
        "baseline_value": None,
        "candidate_value": 0.45,
        "reported_delta": None,
        "joint_change": False,
        "joint_changes": [],
        "outcome": "positive",
        "confounders": [],
        "provenance": {
            "origin": "synthetic",
            "source_content_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "fixture_id": "fix:1",
        },
    }
    res = validate_record(att)
    assert res.status == "invalid"
    assert any(d.code == "attempt.scope_required" for d in res.diagnostics)
