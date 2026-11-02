"""Integration tests for Proposal bundles, hard-constraint coverage, and uncertainty consistency."""

import copy
import pytest
from aimx_recipes.models import ValidationContext
from aimx_recipes.contextual import validate_bundle


def _build_full_bundle(load_fixture, fixtures_dir):
    evidence_bundle = load_fixture("us2/evidence_bundle_valid.json")
    profile = load_fixture("us1/profile_valid.json")
    recipe = load_fixture("us1/recipe_valid.json")
    proposal = load_fixture("us3/proposal_valid.json")

    # Ensure attempt in evidence_bundle links to recipe
    records = []
    for r in evidence_bundle:
        if r["entity_type"] == "attempt":
            r_copy = copy.deepcopy(r)
            r_copy["recipe_id"] = recipe["recipe_id"]
            records.append(r_copy)
        else:
            records.append(r)

    records.extend([profile, recipe, proposal])
    doc_text = (fixtures_dir / "us2/document_text.txt").read_text(encoding="utf-8")
    ctx = ValidationContext(document_texts={"doc:us2-body": doc_text})
    return records, ctx


def test_valid_proposal_bundle(load_fixture, fixtures_dir):
    records, ctx = _build_full_bundle(load_fixture, fixtures_dir)
    res = validate_bundle(records, context=ctx)

    assert res.level == "contextual"
    assert res.status == "valid"
    assert res.contextual_complete is True
    assert len(res.diagnostics) == 0


def test_proposal_missing_hard_condition_assessment_fails(load_fixture, fixtures_dir):
    records, ctx = _build_full_bundle(load_fixture, fixtures_dir)
    # Remove one hard condition assessment
    proposal = [r for r in records if r["entity_type"] == "experiment_proposal"][0]
    proposal["match"]["assessments"] = [
        a for a in proposal["match"]["assessments"]
        if a["condition_id"] != "cond:no-target-leakage"
    ]

    res = validate_bundle(records, context=ctx)
    assert res.status == "invalid"
    assert any(d.code == "assessment.inconsistent" and "hard_constraint" in d.check for d in res.diagnostics)


def test_proposal_conflicted_facet_cannot_be_satisfied(load_fixture, fixtures_dir):
    records, ctx = _build_full_bundle(load_fixture, fixtures_dir)
    proposal = [r for r in records if r["entity_type"] == "experiment_proposal"][0]
    # Give the assessment a real condition whose facet has unresolved conflicts.
    profile = next(r for r in records if r["entity_type"] == "problem_profile")
    profile["hard_constraints"].append({
        "condition_id": "cond:non-stationarity-check",
        "facet": "characteristics.non_stationarity", "op": "eq", "operand": True,
    })
    proposal["match"]["assessments"].append(
        {
            "owner_type": "problem_profile",
            "owner_id": "prof:tab-forecasting-01",
            "condition_id": "cond:non-stationarity-check",
            "facet": "characteristics.non_stationarity",
            "state": "satisfied",
            "reason": "Asserted satisfied despite conflicts.",
        }
    )

    res = validate_bundle(records, context=ctx)
    assert res.status == "invalid"
    assert any(d.code == "assessment.inconsistent" and "uncertainty" in d.check for d in res.diagnostics)


def test_proposal_violated_condition_allowed_and_preserved(load_fixture, fixtures_dir):
    records, ctx = _build_full_bundle(load_fixture, fixtures_dir)
    proposal = [r for r in records if r["entity_type"] == "experiment_proposal"][0]
    # Change an assessment to violated
    for a in proposal["match"]["assessments"]:
        if a["condition_id"] == "cond:no-target-leakage":
            a["state"] = "violated"
            a["reason"] = "Method introduces slight target leakage risk."

    # A proposal with an explicitly reported violation is structurally and contextually valid
    # but retains requires_lead_review and state=violated
    res = validate_bundle(records, context=ctx)
    assert res.status == "valid"
    assert res.contextual_complete is True
