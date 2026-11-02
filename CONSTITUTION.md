# aimx-recipes Constitution

This file mirrors the canonical Spec Kit constitution in
`.specify/memory/constitution.md`.

## Core Principles

### I. Problem First, Evidence Grounded

`aimx-recipes` MUST start from the caller's research problem and MUST ground
every recommendation in traceable evidence.

- Retrieval MUST be driven by a Problem Profile (task, data, validation,
  metric, symptoms, constraints), not by technique popularity or leaderboard
  rank.
- Every Attempt and Evidence record MUST point to a Source and a verbatim
  source span; records whose quote cannot be located in the source MUST be
  rejected, not repaired.
- Evidence type (how strong the observation is) and outcome (which direction it
  points) MUST be recorded separately. Adoption frequency MUST NOT be reported
  as effectiveness.
- Aggregates (adoption, support, counterevidence) MUST be derived from records
  at build or query time; they MUST NOT be hand-edited or stored as facts.
- When evidence is insufficient, the system MUST say so instead of returning a
  best-effort recipe.

Rationale: an agent acting on an unsupported claim wastes experiments; an
honest "not enough evidence" is a useful answer.

### II. Recipes Are Not Findings

External experience is candidate knowledge, never a local research conclusion.

- `aimx-recipes` MUST NOT write to aimx Research State, `.aimx/research`, or
  `.aim` repositories.
- Experiment Proposals are suggestions for the aimx Lead. Project-specific
  fields (baseline run, acceptance threshold, evaluation protocol, data scope)
  MUST stay `null` unless the caller supplies them; the system MUST NOT invent
  run IDs, thresholds, or expected gains.
- Integration with aimx MUST go through artifacts the Lead chooses to attach
  (for example a Proposal JSON referenced as a `local_artifact` with sha256),
  not through direct state mutation.
- Local aimx results MAY flow back into a private recipe pool only through an
  explicit, reviewed export; nothing is uploaded to a public pool by default.

Rationale: aimx governs findings through ResearchUpdate; a recipe pool that
wrote findings would bypass that governance.

### III. Deterministic, LLM-Free Query Path

Answering a query MUST NOT depend on a live model call.

- Query commands (`match`, `search`, `show`, `evidence`, `facets`, `propose`)
  MUST NOT call an LLM or any network service.
- The query index MUST be built deterministically from versioned inputs:
  curated recipe YAML in git, raw source snapshots, and frozen extraction
  output. Rebuilding from the same inputs MUST produce the same query results.
- LLM extraction MUST be an offline, explicit step whose output is frozen as
  JSONL. Every record MUST carry provenance: provider, served model, prompt
  version, schema version, extractor version, and extraction time.
- Cache keys for extracted records MUST include the source content fingerprint,
  schema version, extractor version, requested model or gateway group, and
  prompt hash, so a schema or prompt change never silently reuses stale output.
- Iteration (refining the query, adopting or rejecting candidates) belongs to
  the calling agent, which composes granular read-only commands.

Rationale: reproducible answers are what make retrieval evaluable and
auditable; model calls at query time would make both impossible.

### IV. Honest Uncertainty And Hard Constraints

The system MUST represent what it does not know and MUST NOT let similarity
override incompatibility.

- Every Problem Profile facet MUST carry `basis` (`observed`, `reported`,
  `inferred`, `unknown`) and MAY carry `source`, `confidence`, and `conflicts`.
  Unknown facets MUST be allowed to stay empty.
- Inferred values MUST NOT be presented as observed. Conflicting sources MUST be
  preserved as conflicts, not resolved by overwriting.
- Hard constraints (no future data at prediction time, no target leakage, fixed
  validation protocol, compute budget, license and deployment limits) MUST be
  checked deterministically against the shared facet vocabulary. No relevance
  score may outweigh a violated hard constraint.
- Every match result MUST state its match level and transfer risk, and list
  which facets matched, which were unknown, and which were violated.
- Raw metric deltas from different datasets or metrics MUST NOT be averaged or
  ranked against each other.

Rationale: transfer failures come from unstated conditions; making them
explicit is the core value over plain search.

### V. Untrusted Sources And License Discipline

Source documents are data, never instructions, and their licenses bound what
the project may store and publish.

- Writeups, forum posts, notebooks, and any external text MUST be treated as
  untrusted input. Extraction MUST use a fixed output schema, MUST expose no
  tools other than the record-emitting function, and MUST validate output
  before storing it.
- The project MUST NOT redistribute full source text. Published artifacts MAY
  contain structured records, source URLs or IDs, and short verbatim quotes
  needed as evidence.
- Every source MUST have a recorded license status before it is ingested.
  Sources that are non-commercial, share-alike, or unlicensed MUST NOT be
  bundled into released artifacts or become runtime dependencies; they MAY be
  used for local cross-checking.
