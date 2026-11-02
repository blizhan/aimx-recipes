# Feature Specification: Core Schemas & Facet Vocabulary

**Feature Branch**: `main` (existing branch; no branch-creation hook configured)

**Created**: 2026-11-02

**Status**: Draft — validated for planning

**Input**: User description: "@ROADMAP.md 规划spec01， 使用subagent worker收集信息"

This specification establishes the shared meaning and validation contracts for roadmap item 001. Research curators, benchmark authors, and the aimx Lead need to exchange problem descriptions, reusable actions, and source-backed observations without losing uncertainty or turning external experience into local findings.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Describe a problem and recipe consistently (Priority: P1)

A benchmark author describes a tabular or tabularized time-series problem. A curator describes a reusable action using the same vocabulary, so both can identify applicable conditions and hard incompatibilities without interpreting free-form synonyms.

**Why this priority**: Every downstream comparison depends on shared meanings and honest treatment of missing information.

**Independent Test**: Validate independently authored profiles and recipes against the published vocabulary, including incomplete profiles and invalid values.

**Acceptance Scenarios**:

1. **Given** a forecasting profile and a recipe condition both using `rolling_origin` validation, **When** each is validated, **Then** both accept that value with the same definition.
2. **Given** an unknown temporal facet, an inferred symptom, and two conflicting source reports, **When** the profile is validated, **Then** the unknown stays empty, the inference retains its basis, and both conflicting reports remain available.
3. **Given** an undeclared facet, unsupported value, or invalid action category, **When** a record is validated, **Then** it is rejected with the offending field and reason; no synonym is silently substituted.
4. **Given** a recipe with a future-data prohibition and a profile with unknown future-covariate availability, **When** their condition records are validated, **Then** they can represent an unknown assessment without declaring compatibility; an explicit violation is representable separately from relevance.

---

### User Story 2 - Preserve the evidence behind an observation (Priority: P1)

An annotator records an intervention and its source excerpt, including negative results and missing measurements, so reviewers can distinguish actual comparisons from adoption or opinion.

**Why this priority**: Traceability and evidence strength determine whether external experience is useful or misleading.

**Independent Test**: Validate a linked Source, Document, Problem, Attempt, and Evidence example with its reference text, then introduce broken references and altered quotes.

**Acceptance Scenarios**:

1. **Given** a quoted controlled comparison with a negative outcome, **When** it is validated, **Then** it remains a `controlled_ablation` with `negative` outcome.
2. **Given** a source that only says a technique was used, **When** an annotator records it, **Then** a `used_in_solution` record with `unclear` outcome and absent measurements is valid without fabricating a gain.
3. **Given** an intervention with no canonical recipe mapping, **When** its evidence is otherwise valid, **Then** a null recipe reference is accepted and its original method name is preserved.
4. **Given** an altered quote, invalid span, missing reference, numeric result without evaluation scope, or missing extracted-record provenance, **When** contextual validation runs, **Then** it reports the specific failure without repairing the record.
5. **Given** multiple simultaneous interventions or a claimed controlled comparison, **When** the observation is submitted, **Then** joint changes and confounders are explicitly represented, and a controlled-ablation claim requires a quoted comparison.
6. **Given** a 500-character excerpt and an otherwise equivalent 501-character excerpt, **When** each is validated, **Then** the former passes the length rule and the latter fails without truncation.

---

### User Story 3 - Review a proposal without inventing an executable experiment (Priority: P2)

The aimx Lead receives a candidate experiment with its hypothesis, source evidence, applicability, and risks, and can see which local execution decisions still need to be supplied.

**Why this priority**: Proposals must be useful to the Lead while respecting ownership of local research decisions.

**Independent Test**: Validate a proposal referring to a profile, recipe, and evidence, first without local execution details and then with caller-supplied values.

**Acceptance Scenarios**:

1. **Given** no caller-supplied baseline, threshold, evaluation protocol, or data scope, **When** a proposal is validated, **Then** those fields remain null and the artifact is identified as a proposal requiring Lead completion.
2. **Given** supplied execution details, **When** the proposal is validated, **Then** supplied values retain their meaning and use the corresponding aimx contract types; a qualitative cost such as `low` is not accepted as a numeric resource budget.
3. **Given** match metadata with unknown conditions and supporting evidence, **When** the Lead inspects the proposal, **Then** match level, transfer risk, satisfied/unknown/violated facets, and evidence references are distinguishable. A violated hard constraint cannot be labelled satisfied.
4. **Given** a valid proposal, **When** validation completes, **Then** no experiment is admitted or executed and no aimx or Aim state is changed.

