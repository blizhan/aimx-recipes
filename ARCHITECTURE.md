# aimx-recipes Architecture

Status: design baseline for P0 (2026-11-02). Commands and schemas described
here are **proposed**; nothing is implemented yet. Policy lives in the
[constitution](CONSTITUTION.md); sequencing lives in the [roadmap](ROADMAP.md).

## 1. Purpose And Boundaries

`aimx-recipes` is a problem-aware research retrieval system and recipe pool for
autonomous ML research. Given a structured description of the current problem,
it returns optimization recipes that others have tried, together with the
conditions under which they were tried and the evidence for and against them.
The aimx Lead decides what, if anything, to run.

```text
                 problem.json (Problem Profile)
                            │
   ┌────────────────────────▼─────────────────────────┐
   │ aimx-recipes  (read-only query CLI, no LLM)       │
   │   match · search · show · evidence · facets ·     │
   │   propose                                         │
   └────────────────────────┬─────────────────────────┘
                            │ Experiment Proposal JSON
                            ▼
   aimx Lead ──ResearchUpdate──► aimx Research State (Agenda: proposed)
                            │
                  AutoResearch executes ──► Aim runs ──► Findings ──► Retro
```

| System | Owns |
| --- | --- |
| aimx-recipes | External experience, problem matching, evidence retrieval, recipe candidates, proposals |
| aimx Research | Findings, Frontier, Agenda, Research State |
| AutoResearch | Planning, agent dispatch, execution, result integration |
| aimx Retro | Retrospectives, failure analysis, follow-up options |
| Aim | Raw runs, params, metrics, curves |

`aimx-recipes` never writes to aimx or Aim state.

## 2. Data Model

Five core entities (Source, Problem, Recipe, Attempt, Evidence) and two
interface objects (Problem Profile, Experiment Proposal).

```text
Source 1──N Document
Problem 1──1 Problem Profile (facets)
Problem 1──N Attempt N──0..1 Recipe        (recipe_id null = "unmapped")
Attempt 1──N Evidence N──1 Document         (verbatim span)
Recipe ──derived──► support / adoption / counterevidence views
```

### 2.1 Source And Document

A **Source** is one identity for one original artifact (a writeup, a
competition page, an OpenML run, a local aimx result). Mirrors and duplicates
resolve to the same Source. Each Source records `kind`, canonical URL or ID,
`license`, snapshot ID, and `content_sha256`.

