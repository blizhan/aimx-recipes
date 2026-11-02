"""Offline linked-record validation, exact quote spans, and condition assessments."""

from __future__ import annotations

import hashlib
from typing import Mapping, Sequence

from aimx_recipes.diagnostics import build_validation_result, escape_pointer
from aimx_recipes.models import Diagnostic, JSONValue, ValidationContext, ValidationResult
from aimx_recipes.validation import ID_FIELD_FOR_ENTITY, extract_record_identity, validate_record


def validate_bundle(
    records: Sequence[Mapping[str, JSONValue]],
    *,
    context: ValidationContext,
) -> ValidationResult:
    """Validate records first, then resolve only structurally sound records locally."""
    diagnostics: list[Diagnostic] = []
    record_map: dict[tuple[str, str], Mapping[str, JSONValue]] = {}
    valid_records: list[tuple[int, Mapping[str, JSONValue]]] = []

    def report(idx, record, pointer, code, message, check, severity="error"):
        entity_type, record_id = extract_record_identity(record)
        diagnostics.append(Diagnostic(
            entity_type=entity_type, record_id=record_id, input_index=idx,
            pointer=pointer, code=code, message=message, check=check, severity=severity,
        ))

    for idx, record in enumerate(records):
        result = validate_record(record, input_index=idx)
        diagnostics.extend(result.diagnostics)
        if not result.structurally_valid:
            continue
        entity_type, record_id = extract_record_identity(record)
        key = (entity_type, record_id)
        if key in record_map:
            report(idx, record, f"/{ID_FIELD_FOR_ENTITY[entity_type]}",
                   "identity.duplicate", "Duplicate typed record identity.", "unique_typed_id")
            continue
        record_map[key] = record
        valid_records.append((idx, record))

    def resolve(idx, record, pointer, entity_type, record_id):
        target = record_map.get((entity_type, record_id))
        if target is None:
            report(idx, record, pointer, "reference.missing",
                   "Referenced record is absent or structurally invalid in this bundle.", "reference_resolution")
        return target

    def check_provenance(idx, record, document):
        if document is not None and record["provenance"]["source_content_sha256"] != document["content_sha256"]:
            report(idx, record, "/provenance/source_content_sha256", "provenance.mismatch",
                   "Provenance hash does not match referenced Document hash.", "provenance_hash")

    attempt_evidence_counts = {rid: 0 for etype, rid in record_map if etype == "attempt"}
    for idx, record in valid_records:
        entity_type = record["entity_type"]
        if entity_type == "problem":
            for ref_idx, source_id in enumerate(record["source_ids"]):
                resolve(idx, record, f"/source_ids/{ref_idx}", "source", source_id)

        elif entity_type == "problem_profile":
            resolve(idx, record, "/problem_id", "problem", record["problem_id"])
            for name, assertion in record["facets"].items():
                pointer = "/facets" + escape_pointer([name])
                assertions = [(pointer, assertion)] + [
                    (f"{pointer}/conflicts/{c_idx}", conflict)
                    for c_idx, conflict in enumerate(assertion.get("conflicts", []))
                ]
                for assertion_pointer, item in assertions:
                    source = item.get("source")
                    if source and source["kind"] == "document":
                        resolve(idx, record, f"{assertion_pointer}/source/ref", "document", source["ref"])
                if name == "prior_attempts":
                    for assertion_pointer, item in assertions:
                        for prior_idx, prior in enumerate(item["value"] or []):
                            resolve(idx, record, f"{assertion_pointer}/value/{prior_idx}/recipe_id",
                                    "recipe", prior["recipe_id"])

        elif entity_type == "document":
            source = resolve(idx, record, "/source_id", "source", record["source_id"])
            if source is not None and record["snapshot_id"] != source["snapshot_id"]:
                report(idx, record, "/snapshot_id", "reference.missing",
                       "Document snapshot_id does not match Source snapshot_id.", "snapshot_agreement")
            doc_id = record["document_id"]
            text = context.document_texts.get(doc_id)
            if text is None:
                report(idx, record, "/content_sha256", "context.document_text_missing",
                       "Document text is required to verify its content hash.", "document_hash", "incomplete")
            elif not isinstance(text, str):
                report(idx, record, "/content_sha256", "type.invalid",
                       "Document context must contain normalized Unicode text.", "document_hash")
            else:
                try:
                    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                except UnicodeEncodeError:
                    text_hash = None
                if text_hash != record["content_sha256"]:
                    report(idx, record, "/content_sha256", "document.hash_mismatch",
                           "Supplied document text hash does not match Document content_sha256.", "document_hash")

        elif entity_type == "attempt":
            resolve(idx, record, "/problem_id", "problem", record["problem_id"])
            document = resolve(idx, record, "/document_id", "document", record["document_id"])
            check_provenance(idx, record, document)
            if record["recipe_id"] is not None:
                resolve(idx, record, "/recipe_id", "recipe", record["recipe_id"])

        elif entity_type == "evidence":
            attempt = resolve(idx, record, "/attempt_id", "attempt", record["attempt_id"])
            if attempt is not None:
                attempt_evidence_counts[record["attempt_id"]] += 1
                if attempt["document_id"] != record["document_id"]:
                    report(idx, record, "/document_id", "reference.missing",
                           "Evidence document_id must match Attempt document_id.", "attempt_document_agreement")
            document = resolve(idx, record, "/document_id", "document", record["document_id"])
            check_provenance(idx, record, document)
            text = context.document_texts.get(record["document_id"])
            if text is None:
                report(idx, record, "/quote", "context.document_text_missing",
                       "Document text is required to verify this quote.", "quote_span", "incomplete")
            elif isinstance(text, str):
                start, end = record["char_start"], record["char_end"]
                if end > len(text) or start >= len(text):
                    report(idx, record, "/char_end", "quote.span_invalid",
                           "Quote span extends beyond document text boundaries.", "quote_span")
                elif text[start:end] != record["quote"]:
                    report(idx, record, "/quote", "quote.mismatch",
                           "Supplied quote does not match document text at the specified span.", "quote_span")

        elif entity_type == "experiment_proposal":
            profile = resolve(idx, record, "/profile_id", "problem_profile", record["profile_id"])
            recipe = resolve(idx, record, "/recipe_id", "recipe", record["recipe_id"])
            for ev_idx, ev_id in enumerate(record["evidence_ids"]):
                resolve(idx, record, f"/evidence_ids/{ev_idx}", "evidence", ev_id)
            if profile is None or recipe is None:
                continue

            conditions = {}
            required_hard = set()
            for owner in (profile, recipe):
                owner_type, owner_id = extract_record_identity(owner)
                lists = ("hard_constraints",) if owner_type == "problem_profile" else (
                    "applicability", "preconditions", "hard_constraints",
                )
                for list_name in lists:
                    for condition in owner[list_name]:
                        key = (owner_type, owner_id, condition["condition_id"])
                        conditions[key] = condition
                        if list_name == "hard_constraints":
                            required_hard.add(key)

            assessed = set()
            for a_idx, assessment in enumerate(record["match"]["assessments"]):
                pointer = f"/match/assessments/{a_idx}"
                key = (assessment["owner_type"], assessment["owner_id"], assessment["condition_id"])
                if key in assessed:
                    report(idx, record, f"{pointer}/condition_id", "identity.duplicate",
                           "Duplicate assessment for the same typed condition.", "assessment_uniqueness")
                assessed.add(key)
                condition = conditions.get(key)
                if condition is None or assessment["facet"] != condition["facet"]:
                    report(idx, record, pointer, "assessment.inconsistent",
                           "Assessment must identify an existing condition and its declared facet.", "assessment_reference")
                    continue
                if assessment["state"] == "satisfied":
                    assertion = profile["facets"].get(condition["facet"])
                    if assertion is None or assertion["basis"] == "unknown" or assertion.get("conflicts"):
                        report(idx, record, f"{pointer}/state", "assessment.inconsistent",
                               "Unknown or conflicted profile facets cannot support satisfied assessments.", "uncertainty_consistency")

            if required_hard - assessed:
                report(idx, record, "/match/assessments", "assessment.inconsistent",
                       "Every hard constraint requires exactly one assessment.", "hard_constraint_coverage")

    for idx, record in valid_records:
        if record["entity_type"] == "attempt" and attempt_evidence_counts[record["attempt_id"]] == 0:
            report(idx, record, "/attempt_id", "attempt.evidence_missing",
                   "Attempt has no associated Evidence records in bundle.", "attempt_evidence")

    return build_validation_result(level="contextual", diagnostics=diagnostics)
