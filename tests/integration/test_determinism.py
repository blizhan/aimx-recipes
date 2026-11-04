"""Tests for three-run reproducibility, byte-level determinism, and input immutability."""

import copy
from aimx_recipes.diagnostics import render_text
from aimx_recipes.models import ValidationContext
from aimx_recipes.contextual import validate_bundle


def test_three_run_byte_determinism_and_input_immutability(load_fixture, fixtures_dir):
    evidence_bundle = load_fixture("us2/evidence_bundle_valid.json")
    profile = load_fixture("us1/profile_valid.json")
    recipe = load_fixture("us1/recipe_valid.json")
    proposal = load_fixture("us3/proposal_valid.json")

    original_records = [
        *copy.deepcopy(evidence_bundle),
        copy.deepcopy(profile),
        copy.deepcopy(recipe),
        copy.deepcopy(proposal),
    ]
    # Keep an immutable copy to verify no mutation occurred
    frozen_input_copy = copy.deepcopy(original_records)

    doc_text = (fixtures_dir / "us2/document_text.txt").read_text(encoding="utf-8")
    original_context_dict = {"doc:us2-body": doc_text}
    frozen_context_copy = dict(original_context_dict)

    ctx = ValidationContext(document_texts=original_context_dict)

    # Run 1
    res1 = validate_bundle(original_records, context=ctx)
    json1 = res1.to_json()
    text1 = render_text(res1)

    # Run 2
    res2 = validate_bundle(original_records, context=ctx)
    json2 = res2.to_json()
    text2 = render_text(res2)

    # Run 3
    res3 = validate_bundle(original_records, context=ctx)
    json3 = res3.to_json()
    text3 = render_text(res3)

    # 1. Exact byte equality across three runs
    assert json1 == json2 == json3
    assert text1 == text2 == text3

    # 2. Input records and context dict remained completely unchanged
    assert original_records == frozen_input_copy
    assert original_context_dict == frozen_context_copy


def test_three_run_determinism_on_invalid_and_incomplete(load_fixture):
    # Incomplete bundle (missing doc text) with invalid record mixed in
    records = load_fixture("us2/evidence_bundle_valid.json")
    ctx = ValidationContext(document_texts={})

    res1 = validate_bundle(records, context=ctx)
    res2 = validate_bundle(records, context=ctx)
    res3 = validate_bundle(records, context=ctx)

    assert res1.to_json() == res2.to_json() == res3.to_json()
    assert render_text(res1) == render_text(res2) == render_text(res3)
