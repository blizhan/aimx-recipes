"""Unit tests for closed offline schema registry, reference resolution, and network isolation."""

import pytest
from jsonschema import Draft202012Validator
from referencing.exceptions import NoSuchResource, Unresolvable
from aimx_recipes.schema_registry import get_global_registry
from aimx_recipes.validation import validate_record


def test_registry_contains_all_packaged_schemas():
    registry = get_global_registry()
    expected_urns = [
        "urn:aimx-recipes:schema:2.0.0:common",
        "urn:aimx-recipes:schema:2.0.0:problem",
        "urn:aimx-recipes:schema:2.0.0:problem_profile",
        "urn:aimx-recipes:schema:2.0.0:recipe",
        "urn:aimx-recipes:schema:2.0.0:source",
        "urn:aimx-recipes:schema:2.0.0:document",
        "urn:aimx-recipes:schema:2.0.0:attempt",
        "urn:aimx-recipes:schema:2.0.0:evidence",
        "urn:aimx-recipes:schema:2.0.0:experiment_proposal",
        "urn:aimx-recipes:schema:2.0.0:validation-result",
        "urn:aimx-recipes:schema:2.0.0:facet-vocabulary",
        "urn:aimx-recipes:schema:2.0.0:action-taxonomy",
    ]
    for urn in expected_urns:
        # Resolving known packaged resource must succeed without network
        res = registry.registry.resolver().lookup(urn)
        assert res.contents is not None


def test_unregistered_urn_or_url_fails_offline_without_network():
    registry = get_global_registry()
    resolver = registry.registry.resolver()

    with pytest.raises((Unresolvable, NoSuchResource)):
        resolver.lookup("urn:aimx-recipes:schema:2.0.0:nonexistent")

    with pytest.raises((Unresolvable, NoSuchResource)):
        resolver.lookup("https://example.com/remote.schema.json")


def test_standalone_schema_shape_versus_library_validation():
    # Standalone JSON Schema for problem_profile verifies generic JSON shape:
    # 'facets' is an object with facet_assertion values.
    # It does not know the controlled vocabulary of facet names.
    registry = get_global_registry()
    schema = registry.get_entity_schema("problem_profile", "2.0.0")
    validator = Draft202012Validator(schema, registry=registry.registry)

    record_unknown_facet = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof:1",
        "problem_id": "prob:1",
        "vocabulary_version": "2.0.0",
        "facets": {
            "unregistered.invented_facet": {
                "value": "custom",
                "basis": "observed",
            }
        },
        "hard_constraints": [],
    }

    # Standalone JSON Schema shape passes because any string key is structurally an object
    errors = list(validator.iter_errors(record_unknown_facet))
    assert len(errors) == 0

    # BUT full library validate_record enforces the closed vocabulary registry!
    lib_res = validate_record(record_unknown_facet)
    assert lib_res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "facet_vocabulary" in d.check
        for d in lib_res.diagnostics
    )
