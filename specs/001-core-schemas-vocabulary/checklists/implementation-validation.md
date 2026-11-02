# Implementation Validation Record: Core Schemas & Facet Vocabulary

**Date**: 2026-11-02
**Environment**: Python 3.13.13 (aarch64-linux), uv 0.11.21, jsonschema 4.26.0, referencing 0.37.0, pytest 9.2.0

**Current status**: The original 1.0.0 acceptance claim below was superseded by the completion review, which found missing input, reference, assessment, and determinism checks despite the original 54 passing tests. Checkpoints 1–5 are historical execution records, not acceptance evidence for the corrected implementation. See Checkpoint 6 for the current 2.0.0 release and verified results.

## Checkpoint 1: MVP (User Story 1, T018)

- **Scope**: Setup (T001–T003), Foundation (T004–T010), and User Story 1 (T011–T018).
- **Deliverables**:
  - `pyproject.toml`, `uv.lock`, test discovery and offline network blocking fixture.
  - Draft 2020-12 schemas: `common.schema.json`, `problem.schema.json`, `validation-result.schema.json`, `facet-vocabulary.schema.json`, `facet-vocabulary.json`, `action-taxonomy.schema.json`, `action-taxonomy.json`, `problem_profile.schema.json`, `recipe.schema.json`.
  - Modules: `models.py`, `schema_registry.py`, `diagnostics.py`, `validation.py`, `contextual.py`.
  - Synthetic fixtures: `problem/` and `us1/`.
  - Acceptance ledger: `manifest.json` with Problem, Profile, and Recipe cases.
- **Independent Test**:
  - `uv run --no-sync pytest tests/contract/test_vocabulary.py tests/contract/test_entities.py`
  - Result: 10 passed.
- **Foundation Regressions**:
  - `uv run pytest tests/unit tests/contract`
  - Result: 24 passed in 0.04s.
- **Verdict**: PASS. Controlled vocabulary, action taxonomy, Profile/Recipe structural contracts, and preserved uncertainty/conflicts verified without external dependencies.

## Checkpoint 2: Evidence Grounding (User Story 2, T027)

- **Scope**: Source, Document, Attempt, Evidence contracts (T019–T027).
- **Deliverables**:
  - Schemas: `source.schema.json`, `document.schema.json`, `attempt.schema.json`, `evidence.schema.json`.
  - Provenance models: extracted, human, synthetic.
  - Span verification, quote character cap (500), and comparison anchors in `contextual.py` and `validation.py`.
  - Synthetic fixtures: `us2/` bundle, document text, and entity test cases.
  - Acceptance ledger: `manifest.json` updated with Source, Document, Attempt, Evidence valid/invalid entries.
- **Independent Test**:
  - `uv run --no-sync pytest tests/integration/test_evidence_bundle.py tests/unit/test_quote_spans.py`
  - Result: 9 passed in 0.03s.
- **Accumulated Regressions**:
  - `uv run pytest tests/unit tests/contract tests/integration`
  - Result: 33 passed in 0.05s.
- **Verdict**: PASS. Strict quote spans, hash verification, missing-context incomplete status, license metadata, and unmapped/mapped recipe references verified.

## Checkpoint 3: Proposal Governance and Lead Review (User Story 3, T034)

- **Scope**: Experiment Proposal entity, aimx-compatibility manifest, assessment consistency (T028–T034).
- **Deliverables**:
  - Schema: `experiment_proposal.schema.json`.
  - Pinned compatibility manifest: `tests/fixtures/us3/aimx-compatibility.json` pinned to aimx revision `1b2dd98b6621aa893c056013cd0dd06fff7ca405`.
  - Proposal models, nullability validation, resource verification, and assessment consistency in `validation.py` and `contextual.py`.
  - Synthetic fixtures: `us3/proposal_valid.json`, `us3/proposal_invalid.json`.
  - Acceptance ledger: `manifest.json` updated with Proposal entries.
- **Independent Test**:
  - `uv run --no-sync pytest tests/contract/test_proposal.py tests/integration/test_proposal_bundle.py`
  - Result: 11 passed in 0.04s.
