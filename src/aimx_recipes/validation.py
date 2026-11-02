"""Parsing, JSON-domain preflight, and validation entry points."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Mapping
from aimx_recipes.diagnostics import build_validation_result, escape_pointer
from aimx_recipes.models import Diagnostic, JSONValue, ParseResult, ValidationResult
from aimx_recipes.schema_registry import SUPPORTED_SCHEMA_VERSIONS, get_global_registry

ID_FIELD_FOR_ENTITY = {
    "source": "source_id",
    "document": "document_id",
    "problem": "problem_id",
    "problem_profile": "profile_id",
    "recipe": "recipe_id",
    "attempt": "attempt_id",
    "evidence": "evidence_id",
    "experiment_proposal": "proposal_id",
}

KNOWN_ENTITY_TYPES = frozenset(ID_FIELD_FOR_ENTITY.keys())


class DuplicateKeyError(ValueError):
    """Raised when duplicate keys are found in a JSON object."""


def _detect_surrogates(text: str) -> bool:
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            return True
    return False


def _has_surrogate_in_obj(val: Any) -> bool:
    if isinstance(val, str):
        return _detect_surrogates(val)
    elif isinstance(val, dict):
        return any(_has_surrogate_in_obj(k) or _has_surrogate_in_obj(v) for k, v in val.items())
    elif isinstance(val, list):
        return any(_has_surrogate_in_obj(x) for x in val)
    return False


def _pairs_hook_reject_duplicates(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for key, val in pairs:
        if key in res:
            raise DuplicateKeyError(f"Duplicate key encountered")
        res[key] = val
    return res


def extract_record_identity(record: Any) -> tuple[str | None, str | None]:
    """Safely extract entity_type and record_id from a mapping if present and well-formed."""
    if not isinstance(record, (dict, Mapping)):
        return None, None
    raw_type = record.get("entity_type")
    entity_type = raw_type if isinstance(raw_type, str) and not _detect_surrogates(raw_type) else None
    if not entity_type:
        return None, None
    id_field = ID_FIELD_FOR_ENTITY.get(entity_type)
    if not id_field:
        return entity_type, None
    raw_id = record.get(id_field)
    record_id = raw_id if isinstance(raw_id, str) and not _detect_surrogates(raw_id) else None
    return entity_type, record_id


def _reject_constant(constant: str) -> None:
    raise ValueError(f"Non-finite numeric literal: {constant}")


def parse_record(text: str, input_index: int = 0) -> ParseResult:
    """Parse a single JSON record string with strict domain checks."""
    if _detect_surrogates(text):
        diag = Diagnostic(
            entity_type=None,
            record_id=None,
            input_index=input_index,
            pointer="",
            code="parse.invalid_json",
            message="Input contains lone Unicode surrogates.",
            check="unicode_surrogates",
            severity="error",
        )
        return ParseResult(record=None, diagnostics=[diag])

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_pairs_hook_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except DuplicateKeyError:
        diag = Diagnostic(
            entity_type=None,
            record_id=None,
            input_index=input_index,
            pointer="",
            code="parse.duplicate_key",
            message="JSON object contains duplicate keys.",
            check="duplicate_keys",
            severity="error",
        )
        return ParseResult(record=None, diagnostics=[diag])
    except Exception:
        diag = Diagnostic(
            entity_type=None,
            record_id=None,
            input_index=input_index,
            pointer="",
            code="parse.invalid_json",
            message="Invalid JSON syntax or non-finite numeric literal.",
            check="json_syntax",
            severity="error",
        )
        return ParseResult(record=None, diagnostics=[diag])

    if _has_surrogate_in_obj(parsed):
        diag = Diagnostic(
            entity_type=None,
            record_id=None,
            input_index=input_index,
            pointer="",
            code="parse.invalid_json",
            message="Parsed values contain lone Unicode surrogates.",
            check="unicode_surrogates",
            severity="error",
        )
        return ParseResult(record=None, diagnostics=[diag])

    if not isinstance(parsed, dict):
        diag = Diagnostic(
            entity_type=None,
            record_id=None,
            input_index=input_index,
            pointer="",
            code="type.invalid",
            message="Record root must be a JSON object.",
            check="root_type",
            severity="error",
        )
        return ParseResult(record=None, diagnostics=[diag])

    if preflight_json_domain(parsed):
        return ParseResult(record=None, diagnostics=[Diagnostic(
            entity_type=None, record_id=None, input_index=input_index, pointer="",
            code="parse.invalid_json", message="Parsed value is outside the JSON domain.",
            check="json_domain", severity="error",
        )])
    return ParseResult(record=parsed, diagnostics=[])


def preflight_json_domain(
    record: Any,
    input_index: int = 0,
    entity_type: str | None = None,
    record_id: str | None = None,
) -> list[Diagnostic]:
    """Inspect data structure for non-JSON or domain violation types."""
    diagnostics: list[Diagnostic] = []
    ancestors: set[int] = set()

    def _traverse(node: Any, path: list[str | int]):
        pointer = escape_pointer(path)
        message = None
        code = "type.invalid"
        is_container = isinstance(node, (Mapping, list))
        if is_container:
            if id(node) in ancestors:
                diagnostics.append(Diagnostic(
                    entity_type=entity_type, record_id=record_id, input_index=input_index,
                    pointer=pointer, code="type.invalid", message="Cyclic values are outside the JSON domain.",
                    check="json_domain", severity="error",
                ))
                return
            ancestors.add(id(node))
        if isinstance(node, (dict, Mapping)):
            for k, v in node.items():
                if not isinstance(k, str):
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer=pointer,
                            code="type.invalid",
                            message="Object keys must be strings.",
                            check="json_domain",
                            severity="error",
                        )
                    )
                    continue
                if _detect_surrogates(k):
                    diagnostics.append(Diagnostic(
                        entity_type=entity_type, record_id=record_id, input_index=input_index,
                        pointer=pointer, code="value.invalid", message="Object key contains lone Unicode surrogates.",
                        check="json_domain", severity="error",
                    ))
                    continue
                _traverse(v, [*path, k])
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _traverse(item, [*path, idx])
        elif isinstance(node, float):
            if not math.isfinite(node):
                code = "value.invalid"
                message = "Non-finite floating point numbers are prohibited."
        elif isinstance(node, str):
            if _detect_surrogates(node):
                code = "value.invalid"
                message = "String contains lone Unicode surrogates."
        elif node is not None and not isinstance(node, (bool, int)):
            message = "Value is outside the JSON domain."
        if is_container:
            ancestors.remove(id(node))
        if message:
            diagnostics.append(Diagnostic(
                entity_type=entity_type, record_id=record_id, input_index=input_index,
                pointer=pointer, code=code, message=message, check="json_domain", severity="error",
            ))

    _traverse(record, [])
    return diagnostics


def _map_jsonschema_error(
    err: Any,
    entity_type: str | None,
    record_id: str | None,
    input_index: int,
) -> Diagnostic:
    path_parts = list(err.absolute_path)
    validator_name = err.validator

    if validator_name == "required":
        code = "field.required"
        message = "Required field is missing."
        m = re.search(r"'([^']+)' is a required property", err.message)
        if m:
            path_parts.append(m.group(1))
    elif validator_name == "additionalProperties":
        code = "field.unknown"
        message = "Unexpected field."
        m = re.search(r"'([^']+)' was unexpected", err.message)
        if m:
            path_parts.append(m.group(1))
    elif validator_name == "maxLength" and path_parts == ["quote"]:
        code = "quote.too_long"
        message = "Quote exceeds maximum allowed length of 500 characters."
    elif validator_name == "type":
        code = "type.invalid"
        message = "Field value has invalid type."
    elif validator_name in (
        "enum",
        "const",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "uniqueItems",
        "format",
    ):
        code = "value.invalid"
        message = "Field value violates domain constraints."
    else:
        code = "value.invalid"
        message = "Field value violates schema validation rule."

    pointer = escape_pointer(path_parts)
    return Diagnostic(
        entity_type=entity_type,
        record_id=record_id,
        input_index=input_index,
        pointer=pointer,
        code=code,
        message=message,
        check=f"schema.{validator_name}",
        severity="error",
    )


def _validate_facet_scalar_or_collection(facet_def: dict[str, Any], val: Any) -> bool:
    t = facet_def.get("type")
    if t == "enum":
        return isinstance(val, str) and val in facet_def.get("allowed_values", [])
    elif t == "boolean":
        return isinstance(val, bool)
    elif t == "integer":
        if not (isinstance(val, int) and not isinstance(val, bool)):
            return False
        if "minimum" in facet_def and val < facet_def["minimum"]:
            return False
        if "maximum" in facet_def and val > facet_def["maximum"]:
            return False
        return True
    elif t == "number":
        if not (isinstance(val, (int, float)) and not isinstance(val, bool)):
            return False
        if "minimum" in facet_def and val < facet_def["minimum"]:
            return False
        if "maximum" in facet_def and val > facet_def["maximum"]:
            return False
        return True
    elif t == "collection":
        if not isinstance(val, list) or len(val) == 0:
            return False
        allowed = facet_def.get("allowed_values", [])
        return all(isinstance(v, str) and v in allowed for v in val) and len(val) == len(set(val))
    elif t == "prior_attempts":
        if not isinstance(val, list):
            return False
        seen_recipes = set()
        for item in val:
            if not isinstance(item, dict):
                return False
            rid = item.get("recipe_id")
            st = item.get("status")
            if not isinstance(rid, str) or not rid:
                return False
            if st not in ("tried", "rejected", "unresolved"):
                return False
            if rid in seen_recipes:
                return False
            seen_recipes.add(rid)
        return True
    return False


def _validate_condition_shape(
    cond: Any,
    cond_index: int,
    pointer_prefix: str,
    vocab: dict[str, Any],
    entity_type: str | None,
    record_id: str | None,
    input_index: int,
    seen_cond_ids: set[str],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not isinstance(cond, dict):
        return diags

    cond_id = cond.get("condition_id")
    if isinstance(cond_id, str):
        if cond_id in seen_cond_ids:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/condition_id",
                    code="identity.duplicate",
                    message="Condition IDs must be unique within the record.",
                    check="condition_id_unique",
                    severity="error",
                )
            )
        else:
            seen_cond_ids.add(cond_id)

    facet_name = cond.get("facet")
    op = cond.get("op")
    operand = cond.get("operand")

    if not isinstance(facet_name, str) or facet_name not in vocab["facets"]:
        diags.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer=f"{pointer_prefix}/{cond_index}/facet",
                code="value.invalid",
                message="Condition facet is unknown in the vocabulary.",
                check="condition_facet",
                severity="error",
            )
        )
        return diags

    facet_def = vocab["facets"][facet_name]
    allowed_ops = facet_def.get("allowed_operators", [])
    if op not in allowed_ops:
        diags.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer=f"{pointer_prefix}/{cond_index}/op",
                code="value.invalid",
                message="Operator is not allowed for this facet.",
                check="condition_operator",
                severity="error",
            )
        )
        return diags

    # Check operand
    if op in ("present", "absent"):
        if operand is not None:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/operand",
                    code="value.invalid",
                    message="Presence operators require a null operand.",
                    check="condition_operand",
                    severity="error",
                )
            )
    elif op in ("eq", "ne"):
        if not _validate_facet_scalar_or_collection(facet_def, operand):
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/operand",
                    code="value.invalid",
                    message="Operand does not match scalar domain for facet.",
                    check="condition_operand",
                    severity="error",
                )
            )
    elif op in ("in", "not_in"):
        if not isinstance(operand, list) or len(operand) == 0:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/operand",
                    code="value.invalid",
                    message="Membership operators require a nonempty unique list operand.",
                    check="condition_operand",
                    severity="error",
                )
            )
        else:
            # Check unique items
            try:
                unique = len(operand) == len(set(operand))
            except TypeError:
                unique = False
            if not unique or not all(_validate_facet_scalar_or_collection(facet_def, x) for x in operand):
                diags.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer=f"{pointer_prefix}/{cond_index}/operand",
                        code="value.invalid",
                        message="Operand elements must be unique valid scalar values for facet.",
                        check="condition_operand",
                        severity="error",
                    )
                )
    elif op in ("lt", "lte", "gt", "gte"):
        is_valid_num = _validate_facet_scalar_or_collection(facet_def, operand)
        if not is_valid_num:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/operand",
                    code="value.invalid",
                    message="Numeric operator requires a finite number in facet domain.",
                    check="condition_operand",
                    severity="error",
                )
            )
    elif op in ("contains", "not_contains"):
        allowed = facet_def.get("allowed_values", [])
        if not (isinstance(operand, str) and operand in allowed):
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/{cond_index}/operand",
                    code="value.invalid",
                    message="Collection operator requires an allowed member.",
                    check="condition_operand",
                    severity="error",
                )
            )

    return diags


def _validate_facet_assertion(
    assertion: Any,
    facet_name: str,
    pointer_prefix: str,
    vocab: dict[str, Any],
    entity_type: str | None,
    record_id: str | None,
    input_index: int,
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not isinstance(assertion, dict):
        return diags

    facet_def = vocab["facets"].get(facet_name)
    if not facet_def:
        return diags

    basis = assertion.get("basis")
    val = assertion.get("value")

    if basis == "unknown":
        if val is not None:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/value",
                    code="value.invalid",
                    message="Unknown basis requires null value.",
                    check="basis_nullability",
                    severity="error",
                )
            )
    elif basis in ("observed", "reported", "inferred"):
        if val is None:
            diags.append(
                Diagnostic(
                    entity_type=entity_type,
                    record_id=record_id,
                    input_index=input_index,
                    pointer=f"{pointer_prefix}/value",
                    code="value.invalid",
                    message="Known basis requires nonnull value.",
                    check="basis_nullability",
                    severity="error",
                )
            )
        else:
            if not _validate_facet_scalar_or_collection(facet_def, val):
                diags.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer=f"{pointer_prefix}/value",
                        code="value.invalid",
                        message="Facet value violates vocabulary rules.",
                        check="facet_vocabulary",
                        severity="error",
                    )
                )

    # Check conflicts
    conflicts = assertion.get("conflicts", [])
    if isinstance(conflicts, list):
        for c_idx, c_assert in enumerate(conflicts):
            c_diags = _validate_facet_assertion(
                c_assert,
                facet_name,
                f"{pointer_prefix}/conflicts/{c_idx}",
                vocab,
                entity_type,
                record_id,
                input_index,
            )
            diags.extend(c_diags)

    return diags


def validate_record(
    record: Mapping[str, JSONValue],
    input_index: int = 0,
) -> ValidationResult:
    """Validate a single record structurally against its packaged schema and vocabulary rules."""
    entity_type, record_id = extract_record_identity(record)

    diagnostics: list[Diagnostic] = []
    if not isinstance(record, Mapping):
        return build_validation_result(level="structural", diagnostics=[Diagnostic(
            entity_type=None, record_id=None, input_index=input_index, pointer="",
            code="type.invalid", message="Record root must be a JSON object.",
            check="root_type", severity="error",
        )])

    # 1. Domain preflight
    preflight_diags = preflight_json_domain(
        record,
        input_index=input_index,
        entity_type=entity_type,
        record_id=record_id,
    )
    diagnostics.extend(preflight_diags)
    if preflight_diags:
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )

    # 2. Check schema_version
    schema_version = record.get("schema_version")
    if schema_version is None:
        diagnostics.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer="/schema_version",
                code="field.required",
                message="Field schema_version is required.",
                check="schema_version",
                severity="error",
            )
        )
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )
    if not isinstance(schema_version, str) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        diagnostics.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer="/schema_version",
                code="version.unsupported",
                message="Schema version is not supported.",
                check="version_dispatch",
                severity="error",
            )
        )
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )

    # 3. Check entity_type
    raw_entity_type = record.get("entity_type")
    if raw_entity_type is None:
        diagnostics.append(
            Diagnostic(
                entity_type=None,
                record_id=record_id,
                input_index=input_index,
                pointer="/entity_type",
                code="field.required",
                message="Field entity_type is required.",
                check="entity_type",
                severity="error",
            )
        )
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )
    if not isinstance(raw_entity_type, str) or raw_entity_type not in KNOWN_ENTITY_TYPES:
        diagnostics.append(
            Diagnostic(
                entity_type=None,
                record_id=record_id,
                input_index=input_index,
                pointer="/entity_type",
                code="value.invalid",
                message="Entity type is unknown.",
                check="entity_type",
                severity="error",
            )
        )
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )

    # 4. JSON Schema structural validation
    try:
        registry = get_global_registry()
        validator = registry.get_validator(raw_entity_type, schema_version)
    except (KeyError, RuntimeError, OSError):
        diagnostics.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer="",
                code="schema.resource_unavailable",
                message="Schema resource for this entity is unavailable.",
                check="schema_resolution",
                severity="error",
            )
        )
        return build_validation_result(
            level="structural",
            diagnostics=diagnostics,
            structurally_valid=False,
            contextual_complete=False,
        )

    try:
        for err in validator.iter_errors(record):
            errors = [err]
            if err.validator == "oneOf" and list(err.path) == ["provenance"]:
                origins = {"extracted": 0, "human": 1, "synthetic": 2}
                provenance = record.get("provenance")
                origin = provenance.get("origin") if isinstance(provenance, dict) else None
                if isinstance(origin, str) and origin in origins:
                    errors = [child for child in err.context if child.schema_path[0] == origins[origin]] or errors
            diagnostics.extend(_map_jsonschema_error(error, entity_type, record_id, input_index) for error in errors)
    except Exception:
        diagnostics.append(
            Diagnostic(
                entity_type=entity_type,
                record_id=record_id,
                input_index=input_index,
                pointer="",
                code="schema.resource_unavailable",
                message="Referenced schema resource could not be resolved.",
                check="schema_resolution",
                severity="error",
            )
        )

    # Semantic checks depend on the generic shape; do not inspect malformed fields.
    if diagnostics:
        return build_validation_result(level="structural", diagnostics=diagnostics)

    provenance = record.get("provenance")
    if isinstance(provenance, dict) and provenance.get("origin") == "extracted":
        if provenance["schema_version"] != schema_version:
            diagnostics.append(Diagnostic(
                entity_type=entity_type, record_id=record_id, input_index=input_index,
                pointer="/provenance/schema_version", code="version.unsupported",
                message="Extraction schema version must match the containing record.",
                check="provenance_version", severity="error",
            ))

    # 5. Entity-specific vocabulary and taxonomy enforcement
    vocab = registry.get_vocabulary_data(schema_version)
    tax = registry.get_taxonomy_data(schema_version)

    if raw_entity_type == "problem_profile":
        facets = record.get("facets", {})
        if isinstance(facets, dict):
            for f_name, f_assertion in facets.items():
                if f_name not in vocab["facets"]:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer=f"/facets/{escape_pointer([f_name])[1:]}",
                            code="value.invalid",
                            message="Facet is not defined in the vocabulary.",
                            check="facet_vocabulary",
                            severity="error",
                        )
                    )
                else:
                    f_diags = _validate_facet_assertion(
                        f_assertion,
                        f_name,
                        f"/facets/{escape_pointer([f_name])[1:]}",
                        vocab,
                        entity_type,
                        record_id,
                        input_index,
                    )
                    diagnostics.extend(f_diags)

        metric = facets.get("metric.name", {})
        cutoff = facets.get("metric.k", {})
        metric_value = metric.get("value")
        cutoff_value = cutoff.get("value")
        if metric_value == "map_at_k" and cutoff_value is None:
            diagnostics.append(Diagnostic(
                entity_type=entity_type, record_id=record_id, input_index=input_index,
                pointer="/facets/metric.k", code="field.required",
                message="Metric map_at_k requires a known metric.k.", check="metric_k", severity="error",
            ))
        elif cutoff_value is not None and metric_value != "map_at_k":
            diagnostics.append(Diagnostic(
                entity_type=entity_type, record_id=record_id, input_index=input_index,
                pointer="/facets/metric.k/value", code="value.invalid",
                message="A known metric.k is permitted only with map_at_k.", check="metric_k", severity="error",
            ))

        # Validate hard constraints
        hard_constraints = record.get("hard_constraints", [])
        if isinstance(hard_constraints, list):
            seen_conds: set[str] = set()
            for c_idx, cond in enumerate(hard_constraints):
                c_diags = _validate_condition_shape(
                    cond,
                    c_idx,
                    "/hard_constraints",
                    vocab,
                    entity_type,
                    record_id,
                    input_index,
                    seen_conds,
                )
                diagnostics.extend(c_diags)

    elif raw_entity_type == "recipe":
        action_type = record.get("action_type")
        action = record.get("action")

        if isinstance(action_type, str) and action_type in tax["groups"]:
            expected_prefix = f"{action_type}."
            leaves = tax["groups"][action_type]["leaves"]
            if not isinstance(action, str) or not action.startswith(expected_prefix) or action.split(".", 1)[1] not in leaves:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/action",
                        code="value.invalid",
                        message="Action is not an authorized leaf under the declared group.",
                        check="action_taxonomy",
                        severity="error",
                    )
                )

        # IDs identify a condition across all three recipe lists.
        seen_recipe_conds: set[str] = set()
        for c_idx, cond in enumerate(record["applicability"]):
            diagnostics.extend(_validate_condition_shape(
                cond, c_idx, "/applicability", vocab, entity_type, record_id,
                input_index, seen_recipe_conds,
            ))
        preconditions = record.get("preconditions", [])
        if isinstance(preconditions, list):
            for c_idx, cond in enumerate(preconditions):
                c_diags = _validate_condition_shape(
                    cond,
                    c_idx,
                    "/preconditions",
                    vocab,
                    entity_type,
                    record_id,
                    input_index,
                    seen_recipe_conds,
                )
                diagnostics.extend(c_diags)

        hard_constraints = record.get("hard_constraints", [])
        if isinstance(hard_constraints, list):
            for c_idx, cond in enumerate(hard_constraints):
                c_diags = _validate_condition_shape(
                    cond,
                    c_idx,
                    "/hard_constraints",
                    vocab,
                    entity_type,
                    record_id,
                    input_index,
                    seen_recipe_conds,
                )
                diagnostics.extend(c_diags)

    elif raw_entity_type == "source":
        license_info = record.get("license")
        if isinstance(license_info, dict):
            status = license_info.get("status")
            identifier = license_info.get("identifier")
            if status in ("permissive", "restricted") and (not isinstance(identifier, str) or not identifier.strip()):
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/license/identifier",
                        code="value.invalid",
                        message="Declared license status requires a non-null, non-empty identifier.",
                        check="license_identifier",
                        severity="error",
                    )
                )

    elif raw_entity_type == "attempt":
        base_val = record.get("baseline_value")
        cand_val = record.get("candidate_value")
        delta_val = record.get("reported_delta")
        scope = record.get("evaluation_scope")
        metric_name = record.get("metric_name")
        metric_dir = record.get("metric_direction")
        metric_k = record.get("metric_k")

        has_measurement = base_val is not None or cand_val is not None or delta_val is not None
        if has_measurement:
            if scope is None:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/evaluation_scope",
                        code="attempt.scope_required",
                        message="Numeric measurements require an evaluation scope.",
                        check="attempt_scope",
                        severity="error",
                    )
                )
            if metric_name is None:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/metric_name",
                        code="attempt.scope_required",
                        message="Numeric measurements require a metric name.",
                        check="attempt_metric",
                        severity="error",
                    )
                )
            if metric_dir is None:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/metric_direction",
                        code="attempt.scope_required",
                        message="Numeric measurements require a metric direction.",
                        check="attempt_direction",
                        severity="error",
                    )
                )

        if metric_name is not None and isinstance(metric_name, str):
            metric_def = vocab["metrics"].get(metric_name)
            if metric_def:
                expected_dir = metric_def["direction"]
                if metric_dir is not None and metric_dir != expected_dir:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/metric_direction",
                            code="value.invalid",
                            message="Metric direction must agree with the vocabulary.",
                            check="metric_direction",
                            severity="error",
                        )
                    )
                domain = metric_def["domain"]
                min_val, max_val = domain[0], domain[1]
                for f_name, f_val in [("baseline_value", base_val), ("candidate_value", cand_val)]:
                    if f_val is not None and isinstance(f_val, (int, float)) and not isinstance(f_val, bool):
                        if min_val is not None and f_val < min_val:
                            diagnostics.append(
                                Diagnostic(
                                    entity_type=entity_type,
                                    record_id=record_id,
                                    input_index=input_index,
                                    pointer=f"/{f_name}",
                                    code="value.invalid",
                                    message="Metric value is below its domain minimum.",
                                    check="metric_domain",
                                    severity="error",
                                )
                            )
                        if max_val is not None and f_val > max_val:
                            diagnostics.append(
                                Diagnostic(
                                    entity_type=entity_type,
                                    record_id=record_id,
                                    input_index=input_index,
                                    pointer=f"/{f_name}",
                                    code="value.invalid",
                                    message="Metric value exceeds its domain maximum.",
                                    check="metric_domain",
                                    severity="error",
                                )
                            )

            if metric_name == "map_at_k":
                if metric_k is None:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/metric_k",
                            code="field.required",
                            message="Metric map_at_k requires metric_k.",
                            check="metric_k",
                            severity="error",
                        )
                    )
            else:
                if metric_k is not None:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/metric_k",
                            code="value.invalid",
                            message="metric_k is permitted only with map_at_k.",
                            check="metric_k",
                            severity="error",
                        )
                    )

        joint_change = record.get("joint_change")
        joint_changes = record.get("joint_changes", [])
        confounders = record.get("confounders", [])
        if joint_change is True:
            if not joint_changes:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/joint_changes",
                        code="value.invalid",
                        message="joint_change=true requires nonempty joint_changes.",
                        check="joint_change_consistency",
                        severity="error",
                    )
                )
            if not confounders:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/confounders",
                        code="value.invalid",
                        message="joint_change=true requires nonempty confounders.",
                        check="joint_change_consistency",
                        severity="error",
                    )
                )
        elif joint_change is False:
            if isinstance(joint_changes, list) and len(joint_changes) > 0:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/joint_changes",
                        code="value.invalid",
                        message="joint_change=false requires empty joint_changes.",
                        check="joint_change_consistency",
                        severity="error",
                    )
                )

    elif raw_entity_type == "evidence":
        quote = record.get("quote")
        char_start = record.get("char_start")
        char_end = record.get("char_end")
        ev_type = record.get("type")
        comparison = record.get("comparison")

        if isinstance(quote, str) and isinstance(char_start, int) and isinstance(char_end, int):
            if char_start < 0 or char_end <= char_start or (char_end - char_start) != len(quote):
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/char_end",
                        code="quote.span_invalid",
                        message="Quote span does not match quote character length.",
                        check="quote_span",
                        severity="error",
                    )
                )
            if len(quote) > 500:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/quote",
                        code="quote.too_long",
                        message="Quote exceeds maximum allowed length of 500 characters.",
                        check="quote_length",
                        severity="error",
                    )
                )

        if ev_type == "controlled_ablation":
            if comparison is None:
                diagnostics.append(
                    Diagnostic(
                        entity_type=entity_type,
                        record_id=record_id,
                        input_index=input_index,
                        pointer="/comparison",
                        code="field.required",
                        message="Controlled ablation requires comparison anchors.",
                        check="comparison_anchor",
                        severity="error",
                    )
                )
            elif isinstance(comparison, dict) and isinstance(quote, str):
                b = comparison.get("baseline")
                c = comparison.get("candidate")
                if isinstance(b, str) and b not in quote:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/comparison/baseline",
                            code="value.invalid",
                            message="Comparison baseline anchor was not found in quote.",
                            check="comparison_anchor",
                            severity="error",
                        )
                    )
                if isinstance(c, str) and c not in quote:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/comparison/candidate",
                            code="value.invalid",
                            message="Comparison candidate anchor was not found in quote.",
                            check="comparison_anchor",
                            severity="error",
                        )
                    )

    elif raw_entity_type == "experiment_proposal":
        contract = record.get("experiment_contract")
        if isinstance(contract, dict):
            interventions = contract.get("interventions", [])
            confounders = contract.get("confounders", [])
            if isinstance(interventions, list) and len(interventions) > 1:
                if not isinstance(confounders, list) or len(confounders) == 0:
                    diagnostics.append(
                        Diagnostic(
                            entity_type=entity_type,
                            record_id=record_id,
                            input_index=input_index,
                            pointer="/experiment_contract/confounders",
                            code="value.invalid",
                            message="Multiple interventions require nonempty confounders.",
                            check="proposal_confounders",
                            severity="error",
                        )
                    )

            resources = contract.get("resources")
            if isinstance(resources, list):
                for r_idx, res_item in enumerate(resources):
                    if isinstance(res_item, dict):
                        verif = res_item.get("verification")
                        enforce = res_item.get("enforcement")
                        actual = res_item.get("actual")
                        source = res_item.get("source")
                        if verif == "verified":
                            if actual is None or not (isinstance(actual, (int, float)) and not isinstance(actual, bool)):
                                diagnostics.append(
                                    Diagnostic(
                                        entity_type=entity_type,
                                        record_id=record_id,
                                        input_index=input_index,
                                        pointer=f"/experiment_contract/resources/{r_idx}/actual",
                                        code="value.invalid",
                                        message="Verified resource requires finite actual value.",
                                        check="resource_verification",
                                        severity="error",
                                    )
                                )
                            if source is None or not isinstance(source, str) or not source.strip():
                                diagnostics.append(
                                    Diagnostic(
                                        entity_type=entity_type,
                                        record_id=record_id,
                                        input_index=input_index,
                                        pointer=f"/experiment_contract/resources/{r_idx}/source",
                                        code="value.invalid",
                                        message="Verified resource requires non-empty source documentation.",
                                        check="resource_verification",
                                        severity="error",
                                    )
                                )
                        if enforce == "executor_enforced":
                            if verif != "verified":
                                diagnostics.append(
                                    Diagnostic(
                                        entity_type=entity_type,
                                        record_id=record_id,
                                        input_index=input_index,
                                        pointer=f"/experiment_contract/resources/{r_idx}/enforcement",
                                        code="value.invalid",
                                        message="Executor enforced resource requires verified verification.",
                                        check="resource_enforcement",
                                        severity="error",
                                    )
                                )

            evaluation = contract.get("evaluation")
            if isinstance(evaluation, dict):
                preflight = evaluation.get("preflight_evidence")
                if isinstance(preflight, list) and len(preflight) > 0:
                    has_local = any(isinstance(p, dict) and p.get("kind") == "local_artifact" for p in preflight)
                    if not has_local:
                        diagnostics.append(
                            Diagnostic(
                                entity_type=entity_type,
                                record_id=record_id,
                                input_index=input_index,
                                pointer="/experiment_contract/evaluation/preflight_evidence",
                                code="value.invalid",
                                message="Populated preflight_evidence requires at least one local_artifact.",
                                check="preflight_evidence",
                                severity="error",
                            )
                        )

    is_valid = len(diagnostics) == 0
    return build_validation_result(
        level="structural",
        diagnostics=diagnostics,
        structurally_valid=is_valid,
        contextual_complete=False,
    )
