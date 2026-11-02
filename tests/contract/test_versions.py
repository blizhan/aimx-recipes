"""Contract tests for schema versions, release declaration, and version dispatch."""

import pytest
from aimx_recipes.schema_registry import get_global_registry
from aimx_recipes.validation import validate_record


def test_release_ledger_contents():
    reg = get_global_registry()
    release = reg.get_release_data("2.0.0")

    assert release["schema_version"] == "2.0.0"
    assert release["vocabulary_version"] == "2.0.0"
    assert release["taxonomy_version"] == "2.0.0"
    assert release["compatibility"] == "breaking"
    assert "1.0.0" in release["rationale"]
    assert "frozen" in release["rationale"]
    assert release["extraction_regeneration"] == "not_applicable"
    assert release["aimx_contract_revision"] == "1b2dd98b6621aa893c056013cd0dd06fff7ca405"

    expected_entities = [
        "source",
        "document",
        "problem",
        "problem_profile",
        "recipe",
        "attempt",
        "evidence",
        "experiment_proposal",
    ]
    assert set(release["affected_entities"]) == set(expected_entities)


def test_unsupported_schema_version_rejected(load_fixture):
    record = load_fixture("us4/unsupported_version_record.json")
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(d.code == "version.unsupported" and d.pointer == "/schema_version" for d in res.diagnostics)


def test_previous_draft_version_is_not_silently_migrated(load_fixture):
    record = load_fixture("problem/valid.json")
    record["schema_version"] = "1.0.0"
    result = validate_record(record)
    assert result.status == "invalid"
    assert any(d.code == "version.unsupported" for d in result.diagnostics)


def test_missing_schema_version_rejected(load_fixture):
    record = load_fixture("us4/missing_version_record.json")
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(d.code == "field.required" and d.pointer == "/schema_version" for d in res.diagnostics)


def test_all_eight_entities_manifest_coverage(manifest):
    cases = manifest["cases"]
    entities = [
        "problem",
        "profile",
        "recipe",
        "source",
        "document",
        "attempt",
        "evidence",
        "proposal",
    ]
    for entity in entities:
        valid_case = f"{entity}_valid"
        invalid_case = f"{entity}_invalid"
        assert valid_case in cases, f"Manifest missing {valid_case}"
        assert invalid_case in cases, f"Manifest missing {invalid_case}"
        assert cases[valid_case]["expected_status"] == "valid"
        assert cases[invalid_case]["expected_status"] == "invalid"