- **Accumulated Regressions**:
  - `uv run pytest tests/unit tests/contract tests/integration`
  - Result: 44 passed in 0.07s.
- **Verdict**: PASS. Proposal retains `requires_lead_review`, all hard conditions are assessed, conflicted/unknown facets cannot support satisfied assessments, and no aimx/Aim state writes or file-backed admissions occur.

## Checkpoint 4: Versions, Closure, and Determinism (User Story 4, T041)

- **Scope**: Release manifest, offline registry closure, version policy, determinism (T035–T041).
- **Deliverables**:
  - `schemas/1.0.0/release.json`: initial release declaration, compatibility=initial, extraction_regeneration=not_applicable, aimx commit pin `1b2dd98b6621aa893c056013cd0dd06fff7ca405`.
  - `schemas/README.md`: versioning and offline registry documentation.
  - Acceptance ledger: `manifest.json` complete with all 8 entity pairs and version cases.
  - Determinism test: three repeated runs verify identical canonical JSON bytes, stable text rendering, and unchanged input objects.
  - Registry closure test: offline resolution, no socket calls, explicit `NoSuchResource`/`Unresolvable` on unknown resources.
- **Independent Test**:
  - `uv run --no-sync pytest tests/contract/test_versions.py tests/contract/test_entities.py tests/integration/test_determinism.py tests/unit/test_offline_registry.py tests/unit/test_diagnostics.py`
  - Result: 14 passed in 0.04s.
- **Accumulated Regressions**:
  - `uv run pytest tests/unit tests/contract tests/integration`
  - Result: 53 passed in 0.08s.
- **Verdict**: PASS. Offline resource closure, exact version dispatch, deterministic canonical results, and complete 8-entity manifest coverage verified.

## Checkpoint 5: Polish, Matrix Validation & Final Acceptance (T044)

- **Scope**: Installed wheel validation outside checkout, documentation, Python 3.12 and 3.13 dual-version acceptance matrix, final Constitution verification (T042–T044).
- **Environment Matrix**:
  - Python 3.12.3: 54 / 54 tests passed in 0.51s.
  - Python 3.13.13: 54 / 54 tests passed in 0.42s.
- **Quickstart Scenarios (All Passed)**:
  - Scenario 1 (Entity contracts and vocabulary): 10 passed.
  - Scenario 2 (Linked evidence and quote verification): 9 passed.
  - Scenario 3 (Nullable proposal and Lead boundary): 11 passed.
  - Scenario 4 (Reproducibility and offline safety): 9 passed.
  - Scenario 5 (Installed-wheel resource closure and isolation): 1 passed.
- **Wheel Resource Verification**:
  - `aimx_recipes-0.1.0-py3-none-any.whl` contains all schemas under `aimx_recipes/_schemas/` matching repository source files byte-for-byte.
  - Installed and verified in isolated temporary environment outside the repository checkout with network blocked.
- **Constitution Compliance Gate**:
  - Principle I (Evidence Grounding): PASS. Required Attempt→Evidence→Document→Source traceability, exact code-point spans (1–500), content hash matching, and distinct type/outcome classifications.
  - Principle II (Recipes Are Not Findings): PASS. Proposals remain `requires_lead_review`, execution fields remain nullable, and no writes to aimx/Aim repositories occur.
  - Principle III (Deterministic, LLM-Free Path): PASS. Completely offline registry with no network or LLM dependencies; three repeat runs produce bit-for-bit identical JSON bytes and stable text output.
  - Principle IV (Uncertainty & Hard Constraints): PASS. Basis preservation, unknown values remain null, conflicts preserved, hard constraints strictly enforced, and satisfied assessments forbidden for unknown/conflicted facets.
  - Principle V (Untrusted Sources & License Discipline): PASS. Source licenses recorded and validated as metadata without inferring redistribution permissions.
  - Principle VI (Evaluation Before Expansion): PASS. Pinned to aimx commit `1b2dd98b6621aa893c056013cd0dd06fff7ca405`; acceptance ledger verified.
  - Principle VII (Progressive Complexity): PASS. Clean library surface (`parse_record`, `validate_record`, `validate_bundle`, `render_text`) with zero runtime framework or CLI bloat.
