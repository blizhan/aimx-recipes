"""Contract tests for entity schemas (valid/invalid pairs, closed objects, exact fields)."""

import pytest
from aimx_recipes.validation import validate_record

KNOWN_PREFIXES = (
    "problem_",
    "profile_",
    "recipe_",
    "source_",
    "document_",
    "attempt_",
    "evidence_",
    "proposal_",
)


def test_entities_fixtures_against_manifest(manifest, load_fixture):
    for case_id, case_info in manifest["cases"].items():
        if not any(case_id.startswith(p) for p in KNOWN_PREFIXES):
            continue
        record = load_fixture(case_info["input_path"])
        result = validate_record(record)

        assert result.level == case_info["expected_level"]
        assert result.status == case_info["expected_status"]

        expected_diags = case_info["expected_diagnostics"]
        if not expected_diags:
            assert len(result.diagnostics) == 0, f"Case {case_id} had unexpected diagnostics: {result.diagnostics}"
            assert result.structurally_valid is True
        else:
            assert len(result.diagnostics) > 0, f"Case {case_id} expected diagnostics but got none"
            assert result.structurally_valid is False
            for exp in expected_diags:
                assert any(
                    d.code == exp["code"] and d.pointer == exp["pointer"]
                    for d in result.diagnostics
                ), f"Case {case_id} missing diagnostic {exp} in {result.diagnostics}"
