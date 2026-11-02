<!--
SYNC IMPACT REPORT
==================
Version change: 2.0.0 → 2.0.1
Bump rationale: PATCH — lifecycle status and terminology clarification only;
no vision, constraint meaning, spec scope, dependency, or open question changed.

Changes this revision (2026-11-02; user-confirmed after the 001 debrief):
  - 001: planned → verified; link the spec, current acceptance record, and debrief
  - Record contract 2.0.0 and the observed Python 3.12/3.13 results (108 passed each)
  - C-10: use applicability / preconditions / hard_constraints; retain requires
    as historical terminology, not an accepted contract alias

Specs affected: 001 (status and verification evidence); C-10 wording clarified
Open questions added/resolved: none
Follow-up: retain 012 as needs-info and 014 as undecided; existing open questions
remain assigned to their recorded downstream specs.

Previous revision (retained for history):
Version change: 1.1.0 → 2.0.0
Bump rationale: MAJOR — reverses decision C-07 (pinned extraction model
group), which invalidates the outcome and scope of spec 005; superseded by
C-15.

Changes this revision:
  - Decision superseded: C-07 (pinned, order-routed model group) → C-15
    (magpie `group/worker`, gateway does the routing; resolves Q1)
  - C-06 cache key clarified: keyed on the requested model/group, not the
    served model
  - Scope changed on 005: no model selection step; the gold-set report is
    broken down by served model
  - Notes on 003: pre-labelling uses a model outside the worker group

Specs affected: 003 (notes), 005 (outcome, scope)
Open questions added/resolved: resolved Q1

Notes: 1.1.0 (2026-11-02) added C-13 and C-14 (resolved Q3, Q6).
1.0.0 (2026-11-02) created specs 001–014, decisions C-01 … C-12, and
open questions Q1 … Q8 from the v0.2 design draft and the design discussion.
That revision superseded the draft's on-demand extraction over a third-party
815-doc corpus with full batch extraction of the P0 subset from Meta Kaggle
(C-04, C-06).
-->

# aimx-recipes — Spec Roadmap

Living, non-binding map of the specs planned for aimx-recipes. It is **not a
commitment to order or scope** — it captures the spec-specific discussion,
decisions, technology choices, outcomes, and constraints surfaced during the
constitution and design phases so they are not lost before the spec that needs
them is written. Specs are scoped and clarified when they are actually started.
Foundations: the project [constitution](CONSTITUTION.md), the
[architecture](ARCHITECTURE.md), the [evaluation protocol](docs/EVALUATION.md),
and the [data source register](docs/DATA_SOURCES.md).

Status legend (lifecycle): **undecided** · **needs-info** · **planned** ·
**specced** · **in-progress** · **implemented** · **verified** · **deferred** ·
**abandoned**.

---

## Vision & End States

- An agent holding a Problem Profile can call a read-only CLI and get recipe
  candidates that say **why** they apply: matched / unknown / violated facets,
  match level, transfer risk, and the evidence behind each candidate.
- Every recipe claim traces to a verbatim source span with a typed evidence
  record (type, outcome, evaluation scope), and absent evidence is reported as
  absent.
- A chosen candidate becomes an Experiment Proposal that the aimx Lead can
  attach to an Agenda item without any change to aimx.
- On a frozen benchmark, problem-aware retrieval is compared against BM25 and
  semantic baselines on applicability precision and constraint violations; the
  P0 result decides whether to expand.
- Long term: results validated locally in aimx flow back, through an explicit
  export, into a private recipe pool that improves future ranking.

## Constraints & Decisions

- **C-01 — Three storage layers:** curated recipe YAML (plus schemas and facet
  vocabulary) in git is the single authority; `data/` (gitignored) holds raw
  Parquet snapshots and frozen extraction JSONL, released as versioned
  artifacts; `data/index.duckdb` is rebuilt deterministically by
  `aimx-recipes build` and is the only thing query commands read. Keeps review
  in git and makes the index disposable.
