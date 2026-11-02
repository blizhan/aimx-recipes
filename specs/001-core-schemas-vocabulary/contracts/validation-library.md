# Public Validation Library Contract

Status: implemented interface, contract release 2.0.0. Import namespace: `aimx_recipes`. This feature adds no CLI command, HTTP endpoint, database, or service.

## Interfaces

- `parse_record(text: str) -> ParseResult`: parse one JSON object. Reject duplicate keys, non-finite numeric literals, lone Unicode surrogates, and non-object roots. Return `record` and diagnostics; failures yield record=null. Never repair or print input text.
- `validate_record(record: Mapping[str, JSONValue]) -> ValidationResult`: JSON-domain and exact-type preflight, version dispatch, then structural/value invariants for one entity. No reference resolution against user files or external state.
- `validate_bundle(records: Sequence[Mapping[str, JSONValue]], *, context: ValidationContext) -> ValidationResult`: structural checks followed by linked-record checks over this bundle. Bundle is a complete declared set of related entities; missing entity references are invalid. A missing document body in context is incomplete. Unrelated records need not be included.
- `render_text(result: ValidationResult) -> str`: stable human-readable rendering of the result, without ANSI escapes, timestamps, roots, raw quotes, or dependency exception wording.
- `result.to_dict() -> dict`: JSON-domain representation below, deterministic insertion order. Canonical serialization uses UTF-8, sorted keys, no NaN and compact separators.

`ValidationContext` is a frozen dataclass containing `document_texts: Mapping[document_id, str]`. Inputs are treated read-only; internal snapshots may be copied, but caller mappings and nested values must not be modified. Context carries normalized text only. It contains no filesystem resolver, network client, aimx resolver, model, or ambient project state.

TypedDict entity interfaces mirror [data-model.md](../data-model.md) for developer navigation. Runtime validity belongs to the packaged schemas plus explicit semantic/contextual checks. Static typing must not be advertised as runtime validation.

## ValidationResult

```json
{
  "result_version": "2.0.0",
  "level": "contextual",
  "status": "incomplete",
  "structurally_valid": true,
  "contextual_complete": false,
  "diagnostics": [
    {
      "entity_type": "evidence",
      "record_id": "evidence:example",
      "input_index": 0,
      "pointer": "/quote",
      "code": "context.document_text_missing",
      "message": "Document text is required to verify this quote.",
      "check": "quote_span",
      "severity": "incomplete"
    }
  ]
}
```

For single-record validation, level=structural, contextual_complete=false, and status=valid means structurally valid only. For bundles, level=contextual and status=valid requires structurally_valid=true and contextual_complete=true. Invariant failures produce severity=error and status=invalid. Any error dominates incomplete status, while missing-check diagnostics remain visible. Contextual checks depending on malformed fields are skipped without duplicating structural errors; contextual_complete=false if any required contextual check could not run.

`record_id` and `entity_type` are nullable when malformed/missing. `input_index` always identifies the input record. JSON Pointer uses RFC 6901 escaping; root is the empty string. Sorting key is `(entity_type or '', record_id or '', input_index, pointer, code, check, severity)`. Exact duplicates are collapsed, preserving deterministic templates. Diagnostic messages identify the kind of failure without dumping source text or arbitrary metadata.

Stable code families: `parse.invalid_json`, `parse.duplicate_key`, `type.invalid`, `field.required`, `field.unknown`, `value.invalid`, `version.unsupported`, `reference.missing`, `identity.duplicate`, `context.document_text_missing`, `document.hash_mismatch`, `provenance.mismatch`, `quote.span_invalid`, `quote.mismatch`, `quote.too_long`, `attempt.evidence_missing`, `attempt.scope_required`, `assessment.inconsistent`, `schema.resource_unavailable`. Additional precise codes require documentation and fixture expectations; dependency-specific validator keywords are not public codes.

## Structural and contextual checks

Structural checks include closed objects, types, enums, lengths, nullability, numeric domains, provenance variants, metric/scope conditional requirements, condition operands, exact integers and no lone surrogates. Controlled-ablation comparison strings must occur within the quote; semantic sufficiency remains human-reviewed.

Bundle checks include duplicate typed IDs; typed entity references; Source/Document snapshot agreement; Document hash against supplied UTF-8 text; provenance hash agreement; Attempt/Evidence document agreement; at least one Evidence per Attempt; Proposal profile/recipe/evidence references; and supplied match-assessment consistency. Assessments resolve by `(owner_type, owner_id, condition_id)` against the referenced Profile/Recipe condition lists and must repeat the declared facet. Known conflicted or unknown profile assertions cannot support satisfied assessments. Every hard constraint of the referenced Recipe/Profile must appear exactly once. The validator does not evaluate general condition truth, rank, infer causality, count independent replications, or authorize release.

Self-contained Source/Recipe records with no required external checks can receive contextual valid in a bundle. An isolated Attempt without its linked records is structurally valid at most; contextual bundle validation rejects its missing references.

## Schema resources and packaging

Root `schemas/2.0.0/` is authoritative. Planned files: `common.schema.json`, one `<entity_type>.schema.json` for each of eight types, `facet-vocabulary.schema.json`, `facet-vocabulary.json`, `action-taxonomy.schema.json`, `action-taxonomy.json`, `validation-result.schema.json`, and `release.json`. Schemas use Draft 2020-12 and URN IDs of the form `urn:aimx-recipes:schema:2.0.0:<name>`. References resolve only in the bundled registry. The schema loader rejects unregistered refs; no arbitrary file or HTTP retrieval is allowed.

Use shared `$defs` for reusable structural components. Vocabulary/taxonomy data is loaded once as validated versioned resources; any structural branches derived from it are deterministically constructed in memory and are never a second handwritten authority. A standalone schema validates generic shape; complete library validation additionally enforces registry membership/operand rules. Documentation must distinguish these surfaces.

Hatchling maps root schemas to `aimx_recipes/_schemas` inside the wheel. The source package exposes the same resources via the `_schemas` symlink for editable installs; the wheel excludes that source link before force-including the authoritative files. `importlib.resources` is the only runtime resource lookup, avoiding checkout-relative paths. The wheel resource inventory must equal the source inventory byte-for-byte, and every packaged schema reference must resolve offline. No YAML parser is required; later consumers may parse YAML before calling this JSON-domain interface.

## Release declaration

`release.json` fields: `schema_version`, `vocabulary_version`, `taxonomy_version`, `compatibility` (`initial|breaking|additive|correction`), `affected_entities` (entity-type array), `extraction_regeneration` (`required|not_required|not_applicable`), `rationale` (text), `aimx_contract_revision` (pinned commit string). Current values: all versions 2.0.0, compatibility breaking relative to the unreleased 1.0.0 draft, all entities affected, regeneration not_applicable because no frozen extraction exists. Previous draft versions are rejected; external frozen 1.0.0 records require explicit regeneration and review.

Version support is exact, not a broad SemVer range. An additive release promises a new validator can still interpret older versions only when those schemas are deliberately retained and tested; old strict validators need not accept new fields. Schema/vocabulary interpretation changes require an explicit release decision before use; no cache regeneration or migration is performed by validators.