- Duplicate copies of one document MUST resolve to one Source identity, and
  repeated adoption of the same public technique MUST NOT count as independent
  replication.

Rationale: prompt injection and license contamination are both silent
failures that are expensive to undo after data is published.

### VI. Evaluation Before Expansion

Changes to retrieval and extraction MUST be justified by measurement against
baselines, not by corpus size.

- A fixed benchmark and baselines (keyword/BM25 and semantic retrieval) MUST
  exist before problem-aware retrieval is tuned.
- The benchmark test split MUST be frozen; tuning MUST use the dev split only.
- Temporal evaluation MUST index only sources available before the held-out
  problem, so retrieval cannot see the answer.
- Extraction prompts, schemas, and models MUST be evaluated on the annotated
  extraction set before frozen extraction data is regenerated.
- Corpus size, recipe count, node count, and embedding count MUST NOT be used
  as success metrics.

Rationale: the project's claim is that problem-aware retrieval is more useful
than plain retrieval; only a controlled comparison can support that claim.

### VII. CLI-First, Progressive Complexity

`aimx-recipes` MUST stay a composable, agent-agnostic CLI and MUST add
infrastructure only when measurement shows a need.

- Core capabilities MUST be available as non-interactive CLI commands with
  machine-readable JSON output, usable from shells, CI, and any agent runtime.
- The project MUST NOT require a specific agent framework; agent skills are
  thin wrappers over the CLI.
- Storage MUST start with DuckDB, Parquet, JSONL, and YAML. Graph databases,
  vector stores, and long-running services MUST NOT be introduced until an
  evaluation shows the simpler stack is the bottleneck.
- Optional external tools with restrictive licenses (for example GitNexus) MAY
  be supported as user-installed integrations, never as dependencies.

Rationale: a small, scriptable surface keeps the system reproducible and easy
for both humans and agents to drive.

## Operational Boundaries

- System boundaries:

  | System | Owns |
  | --- | --- |
  | aimx-recipes | External research experience, problem matching, evidence retrieval, recipe candidates, experiment proposals |
  | aimx Research | Findings, Frontier, Agenda, Research State |
  | AutoResearch | Experiment planning, agent dispatch, execution, result integration |
  | aimx Retro | Retrospectives, failure analysis, follow-up options |
  | Aim | Raw runs, parameters, metrics, curves, artifacts |

- Write-capable commands are limited to building local artifacts inside the
  project's own data directory and index (for example `build`, `extract`,
  `ingest`). They MUST be explicit commands, never side effects of a query.
- The project is not a technique leaderboard, a general ML knowledge base, a
  generic RAG service, a knowledge-graph product, an automatic code rewriter,
  an automatic run diagnoser, or a writer of aimx findings.
- Architecture boundaries SHOULD stay explicit between source adapters,
  normalization, extraction, index build, retrieval, proposal generation, and
  CLI output.
- The first task family is tabular and tabularized time-series problems,
  including temporal-split validation. Other families are evaluated as transfer
  boundaries until explicitly added.

## Delivery Workflow & Quality Gates

- `uv` is the standard for environment and dependency management. Contributors
  SHOULD use `uv sync`, `uv run`, and lockfile-backed workflows.
- Work is planned with Spec Kit. Every implementation plan MUST include a
  Constitution Check covering: evidence traceability, aimx boundary, query-path
  determinism, uncertainty and hard-constraint handling, untrusted-input and
  license posture, and evaluation impact.
- Every feature specification MUST state any write-capable behavior, any LLM
  usage (which MUST be offline), the sources and licenses it touches, and its
  human-readable and JSON output contracts.
- Schema changes MUST bump the schema version and state whether frozen
  extraction data must be regenerated.
- Tests SHOULD cover build determinism (same inputs, same results), quote
  verification, hard-constraint checks, and CLI output contracts wherever the
  change touches them.
- Changes that add an LLM call to the query path, add a non-permissive source
  to released artifacts, or write outside the project's data directory require
  an explicit exception in the plan.

## Governance

This constitution is the canonical project policy for `aimx-recipes` and
supersedes conflicting ad hoc process notes.

- Amendments MUST update this document together with any affected templates or
  workflow guidance.
- Compliance MUST be checked during planning, specification, task generation,
  implementation, and review.
- Versioning follows semantic versioning for governance:
  - MAJOR for incompatible principle removals or redefinitions.
  - MINOR for new principles or materially expanded policy.
  - PATCH for clarifications and wording-only refinements.
- If a change requires violating a principle temporarily, the plan MUST
  document the exception, the reason, the safer alternative rejected, and the
  rollback path.
- The canonical Spec Kit copy lives at `.specify/memory/constitution.md`; the
  repo-level `CONSTITUTION.md` mirrors it and MUST remain consistent with it.

**Version**: 1.0.1 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