- **C-02 — LLM-free query path:** query commands never call a model or the
  network. The calling agent iterates over granular results (re-query,
  inspect evidence, adopt or reject). Mirrors how GitNexus-style code queries
  work; makes retrieval evaluable.
- **C-03 — P0 task family:** tabular and tabularized time-series problems,
  including temporal-split validation. Other modalities are transfer-boundary
  cases in evaluation only.
- **C-04 — Corpus backbone is Meta Kaggle:** official Meta Kaggle CSVs
  (apache-2.0) resolve writeups via `Teams.WriteUpForumTopicId` →
  `ForumTopics.FirstForumMessageId` → `ForumMessages`. Spike on the
  2026-11-01 snapshot: 6,276/6,276 writeups resolve, 6,211 have more than 200
  characters, new-style 2024+ writeups included, no scraping needed.
  Third-party corpora (HF writeups, Kaggle Chronicles, First Place Solutions)
  are cross-checks only. See [DATA_SOURCES](docs/DATA_SOURCES.md).
- **C-05 — No full-text redistribution:** released artifacts contain
  structured records, source IDs/URLs, and short verbatim quotes only.
  Non-commercial, share-alike, or unlicensed sources (Kaggle Knowledge Graph
  CC BY-NC-SA, GitNexus PolyForm Noncommercial, First Place Solutions and the
  HF writeups dataset without a license) are never bundled or depended on.
- **C-06 — Extraction is an offline batch pipeline, not an agent loop:** one
  call per document with its competition context, against an OpenAI-compatible
  chat-completions endpoint (locally the magpie gateway, worker-tier models).
  Structured output via a **forced tool call with a strict JSON-Schema
  function**, then local validation: schema, verbatim-quote location with
  offsets computed in code, facet values in vocabulary, `recipe_id` in catalog
  or `unmapped`. Rejected records are logged, not repaired. Output is frozen
  JSONL keyed by content fingerprint + schema version + extractor version +
  requested model/group + prompt hash. (`response_format: json_schema` was ignored by
  several worker backends in a 2026-11-02 probe; forced tool calling worked on
  all six tested.)
- ~~**C-07 — Pinned extraction model:** the production extraction run targets a
  pinned, order-routed gateway group (winner + fallback) chosen on the
  annotated extraction set, not a smart-routing group that mixes models per
  request. The served model (`X-Magpie-Model` or equivalent) is recorded on
  every record and fallback-served records are flagged. Benchmark
  pre-labelling uses a different model family than extraction.~~
  _Superseded 2026-11-02 by C-15._
- **C-08 — Recipes Are Not Findings:** the Experiment Proposal reuses aimx
  `experiment_contract` field names, leaves project-specific fields `null`,
  and reaches aimx as a `local_artifact` evidence reference (with sha256) on a
  Lead-created Agenda item. aimx needs no code change.
- **C-09 — Evaluation first:** P0 is split into P0a (benchmark, corpus,
  baselines) and P0b (problem-aware matching, extraction, proposal). The
  benchmark is ~30 problems: Tabloom's 3 real cases plus ~27 Kaggle
  competitions under temporal leave-one-competition-out; 10 dev / 20 test,
  test frozen. See [EVALUATION](docs/EVALUATION.md).
