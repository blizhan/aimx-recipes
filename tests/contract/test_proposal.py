"""Contract tests for ExperimentProposal schema, types, nullability, and Lead boundaries."""

import copy
import pytest
from aimx_recipes.validation import validate_record


def test_proposal_valid_nullable_decisions(load_fixture):
    record = load_fixture("us3/proposal_valid.json")
    res = validate_record(record)
    assert res.status == "valid"
    assert res.structurally_valid is True
    assert len(res.diagnostics) == 0


def test_proposal_rejects_non_integer_contract_version(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["experiment_contract"]["contract_version"] = 1.0  # Float 1.0 not exact int 1
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(d.code in ("type.invalid", "value.invalid") and "contract_version" in d.pointer for d in res.diagnostics)


def test_proposal_rejects_non_lead_review_status(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["review_status"] = "auto_admitted"
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(d.code == "value.invalid" and "review_status" in d.pointer for d in res.diagnostics)


def test_proposal_rejects_qualitative_resource_budget(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["experiment_contract"]["resources"] = [
        {
            "kind": "gpu_hours",
            "unit": "hours",
            "planned": "low",  # String instead of finite number
            "verification": "unverified",
            "enforcement": "declared_only",
        }
    ]
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(d.code == "type.invalid" and "planned" in d.pointer for d in res.diagnostics)


def test_proposal_verified_resource_requires_actual_and_source(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["experiment_contract"]["resources"] = [
        {
            "kind": "gpu_hours",
            "unit": "hours",
            "planned": 10.0,
            "verification": "verified",
            "enforcement": "declared_only",
            # missing actual and source!
        }
    ]
    res = validate_record(record)
    assert res.status == "invalid"
    assert any("verification" in d.check for d in res.diagnostics)


def test_proposal_executor_enforced_requires_verified(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["experiment_contract"]["resources"] = [
        {
            "kind": "gpu_hours",
            "unit": "hours",
            "planned": 10.0,
            "verification": "unverified",
            "enforcement": "executor_enforced",  # Requires verified!
        }
    ]
    res = validate_record(record)
    assert res.status == "invalid"
    assert any("enforcement" in d.check for d in res.diagnostics)


def test_proposal_multiple_interventions_require_confounders(load_fixture):
    record = copy.deepcopy(load_fixture("us3/proposal_valid.json"))
    record["experiment_contract"]["interventions"] = ["Intervention A", "Intervention B"]
    record["experiment_contract"]["confounders"] = []  # Empty confounders for multi-intervention!
    res = validate_record(record)
    assert res.status == "invalid"
    assert any("confounders" in d.check for d in res.diagnostics)
