"""Regression cases from the spec001 completion review."""

import os
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from aimx_recipes import parse_record, render_text, validate_record
from aimx_recipes.contextual import validate_bundle
from aimx_recipes.models import ValidationContext
from aimx_recipes.schema_registry import get_global_registry


@pytest.fixture
def proposal_bundle(load_fixture, fixtures_dir):
    records = load_fixture("us2/evidence_bundle_valid.json")
    profile = load_fixture("us1/profile_valid.json")
    recipe = load_fixture("us1/recipe_valid.json")
    proposal = load_fixture("us3/proposal_valid.json")
    for record in records:
        if record["entity_type"] == "attempt":
            record["recipe_id"] = recipe["recipe_id"]
    records.extend([profile, recipe, proposal])
    context = ValidationContext(document_texts={
        "doc:us2-body": (fixtures_dir / "us2/document_text.txt").read_text()
    })
    return records, context


def test_seven_evidence_types_have_linked_acceptance_examples(manifest, load_fixture, fixtures_dir):
    expected = {
        "controlled_ablation", "reported_gain", "reported_failure", "used_in_solution",
        "attempted", "author_opinion", "independently_reproduced",
    }
    seen = set()
    for case in manifest["cases"].values():
        if not case["case_id"].startswith("us2_type_"):
            continue
        records = load_fixture(case["input_path"])
        text = (fixtures_dir / case["context_path"]).read_text()
        document = next(r for r in records if r["entity_type"] == "document")
        evidence = next(r for r in records if r["entity_type"] == "evidence")
        attempt = next(r for r in records if r["entity_type"] == "attempt")
        result = validate_bundle(records, context=ValidationContext(document_texts={document["document_id"]: text}))
        assert result.status == case["expected_status"] == "valid"
        assert result.level == case["expected_level"] == "contextual"
        assert not result.diagnostics
        seen.add(evidence["type"])
        if evidence["type"] == "controlled_ablation":
            assert evidence["outcome"] == "negative"
        if evidence["type"] == "used_in_solution":
            assert evidence["outcome"] == "unclear"
            assert attempt["candidate_value"] is None
    assert seen == expected