---

### User Story 4 - Recognize compatible and incompatible records (Priority: P2)

A data maintainer checks whether records and vocabulary belong to a supported contract version before using them in a later extraction, benchmark, or retrieval workflow.

**Why this priority**: Silent interpretation changes would make frozen evidence and evaluations unreliable.

**Independent Test**: Validate versioned examples of every entity and inspect an example release declaration describing compatibility and regeneration impact.

**Acceptance Scenarios**:

1. **Given** one valid example and one invalid example for each of the eight entities, **When** validation runs, **Then** every example receives its documented verdict and invalid examples identify their failing fields.
2. **Given** an absent or unsupported version, **When** a record is validated, **Then** it is rejected explicitly rather than interpreted as the current version.
3. **Given** a schema or vocabulary change, **When** a new contract version is published, **Then** its compatibility classification, affected records, and frozen-extraction regeneration decision are documented.
4. **Given** the same records and reference context, **When** validation is repeated offline, **Then** verdicts and diagnostic ordering are identical and inputs remain unchanged.

### Edge Cases

- Missing optional facets are unknown, not false or implicitly satisfied. An explicit `unknown` facet cannot also assert a known value.
- Conflicting observations remain distinct even if they share a value; conflicting values must not be resolved by overwriting the less convenient source.
- A quote repeated within a document is valid only when its supplied span identifies a matching occurrence. Unicode characters and line breaks must not shift span interpretation.
- Reference text unavailable to a consumer permits structural checks only; the result must say quote verification is incomplete, never claim full validation.
- A source with unknown or restrictive license status can be described for local review; structural validity is not permission to publish it.
- Mirrors retain a single Source identity. Source deduplication itself belongs to spec 002.
- Negative and zero measurements are valid where the metric permits them; missing measurements are not zero. Non-finite numbers are invalid.
- Public and private leaderboard measurements are separate observations/scopes. Raw deltas from different problems or metrics are not comparable aggregate facts.
- Unknown action categories and vocabulary versions fail explicitly. A schema cannot silently expand the vocabulary from source text.
- Unsupported modalities may be represented as transfer-boundary cases without implying P0 retrieval support.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 — Entity contracts**: Provide versioned, documented validation contracts for Source, Document, Problem, Problem Profile, Recipe, Attempt, Evidence, and Experiment Proposal. Each defines identity, required/optional/nullable values, allowed values, and relationships. Provide valid and invalid examples for each entity.
- **FR-002 — Validation results**: Support record-level structural validation and contextual validation of linked records. Human-readable diagnostics and JSON results must agree on validity and identify entity/record, field location, stable reason, and incomplete contextual checks. Full validity must not be reported when required reference checks were unavailable. Validation must be deterministic, offline, and non-mutating.
- **FR-003 — Source and document identity**: Sources must record original-artifact identity, kind, canonical identifier or URL, license status, snapshot identity, and content fingerprint. Documents must identify their Source and normalized content version. Contextual validation must reject missing or inconsistent references. Full document text is local verification material, not part of released evidence records.
- **FR-004 — Shared vocabulary**: Profiles and recipe applicability, preconditions, and hard constraints must use one versioned vocabulary with definitions, allowed values or value types, and cardinality. The initial vocabulary must cover task, target, modality, dataset characteristics, temporal conditions, validation, metric, problem characteristics, symptoms, compute, and prior attempts. It must express tabular regression/classification and tabularized forecasting, including grouped and temporal validation, future-known covariates, leakage restrictions, and resource limits. License/deployment restrictions must also be representable as hard conditions. Unsupported names or values must fail explicitly.
- **FR-005 — Uncertainty**: Every present facet must carry `basis` from `observed`, `reported`, `inferred`, `unknown`. Optional source, confidence, and conflicts must have documented meanings. An unknown facet has an empty value. Confidence, when supplied, is `low`, `medium`, or `high`; absence means unassessed. Each conflicting assertion retains its value, basis, and available source. Validation must not strengthen an inference or resolve conflicts automatically.
- **FR-006 — Recipe conditions**: Recipes must distinguish applicability, required preconditions, hard constraints, contraindications, and qualitative cost. Conditions must identify the shared facet, comparison, and permitted operand type; equality, membership, numeric bounds, and presence/absence must be expressible without executable expressions. Assessment states are `satisfied`, `violated`, and `unknown`; unknown information cannot establish satisfaction. This feature defines these contracts, not the matching engine.
- **FR-007 — Action taxonomy**: Publish an independently authored, documented hierarchy for `action_type` covering data preparation, feature engineering, model choice, training, validation, ensembling, and prediction post-processing. Initial named examples must include encoding, lag features, split selection, and stacking. Recipes must reference declared categories; taxonomy changes follow the same version policy as vocabulary changes.
- **FR-008 — Attempts**: Attempts must identify their Problem, Document, raw intervention name, optional canonical Recipe, baseline/candidate descriptions, available measurements, metric and direction, outcome, joint changes, confounders, and provenance. Unmapped recipes use null. Missing measurements remain absent/null; any numeric measurement requires metric identity, direction, and evaluation scope from `cv`, `public_lb`, `private_lb`, `holdout`. Separate scopes must not be collapsed into one unlabeled comparison.
- **FR-009 — Typed evidence**: Evidence must link an Attempt to a Document and, through it, a Source. Types are `controlled_ablation`, `reported_gain`, `reported_failure`, `used_in_solution`, `attempted`, `author_opinion`, and `independently_reproduced`. Outcomes for Attempts and Evidence are `positive`, `negative`, `neutral`, `mixed`, and `unclear`. Type and outcome are independent; adoption must not imply effectiveness. A controlled-ablation annotation must include an explicit source comparison; joint interventions must retain their joint-change declaration and confounders. Semantic evidence judgments remain reviewable annotations, not claims that structural validation can understand source meaning.
- **FR-010 — Verbatim evidence**: Every Attempt must have at least one Evidence record in a fully validated bundle. Every Evidence quote must be a nonempty exact span of the identified document content, with zero-based start-inclusive/end-exclusive positions counted in Unicode code points. Quotes are limited to 500 code points each. Contextual validation must reject mismatched spans, altered quotes, and excess length without rewriting or truncation. Quote limits do not waive source-license or no-full-text-release restrictions.
- **FR-011 — Provenance**: Extracted records must distinguish provider, requested model or gateway group, served model, prompt version and hash, schema version, extractor version, extraction time, and source content fingerprint. Human-authored fixtures and annotations must identify their origin without inventing model provenance. Served-model provenance must not be confused with the requested model/group used to identify an extraction request.
- **FR-012 — No authored aggregate facts**: Recipe contracts must not accept adoption/support/counterevidence totals as authoritative authored evidence. Repeated use is not independent replication, and cross-problem metric deltas must not be stored as a single aggregate effectiveness claim. Deriving aggregates belongs to later workflows.
- **FR-013 — Match metadata**: Define match levels `L1` (task, data, validation, symptoms, resources), `L2` (task and data mechanism), `L3` (symptoms across tasks), and `L4` (general reference). Define transfer risk as `low`, `medium`, `high`, or `unknown`, where unknown means insufficient information, not low risk. Proposal applicability metadata must identify satisfied, unknown, and violated facets, and distinguish hard violations from other mismatches. Scoring and thresholds are out of scope.
- **FR-014 — Proposal boundary**: An Experiment Proposal must identify its profile, recipe, question/intervention, fixed controls, expected evidence, disconfirmation, confounders, source evidence, and match metadata. It must preserve aimx `experiment_contract` names and populated value types for corresponding fields, including contract version, evaluation, data, resources, and failure policy. Unknown project-specific baseline, acceptance threshold, evaluation protocol, data scope, and numeric budgets must remain null unless supplied. Qualitative recipe costs are separate proposal metadata, not execution budgets. Proposal validation must explicitly distinguish an incomplete suggestion from admission as an executable aimx contract; the latter remains the Lead's responsibility.
- **FR-015 — Version policy**: Every contract-bearing record must declare its schema version, and its applicable vocabulary/taxonomy version must be identifiable. Use semantic versions: incompatible shape/meaning changes require a major bump, backward-compatible additions a minor bump, and contract-documentation corrections a patch bump. Every schema change requires a version bump and an explicit regeneration decision with rationale. Unrecognized versions are rejected, never silently migrated. A new version does not itself authorize regenerating frozen evidence.
- **FR-016 — Scope and source boundaries**: Deliver definitions, validators, fixtures, and contract documentation only. Validation must not write external state, call a model, access the network, ingest data, build an index, or generate/execute experiments. Fixtures must use project-authored synthetic text; third-party taxonomies or source bodies are not bundled. The documentation must explain human-readable and JSON validation results, local-only source text, and source-license metadata. Runtime commands, storage layout, extraction prompts, catalog seeding, retrieval algorithms, and proposal attachment workflows belong to later specs.

