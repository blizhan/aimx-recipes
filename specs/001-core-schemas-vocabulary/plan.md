# Implementation Plan: Core Schemas & Facet Vocabulary

**Branch**: `main` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-core-schemas-vocabulary/spec.md`

**Status**: Implemented and corrected after completion review; current contract release 2.0.0. The original planning structure below is retained for traceability. The setup script returned `001-core-schemas-vocabulary` as BRANCH from feature discovery; actual Git branch remains `main`. `.specify/feature.json` selects this feature independently of branch naming.

## Summary

Build a small offline Python contract library for eight research entities with versioned JSON Schemas as the structural authority. A shared facet vocabulary and action taxonomy define controlled values; explicit Python checks verify relationships, provenance, exact quotes, and supplied assessment consistency. Typed Python interfaces support callers without duplicating runtime validation authority. Proposals preserve aimx field types while keeping local execution decisions nullable and admission under Lead ownership.

The output is schemas, validators, fixtures, and contract documentation. It adds no runtime command, data ingestion, extraction, storage engine, matching algorithm, or proposal generator. Research and design decisions are recorded in [research.md](research.md), [data-model.md](data-model.md), and [contracts/validation-library.md](contracts/validation-library.md).

## Technical Context

**Language/Version**: Python >=3.12; acceptance matrix 3.12 and 3.13; uv environment and lockfile management.

**Primary Dependencies**: jsonschema >=4.26,<5; referencing >=0.37,<0.38; rfc3339-validator >=0.1.4,<0.2 to enable offline date-time format validation. Hatchling >=1.27,<2 for packaging; pytest >=8,<10 for development. Implementation resolves and commits exact versions in uv.lock. No aimx, Aim, YAML parser, DuckDB, Arrow, model SDK, or CLI framework dependency.

**Storage**: Versioned project-authored schema/vocabulary resources and synthetic fixtures; no runtime persistence. Root schemas are packaged into the wheel and loaded via importlib.resources.

**Testing**: pytest contract, unit, and integration suites; acceptance ledger; schema-reference closure; installed-wheel smoke test outside checkout; three-run deterministic results and unchanged inputs.

**Target Platform**: Offline local Python environments and Linux CI; dependency bootstrap is separate from offline validation.

**Project Type**: Python library foundation consumed by later CLI workflows.

**Performance Goals**: Identical results in three repeat runs with stable diagnostics; no latency SLA or benchmark optimization is introduced by this spec. Bundle memory is proportional to supplied records and document text; no corpus loading occurs.

**Constraints**: No network/model access, source or state mutation, implicit coercion, remote reference fetching, text normalization, invented local execution decisions, or executable expressions. Quote cap 500 Unicode code points. Exact integer boundary rules supplement JSON Schema semantics.

**Scale/Scope**: Eight entities; one supported schema/vocabulary/taxonomy release 2.0.0 (breaking correction of the unreleased 1.0.0 draft); P0 tabular/temporal facets, transfer-boundary modalities, and small action taxonomy. Bundle-scoped validation only.

## Constitution Check

*GATE: evaluated before research and again against the completed Phase 1 design. Constitution version 1.0.1.*

| Gate | Before research | Post-design evidence and verdict |
| --- | --- | --- |
| I. Evidence traceability | PASS | PASS: required Attempt→Evidence→Document→Source links; exact span/hash checks; typed evidence/outcomes; no authored support totals |
| II. aimx ownership | PASS | PASS: nullable proposal contract, requires_lead_review invariant, no aimx runtime dependency/resolver/state write |
| III. Determinism | PASS | PASS: closed offline schema registry, pure validators, explicit context, stable result ordering, repeat-run acceptance test |
| IV. Uncertainty/hard constraints | PASS | PASS: null unknowns and preserved conflicts; typed conditions and consistent assessments; no relevance or scoring bypass |
| V. Untrusted input/licenses | PASS | PASS: strict JSON domain, no expression execution, synthetic fixtures, local text context only, source license metadata; no release authorization inferred |
| VI. Evaluation before expansion | PASS | PASS: fixture-based contract validation, no retrieval tuning or benchmark modifications; future extraction regeneration remains gated |
| VII. Progressive complexity | PASS | PASS: small library, no new service/storage, future CLI can serialize the same results; CLI deferred explicitly by Spec01 |
| Versioning/output discipline | PASS | PASS: exact version dispatch, release/regeneration declaration, human/JSON result contract and package-resource checks |

No violation or exception is required. Library validation is read-only; authoring code/contracts during development is not a write-capable runtime command. This feature does not release third-party evidence. Source license status remains metadata subject to later release checks.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-schemas-vocabulary/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── validation-library.md
│   ├── vocabulary.md
│   └── proposal.md
└── checklists/requirements.md
```