def test_registry_rejects_invalid_vocabulary_at_load(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path
    from jsonschema.exceptions import ValidationError
    import aimx_recipes.schema_registry as registry_module

    root = tmp_path / "schemas"
    shutil.copytree(Path(__file__).resolve().parents[2] / "schemas", root)
    resource = root / "2.0.0" / "facet-vocabulary.json"
    resource.write_text('{"schema_version": "2.0.0"}')
    monkeypatch.setattr(registry_module, "_find_schemas_root", lambda: root)
    with pytest.raises(ValidationError):
        registry_module.SchemaRegistry()


def test_registry_never_falls_back_to_checkout(monkeypatch):
    from pathlib import Path
    import aimx_recipes.schema_registry as registry_module

    monkeypatch.setattr(registry_module.importlib.resources, "files", lambda _: Path("/absent/package"))
    with pytest.raises(RuntimeError, match="Packaged schema resources"):
        registry_module.SchemaRegistry()


def test_versioned_vocabulary_resources_validate():
    registry = get_global_registry()
    for name in ("facet-vocabulary", "action-taxonomy"):
        schema = registry.get_raw_resource("2.0.0", f"{name}.schema.json")
        data = registry.get_raw_resource("2.0.0", f"{name}.json")
        Draft202012Validator(schema).validate(data)


@pytest.mark.parametrize("value", [object(), (1, 2), {1, 2}, "\ud800", {"\ud800": "x"}])
def test_non_json_configuration_is_rejected(load_fixture, value):
    recipe = load_fixture("us1/recipe_valid.json")
    recipe["configuration"] = {"x": value}
    result = validate_record(recipe)
    assert result.status == "invalid"
    assert any(d.check == "json_domain" for d in result.diagnostics)
    result.to_json().encode("utf-8")


@pytest.mark.parametrize("value", [[], None, 1, "record"])
def test_non_object_record_returns_diagnostic(value):
    result = validate_record(value)
    assert result.status == "invalid"
    assert any(d.pointer == "" and d.code == "type.invalid" for d in result.diagnostics)


def test_overflowed_json_number_is_rejected_during_parsing():
    result = parse_record('{"overflow": 1e999}')
    assert result.record is None
    assert any(d.code == "parse.invalid_json" for d in result.diagnostics)


def test_cyclic_metadata_is_not_json(load_fixture):
    recipe = load_fixture("us1/recipe_valid.json")
    recipe["configuration"]["cycle"] = recipe
    result = validate_record(recipe)
    assert result.status == "invalid"
    assert any(d.pointer == "/configuration/cycle" and d.check == "json_domain" for d in result.diagnostics)


def test_malformed_collection_returns_diagnostic(load_fixture):
    profile = load_fixture("us1/profile_valid.json")
    profile["facets"]["temporal.covariates"] = {"basis": "observed", "value": [{}]}
    result = validate_record(profile)
    assert result.status == "invalid"
    assert any(d.pointer.endswith("temporal.covariates/value") for d in result.diagnostics)


@pytest.mark.parametrize("field", ["problem_id", "facets", "hard_constraints"])
def test_malformed_bundle_fields_do_not_crash(load_fixture, field):
    profile = load_fixture("us1/profile_valid.json")
    profile[field] = ["bad"]
    result = validate_bundle([profile], context=ValidationContext())
    assert result.status == "invalid"
    assert result.contextual_complete is False


@pytest.mark.parametrize("facet,operand", [
    ("dataset.rows", -1), ("dataset.missing_fraction", 1.1),
    ("temporal.horizon_steps", 0), ("compute.runtime_seconds", -0.1),
])
def test_numeric_condition_obeys_domain(load_fixture, facet, operand):
    recipe = load_fixture("us1/recipe_valid.json")
    recipe["preconditions"][0].update(facet=facet, op="lt", operand=operand)
    result = validate_record(recipe)
    assert result.status == "invalid"
    assert any(d.pointer == "/preconditions/0/operand" for d in result.diagnostics)


def test_applicability_is_a_vocabulary_condition_list(load_fixture):
    recipe = load_fixture("us1/recipe_valid.json")
    recipe["applicability"] = [{"condition_id": "cond:app", "facet": "task.kind", "op": "eq", "operand": "forecasting"}]
    assert validate_record(recipe).status == "valid"
    recipe["applicability"][0]["operand"] = "invented"
    assert validate_record(recipe).status == "invalid"
    recipe["applicability"] = "Free text only"
    assert validate_record(recipe).status == "invalid"


@pytest.mark.parametrize("metric,k,valid", [("map_at_k", None, False), ("rmse", 3, False), ("map_at_k", 3, True)])
def test_profile_metric_cutoff_pair(load_fixture, metric, k, valid):
    profile = load_fixture("us1/profile_valid.json")
    profile["facets"]["metric.name"] = {"basis": "observed", "value": metric}
    profile["facets"].pop("metric.k", None)
    if k is not None:
        profile["facets"]["metric.k"] = {"basis": "observed", "value": k}
    assert (validate_record(profile).status == "valid") is valid


@pytest.mark.parametrize("section,key,value", [
    ("evaluation", "protocol_id", " "), ("evaluation", "protocol_sha256", ""),
    ("evaluation", "protocol_sha256", "a" * 64 + "\n"),
    ("evaluation", "metric", ""), ("evaluation", "acceptance_rule", "\n"),
    ("data", "candidate_fingerprint", " "),
])
def test_nullable_proposal_decisions_validate_populated_values(load_fixture, section, key, value):
    proposal = load_fixture("us3/proposal_valid.json")
    proposal["experiment_contract"][section][key] = value
    result = validate_record(proposal)
    assert result.status == "invalid"
    assert any(d.pointer == f"/experiment_contract/{section}/{key}" for d in result.diagnostics)


def test_nullable_baseline_rejects_blank(load_fixture):
    proposal = load_fixture("us3/proposal_valid.json")
    proposal["experiment_contract"]["extensions"]["aimx_recipes"]["baseline_run"] = " "
    assert validate_record(proposal).status == "invalid"


def test_problem_source_reference_must_resolve(load_fixture):
    problem = load_fixture("problem/valid.json")
    problem["source_ids"] = ["source:missing"]
    result = validate_bundle([problem], context=ValidationContext())
    assert result.status == "invalid"
    assert any(d.pointer == "/source_ids/0" and d.code == "reference.missing" for d in result.diagnostics)


def test_conflict_document_reference_must_resolve(proposal_bundle):
    records, context = proposal_bundle
    profile = next(r for r in records if r["entity_type"] == "problem_profile")
    profile["facets"]["characteristics.non_stationarity"]["conflicts"][0]["source"] = {
        "kind": "document", "ref": "doc:missing"
    }
    result = validate_bundle(records, context=context)
    assert result.status == "invalid"
    assert any("/conflicts/0/source/ref" in d.pointer for d in result.diagnostics)


@pytest.mark.parametrize("texts,status,code", [({}, "incomplete", "context.document_text_missing"),
    ({"doc:us2-body": "wrong"}, "invalid", "document.hash_mismatch")])
def test_document_is_checked_without_evidence(proposal_bundle, texts, status, code):
    records, _ = proposal_bundle
    records = [r for r in records if r["entity_type"] in ("source", "document")]
    result = validate_bundle(records, context=ValidationContext(document_texts=texts))
    assert result.status == status
    assert any(d.entity_type == "document" and d.code == code for d in result.diagnostics)


@pytest.mark.parametrize("tamper", ["facet", "owner_type", "owner_id", "condition_id"])
def test_assessment_must_reference_exact_condition(proposal_bundle, tamper):
    records, context = proposal_bundle
    proposal = records[-1]
    assessment = proposal["match"]["assessments"][1]
    assessment[tamper] = {"facet": "task.kind", "owner_type": "recipe", "owner_id": "prof:missing", "condition_id": "cond:missing"}[tamper]
    result = validate_bundle(records, context=context)
    assert result.status == "invalid"
    assert any(d.code == "assessment.inconsistent" for d in result.diagnostics)


def test_condition_identity_is_typed_even_when_owner_ids_collide(proposal_bundle):
    records, context = proposal_bundle
    profile, recipe, proposal = records[-3:]
    recipe["recipe_id"] = profile["profile_id"]
    proposal["recipe_id"] = recipe["recipe_id"]
    for record in records:
        if record["entity_type"] == "attempt":
            record["recipe_id"] = recipe["recipe_id"]
    for assessment in proposal["match"]["assessments"]:
        if assessment["owner_type"] == "recipe":
            assessment["owner_id"] = recipe["recipe_id"]
    recipe["hard_constraints"][0]["condition_id"] = profile["hard_constraints"][0]["condition_id"]
    recipe_assessment = next(a for a in proposal["match"]["assessments"] if a["owner_type"] == "recipe")
    recipe_assessment["condition_id"] = recipe["hard_constraints"][0]["condition_id"]
    assert validate_bundle(records, context=context).status == "valid"
    proposal["match"]["assessments"].remove(recipe_assessment)
    assert validate_bundle(records, context=context).status == "invalid"


def test_unknown_condition_cannot_be_disguised_as_known_facet(proposal_bundle):
    records, context = proposal_bundle
    records[-3]["facets"]["temporal.covariates"] = {"basis": "unknown", "value": None}
    records[-1]["match"]["assessments"][1]["facet"] = "task.kind"
    assert validate_bundle(records, context=context).status == "invalid"


def extracted_evidence(load_fixture):
    evidence = load_fixture("us2/evidence_valid.json")
    evidence["provenance"] = {
        "origin": "extracted", "source_content_sha256": "a" * 64,
        "provider": "synthetic", "requested_model": "synthetic", "served_model": "synthetic",
        "prompt_version": "test", "prompt_hash": "b" * 64, "schema_version": evidence["schema_version"],
        "extractor_version": "test", "extracted_at": "2026-11-02T00:00:00Z",
    }
    return evidence


def test_extracted_schema_version_matches_record(load_fixture):
    evidence = extracted_evidence(load_fixture)
    assert validate_record(evidence).status == "valid"
    evidence["provenance"]["schema_version"] = "999"
    result = validate_record(evidence)
    assert result.status == "invalid"
    assert any(d.pointer == "/provenance/schema_version" for d in result.diagnostics)


@pytest.mark.parametrize("timestamp", ["yesterday", "2026-02-30T00:00:00Z", "2026-11-02"])
def test_provenance_timestamp_is_rfc3339(load_fixture, timestamp):
    evidence = extracted_evidence(load_fixture)
    evidence["provenance"]["extracted_at"] = timestamp
    result = validate_record(evidence)
    assert result.status == "invalid"
    assert any(d.pointer == "/provenance/extracted_at" for d in result.diagnostics)


def test_diagnostics_do_not_echo_comparison_text(load_fixture):
    evidence = load_fixture("us2/evidence_valid.json")
    secret = "\x1b[31mPRIVATE SOURCE TEXT"
    evidence.update(type="controlled_ablation", comparison={"baseline": secret, "candidate": "all"})
    result = validate_record(evidence)
    assert secret not in result.to_json()
    assert "PRIVATE SOURCE TEXT" not in render_text(result)
    assert "\x1b" not in render_text(result)


def test_source_digest_requires_exact_length(load_fixture):
    source = load_fixture("us2/source_valid.json")
    source["content_sha256"] += "\n"
    assert validate_record(source).status == "invalid"


def test_id_must_not_end_with_a_newline(load_fixture):
    problem = load_fixture("problem/valid.json")
    problem["problem_id"] += "\n"
    assert validate_record(problem).status == "invalid"


def test_renderer_escapes_dynamic_identity(load_fixture):
    problem = load_fixture("problem/valid.json")
    problem["problem_id"] = "\x1b[31midentifier\n"
    assert "\x1b" not in render_text(validate_record(problem))


def test_hard_constraint_diagnostics_are_stable_between_processes(fixtures_dir):
    script = '''
import json, sys
from pathlib import Path
from aimx_recipes.contextual import validate_bundle
from aimx_recipes.models import ValidationContext
p=Path(sys.argv[1]); load=lambda s:json.loads((p/s).read_text())
records=load('us2/evidence_bundle_valid.json')+[load('us1/profile_valid.json'),load('us1/recipe_valid.json'),load('us3/proposal_valid.json')]
records[-1]['match']['assessments']=[]
context=ValidationContext(document_texts={'doc:us2-body':(p/'us2/document_text.txt').read_text()})
print(validate_bundle(records,context=context).to_json())
'''
    outputs = [subprocess.check_output([sys.executable, "-c", script, str(fixtures_dir)],
        env={**os.environ, "PYTHONHASHSEED": seed}, text=True) for seed in ("1", "2", "3")]
    assert outputs[0] == outputs[1] == outputs[2]