### Key Entities *(include if feature involves data)*

| Entity | Meaning and relationships |
| --- | --- |
| Source | One original artifact identity with provenance and license status; may have several Documents and mirrors. |
| Document | A normalized text unit/version belonging to a Source; provides the coordinate system for evidence spans. |
| Problem | A competition, benchmark case, or caller research task, identified independently of any proposed intervention. |
| Problem Profile | A versioned description of a Problem through shared facets, uncertainties, and constraints. |
| Recipe | A reusable action with stable identity, aliases, action category, applicability, preconditions, hard constraints, risks, and cost; observed support comes from linked records. |
| Attempt | One reported intervention on a Problem, linked to its source Document and optionally a canonical Recipe; supported by one or more Evidence records. |
| Evidence | A typed observation with a separate outcome, verbatim document span, uncertainty, and provenance, supporting an Attempt. |
| Experiment Proposal | A candidate experiment grounded in a Profile, Recipe, and evidence, carrying match information and explicitly incomplete local execution details for the Lead. |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can accept one valid example and reject one invalid example for each of the eight entities with 100% agreement between documented expectations and validation results; every rejection identifies its location and reason.
- **SC-002**: In acceptance examples covering missing, inferred, and conflicting conditions, 100% preserve the original uncertainty, and no unknown or violated hard condition is presented as satisfied.
- **SC-003**: All fully validated evidence examples trace to an original source and exact excerpt. Every acceptance example with a damaged quote, broken reference, oversized quote, or unscoped numeric result is rejected; missing verification context is always reported as incomplete.
- **SC-004**: Reviewers can distinguish comparison strength from outcome in all seven evidence-type examples, including a negative controlled ablation and adoption without a measured gain.
- **SC-005**: Every proposal acceptance example identifies supporting evidence and missing local execution decisions. Zero examples invent execution details or present an incomplete proposal as execution-ready.
- **SC-006**: Identical inputs and context produce identical validation results in three consecutive offline runs, with no input or external-state changes.
- **SC-007**: Every version-change example states compatibility and regeneration impact, and every unsupported-version example fails explicitly. A curator can identify the applicable rules from the published contract without consulting implementation code.

