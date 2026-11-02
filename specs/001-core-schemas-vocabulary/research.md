# Research: Core Schemas & Facet Vocabulary

Date: 2026-11-02. Status: complete. Scope: local repository and pinned sibling aimx source; no web research, dependency installation, or implementation. A read-only subagent worker inspected source contracts and ran small validation probes; the parent owns the decisions below.

## 1. Structural authority

**Decision:** Author JSON Schema Draft 2020-12 contracts under `schemas/1.0.0/`. Use `jsonschema` and `referencing` for structural checks, with Python TypedDict interfaces and frozen result/context dataclasses. Vocabulary and taxonomy have one authoritative definition each. Python interfaces do not maintain independent enum registries or perform competing validation.

**Rationale:** [Roadmap 001](../../ROADMAP.md) calls for portable schemas and Python models. Consumers outside Python need the same structural rules. Cross-record invariants cannot be expressed by standalone schemas and remain explicit contextual checks.

**Alternatives considered:** Pydantic-first schema generation introduces generation synchronization and custom-validator visibility concerns. Two independently maintained runtime validators would create conflicting authorities. A handwritten validator alone would not provide portable contracts.

## 2. Strictness and offline references

**Decision:** Accept JSON-domain values only, reject duplicate JSON keys, booleans in numeric slots, non-finite numbers, unsupported versions, extra properties, and implicit coercion. Exact integers are required for all integer fields, including span offsets and aimx integers. Package a closed schema registry whose unknown-resource retrieval callback always raises `NoSuchResource`.

**Rationale:** The worker's local probes confirmed that standard JSON Schema accepts `1.0` for integer, while aimx does not. A small JSON-domain/type preflight closes that boundary. Schema identifiers are identities, never permission to fetch remote resources.

**Alternatives considered:** Automatic reference retrieval violates offline determinism. Coercion/default filling would change evidence. Depending on validator exception wording would make diagnostics unstable.

## 3. Validation layers and outcomes

**Decision:** Separate parsing, structural validation, and contextual checks. Return `valid`, `invalid`, or `incomplete`, with an explicit `level` of `structural` or `contextual`. Missing caller-supplied reference material is incomplete; a broken reference inside a declared complete bundle is invalid. Normalize and sort diagnostics; human text renders the same result.

**Rationale:** A schema-valid record cannot establish that a quote exists. Contextual checks validate supplied context, never open files or inspect aimx state. Annotation meaning remains a human review concern.

**Alternatives considered:** A single boolean hides unavailable verification. Automatic quote location or whitespace normalization conflicts with FR-010, even though the older architecture §5.3 mentioned normalization.

## 4. Proposal alignment

**Decision:** Use a proposal envelope containing `experiment_contract` with the pinned aimx field names and populated types. Permit null only for explicitly listed execution decisions. Keep baseline and qualitative cost in `experiment_contract.extensions.aimx_recipes`. Always identify the artifact as requiring Lead review; do not expose an execution-ready verdict.

**Rationale:** Local aimx HEAD `1b2dd98b6621aa893c056013cd0dd06fff7ca405` matches the specification pin. Inspection of `specs/007-research-state/contracts/research-update.schema.json` and `src/aimx/research/validation.py` found runtime requirements beyond schema shape. These include artifact resolution, scope history, resource attestations, and independent-confirmation rules. This library cannot certify them.

**Alternatives considered:** Passing the architecture's proposal directly to aimx fails: incomplete evaluation/data, absent failure policy, and qualitative `planned` resource values. Importing aimx would add unrelated dependencies and state coupling. Copying an entire upstream schema is unnecessary; record the narrow compatibility surface in [proposal.md](contracts/proposal.md).

## 5. Vocabulary, conditions, and uncertainty

**Decision:** Enumerate the initial vocabulary in [vocabulary.md](contracts/vocabulary.md), using measured nonnegative resource/size values rather than arbitrary buckets. Use explicitly typed equality, membership, numeric bound, presence and absence conditions. Only validate condition representation and supplied assessment consistency in Spec01; evaluating conditions against profiles belongs to matching.

**Rationale:** Concrete units avoid invented bucket boundaries. Shared definitions prevent profile and recipe drift. Unknown basis is represented by null, not empty string or a fabricated category. Conflicts preserve alternative assertions without resolving them.

**Alternatives considered:** Free-form synonyms make deterministic matching impossible. A general expression language or an early matching engine would expand scope. Broad taxonomies without P0 examples would be hard to annotate consistently.

## 6. Packaging and testing

**Decision:** Support Python >=3.12, develop on 3.12 and verify 3.13. Use uv, Hatchling, pytest, a src layout, and a committed lockfile. Runtime dependencies: `jsonschema>=4.26,<5` and `referencing>=0.37,<0.38`; development: `pytest>=8,<10`; build: `hatchling>=1.27,<2`. Resolve exact transitive versions in implementation and commit `uv.lock`. Include root `schemas/` in the wheel at `aimx_recipes/_schemas/` and load via `importlib.resources`.

**Rationale:** This repository has no package or tests yet. The sibling aimx uses Hatchling and pytest, but its Aim-specific Python upper bound does not apply here. Worker probes on Python 3.13.13 with jsonschema 4.26.0 and referencing 0.37.0 verified the selected mechanisms. An installed-wheel test outside the checkout proves packaged resources are complete.

**Alternatives considered:** No YAML parser, database, Arrow, Aim SDK, model client, service framework, or CLI dependency is needed for this spec. Supporting older Python adds an unrequested compatibility matrix.

## 7. Versions and release policy

**Decision:** Initial schema/vocabulary/taxonomy versions are `1.0.0`, independently identified but released together initially. Use exact supported-version dispatch; no automatic migration. Publish a release manifest recording compatibility and `extraction_regeneration` (`required`, `not_required`, `not_applicable`) plus rationale. The initial release is `not_applicable` because no frozen extraction exists.

**Rationale:** Versions describe interpretation, not just file format. Adding an optional field is backward-compatible for new readers but old strict readers may reject new records; exact dispatch makes this explicit.

**Alternatives considered:** Accepting any version with a compatible major number could silently change evidence meaning. Automatically regenerating extraction would violate the evaluation gate.

## Research closure

All technical unknowns are resolved by the decisions above and companion contracts. The source repository remains design-only. The quickstart specifies future implementation acceptance commands, not commands claimed to pass today. No external source text or third-party taxonomy was copied. No constitution exception is needed.