- **C-10 — Shared facet vocabulary and typed evidence:** Problem Profile facets
  and recipe `applicability` / `preconditions` / `hard_constraints` use one
  controlled vocabulary, so constraint checks are deterministic comparisons.
  Facets carry `basis`
  (`observed` / `reported` / `inferred` / `unknown`, aligned with aimx-retro).
  Evidence type is separate from outcome; Attempt carries `evaluation_scope`
  (`cv` / `public_lb` / `private_lb` / `holdout`); aggregates are derived
  views; no generic `relations` table.
  _Clarified 2026-11-02: the former roadmap term `requires` is named
  `preconditions` in [spec 001](specs/001-core-schemas-vocabulary/spec.md#assumptions).
  `requires` is historical terminology, not an accepted contract alias._
- **C-11 — Recipe catalog is seeded, extraction maps to it:** P0 needs a
  minimal canonical catalog (target 50–150 tabular recipes) so extraction can
  map Attempts to `recipe_id` or `unmapped`; LLM-assisted canonicalization
  later only proposes YAML changes for review.
- **C-12 — Tooling:** Python + `uv`; DuckDB (FTS) + Parquet + JSONL + YAML; Spec
  Kit with pi and claude integrations and the speckit-roadmap extension; docs
  in English with `README.zh-CN.md`. No graph database or vector store until
  evaluation shows need. Spec Kit and agent integration state (`.specify/`,
  `.pi/`, `.claude/`) stays out of git; `CONSTITUTION.md` and `ROADMAP.md` are
  the tracked copies.
- **C-13 — Data release license:** Meta Kaggle is apache-2.0 and so is this
  project; released extraction artifacts are published under Apache-2.0 with
  attribution to Meta Kaggle. The no-full-text policy (C-05) still applies:
  artifacts carry structured records, IDs/URLs, and short quotes only.
  _Resolves Q3._
- **C-14 — Tabloom cases in the benchmark:** the project is non-commercial,
  which matches the Tabloom cases' non-commercial use class, so the three
  cases are part of the public benchmark. The benchmark stores
  project-authored Problem Profiles, constraints, and judgments; Tabloom's
  underlying data is not copied into this repository. _Resolves Q6._
- **C-15 — Extraction runs on magpie `group/worker`:** extraction requests
  `group/worker` and lets magpie route each request across the worker
  backends; there is no model-selection step and no pinned group. Because
  documents may be served by different backends, every record stores the
  served model (`X-Magpie-Model`, else the response `model` field), and the
  gold-set evaluation reports quality per served model. A backend that
  underperforms is removed from the worker group in magpie's config, and the
  records it served are re-extracted. Benchmark pre-labelling uses a model
  outside the worker group. _Supersedes C-07; resolves Q1._

## Planned Specs

### P0a — Evaluation-first foundation

### 001 — Core schemas & facet vocabulary  [status: verified]

- **Description:** JSON Schemas and Python models for Source, Document,
  Problem, Problem Profile, Recipe, Attempt, Evidence, and Experiment Proposal,
  plus the controlled facet vocabulary and the `action_type` taxonomy.
- **Outcome:** versioned schemas in `schemas/` with validators and fixtures;
  a facet vocabulary file that Problem Profiles and recipe constraints both
  validate against; a documented `schema_version` policy.
- **Scope (in):** entity schemas; facet value/basis/source/confidence/conflicts
  shape; evidence type and outcome enums; `evaluation_scope`; match level and
  transfer-risk enums; Proposal schema aligned to aimx `experiment_contract`;
  initial `action_type` hierarchy (informed by First Place Solutions' stage
  and canonical fields, authored independently).
- **Scope (out):** storage layout, CLI, extraction prompts.
- **Depends on:** none
- **Governed by:** C-08, C-10
- **Notes:** the vocabulary must be small enough to annotate consistently;
  extend it through benchmark failures, not up front.
- **Spec dir:** [001-core-schemas-vocabulary](specs/001-core-schemas-vocabulary/)
- **Verification:** restatused from `planned` to `verified` on 2026-11-02
  following the [post-implementation debrief](specs/001-core-schemas-vocabulary/roadmap-reviews/debrief-20261102T090856167307279Z.md):
  outcome met, no Must-Address findings. Contract resources and validation
  envelopes are version 2.0.0; Python 3.12.3 and 3.13.13 each passed all 108
  tests, including offline validation, wheel isolation, and cross-process
  determinism. See [Checkpoint 6](specs/001-core-schemas-vocabulary/checklists/implementation-validation.md#checkpoint-6-completion-review-corrections--contract-200).
  Verification concerns the current local implementation, not a published
  release. The [release declaration](schemas/2.0.0/release.json) records the
  breaking correction of the unreleased 1.0.0 draft and the explicit
  extraction-regeneration decision; no migration or regeneration is performed.

### 002 — Meta Kaggle source adapter & corpus normalization  [status: planned]

- **Description:** ingest the P0 subset of Meta Kaggle into hashed Parquet
  snapshots and normalize it into Source / Document / competition-context
  records.
- **Outcome:** `aimx-recipes ingest kaggle` produces `data/raw/` Parquet with
  sha256 manifests and a normalized document table (writeup text, competition
  overview, evaluation description, dataset description, dates, metric,
  medal/rank) that the index build and the extractor consume.
- **Scope (in):** writeup resolution path; competition metadata join; P0
  subset selection rule; Source identity and de-duplication; snapshot
  manifest; license field per source.
- **Scope (out):** forum threads beyond writeups (009); notebooks (012).
- **Depends on:** 001
- **Governed by:** C-04, C-05
- **Notes:** tag filter (`tabular` or `time series analysis`, excluding image /
  computer vision / text / nlp) yields 179 competitions, 1,582 writeups,
  ~7.7M characters (~1.9M tokens), but misses older untagged competitions —
  final subset rule is Q2. Median writeup length grew from ~2.7k chars (2019)
  to ~10.7k (2026). ForumMessages.csv needs a raised `max_line_size`.

### 003 — Evaluation harness & benchmark  [status: planned]

- **Description:** the frozen retrieval benchmark, the annotated extraction
  set, baseline retrievers, and the scoring harness.
- **Outcome:** `evals/` contains ~30 benchmark problems with Problem Profiles
  and graded judgments (10 dev / 20 test), a 50-document annotated extraction
  set, BM25 and semantic baselines over the same corpus, and a harness that
  reports the metrics in [EVALUATION](docs/EVALUATION.md) with as-of temporal
  filtering.
- **Scope (in):** benchmark problem selection (Tabloom 3 + ~27 Kaggle);
  profile construction from description/evaluation only; pooling from
  baselines; LLM pre-labelling + human review (~900 judgments); extraction
  gold set; metric computation; report format.
- **Scope (out):** tuning the problem-aware ranker (006).
- **Depends on:** 001, 002
- **Governed by:** C-09
- **Notes:** pre-labelling uses a model outside the magpie worker group
  (C-15). Tabloom cases enter as project-authored profiles and judgments
  (C-14); their dev/test assignment is decided here.

### P0b — Problem-aware vertical slice

### 004 — Recipe catalog seed  [status: planned]

- **Description:** the first curated catalog of canonical tabular /
  time-series recipes as YAML in git.
- **Outcome:** 50–150 reviewed recipe YAML files with action type,
  applicability, preconditions, hard constraints, contraindications,
  configuration notes, and implementation references; validated by 001.
- **Scope (in):** recipe authoring guide; catalog validation in CI; seed list
  drawn from frequent techniques in the P0 corpus.
- **Scope (out):** evidence linking (005); automated canonicalization (008).
- **Depends on:** 001
- **Governed by:** C-01, C-11
- **Notes:** granularity rule: between an abstract trick and project code
  (example: OOF target encoding). Do not merge methods just because they share
  a category.

### 005 — Evidence extraction pipeline  [status: planned]

- **Description:** offline batch extraction of Problem Profiles (per
  competition) and Attempts + Evidence (per writeup) through the
  OpenAI-compatible gateway, with deterministic validation and frozen output.
- **Outcome:** `aimx-recipes extract` writes validated, provenance-stamped
  JSONL under `data/extracted/`; a rejection log; an extraction evaluation
  report on the 50-document set run through `group/worker`, broken down by
  served model.
- **Scope (in):** context bundle assembly; forced tool-call schema; quote
  location and offsets; vocabulary and catalog checks; cache keys; retry and
  quota handling; served-model provenance; per-served-model quality
  breakdown; selective re-extraction by served model.
- **Scope (out):** query-time extraction (never); canonicalization of
  `unmapped` attempts (008).
- **Depends on:** 001, 002, 003 (gold set), 004
- **Governed by:** C-05, C-06, C-15
- **Notes:** prompt treats documents as untrusted data; no tools besides the
  record function. Evidence verification also flags joint changes reported as
  single-factor gains and CV/public/private leaderboard confusion.

### 006 — Problem-aware retrieval & query CLI  [status: planned]

- **Description:** deterministic `build` of `index.duckdb` and the read-only
  query commands.
- **Outcome:** `build`, `match`, `search`, `show`, `evidence`, `facets` with
  JSON output; hard-constraint filtering; L1–L4 matching with transfer risk;
  evidence-aware reranking; `--as-of` temporal filter; benchmark report
  comparing against the 003 baselines.
- **Scope (in):** index schema and FTS; deterministic scoring; insufficient
  evidence response; output contracts; build determinism tests.
- **Scope (out):** LLM calls of any kind; Aim context reading (010).
- **Depends on:** 001, 002, 003, 004, 005
- **Governed by:** C-01, C-02, C-10
- **Notes:** semantic retrieval enters the product path only if it beats
  BM25 + facets on the dev split (Q4).

### 007 — Experiment Proposal & `aimx-recipes` skill  [status: planned]

- **Description:** `propose` turns a recipe + Problem Profile into an
  Experiment Proposal; a minimal agent skill documents the
  match → inspect → propose loop and the aimx hand-off.
- **Outcome:** schema-valid Proposal JSON with `null` project-specific fields;
  a worked end-to-end example on a Tabloom case; skill installable with
  `npx skills`.
- **Scope (in):** proposal generation (deterministic template, no LLM);
  applicability assessment and risks from match output; aimx attachment
  instructions.
- **Scope (out):** writing to aimx; automatic Agenda creation.
- **Depends on:** 006
- **Governed by:** C-08
- **Notes:** P0 exit = 003 report + this end-to-end example.

### P1 — Coverage

### 008 — Recipe canonicalization workflow  [status: planned]

- **Description:** cluster `unmapped` attempts and propose new or merged
  recipes as reviewable YAML diffs.
- **Outcome:** an offline command that emits candidate YAML plus supporting
  attempts; merges happen only through review.
- **Scope (in):** rule-based grouping, LLM-assisted naming, review checklist.
- **Scope (out):** automatic catalog writes.
- **Depends on:** 004, 005

### 009 — Forum & failure expansion, incremental updates  [status: planned]

- **Description:** extend sources to competition forum threads and
  failure-focused posts; support incremental Meta Kaggle refreshes.
- **Outcome:** new snapshots ingest only changed sources; extraction re-runs
  only on changed fingerprints; failure evidence coverage measured.
- **Scope (in):** forum thread selection; incremental manifests; dedupe.
- **Scope (out):** notebooks.
- **Depends on:** 002, 005

### 010 — Read-only Aim context adapter  [status: planned]

- **Description:** build a draft Problem Profile from an Aim repo / run hash
  and aimx Research State, read-only.
- **Outcome:** `match --repo <path> --run-hash <hash>` assembles facets with
  `basis` marked (observed from Aim, reported from research state, unknown
  otherwise).
- **Scope (in):** read via `aimx` CLI JSON output; prior-attempt facets from
  findings and agenda outcomes.
- **Scope (out):** automatic symptom diagnosis.
- **Depends on:** 006

### P2 — Code & structured experiments

### 011 — OpenML adapter  [status: planned]

- **Description:** ingest OpenML runs for selected suites as Attempt evidence
  under standardized splits.
- **Outcome:** suite-filtered ingestion (for example CTR23, AMLB regression,
  CC18) with evidence typed as controlled comparisons where setups allow.
- **Scope (in):** REST/openml-python pull; rate limiting; local-only derived
  data.
- **Scope (out):** redistribution of OpenML-derived data (no blanket license).
- **Depends on:** 001, 006
- **Notes:** the full SQL dump link is dead; API reads are rate limited.

### 012 — Notebook & code evidence  [status: needs-info]

- **Description:** link recipes to implementation evidence in Kaggle
  notebooks.
- **Outcome:** _to be defined_
- **Scope (in):** _to be defined_
- **Depends on:** 002, 006
- **Notes:** Meta Kaggle Code download returned 404 locally; availability and
  license must be confirmed. GitNexus is optional and user-installed only.

### P3 — Evidence flywheel

### 013 — Local evidence exporter  [status: planned]

- **Description:** explicit export of reviewed aimx results (runs, findings,
  agenda outcomes, retro reports) into a private recipe pool.
- **Outcome:** an export command that only accepts comparable, reviewed,
  baseline-backed results and writes local Attempt/Evidence records typed as
  `independently_reproduced` or local outcomes.
- **Scope (in):** eligibility checks; private data layer; ranking signal.
- **Scope (out):** any public sync.
- **Depends on:** 006, 010

### Optional

### 014 — Graphify comparison  [status: undecided]

- **Description:** run Graphify on the 50-document extraction set as a
  comparison point.
- **Outcome:** _to be defined_
- **Scope (in):** _to be defined_
- **Depends on:** 003
- **Notes:** Graphify (Apache-2.0) uses a fixed node/edge taxonomy without
  custom fields or notebook support, so it is a reference for concept graphs,
  not a peer of schema-based extraction. Not a P0 gate.

## Open Questions

- ~~**Q1 — Extraction model winner:** which worker-tier model (and fallback)
  wins on the 50-document set for quote fidelity, evidence typing, and cost?
  Resolved in 005.~~ _Resolved 2026-11-02 → C-15._
- **Q2 — Exact P0 subset:** tag filter misses older untagged tabular
  competitions; add metric-based or manual inclusion? Resolved in 002.
- ~~**Q3 — Writeup text rights:** does Meta Kaggle's apache-2.0 cover
  user-authored forum text? The no-full-text policy (C-05) limits exposure;
  confirm before the first public data release.~~ _Resolved 2026-11-02 →
  C-13._
- **Q4 — Semantic retrieval in the product path:** if it helps on dev, which
  local, pinned embedding model keeps the query path deterministic and
  offline?
- **Q5 — Release channel for `data/` artifacts:** GitHub Releases, Hugging
  Face, or Kaggle dataset; versioning scheme tied to snapshot date + schema
  version.
- ~~**Q6 — Tabloom cases in a public benchmark:** the cases are
  non-commercial project data; publish their profiles, or keep them in a
  private test split?~~ _Resolved 2026-11-02 → C-14._
- **Q7 — Annotation capacity:** who reviews ~900 retrieval judgments and the
  50-document gold set, and with what tool?
- **Q8 — Profile input in P0:** P0 accepts hand-written `problem.json`; how
  much of 010 (Aim adapter) is needed before AutoResearch can use the CLI
  unattended?

## Cross-Cutting Notes

- Schema versions flow into extraction cache keys; any schema change states
  whether `data/extracted/` must be regenerated.
- Determinism is tested: two builds from the same inputs produce identical
  query results.
- Temporal correctness: every query supports an as-of date; benchmark runs
  index only sources dated before the held-out competition.
- License status is recorded per Source and checked at release time.
- Untrusted-input posture applies to every adapter, not only writeups.

---

**Version**: 2.0.1 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