`tasks.md` belongs to the next command and is not created here. Contracts are normative design documents; executable JSON Schemas are implementation deliverables.

### Source Code (repository root)

```text
pyproject.toml
uv.lock
schemas/2.0.0/
├── common.schema.json
├── <entity_type>.schema.json      # eight entity schemas
├── facet-vocabulary.schema.json
├── facet-vocabulary.json
├── action-taxonomy.schema.json
├── action-taxonomy.json
├── validation-result.schema.json
└── release.json
src/aimx_recipes/
├── __init__.py                   # public interfaces
├── models.py                     # TypedDicts, context/results
├── schema_registry.py            # packaged resources, offline ref closure
├── validation.py                 # strict parse/preflight and entry points
├── contextual.py                 # references, provenance, quotes, assessments
└── diagnostics.py                # normalized codes, sorting, text rendering
# Wheel additionally contains aimx_recipes/_schemas from root schemas/.
tests/
├── fixtures/                     # synthetic data + acceptance manifest
├── contract/                     # entities, vocabulary, proposal
├── unit/                         # strictness, spans, diagnostics, offline registry
└── integration/                  # linked bundles, determinism, installed wheel
```

**Structure Decision**: Start with one package and one authoritative root schema tree, consistent with the repository's proposed src layout. Modules follow concrete validation responsibilities rather than future pipeline services. No source/package/test files exist yet; this tree is the implementation target. Package-resource mapping is explicit so tests cannot accidentally depend on checkout-relative schema paths.

## Phase 0: Research Closure

The worker inspected current repository documents and the exact local aimx contract, and probed jsonschema/referencing behavior without modifying files. [research.md](research.md) records decisions, rationale, and alternatives for authority, strictness, offline references, nullable proposals, vocabulary, packaging, and versions. No unresolved technical clarification remains.

The pinned aimx contract is `1b2dd98b6621aa893c056013cd0dd06fff7ca405`. Two older architecture examples are superseded for this feature: quote normalization is prohibited, and qualitative costs cannot populate numeric resource budgets. The local upstream contract requires exact integers and more runtime admission checks than its schema alone expresses.

## Phase 1: Design and Implementation Sequence

1. Establish package metadata, uv lockfile, resource packaging, strict JSON parsing, and result/context types. Define stable diagnostics and tests for duplicate keys, non-finite values, exact integers, and unsupported versions.
2. Author shared definitions, eight schemas, initial vocabulary/taxonomy, and release declaration from [data-model.md](data-model.md) and [vocabulary.md](contracts/vocabulary.md). Add valid/invalid fixtures and registry membership checks; do not duplicate enum authorities in Python.
3. Add contextual validation over complete bundles: typed references and identity collisions, source/document snapshot/hash relationships, provenance variants, Attempt/Evidence links, exact quote spans, and missing-context results. Keep semantic evidence review explicit.
4. Implement nullable Proposal validation against [proposal.md](contracts/proposal.md), including populated upstream types, assessment references, null preservation, and requires_lead_review. No upstream state resolution or execution-ready result.
5. Complete public result rendering, fixture coverage mapping, offline/determinism tests, and installed-wheel validation. Exercise [quickstart.md](quickstart.md) on both supported test interpreters.

These are implementation dependencies, not generated task assignments. A single implementation owner can deliver them in order; parallel writers are not required by this plan.

## Acceptance and Traceability

| Requirements | Planned evidence |
| --- | --- |
| FR-001/002/015 | Eight valid/invalid pairs; strict parse and versions; stable text/JSON diagnostics; release declaration |
| FR-003/008–012 | Linked synthetic evidence bundles; hash/quote checks; scope and provenance failures; missing-context and duplicate-ID cases |
| FR-004–007 | Shared vocabulary, typed conditions, uncertainty/conflict preservation, complete action taxonomy fixtures |
| FR-013/014 | Nullable/fully populated Proposal cases, upstream strict types, match-assessment consistency and immutable review status |
| FR-016 | Network-blocked tests, unchanged input/state checks, wheel outside checkout, no corpus/model/service dependency |

All SC-001–007 map to runnable future checks in quickstart. No implementation acceptance tests have been run at planning time. Planning verification passed for all seven design artifacts: relative links, balanced code fences, whitespace, feature pointer, absence of unresolved placeholders, and the Phase 1 boundary (no tasks.md). Scope and constitution checks passed on review. `.specify/extensions.yml` registers neither before_plan nor after_plan hooks, so both were skipped.

## Complexity Tracking

No constitutional violations to justify. Contextual checks supplement portable schemas because references and local document bodies are not part of a single record. No second runtime schema authority, general expression evaluator, or compatibility adapter service is introduced.