## Assumptions

- Authority is [ROADMAP item 001](../../ROADMAP.md), governed by C-08 and C-10, and constitution version 1.0.1. The [architecture](../../ARCHITECTURE.md), [evaluation protocol](../../docs/EVALUATION.md), and [source register](../../docs/DATA_SOURCES.md) supply domain context. Later-spec source-selection and model-routing decisions do not expand this feature.
- Primary users are research curators, benchmark authors, and the aimx Lead. English is the repository documentation language. This work creates the specification; the subsequent implementation plan selects field layouts and validation mechanisms consistent with these requirements.
- The 500-code-point quote cap, three-level confidence vocabulary, explicit unknown transfer risk, and schema semantic-version policy are defaults adopted by this specification, not claims about already implemented behavior. The quote cap is an evidence-minimization rule, not legal permission; future changes must be versioned.
- The initial vocabulary is intentionally small: only distinctions required to describe the acceptance scenarios and P0 tabular/temporal problems are included. Exact entries and numeric bucket boundaries must be enumerated with definitions during contract design, rather than inferred by consumers. Expansion requires a concrete annotation or benchmark need.
- `preconditions` is the canonical term for the required conditions called `requires` in parts of the roadmap. Unmapped recipe references use null; missing optional metadata means unavailable, never a fabricated value.
- The Proposal is a separate, nullable artifact. The locally inspected aimx contract at revision `1b2dd98b6621aa893c056013cd0dd06fff7ca405` is the alignment reference; its executable contract requires more information than the architecture's illustrative proposal supplies. Planning must pin and verify that reference, including evaluation, resource types, and failure policy. No aimx runtime dependency or state mutation is required for this feature.
- Structural validation can verify shape, references, and exact spans when context is available. Whether a quote truly supports an ablation or independent reproduction remains an annotation/review decision; examples must demonstrate the distinction.
- No previous spec is required. Specs 002–007 consume these definitions but their ingestion, benchmark, catalog, extraction, matching, and proposal-generation workflows are not acceptance prerequisites for Spec01.