A **Document** is the normalized text unit used for extraction and search
(for example a writeup body or a competition's evaluation section). Full text
lives only in the local raw snapshot (`data/raw/`) and is never released.

### 2.2 Problem And Problem Profile

A **Problem** is a research problem with conditions: a Kaggle competition, a
benchmark case, or the caller's current task. Its **Problem Profile** is a set
of facets drawn from a controlled vocabulary shared with recipe constraints.

Every facet value has this shape:

```json
{
  "value": "rolling_origin",
  "basis": "reported",
  "source": "competition:evaluation",
  "confidence": "high",
  "conflicts": []
}
```

`basis` is one of `observed`, `reported`, `inferred`, `unknown` (aligned with
aimx-retro). Unknown facets stay unknown. Conflicts between sources are kept as
`conflicts`, never overwritten.

Initial facet groups (spec 001 fixes the exact vocabulary):

| Group | Examples |
| --- | --- |
| `task` | regression, binary/multiclass classification, ranking, forecasting |
| `target` | point, quantile, distribution, probability; long-tail, bounded |
| `modality` | tabular, time_series (others only as transfer cases) |
| `dataset` | row/feature size buckets, missingness, high-cardinality categoricals, group structure |
| `temporal` | frequency, horizon, covariates (static, historical, future-known) |
| `validation` | kfold, stratified, group, time split, rolling origin, holdout |
| `metric` | rmse, mae, rmsle, pinball, auc, logloss, map@k, … |
| `characteristics` | non-stationarity, class imbalance, distribution shift, leakage risk |
| `symptoms` | overfitting, CV–LB gap, poor calibration, extreme-value underprediction |
| `compute` | GPU availability, runtime and memory budget buckets |
| `prior_attempts` | recipe IDs marked tried / rejected / unresolved |

### 2.3 Recipe

A **Recipe** is a reusable optimization action, between an abstract trick and
project code (for example *out-of-fold target encoding*). Recipes are authored
as YAML in git and reviewed like code.

| Field | Meaning |
| --- | --- |
| `recipe_id`, `canonical_name`, `aliases` | stable identity and names seen in sources |
| `action_type` | hierarchical, e.g. `feature_engineering.encoding`, `validation.split`, `ensemble.stacking` |
| `action`, `description` | the core operation |
| `applicability` | facet conditions where it is expected to help |
| `preconditions` | facet conditions that must hold to apply it at all |
| `hard_constraints` | facet predicates that must not be violated |
| `contraindications` | known risks and failure settings |
| `configuration` | reference settings seen in sources |
| `implementation_refs` | pseudocode, library APIs, code links |
| `expected_effect` | metrics or symptoms it targets |
| `cost_profile` | implementation and compute cost |

Evidence is **not** listed on the recipe. It is derived at build time from
Attempts that map to the recipe.

### 2.4 Attempt

An **Attempt** is one reported try of an intervention in one problem: what was
changed, against what, measured how.

Key fields: `attempt_id`, `problem_id`, `document_id`, `recipe_id` (nullable),
`raw_method_name`, `baseline_method`, `candidate_method`, `configuration`,
`validation_protocol`, `evaluation_scope` (`cv`, `public_lb`, `private_lb`,
`holdout`), `metric_name`, `metric_direction`, `baseline_value`,
`candidate_value`, `reported_delta`, `joint_change` (other things changed at
the same time), `outcome`, `confounders`, `provenance`.

An Attempt is an observation, not a general claim that the method works.

### 2.5 Evidence

An **Evidence** record ties an Attempt to a verbatim span of a Document.

| Field | Meaning |
| --- | --- |
| `type` | `controlled_ablation`, `reported_gain`, `reported_failure`, `used_in_solution`, `attempted`, `author_opinion`, `independently_reproduced` |
| `outcome` | `positive`, `negative`, `neutral`, `mixed`, `unclear` |
| `quote` | short verbatim excerpt |
| `char_start`, `char_end` | offsets in the Document, computed by code |
| `uncertainty` | confounders, missing conditions, scope caveats |
| `provenance` | extractor, schema, prompt, model, content fingerprint |

Type and outcome are independent: a `controlled_ablation` can be `negative`.

### 2.6 Derived Aggregates

Computed in the index, never authored:

- **adoption**: Attempts of type `used_in_solution`, by distinct problem.
- **support** and **counterevidence**: counts by type × outcome × evaluation
  scope, by distinct problem and distinct source.
- **independence**: repeated use of one public kernel or technique across
  teams is not counted as independent replication.

Raw metric deltas are shown per problem and never averaged across problems.

### 2.7 Experiment Proposal

See [§7](#7-experiment-proposal-and-aimx-integration).

## 3. Storage Layers

```text
recipes/**/<recipe_id>.yaml   git — curated recipes, the single authority
schemas/                      git — JSON Schemas, facet vocabulary, action types
evals/                        git — benchmark problems, judgments, gold sets
data/                         gitignored
  raw/          source snapshots as Parquet + sha256 manifests (local only)
  extracted/    frozen extraction JSONL: profiles, attempts, evidence,
                rejections (released as versioned artifacts)
  index.duckdb  built by `aimx-recipes build`; disposable
```

- **YAML in git** keeps recipes diffable and reviewable. Canonicalization can
  only *propose* YAML changes; it cannot edit recipes silently.
- **Parquet snapshots** pin exactly what was ingested. They contain full source
  text and are never published.
- **Extraction JSONL** is the expensive, model-dependent layer. Freezing it
  makes the index reproducible without re-running models.
- **DuckDB index** is compiled from the three layers. Query commands read only
  this file.

A user who downloads released extraction artifacts but not Meta Kaggle can
still build an index. Full-text search then covers recipes and evidence quotes
only, not whole writeups.

## 4. Pipeline

```text
 ingest (adapter)      extract (offline LLM)       build (deterministic)
 Meta Kaggle CSV ──►  data/raw/*.parquet ──► data/extracted/*.jsonl ──┐
                              │                                       ├─► data/index.duckdb
 recipes/*.yaml, schemas/ ────┴───────────────────────────────────────┘
```

| Command | Writes | Calls a model |
| --- | --- | --- |
| `aimx-recipes ingest kaggle` | `data/raw/` | no |
| `aimx-recipes extract` | `data/extracted/` | yes (offline only) |
| `aimx-recipes build` | `data/index.duckdb` | no |
| query commands | nothing | no |

### 4.1 Ingest

The Meta Kaggle adapter resolves writeups through
`Teams.WriteUpForumTopicId → ForumTopics.FirstForumMessageId → ForumMessages`.
It joins competition context (overview, evaluation description, dataset
description, metric, dates, host segment, tags) and team outcome (medal,
public/private rank).

All valid writeups are ingested into immutable snapshot directories under
`data/raw/kaggle/<snapshot_id>/`. P0 tabular membership is not used to discard
writeups at ingest time; instead, it is computed as a deterministic membership
layer under `membership/<membership_id>/` with an explainable `p0` flag and
decision rule for every competition. See [raw-snapshot.md](specs/002-meta-kaggle-ingest/contracts/raw-snapshot.md)
and [DATA_SOURCES](docs/DATA_SOURCES.md).

### 4.2 Build

`build` loads YAML, vocabulary, and extraction JSONL; validates cross-references;
loads documents from `data/raw/` when present; creates tables, views, and the
DuckDB FTS index. It also records a `build_manifest` (input hashes, schema
versions, code version, scoring config hash).

Determinism rules: inputs are read in sorted order, IDs are content-derived,
ties break on IDs, and query output contains no wall-clock values. Building
twice from the same inputs must give identical query results; tests enforce
this.

Main tables: `sources`, `documents`, `problems`, `problem_facets`, `recipes`,
`recipe_conditions`, `attempts`, `evidence`, `facet_vocab`, `build_manifest`.
Main views: `recipe_support`, `recipe_adoption`, `problem_similarity_inputs`.

## 5. Evidence Extraction

Extraction is an offline **batch pipeline**, not an agent loop. It runs only
when someone invokes `extract`.

### 5.1 Units Of Work

| Pass | Unit | P0 volume (tag-filtered subset) |
| --- | --- | --- |
| Problem Profile | one competition: overview + evaluation + data description | ~179 calls |
| Attempts + Evidence | one writeup + its competition context | ~1,582 calls, ~1.9M tokens of writeup text |

Context enrichment matters: a writeup that says "lag features with a time
split" rarely states frequency, horizon, metric, or which covariates are known
in advance. The competition context supplies these, labelled as `reported` from
the competition, not from the writeup.

### 5.2 Model Interface

The extractor talks to any **OpenAI-compatible chat-completions endpoint**,
configured by environment or config file (base URL, API key, model or group
name). The local deployment is the magpie gateway with worker-tier models.

Structured output uses a **forced tool call**. The request declares one
function (`record_extraction`) whose parameters are the strict JSON Schema,
and sets `tool_choice` to that function. A 2026-11-02 probe against the magpie
worker backends found:

- `response_format: json_schema` was ignored by several backends
  (gemini-3.8-flash, deepseek-v4.1-flash, glm-5.3-flash returned prose);
- a forced strict tool call returned schema-shaped arguments with verbatim
  quotes on all six backends tested.

Extraction requests **`group/worker`** and lets magpie route each request
across the worker backends (ROADMAP C-15); there is no model-selection step.
Different documents may therefore be served by different models. Every record
stores the served model (from the gateway's `X-Magpie-Model` header when
present, otherwise the response `model` field), so quality can be reported,
and records re-extracted, per served model. A backend that underperforms is
removed from the worker group in magpie's configuration, not in this project.

### 5.3 Validation

Every tool-call payload goes through deterministic checks before anything is
written:

1. **Schema**: JSON Schema validation of the whole payload.
2. **Quote location**: each `quote` must occur in the Document. Matching
   tolerates whitespace and markdown-escape normalization; offsets are mapped
   back to the original text by code. Quotes that are not found are rejected,
   not repaired.
3. **Vocabulary**: facet values must exist in the vocabulary. Unknown values
   are rejected or recorded as `unknown`, never auto-mapped to a near match.
4. **Catalog**: `recipe_id` must exist in the catalog or be `unmapped`.
5. **Type sanity**: for example, `controlled_ablation` needs an explicit
   comparison in the quoted span; numbers must carry an `evaluation_scope`;
   `joint_change` must be set when several changes are reported together.

Records that pass go to `data/extracted/`, and records that fail go to a
rejection log with the reason. A malformed whole-call response gets one retry,
then it is logged.

### 5.4 Freezing And Provenance

- **Cache key**: `sha256(content_fingerprint, schema_version, extractor_version, requested_model, prompt_hash)`.
  A record with an existing key is not re-extracted. `requested_model` is the
  model or group named in the request (`group/worker`), known before the call;
  the served model is provenance, not part of the key. Changing the worker
  group's membership does not invalidate the cache. Records from a removed
  backend are re-extracted selectively by served model.
- **Provenance on every record**: provider, requested model or group, served
  model, prompt version, schema version, extractor version, `extracted_at`.
- Released extraction artifacts are versioned by snapshot date + schema
  version.

### 5.5 Untrusted Input

Documents are data, never instructions. The prompt says so explicitly. The
only tool exposed is the record function, which has no side effects, and every
output is validated before storage. A document that injects instructions can
at worst produce records that fail validation or carry wrong labels. Labels
are caught by the gold-set evaluation and sampled review; they cannot cause
actions.

### 5.6 Other Model Uses

- **Benchmark pre-labelling** uses the same pipeline shape but a model
  outside the worker group, so extraction models do not grade their own
  output.
- **Canonicalization** (P1) proposes recipe YAML changes for human review.
- **Agents** (pi, Claude Code) are used for curation and review work: prompt
  iteration, catalog PRs, gold-set annotation support. They are never part of
  the query path.

## 6. Problem-Aware Retrieval

### 6.1 Flow

1. **Validate** the input profile against the vocabulary and report unknown
   facets.
2. **Hard constraints**: evaluate every recipe's `preconditions` and
   `hard_constraints` against the profile with three-valued logic:
   `satisfied`, `violated`, `unknown`. Violated recipes are excluded. They
   appear in `excluded` with the reason when requested.
3. **Candidate generation**:
   - problems similar on facets, weighted by `basis`;
   - FTS over evidence quotes and documents using the profile's metric,
     symptoms, and keywords;
   - recipes whose `applicability` matches.
4. **Match level** for each candidate:

   | Level | Meaning |
   | --- | --- |
   | L1 | strict: task, data, validation, symptoms, resources match |
   | L2 | task and data-mechanism match |
   | L3 | symptom match across tasks |
   | L4 | general method reference |

5. **Rerank** with a deterministic, versioned scoring config. Inputs:
   - facet match and level;
   - evidence strength by type and outcome;
   - evaluation scope (`private_lb` and `holdout` above `public_lb`);
   - number of independent problems;
   - counterevidence;
   - cost against the compute facets;
   - novelty against `prior_attempts` (tried or rejected recipes are demoted
     and flagged).

   Weights are tuned on the dev split only.
6. **Respond**. Each candidate includes:
   - match level and transfer risk;
   - matched, unknown, and violated facets;
   - the evidence summary (type × outcome × scope);
   - top evidence IDs with quotes and source links;
   - similar problems;
   - reasons.

A score is a ranking signal, not a probability of success. If no candidate
reaches the minimum evidence bar, the response status is
`insufficient_evidence`.

### 6.2 Temporal Filtering

Every query accepts `--as-of DATE`, which restricts the index to sources dated
before that date. The benchmark uses this for temporal
leave-one-competition-out. Callers can use it to reproduce what was knowable at
a given time.

## 7. Experiment Proposal And aimx Integration

`propose` turns a recipe + Problem Profile (+ optional match result) into an
**Experiment Proposal**. It is a deterministic template fill, with no model
call. Field names follow aimx `experiment_contract` so the Lead can copy them
directly. Recipe-specific data goes under `extensions.aimx_recipes`.

| Proposal field | Filled from | Left `null` |
| --- | --- | --- |
| `question` | recipe expected effect + profile target/metric | — |
| `interventions` | recipe action + reference configuration | — |
| `fixed_controls` | recipe preconditions + profile validation | — |
| `expected_evidence` | profile metric | — |
| `disconfirmation` | contraindications + counterevidence | — |
| `confounders` | evidence confounders | — |
| `evaluation` | `metric` | `protocol_id`, `protocol_sha256`, `argv`, `acceptance_rule` |
| `data` | — | `scope_ids`, `candidate_fingerprint`, … |
| `resources` | recipe cost profile as `declared_only`, `unverified` | actual budget |
| `extensions.aimx_recipes` | `recipe_id`, `evidence_ids`, `applicability_assessment`, `risks`, match level, transfer risk, index `build_manifest` hash | — |

```json
{
  "contract_version": 1,
  "question": "Does out-of-fold target encoding of high-cardinality categoricals reduce RMSE under the existing time split?",
  "interventions": ["out_of_fold_target_encoding (5 folds, smoothing as in ev_0142)"],
  "fixed_controls": ["keep validation split fixed", "fit encodings on training folds only"],
  "expected_evidence": ["paired rmse on the fixed validation split"],
  "disconfirmation": ["no rmse improvement over baseline", "train/validation gap widens"],
  "confounders": [],
  "evaluation": {"metric": "rmse", "protocol_id": null, "acceptance_rule": null},
  "data": null,
  "resources": [{"kind": "compute", "unit": "relative", "planned": "low", "verification": "unverified", "enforcement": "declared_only"}],
  "extensions": {
    "aimx_recipes": {
      "recipe_id": "oof_target_encoding",
      "evidence_ids": ["ev_0142", "ev_0388"],
      "match_level": "L2",
      "transfer_risk": "medium",
      "applicability_assessment": {"matched": ["task", "dataset.high_cardinality"], "unknown": ["characteristics.drift"], "violated": []},
      "risks": ["target leakage if encodings are fit outside folds"]
    }
  }
}
```

Hand-off without any aimx change:

1. The agent writes the Proposal JSON into the project, for example under
   `artifacts/proposals/`.
2. The Lead reviews it against local findings and prior attempts. The Lead
   sets the baseline, acceptance rule, and protocol.
3. The Lead creates an Agenda item through a normal ResearchUpdate (status
   `proposed`). The proposal is attached as
   `{"kind": "local_artifact", "location": …, "sha256": …, "evidence_type": "recipe_proposal"}`.
4. Results come back through Aim runs and Findings, as usual.

aimx Finding evidence accepts only `aim_run` and `local_artifact`
references, so a recipe cannot become a finding without a local run. This
enforces *Recipes Are Not Findings* structurally.

## 8. CLI Surface (Proposed)

| Command | Purpose |
| --- | --- |
| `aimx-recipes ingest kaggle --meta-kaggle <dir>` | snapshot the P0 subset into `data/raw/` |
| `aimx-recipes extract [--group <name>] [--limit N] [--dry-run]` | offline extraction into `data/extracted/` |
| `aimx-recipes build` | compile `data/index.duckdb` |
| `aimx-recipes match --problem problem.json [--as-of D] [--top-k N] [--show-excluded]` | problem-aware recipe candidates |
| `aimx-recipes search "<text>" [--facet k=v] [--as-of D]` | full-text search over evidence and documents |
| `aimx-recipes show <recipe_id>` | recipe definition + derived aggregates |
| `aimx-recipes evidence <recipe_id> [--type T] [--outcome O] [--scope S]` | evidence records with quotes and sources |
| `aimx-recipes facets [<facet>]` | the controlled vocabulary |
| `aimx-recipes propose <recipe_id> --problem problem.json` | Experiment Proposal JSON |

All read commands support `--json` with a stable envelope:
`schema_version`, `build_manifest` hash, `status`, `results`, `warnings`. The
agent loop is: `match` → inspect `unknown`/`violated` facets → refine the
profile or query → `evidence` on promising candidates → `propose`.

## 9. Agent Skill

A thin `aimx-recipes` skill (spec 007) documents:

- how to write `problem.json` with honest `basis` labels;
- how to read match output and when to relax or tighten facets;
- how to check evidence before proposing;
- how to hand the proposal to the aimx Lead.

The skill holds no logic of its own beyond the CLI.

## 10. Technology Choices

| Layer | Choice | Deferred / rejected |
| --- | --- | --- |
| Language / env | Python, `uv` | Rust rewrite until a measured bottleneck |
| Index | DuckDB + FTS | graph DB (Neo4j, FalkorDB) until multi-hop queries are needed |
| Snapshots / artifacts | Parquet, JSONL | — |
| Authority | YAML + JSON Schema in git | recipes in a database |
| Semantic retrieval | evaluated as a baseline first | product path only if it wins on dev, with a pinned local embedding model |
| Extraction | OpenAI-compatible endpoint, forced tool call | agent loops; `response_format` |
| Code intelligence | — | GitNexus (PolyForm Noncommercial): optional user-installed tool only |
| Concept graphs | — | Graphify: optional comparison (spec 014) |

## 11. Repository Layout (Target)

```text
aimx-recipes/
├── src/aimx_recipes/
│   ├── models/          # typed entities matching schemas/
│   ├── sources/kaggle/  # Meta Kaggle adapter
│   ├── extraction/      # context bundles, client, validation, freezing
│   ├── index/           # deterministic build
│   ├── retrieval/       # constraints, matching, scoring
│   ├── proposals/
│   └── cli/
├── schemas/             # JSON Schemas, facet vocabulary, action types
├── recipes/             # curated recipe YAML
├── evals/               # benchmark, judgments, gold set, harness config
├── skills/aimx-recipes/
├── docs/
├── tests/
└── data/                # gitignored
```

Modules are created when the spec that needs them starts, not up front.
