# Schema Registry and Versioning Policy

## Structure

Authoritative schema and vocabulary resources are located under versioned directories:

- `schemas/2.0.0/common.schema.json`: Shared shapes, URN identifiers, timestamps, hashes, and provenance definitions.
- `schemas/2.0.0/<entity>.schema.json`: JSON Schema (Draft 2020-12) for each of the eight entities:
  - `source`, `document`, `problem`, `problem_profile`, `recipe`, `attempt`, `evidence`, `experiment_proposal`.
- `schemas/2.0.0/facet-vocabulary.schema.json` & `facet-vocabulary.json`: Controlled facet definitions and metrics.
- `schemas/2.0.0/action-taxonomy.schema.json` & `action-taxonomy.json`: Seven parent action groups and authorized leaves.
- `schemas/2.0.0/validation-result.schema.json`: Schema for validation outcome and diagnostic envelopes.
- `schemas/2.0.0/release.json`: Release declaration manifest.

## Versioning & Compatibility Policy

1. **Exact Version Support**: Schemas, vocabularies, and taxonomies use exact version identifiers (`2.0.0`). Validators dispatch on exact version strings rather than arbitrary SemVer ranges.
2. **No Automatic Migration**: Records are never mutated, enriched, or upgraded automatically. Compatibility changes require an explicit release declaration. Version 1.0.0 is unsupported. In 2.0.0, Recipe `applicability` is a list of shared vocabulary conditions rather than free text; populated Proposal strings/hashes and reference/provenance/domain checks are stricter. Validation envelopes, vocabulary, and taxonomy resources also declare 2.0.0.
3. **Extraction Regeneration**: `release.json` records whether downstream frozen extraction caches must be regenerated (`required`, `not_required`, or `not_applicable`). Release 2.0.0 is a breaking correction of the unreleased 1.0.0 draft. Regeneration is `not_applicable` because no frozen extraction corpus exists in this repository. Any external frozen 1.0.0 extraction must be explicitly regenerated and reviewed before use; validators never migrate or regenerate it automatically.
4. **Offline Closure**: All schema `$id` and `$ref` links use URN format (`urn:aimx-recipes:schema:2.0.0:<name>`) and resolve strictly within the packaged registry without network or filesystem lookup.
5. **Standalone Shape vs Library Rules**: Standalone JSON Schemas enforce basic structural shape, closed properties, and scalar types. The Python library additionally validates registry membership, exact-type domain boundaries, condition operands, and bundle-wide reference graph integrity.
