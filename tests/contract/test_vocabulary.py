"""Contract tests for facet vocabulary, action taxonomy, and condition representations."""

from aimx_recipes.schema_registry import get_global_registry
from aimx_recipes.validation import validate_record


def test_vocabulary_all_facets_and_metrics_present():
    reg = get_global_registry()
    vocab = reg.get_vocabulary_data("2.0.0")

    expected_facets = [
        "task.kind",
        "target.kind",
        "target.long_tail",
        "target.bounded",
        "modality.kind",
        "dataset.rows",
        "dataset.features",
        "dataset.missing_fraction",
        "dataset.high_cardinality_categoricals",
        "dataset.group_structure",
        "temporal.frequency",
        "temporal.horizon_steps",
        "temporal.covariates",
        "temporal.future_data_allowed",
        "validation.scheme",
        "validation.fixed_protocol",
        "validation.target_leakage_allowed",
        "metric.name",
        "metric.k",
        "characteristics.non_stationarity",
        "characteristics.class_imbalance",
        "characteristics.distribution_shift",
        "characteristics.leakage_risk",
        "symptoms.overfitting",
        "symptoms.cv_lb_gap",
        "symptoms.poor_calibration",
        "symptoms.extreme_underprediction",
        "compute.gpu_available",
        "compute.runtime_seconds",
        "compute.memory_bytes",
        "constraints.commercial_use_required",
        "constraints.redistribution_required",
        "constraints.deployment",
        "prior_attempts",
    ]
    for facet in expected_facets:
        assert facet in vocab["facets"], f"Facet {facet} missing from vocabulary"

    expected_metrics = [
        "rmse",
        "mae",
        "rmsle",
        "pinball",
        "auc",
        "logloss",
        "map_at_k",
        "accuracy",
        "calibration_error",
    ]
    for m in expected_metrics:
        assert m in vocab["metrics"], f"Metric {m} missing from metrics"


def test_taxonomy_seven_parents_and_leaves():
    reg = get_global_registry()
    tax = reg.get_taxonomy_data("2.0.0")

    expected_groups = {
        "data_preparation": ["imputation", "filtering", "resampling"],
        "feature_engineering": [
            "encoding",
            "lag_features",
            "aggregation",
            "transformation",
        ],
        "model_choice": ["family_selection"],
        "training": ["regularization", "objective", "optimization"],
        "validation": ["split"],
        "ensemble": ["blending", "stacking"],
        "prediction": ["calibration", "clipping"],
    }
    assert set(tax["groups"].keys()) == set(expected_groups.keys())
    for parent, leaves in expected_groups.items():
        assert set(tax["groups"][parent]["leaves"].keys()) == set(leaves)


def test_profile_rejects_unknown_facet():
    record = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof-1",
        "problem_id": "prob-1",
        "vocabulary_version": "2.0.0",
        "facets": {
            "unsupported.custom_facet": {
                "value": "custom",
                "basis": "observed",
            }
        },
        "hard_constraints": [],
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "/facets/unsupported.custom_facet" in d.pointer
        for d in res.diagnostics
    )


def test_profile_unknown_basis_requires_null_value():
    # Unknown basis with non-null value must fail
    record = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof-1",
        "problem_id": "prob-1",
        "vocabulary_version": "2.0.0",
        "facets": {
            "task.kind": {
                "value": "regression",
                "basis": "unknown",
            }
        },
        "hard_constraints": [],
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "basis" in d.check for d in res.diagnostics
    )


def test_profile_known_basis_requires_nonnull_value():
    record = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof-1",
        "problem_id": "prob-1",
        "vocabulary_version": "2.0.0",
        "facets": {
            "task.kind": {
                "value": None,
                "basis": "observed",
            }
        },
        "hard_constraints": [],
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "basis" in d.check for d in res.diagnostics
    )


def test_condition_rejects_disallowed_operator():
    # dataset.rows is numeric; 'contains' is not allowed
    record = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof-1",
        "problem_id": "prob-1",
        "vocabulary_version": "2.0.0",
        "facets": {},
        "hard_constraints": [
            {
                "condition_id": "c-1",
                "facet": "dataset.rows",
                "op": "contains",
                "operand": 100,
            }
        ],
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "operator" in d.check for d in res.diagnostics
    )


def test_condition_present_absent_requires_null_operand():
    record = {
        "schema_version": "2.0.0",
        "entity_type": "problem_profile",
        "profile_id": "prof-1",
        "problem_id": "prob-1",
        "vocabulary_version": "2.0.0",
        "facets": {},
        "hard_constraints": [
            {
                "condition_id": "c-1",
                "facet": "task.kind",
                "op": "present",
                "operand": "regression",
            }
        ],
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "operand" in d.check for d in res.diagnostics
    )


def test_recipe_rejects_parent_taxonomy_action():
    # action cannot be parent group name; must be leaf canonical name
    record = {
        "schema_version": "2.0.0",
        "entity_type": "recipe",
        "recipe_id": "rec-1",
        "canonical_name": "Target Encoding",
        "aliases": [],
        "vocabulary_version": "2.0.0",
        "taxonomy_version": "2.0.0",
        "action_type": "feature_engineering",
        "action": "feature_engineering",  # parent group, invalid
        "description": "Encode categorical features using target statistics.",
        "applicability": [],
        "preconditions": [],
        "hard_constraints": [],
        "contraindications": [],
        "configuration": {},
        "implementation_refs": [],
        "expected_effect": ["Reduces cardinality"],
        "cost_profile": {"implementation": "medium", "compute": "low"},
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "value.invalid" and "/action" in d.pointer for d in res.diagnostics
    )


def test_recipe_rejects_duplicate_condition_ids():
    record = {
        "schema_version": "2.0.0",
        "entity_type": "recipe",
        "recipe_id": "rec-1",
        "canonical_name": "Target Encoding",
        "aliases": [],
        "vocabulary_version": "2.0.0",
        "taxonomy_version": "2.0.0",
        "action_type": "feature_engineering",
        "action": "feature_engineering.encoding",
        "description": "Encode categorical features using target statistics.",
        "applicability": [],
        "preconditions": [
            {
                "condition_id": "cond-duplicate",
                "facet": "modality.kind",
                "op": "eq",
                "operand": "tabular",
            }
        ],
        "hard_constraints": [
            {
                "condition_id": "cond-duplicate",
                "facet": "validation.target_leakage_allowed",
                "op": "eq",
                "operand": False,
            }
        ],
        "contraindications": [],
        "configuration": {},
        "implementation_refs": [],
        "expected_effect": [],
        "cost_profile": {"implementation": "medium", "compute": "low"},
    }
    res = validate_record(record)
    assert res.status == "invalid"
    assert any(
        d.code == "identity.duplicate" and "condition" in d.check
        for d in res.diagnostics
    )
