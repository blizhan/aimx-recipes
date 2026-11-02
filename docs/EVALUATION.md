# Evaluation Protocol

Status: protocol baseline for P0 (2026-11-02). Spec
[003](../ROADMAP.md#003--evaluation-harness--benchmark--status-planned) turns
this into a harness. Principle VI of the [constitution](../CONSTITUTION.md)
governs it.

## 1. What We Are Testing

The project claims that **problem-aware retrieval** returns more applicable,
better-evidenced, and safer experiment candidates than plain retrieval over the
same corpus. P0 evaluation exists to support or refute that claim.

These are **not** success metrics: documents collected, recipes extracted,
graph nodes, embeddings stored. They describe scale, not research value.

No improvement threshold is fixed in advance. P0 reports paired comparisons
with confidence intervals, and the decision to expand is made from that report.

## 2. Retrieval Benchmark

### 2.1 Composition

About 30 problems, in the P0 family (tabular + tabularized time series):

| Group | Count | Purpose |
| --- | --- | --- |
| Tabloom cases | 3 | Real downstream use: bike demand, electricity price, grid carbon intensity. All are regression with weather covariates and temporal structure. |
| Kaggle core | ~17 | Temporal leave-one-competition-out problems spread across task, metric, validation scheme, data size, and era |
| Kaggle boundary | ~10 | Probabilistic or quantile targets, strong non-stationarity, small data, tight compute, and a few out-of-family problems where the right answer is a low match level or `insufficient_evidence` |

Split: **10 dev / 20 test**, stratified by group and task. The test split is
frozen in git with a content hash. It is run only at milestones; tuning uses
dev only. The Tabloom cases are part of the public benchmark as
project-authored profiles, constraints, and judgments (ROADMAP C-14). Their
dev/test assignment is decided in spec 003.

### 2.2 Temporal Leave-One-Competition-Out

For each Kaggle benchmark problem *P*:

1. **Profile**: build *P*'s Problem Profile from the competition overview,
   evaluation, and data description only, never from its writeups. Each facet
   carries an honest `basis`. The profile is pre-filled by the extraction
   pipeline and reviewed by a human.
2. **Index as of *P*'s deadline**: queries run with `--as-of <deadline of P>`.
   Only sources dated before that date are visible, and *P*'s own sources are
   always excluded.
3. **Reference answers**: attempts extracted from *P*'s medal-team writeups
   are the reference. Those with positive evidence are "known useful"; those
   with negative evidence are "known not useful here".

This allows automatic recall scoring. Its limitation: a method absent from
*P*'s writeups is not thereby inapplicable. Applicability precision therefore
still needs human judgments (§2.4).

Tabloom cases have no reference writeups. They are judged by humans only and
also serve as end-to-end scenarios (§5).

### 2.3 Annotated Per Problem

- the Problem Profile (facets with basis);
- hard constraints (for example no future actuals at prediction time, fixed
  rolling-origin validation, CPU-only budget);
- known prior attempts, for the novelty metric, where the scenario defines
  them;
- the expected degrade behavior for boundary problems: minimum acceptable
  match level, or `insufficient_evidence`.

### 2.4 Pooling And Judgments

1. Each system returns its top 10 for each problem. The union of results is
   the judgment pool, about 30 items per problem and about **900 judgments** in
   total.
2. **LLM pre-labelling** proposes a grade and a short rationale for each item.
   It uses a model outside the magpie worker group that serves extraction.
3. **Human review** accepts or changes every pre-label. The agreement rate
   between pre-labels and final labels is reported. A ~10% subset is
   double-annotated to report inter-annotator agreement when two annotators
   are available.

The judged unit is a **suggestion**: a method plus its supporting text. For
recipe systems this is a recipe with its top evidence. For document baselines
it is a retrieved passage, and the judge records which method it suggests.

Graded applicability:

| Grade | Meaning |
| --- | --- |
| 3 | directly applicable, worth trying now |
| 2 | applicable with stated caveats |
| 1 | related, general reference only |
| 0 | not applicable |

Separate boolean flags record **violates a hard constraint** and **repeats a
prior attempt**.

## 3. Systems Compared

All systems use the same corpus snapshot, the same `--as-of` filter, and the
same K.

| System | Description |
| --- | --- |
| A — BM25 over documents | DuckDB FTS over writeups and competition text; query = problem description |
| B — Semantic over documents | dense retrieval over passages with a pinned embedding model; same query text |
| A′ — BM25 over extracted records | keyword retrieval over Attempt/Evidence records: same extraction, no problem awareness |
| C — aimx-recipes | profile validation, hard constraints, facet matching, FTS, evidence-aware rerank |

A′ separates the value of **extraction** (structured records) from the value
of **problem-aware matching**. Ablations of C: without hard-constraint
filtering, without evidence weighting, and without basis weighting.

## 4. Metrics

### 4.1 Retrieval

| Metric | Definition |
| --- | --- |
| Coverage@10 | share of problems with at least one grade ≥ 2 item in the top 10 |
| Applicability Precision@K (K = 5, 10) | mean share of top-K items with grade ≥ 2 |
| nDCG@10 | graded ranking quality (supplementary) |
| Reference Recall@10 | Kaggle problems only: share of "known useful" reference recipes found in the top 10 (baseline passages mapped through their extracted attempts) |
| Constraint Violation Rate@K | share of top-K items flagged as violating a hard constraint (target for C: zero) |
| Repeat Rate@K | share of top-K items repeating a prior attempt (lower is better) |
| Degrade Correctness | boundary problems: share answered at or below the expected match level, or with `insufficient_evidence` |
| Evidence Fidelity | sampled: share of shown quotes that support the claimed evidence type and outcome |
| Query cost | wall time per query; extraction tokens and calls amortized per indexed document |

Reporting covers dev and test separately. Each metric gets a bootstrap 95% CI
over problems, and each system pair gets a paired comparison (paired bootstrap
or permutation test). With 20 test problems the intervals will be wide, and the
report says so plainly.

### 4.2 Reproducibility Of The Report

Every report records:

- the `build_manifest` hash of the index;
- the benchmark split hash;
- the scoring config hash;
- the extraction artifact version;
- the commit of the harness.

A report that cannot be regenerated from these inputs is invalid.

## 5. End-To-End Scenarios

The three Tabloom cases run the full loop:

```text
research goal → problem.json → match → evidence → propose → (Lead review)
```

Each run is reviewed with a short rubric:

- Were close enough experiences found?
- Are applicable **and** non-applicable conditions stated?
- Can every claim be traced to a quote and a source?
- Can the proposal become a controlled experiment, with the right fields left
  `null` for the Lead?
- Were the case's constraints respected? For example, electricity price must
  not use realized prices at forecast time.

The electricity-price case is the reference scenario from the design draft:
D+1 probabilistic forecast, pinball loss and calibration, rolling-window
validation, extreme-price underprediction, and distribution shift.

## 6. Extraction Evaluation

### 6.1 Gold Set

- **50 writeups** from the P0 subset, stratified by era (pre-2020,
  2020–2023, 2024+), length, medal rank, and task subtype.
- Drawn only from competitions that are **not** in the retrieval test split.
- Split **20 prompt-dev / 30 held-out**. Prompt and schema iteration use only
  the 20.
- Humans annotate each document:
  - Attempts: method, `recipe_id` or `unmapped`, baseline/candidate,
    evaluation scope, values, joint change;
  - Evidence: span, type, outcome.
- The annotation guideline lives in `evals/` and is versioned.

The gold set also measures the real **distribution of evidence types**: how
often writeups contain controlled ablations, joint-change gains, use-only
mentions, failures, and opinions. The project does not assume that ablations
are rare; it measures it.

### 6.2 Metrics

| Metric | Definition |
| --- | --- |
| Attempt precision / recall | matched by span overlap and method identity |
| Evidence type accuracy | with a confusion matrix; `controlled_ablation` vs `reported_gain` matters most |
| Outcome accuracy | positive / negative / neutral / mixed / unclear |
| Recipe mapping accuracy | correct `recipe_id` or correct `unmapped` |
| Numeric fidelity | values, direction, and evaluation scope correct (CV vs public vs private LB) |
| Joint-change detection | multi-change gains not credited to a single recipe |
| Quote validity | share of quotes found verbatim (automatic) |
| Rejection rate | share of records rejected by validation, by reason |
| Cost | tokens and calls per document; latency; quota usage |

Numeric gains, causal claims, and leakage-related statements get full human
review in the sample. Errors there are the most expensive.

### 6.3 Routed Extraction Quality

There is no model-selection step (ROADMAP C-15). The gold set runs through
`group/worker`, the same route as production
([ARCHITECTURE §5.2](../ARCHITECTURE.md#52-model-interface)), on a fixed prompt
version. The report gives every §6.2 metric overall and broken down by served
model. With 30 held-out documents spread over several backends, per-model
counts are small, so the breakdown flags backends for closer review rather
than ranking them.

If a backend is clearly worse, above all on fidelity (quote validity, evidence
type accuracy, numeric fidelity), it is removed from the worker group in
magpie's configuration and the records it served are re-extracted. After the
production run, an audit of about 100 records, stratified by served model,
checks for drift between the gold-set result and the full run.

### 6.4 Optional: Graphify Comparison

If cheap, Graphify runs on the same 50 documents as a reference point
(spec 014). It is not a P0 gate. Graphify's fixed node and edge taxonomy has
no fields for evidence type, outcome, or evaluation scope, so the comparison
covers method identification and traceability only.

## 7. P0 Exit

P0 is complete when these exist:

1. a test-split report comparing A, B, A′, and C (with ablations) on the
   metrics in §4.1;
2. the extraction evaluation report on the 30 held-out gold documents, with
   overall and by served model;
3. end-to-end runs for the three Tabloom cases, with rubric results and
   proposal JSON.

The decision to expand coverage (P1) is made from these reports, not from
corpus size.