- **Historical Verdict (superseded by completion review)**: The original 54-test suite passed, but did not establish full spec acceptance. The claim that all 44 tasks were fully verified was withdrawn after review.

## Checkpoint 6: Completion Review Corrections — Contract 2.0.0

- **Scope**: All findings from the Standards and Spec completion review, including the duplicated provenance-check heuristic.
- **Regression-first evidence**: The initial review regression suite produced 36 failures and 5 passes against the draft implementation. Those failures exercised real library entry points rather than replacement validators.
- **Corrections and acceptance evidence**:

  | Review area | Corrected behavior and verification |
  | --- | --- |
  | Vocabulary resources | Both data resources validate against their own closed schemas; invalid vocabulary fails registry construction. |
  | JSON domain and malformed inputs | Reject non-JSON objects, tuples, sets, lone surrogates, cyclic values, and non-object roots; malformed bundle fields produce diagnostics instead of exceptions. Overflowed JSON numbers are rejected during parsing. |
  | Conditions and applicability | Recipe applicability is a shared-vocabulary condition list. All condition IDs are unique within the owner; numeric operands obey facet bounds. Profile map_at_k/metric.k pairing is checked. |
  | Proposal values | Nullable decisions still accept null; populated strings must contain non-whitespace text and populated hashes must contain exactly 64 lowercase hex characters. |
  | Assessments | Resolve typed owner/condition identities and verify the declared facet. Wrong owners, nonexistent conditions, disguised unknown facets, missing hard assessments, and cross-type identity collisions have regression cases. |
  | Linked references | Problem source IDs and conflict assertion document references must resolve in the supplied bundle. Structurally invalid records are excluded from contextual resolution. |
  | Document verification | Every Document requires local text for full contextual validity, independently of Evidence presence. Hash checking occurs once per Document; missing text is incomplete and mismatched text is invalid. |
  | Provenance | Extracted schema version must match the containing record. RFC3339 timestamps are actively checked with an offline format checker; provenance diagnostics identify the affected field. Attempt/Evidence share one contextual provenance check. |
  | Diagnostics and determinism | Comparison diagnostics use fixed templates without source-text echo. Rendering escapes control characters. Three separate PYTHONHASHSEED processes produce identical canonical diagnostic JSON. |
  | Evidence examples | The manifest includes fully linked, project-authored examples for all seven evidence types, including negative controlled ablation and adoption with unclear outcome and absent measurements. |
  | Packaging | Runtime lookup uses importlib.resources only; editable installs expose the authoritative schema directory through the source-package symlink. Wheel inventory matches the source byte-for-byte, and isolated validation outside the checkout passes. |

- **Version and regeneration decision**: All contract resources and validation envelopes are 2.0.0. This is a breaking correction of the unreleased 1.0.0 draft, principally because applicability changes shape and validity rules become stricter. Previous versions fail explicitly. No frozen extraction corpus exists here, so regeneration is not_applicable; any external frozen 1.0.0 extraction requires an explicit regeneration/review before use. Validation performs neither migration nor regeneration. The pinned aimx revision and integer experiment contract_version remain unchanged.
- **Final offline verification**:
  - Python 3.12.3: `uv run --frozen --offline pytest -q` — **108 passed**.
  - Python 3.13.13: `UV_PROJECT_ENVIRONMENT=/tmp/aimx-recipes-spec001-py313 uv run --python /home/blizhan/miniconda3/bin/python3.13 --frozen --offline pytest -q` — **108 passed**.
  - Both suites include the installed-wheel isolation test, resource inventory checks, and cross-process determinism regression.
  - Additional bounded probe: 768 malformed top-level field mutations across all eight entity fixtures completed record and bundle validation without exceptions; diagnostic JSON remained UTF-8 serializable.
- **Current verdict**: PASS for the reviewed corrections and the current acceptance suite. No runtime network/model calls, experiment execution, or aimx/Aim state writes were introduced.
