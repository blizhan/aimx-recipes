"""Contract tests for foundation schemas (Draft 2020-12 meta-validation) and Problem entity fixtures."""

from jsonschema import Draft202012Validator
from aimx_recipes.schema_registry import get_global_registry
from aimx_recipes.validation import validate_record


def test_schema_meta_validation():
    registry = get_global_registry()
    for filename in [
        "common.schema.json",
        "problem.schema.json",
        "validation-result.schema.json",
    ]:
        schema = registry.get_raw_resource("2.0.0", filename)
        # Verify schema is valid Draft 2020-12
        Draft202012Validator.check_schema(schema)


def test_problem_fixtures_against_manifest(manifest, load_fixture):
    for case_id, case_info in manifest["cases"].items():
        if not case_id.startswith("problem_"):
            continue
        record = load_fixture(case_info["input_path"])
        result = validate_record(record)

        assert result.level == case_info["expected_level"]
        assert result.status == case_info["expected_status"]

        expected_diags = case_info["expected_diagnostics"]
        if not expected_diags:
            assert len(result.diagnostics) == 0
            assert result.structurally_valid is True
        else:
            assert len(result.diagnostics) > 0
            assert result.structurally_valid is False
            for exp in expected_diags:
                assert any(
                    d.code == exp["code"] and d.pointer == exp["pointer"]
                    for d in result.diagnostics
                ), f"Case {case_id} missing diagnostic {exp} in {result.diagnostics}"
