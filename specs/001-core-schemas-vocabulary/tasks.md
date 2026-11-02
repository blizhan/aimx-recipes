# Tasks: Core Schemas & Facet Vocabulary

**Input**: Design documents from `specs/001-core-schemas-vocabulary/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/validation-library.md](contracts/validation-library.md), [contracts/vocabulary.md](contracts/vocabulary.md), [contracts/proposal.md](contracts/proposal.md), [quickstart.md](quickstart.md).

**Tests**: Included because FR-001 explicitly requires valid/invalid examples, the user stories define validation scenarios, and SC-001–007 require verifiable contract, evidence, proposal, and determinism outcomes. For each story, write its listed tests first and confirm an expected failure before implementing the corresponding behavior. Do not count import/setup errors as evidence that the intended assertion fails.

**Organization**: Four story increments, preceded by shared setup/foundation and followed by cross-cutting acceptance. This file schedules implementation; no task is completed merely because its design exists.

## Format: `[ID] [P?] [Story] Description`

- `[P]` identifies tasks with disjoint files that may run concurrently once their stated prerequisites are complete; it does not waive phase gates.
- `[US1]`–`[US4]` map to the four stories in spec.md. Setup, foundation, and polish tasks have no story label.
- All task paths are relative to the repository root. This is a single Python package, not a service or CLI implementation.
- Shared files (`models.py`, `validation.py`, `contextual.py`, `schema_registry.py`, the fixture manifest) have one writer at a time. Follow serial order unless a parallel group is explicitly listed below.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the Python/uv package and test scaffolding without adding future pipeline dependencies.

- [X] T001 Initialize `pyproject.toml` and `src/aimx_recipes/__init__.py` with Python >=3.12, Hatchling >=1.27,<2, runtime jsonschema >=4.26,<5 and referencing >=0.37,<0.38, development pytest >=8,<10, and explicit root `schemas/` to wheel `aimx_recipes/_schemas/` resource mapping; add no CLI entry point or aimx dependency.
- [X] T002 Resolve the declared environment into `uv.lock`, verify `uv sync --locked`, and configure pytest discovery for `tests/unit/`, `tests/contract/`, and `tests/integration/` in `pyproject.toml`.
- [X] T003 Establish synthetic-fixture loading and a network-blocking test fixture in `tests/conftest.py`, plus the initial empty acceptance ledger in `tests/fixtures/manifest.json` with case IDs, input/context paths, expected level/status/codes/pointers, and covered FR/SC IDs; keep validation network blocking separate from dependency bootstrap.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement common parsing, schema resources, diagnostics, and the shared Problem entity before any story begins.

- [X] T004 Define shared ID, text, SHA-256, timestamp, exact-nullability conventions and reusable shapes in `schemas/2.0.0/common.schema.json`; add `schemas/2.0.0/problem.schema.json` for the shared Problem entity using Draft 2020-12, version 2.0.0, closed objects, and URN resource identities from the contracts.
- [X] T005 Define `ParseResult`, `ValidationContext`, `ValidationResult`, diagnostic dataclasses and the Problem TypedDict in `src/aimx_recipes/models.py`, and encode the result envelope in `schemas/2.0.0/validation-result.schema.json`; distinguish structural validity from contextual completeness and never expose execution readiness.
- [X] T006 [P] Add failing parser and exact-type boundary tests in `tests/unit/test_parsing.py` for duplicate keys, non-object roots, non-string mapping keys, lone surrogates, non-finite numbers, boolean numeric values, exact integers versus 1.0, and no input coercion or mutation.
- [X] T007 [P] Add failing result-contract tests in `tests/unit/test_diagnostics.py` for error-over-incomplete precedence, nullable malformed record identity, JSON Pointer escaping, documented diagnostic sorting/deduplication, stable templates, and matching human/JSON verdicts.
- [X] T008 Implement `parse_record` and JSON-domain preflight in `src/aimx_recipes/validation.py`, then deterministic result serialization and `render_text` in `src/aimx_recipes/diagnostics.py`; satisfy T006–T007 without leaking raw source text or dependency exception messages.
- [X] T009 Implement packaged schema loading, exact schema-version dispatch and an explicitly closed `referencing.Registry` in `src/aimx_recipes/schema_registry.py`, connect structural `validate_record` in `src/aimx_recipes/validation.py`, and export the working structural interfaces through `src/aimx_recipes/__init__.py`; unresolved resources must produce stable failures without HTTP/file retrieval.
- [X] T010 Add valid/invalid shared Problem fixtures in `tests/fixtures/problem/`, exercise them and schema meta-validation in `tests/contract/test_foundation.py`, and register their outcomes in `tests/fixtures/manifest.json`; verify foundation tests pass before opening story work.

**Checkpoint**: Strict parsing, schema loading, structural results, and a validatable Problem record are usable. No future entity schema is required by the loader until that schema is introduced; adding a known entity is explicit, never inferred from arbitrary resources.

## Phase 3: User Story 1 — Describe a problem and recipe consistently (Priority: P1) — MVP

**Goal**: Authors can validate Profiles and Recipes against one small controlled vocabulary while preserving uncertainty and rejecting unsupported conditions/actions.

**Independent Test**: `uv run --no-sync pytest tests/contract/test_vocabulary.py tests/contract/test_entities.py -k 'vocabulary or profile or recipe or problem'`. Valid rolling-origin profile/recipe examples agree; unknowns remain null, conflicts/inference survive unchanged, and invalid values/actions/operands fail at their exact fields. No evidence or Proposal workflow is needed.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing vocabulary/taxonomy/condition tests in `tests/contract/test_vocabulary.py` covering all entries and leaves from `specs/001-core-schemas-vocabulary/contracts/vocabulary.md`, typed operator operands, units, metric/k dependencies, rejection of aliases and executable expressions, and unknown/conflicted assertions.
- [X] T012 [P] [US1] Add failing valid/invalid Profile and Recipe cases in `tests/contract/test_entities.py` and synthetic inputs under `tests/fixtures/us1/`; cover explicit null versus missing fields, observed/reported/inferred/unknown basis, preserved conflict sources, no fabricated defaults, and rejection of authored aggregate evidence totals.

### Implementation for User Story 1

- [X] T013 [P] [US1] Author `schemas/2.0.0/facet-vocabulary.schema.json` and `schemas/2.0.0/facet-vocabulary.json` with every version-1 facet, cardinality, unit, metric domain/direction and permitted operator listed in the vocabulary contract; use measured counts/budgets without invented buckets.
- [X] T014 [P] [US1] Author `schemas/2.0.0/action-taxonomy.schema.json` and `schemas/2.0.0/action-taxonomy.json` with the seven documented parent groups and independently authored leaves, assigning only leaf names to recipes.
- [X] T015 [US1] Define Profile and Recipe contracts in `schemas/2.0.0/problem_profile.schema.json` and `schemas/2.0.0/recipe.schema.json`, extend their TypedDicts in `src/aimx_recipes/models.py`, and add shared facet/conflict/condition shapes in `schemas/2.0.0/common.schema.json`; preserve all required fields from data-model.md.
- [X] T016 [US1] Load validated vocabulary/taxonomy resources in `src/aimx_recipes/schema_registry.py` and enforce membership, null/basis rules, metric/k pairing, cardinality, condition-ID uniqueness and operand compatibility in `src/aimx_recipes/validation.py`; derive rules from the registries without a second handwritten enum authority or a matching engine.
- [X] T017 [US1] Add Profile→Problem and declared document-source reference checks plus duplicate typed-ID handling to the initial bundle validator in `src/aimx_recipes/contextual.py`; expose `validate_bundle` from `src/aimx_recipes/validation.py` and `src/aimx_recipes/__init__.py` with incomplete/error semantics, without reading source files or computing condition truth.
- [X] T018 [US1] Register US1 acceptance outcomes in `tests/fixtures/manifest.json`, run its independent test and foundation regression suite, and record the MVP result in `specs/001-core-schemas-vocabulary/checklists/implementation-validation.md`; use caller/annotation sources in the standalone MVP fixtures so US2 is not required.

**Checkpoint**: Profile and Recipe validation forms the MVP. Conditions can represent unknowns and prohibitions without declaring compatibility; full match assessments are introduced with US3.

## Phase 4: User Story 2 — Preserve the evidence behind an observation (Priority: P1)

**Goal**: Annotators can validate source-backed interventions, distinguish evidence strength/outcome, and obtain exact quote/provenance errors without repairs.

**Independent Test**: `uv run --no-sync pytest tests/integration/test_evidence_bundle.py tests/unit/test_quote_spans.py`. A linked Source/Document/Problem/Attempt/Evidence bundle with `recipe_id=null` validates; broken references/hashes/spans fail, missing text is incomplete, negative ablations remain negative, and adoption-only evidence has no invented gain. This uses the shared metric vocabulary and validator completed in US1 but does not require creating a Recipe or exercising a producer workflow; mapped-recipe behavior has an additional fixture.

### Tests for User Story 2

- [X] T019 [P] [US2] Add failing evidence-bundle scenarios and synthetic text in `tests/integration/test_evidence_bundle.py` and `tests/fixtures/us2/`, covering all seven evidence types, controlled comparison anchors, negative and use-only outcomes, unmapped recipes, numeric scope/metric requirements, joint changes, provenance variants, source licenses, and missing versus broken context.
- [X] T020 [P] [US2] Add failing Unicode/span boundary tests in `tests/unit/test_quote_spans.py` for repeated occurrences, code-point offsets, line breaks, source hash mismatch, 500/501-character limits, altered whitespace, out-of-bounds spans and unavailable text; assert no quote search, normalization, truncation or repair.

### Implementation for User Story 2

- [X] T021 [P] [US2] Define Source and Document contracts in `schemas/2.0.0/source.schema.json` and `schemas/2.0.0/document.schema.json`, with explicit license status, original snapshot identity, distinct normalized content hash and no embedded full-text field.
- [X] T022 [P] [US2] Define Attempt and Evidence contracts in `schemas/2.0.0/attempt.schema.json` and `schemas/2.0.0/evidence.schema.json`, including local extracted/human/synthetic provenance definitions, independent type/outcome enums, nullable recipe/measurements, metric_k, joint-change declarations and comparison anchors.
- [X] T023 [US2] Add Source, Document, Attempt and Evidence TypedDict interfaces in `src/aimx_recipes/models.py`, register their schemas in `src/aimx_recipes/schema_registry.py`, and implement structural scope/metric/domain, provenance-origin and comparison-anchor checks in `src/aimx_recipes/validation.py`; semantic causality remains a review judgment.
- [X] T024 [US2] Implement typed reference resolution, Source/Document snapshot agreement, normalized UTF-8 content hashes, provenance fingerprint/version checks, Attempt/Evidence document agreement and at least one Evidence per Attempt in `src/aimx_recipes/contextual.py`; require missing references in complete bundles to fail without demanding unavailable text be fabricated.
- [X] T025 [US2] Implement exact supplied-span verification in `src/aimx_recipes/contextual.py` using code-point indexing and the quote cap, reporting missing document text as incomplete and mismatches as invalid; preserve input objects and expose no filesystem resolver.
- [X] T026 [US2] Extend `tests/contract/test_entities.py` with valid/invalid pairs for the four US2 entities and add their acceptance entries to `tests/fixtures/manifest.json`; after US1, exercise a nonnull Recipe reference in `tests/integration/test_evidence_bundle.py` without using aggregate support counts as evidence.
- [X] T027 [US2] Run the US2 independent test, accumulated entity contracts and foundation regressions, then record evidence-traceability and missing-context results in `specs/001-core-schemas-vocabulary/checklists/implementation-validation.md`.

**Checkpoint**: The evidence journey is useful with unmapped recipes; mapped examples reuse US1. License metadata validates structure only and never grants redistribution permission.

## Phase 5: User Story 3 — Review a proposal without inventing an executable experiment (Priority: P2)

**Goal**: The Lead can inspect a grounded proposal whose unknown local decisions remain null and whose validation never grants execution admission.

**Independent Test**: `uv run --no-sync pytest tests/contract/test_proposal.py tests/integration/test_proposal_bundle.py`. Both nullable and fully populated suggestions retain `requires_lead_review`; wrong populated types and inconsistent assessments fail, supplied values survive unchanged, and no aimx state/file resolution occurs. Uses completed entity contracts from US1/US2, not their runtime producers.

### Tests for User Story 3

- [X] T028 [P] [US3] Add failing Proposal type/nullability tests in `tests/contract/test_proposal.py` and synthetic cases under `tests/fixtures/us3/`, covering contract_version 1 versus 1.0/boolean, nullable execution decisions, string acceptance_rule, argv array, exact observation_revision, numeric resource budgets, verified/enforced resource rules and the baseline/cost extension namespace.
- [X] T029 [P] [US3] Add failing contextual Proposal tests in `tests/integration/test_proposal_bundle.py` using existing US1/US2 fixtures, covering profile/recipe/evidence references, every hard condition represented exactly once, owner/facet consistency, unknown/conflicted facets never satisfied, explicit violations, and no aimx/Aim writes or file-backed admission checks.

### Implementation for User Story 3

- [X] T030 [US3] Author `schemas/2.0.0/experiment_proposal.schema.json` and its TypedDicts in `src/aimx_recipes/models.py` from the exact envelope and nullable-field matrix in `specs/001-core-schemas-vocabulary/contracts/proposal.md`; keep review_status constant and preflight references distinct from recipes Evidence IDs.
- [X] T031 [US3] Register the Proposal schema in `src/aimx_recipes/schema_registry.py` and implement populated aimx type, resource consistency, multiple-intervention confounder and namespace rules in `src/aimx_recipes/validation.py`; permit only documented nulls and do not import aimx or infer budgets/thresholds.
- [X] T032 [US3] Implement Proposal relationship and assessment consistency checks in `src/aimx_recipes/contextual.py`, requiring each referenced hard condition exactly once and preventing unknown/conflicted assertions from supporting satisfied assessments; do not add a condition evaluator, ranking, proposal generator or execution-ready status.
- [X] T033 [US3] Add a project-authored compatibility reference manifest pinned to aimx `1b2dd98b6621aa893c056013cd0dd06fff7ca405` in `tests/fixtures/us3/aimx-compatibility.json`, extend `tests/contract/test_entities.py` with the eighth valid/invalid pair, and register Proposal cases in `tests/fixtures/manifest.json` without requiring a sibling checkout.
- [X] T034 [US3] Run Proposal and accumulated contract/bundle tests, verify nullable and fully populated artifacts both remain suggestions, and record the result in `specs/001-core-schemas-vocabulary/checklists/implementation-validation.md`.

**Checkpoint**: Eight entity types are supported. A structurally/contextually valid Proposal is still not an executable aimx contract; Lead review and upstream admission remain external.

## Phase 6: User Story 4 — Recognize compatible and incompatible records (Priority: P2)

**Goal**: Maintainers can audit version interpretation, all entity examples, regeneration impact and deterministic results before downstream workflows consume records.

**Independent Test**: `uv run --no-sync pytest tests/contract/test_versions.py tests/contract/test_entities.py tests/integration/test_determinism.py tests/unit/test_offline_registry.py tests/unit/test_diagnostics.py`. All eight valid/invalid pairs have documented verdicts; unsupported versions fail; release impact is explicit; three offline repeats produce identical results and leave all inputs unchanged.

### Tests for User Story 4

- [X] T035 [P] [US4] Add failing version/release-ledger tests in `tests/contract/test_versions.py` and `tests/fixtures/us4/`, covering absent/unsupported entity and vocabulary/taxonomy versions, explicit compatibility classification, regeneration decisions/rationale and all-eight-entity acceptance coverage.
- [X] T036 [P] [US4] Add three-run canonical result-byte, stable human-output and unchanged nested-input/context tests in `tests/integration/test_determinism.py` using accumulated fixtures, including invalid and incomplete outcomes and input IDs with deterministic diagnostic sorting.
- [X] T037 [P] [US4] Add offline registry/resource-closure tests in `tests/unit/test_offline_registry.py` for all packaged schemas, unregistered HTTP/file URNs/URLs, no retrieval or socket calls and explicit resource failures; verify standalone schema shape versus full library vocabulary checks is documented by the assertions.

### Implementation for User Story 4

- [X] T038 [US4] Publish `schemas/2.0.0/release.json` with initial schema/vocabulary/taxonomy versions, all affected entity kinds, compatibility=initial, extraction_regeneration=not_applicable, rationale and pinned aimx revision; add the documented version/regeneration policy to `schemas/README.md` with no automatic migration or regeneration.
- [X] T039 [US4] Complete exact version support and release/registry validation in `src/aimx_recipes/schema_registry.py` and stabilize result aggregation in `src/aimx_recipes/diagnostics.py` and `src/aimx_recipes/validation.py` to satisfy T035–T037; keep old/new-reader compatibility explicit rather than accepting arbitrary matching-major versions.
- [X] T040 [US4] Complete and audit `tests/fixtures/manifest.json` with all eight entity pairs, seven evidence types, boundary/null/version cases and FR-001–016/SC-001–007 mappings; update `tests/contract/test_entities.py` and `tests/contract/test_versions.py` so omissions or undocumented fixture verdicts fail visibly.
- [X] T041 [US4] Run the US4 independent test and complete accumulated suites with network blocked during validation, then record exact interpreter/dependency versions and deterministic outcomes in `specs/001-core-schemas-vocabulary/checklists/implementation-validation.md`.

**Checkpoint**: Release interpretation, evidence validation and uncertainty handling are reproducible; supported versions and incomplete checks are visible to consumers.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Prove the installed artifact works outside the checkout and deliver accurate usage/acceptance documentation.

- [X] T042 [P] Add `tests/integration/test_installed_wheel.py` to build or select exactly one fresh wheel, provision an isolated temporary environment outside the checkout using already available dependencies, compare packaged/source schema resource bytes, and run public-library validation with network blocked; report missing build/prerequisites as failures rather than skips and adjust only resource packaging in `pyproject.toml` if required.
- [X] T043 [P] Document the public parsing/validation/result interfaces and structural-versus-contextual validity in `README.md` and `README.zh-CN.md`, and reconcile `specs/001-core-schemas-vocabulary/quickstart.md` with implemented commands; preserve source-text, unknowns, licensing and requires_lead_review boundaries without adding CLI promises.
- [X] T044 Run the full `specs/001-core-schemas-vocabulary/quickstart.md` acceptance sequence on Python 3.12 and 3.13, including a fresh wheel and installed-resource test, and record results plus the final constitution check in `specs/001-core-schemas-vocabulary/checklists/implementation-validation.md`; leave unresolved failures explicit and do not mark implementation complete while any required check fails.

## Dependencies & Execution Order

### Phase dependencies

```text
Setup T001–T003
  └─ Foundation T004–T010
       └─ US1 T011–T018 (MVP: shared vocabulary + profiles/recipes)
            └─ US2 T019–T027 (shared metric vocabulary + evidence)
                 └─ US3 T028–T034 (profile + recipe + evidence contracts)
                      └─ US4 T035–T041 (all eight entities)
                           └─ Polish T042–T044
```

The default single-owner order is T001 through T044, using the parallel pairs/groups below if helpful. Independent acceptance means a story can be tested on synthetic inputs once its declared contracts exist; it does not mean duplicate shared implementation or bypass dependencies. US3 necessarily consumes the profile/recipe/evidence types, and US4 checks the complete eight-entity surface.

### Within-phase ordering and ownership

- Setup: T001 → T002 → T003. Foundation: T004 → T005 → (T006 ∥ T007) → T008 → T009 → T010.
- US1: (T011 ∥ T012) → (T013 ∥ T014) → T015 → T016 → T017 → T018. Test construction uses frozen design documents; verify expected failures before implementation.
- US2: (T019 ∥ T020) → (T021 ∥ T022) → T023 → T024 → T025 → T026 → T027. T026's mapped Recipe example requires US1. US2 requires US1's shared metric registry; its core tests use recipe_id=null and the foundational Problem contract to isolate the evidence journey.
- US3: (T028 ∥ T029) → T030 → T031 → T032 → T033 → T034.
- US4: (T035 ∥ T036 ∥ T037) → T038 → T039 → T040 → T041.
- Polish: (T042 ∥ T043) → T044. Build/installation may provision artifacts; the validation invocation itself remains offline and read-only.
- Do not run US1/US2 shared-file implementation simultaneously in one checkout even though their input journeys are distinct. Any concurrency uses isolated worktrees or disjoint-file tasks, with one integration owner and serialized manifest/model updates. No agent launch is implied by this task file.

## Parallel Execution Examples

### User Story 1

After foundation, author T011 vocabulary tests and T012 entity tests together: `tests/contract/test_vocabulary.py` versus `tests/contract/test_entities.py` and `tests/fixtures/us1/`. After their assertions are ready, T013 vocabulary resources and T014 taxonomy resources are another disjoint-file pair. Join before T015–T018.

### User Story 2

After US1, author T019 bundle scenarios in `tests/integration/test_evidence_bundle.py` and T020 span boundaries in `tests/unit/test_quote_spans.py` together. Then T021 Source/Document schemas and T022 Attempt/Evidence schemas can be authored concurrently without editing common definitions or models. Join before T023 adds shared interfaces.

### User Story 3

After US1/US2, author T028 Proposal structural cases in `tests/contract/test_proposal.py` and T029 bundle cases in `tests/integration/test_proposal_bundle.py` together. T029 consumes existing fixture inputs and must not mutate T028's fixture directory. Shared schema/validator work remains serial.

### User Story 4

After all eight entities exist, T035 release/version tests, T036 deterministic bundle tests and T037 offline reference tests can be authored concurrently in their separate files. Join before release/registry/diagnostics changes; the global manifest has one writer in T040.

## Requirement Coverage

| Requirement group | Tasks providing implementation and acceptance |
| --- | --- |
| FR-001 entity contracts | T004–T010, T012/T015, T021–T023/T026, T030/T033, T040 |
| FR-002 diagnostic/validation contract | T005–T010, T017, T024–T025, T036–T041 |
| FR-003 identity/source contracts | T021, T024, T019/T026 |
| FR-004–007 vocabulary, uncertainty, conditions, taxonomy | T011–T018; supplied assessment consistency T029/T032 |
| FR-008–011 attempts, typed evidence, spans, provenance | T019–T027 |
| FR-012 no authored aggregate facts | T012/T015 and T019/T026 |
| FR-013–014 match metadata and nullable Proposal | T028–T034 |
| FR-015 version policy | T009, T035, T038–T041 |
| FR-016 offline scope and output boundaries | T001/T003/T008/T009, T029, T036–T037, T042–T044 |
| SC-001/002 | T018, T026, T033, T040 |
| SC-003/004 | T019–T027 |
| SC-005 | T028–T034 |
| SC-006/007 | T035–T044 |

## Implementation Strategy

### MVP first

Complete Setup, Foundation and US1 (T001–T018). Demonstrate the shared rolling-origin Profile/Recipe vocabulary, preserved unknown/conflicts and precise invalid-field diagnostics. This is the suggested MVP; evidence ingestion, extraction, matching, execution and CLI remain outside it.

### Incremental delivery

Add the unmapped observation/evidence journey in US2, then integrate mapped Recipes. Add Proposal validation in US3 once its contracts exist. Finish all-entity/version/reproducibility acceptance in US4 and wheel/documentation checks in Polish. Each checkpoint reruns relevant earlier tests; no optional performance or infrastructure work is added without a demonstrated need.

### Completion discipline

Keep implementation checkboxes unchecked until their concrete artifacts and specified checks exist. Maintain synthetic fixtures rather than bundling source writeups, preserve unknown values instead of repairs, and record only observed validation outcomes. The implementation-validation record is created by T018 and updated by a single owner at each subsequent checkpoint; it must not predeclare tests passed.

## Task Generation Validation

The task list contains 44 sequential tasks: Setup 3, Foundation 7, US1 8, US2 9, US3 7, US4 7, Polish 3. Seventeen tasks carry [P], limited to the disjoint-file groups described above. All tasks have repository-relative file paths and story labels only in story phases. Before/after tasks hook checks found no registrations in `.specify/extensions.yml`; no hook dispatch is required.
