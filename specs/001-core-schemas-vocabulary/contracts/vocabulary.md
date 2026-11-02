# Initial Vocabulary and Condition Contract

Version: `2.0.0`. The implementation will encode these definitions once in `schemas/2.0.0/facet-vocabulary.json` and `action-taxonomy.json`, validated by their own schemas. Profile/condition validation reads that same registry. Every entry includes name, description, value schema, cardinality, allowed operators, and units where applicable. Unknown names are rejected; no aliases or source-derived additions.

## Facets

All values below are scalar except explicitly listed collections. Boolean means true/false, not a string. Numeric counts are exact integers. Unknown is represented by the assertion wrapper's null value and unknown basis, never added to the known-value enum.

| Facet | Values / type | Meaning |
| --- | --- | --- |
| task.kind | regression, binary_classification, multiclass_classification, ranking, forecasting | Prediction task |
| target.kind | point, quantile, distribution, probability | Prediction output |
| target.long_tail | boolean | Long-tailed target |
| target.bounded | boolean | Target has finite domain bounds |
| modality.kind | tabular, time_series, image, text, audio, multimodal | Last four are transfer-boundary cases only |
| dataset.rows | integer >= 0 | Observed row count |
| dataset.features | integer >= 0 | Input feature count |
| dataset.missing_fraction | number in [0,1] | Fraction of missing input cells |
| dataset.high_cardinality_categoricals | boolean | Author reports high-cardinality categorical features |
| dataset.group_structure | boolean | Rows belong to meaningful groups |
| temporal.frequency | irregular, subhourly, hourly, daily, weekly, monthly, quarterly, yearly | Sampling cadence |
| temporal.horizon_steps | integer >= 1 | Forecast horizon in sampling steps |
| temporal.covariates | unique nonempty array of static, historical, future_known | Available covariate classes |
| temporal.future_data_allowed | boolean | Whether information beyond prediction time is permitted |
| validation.scheme | kfold, stratified, group, time_split, rolling_origin, holdout | Validation split procedure |
| validation.fixed_protocol | boolean | Whether split/protocol is fixed by the task |
| validation.target_leakage_allowed | boolean | Explicit task prohibition/permission, never inferred from score |
| metric.name | rmse, mae, rmsle, pinball, auc, logloss, map_at_k, accuracy, calibration_error | Metric identity; map_at_k requires metric.k |
| metric.k | integer >= 1 | Ranking cutoff, permitted only with map_at_k |
| characteristics.non_stationarity | boolean | Reported changing data-generating conditions |
| characteristics.class_imbalance | boolean | Reported class imbalance |
| characteristics.distribution_shift | boolean | Reported train/evaluation distribution shift |
| characteristics.leakage_risk | boolean | Reported potential leakage |
| symptoms.overfitting | boolean | Observed/reported overfitting |
| symptoms.cv_lb_gap | boolean | Cross-validation/leaderboard discrepancy |
| symptoms.poor_calibration | boolean | Prediction calibration concern |
| symptoms.extreme_underprediction | boolean | Underprediction in extreme target values |
| compute.gpu_available | boolean | Accelerator availability |
| compute.runtime_seconds | number >= 0 | Available runtime budget, seconds |
| compute.memory_bytes | integer >= 0 | Available memory budget, bytes |
| constraints.commercial_use_required | boolean | Intended use requires commercial permission |
| constraints.redistribution_required | boolean | Intended use requires redistribution permission |
| constraints.deployment | offline_batch, online_service, edge | Deployment setting |
| prior_attempts | unique array of {recipe_id, status} | Status tried, rejected, or unresolved; unique recipe_id; may be empty |

`metric.name` labels metrics without comparing them. All listed loss/error metrics have nonnegative measurement domains; auc/map_at_k/accuracy are in [0,1]. Metric direction is retained explicitly and must agree with the metric definition: losses/errors minimize, auc/map_at_k/accuracy maximize. New metrics require a vocabulary release; there is no free-text escape in measurement identity. The general Attempt type can represent negative numbers, but the initial metrics reject them according to their domains; reported deltas may be negative. `metric.k` is carried as optional nullable `metric_k` on Attempts and is required positive for map_at_k, otherwise null/absent.

P0 uses measured sizes/budgets, so no row/feature/runtime bucket boundaries need to be guessed. Boolean characteristics are assertions with basis and provenance, not automatic measurements or thresholds. The vocabulary does not infer future-data or leakage permission from absent values.

## Conditions

Condition shape is specified in [data-model.md](../data-model.md). Allowed operators:

| Operator | Allowed facet type | Operand |
| --- | --- | --- |
| eq, ne | scalar enum, boolean, numeric | One value valid for that facet |
| in, not_in | scalar enum, boolean, numeric | Nonempty unique array of valid scalar values |
| lt, lte, gt, gte | numeric | One finite value in the facet's domain |
| contains, not_contains | temporal.covariates collection | One allowed collection member |
| present, absent | all facets | null |

`prior_attempts` supports present/absent only in version 1; recipe-aware matching of that history belongs to later work. Presence operators represent information availability, not boolean truth. Validation checks syntax, operands, and assessment consistency, not truth of conditions. A missing or explicitly unknown facet cannot establish a satisfied assessment even for absence; matching may use the explicit unknown state. In known conflicted assertions, a satisfied assessment is invalid because no conflict resolution is authorized.

All condition lists are conjunctions; there is no nested expression language, negated group, disjunction, user code, or query evaluation in this feature. Multiple conditions on a facet are allowed with distinct IDs. No optimizer attempts to solve their satisfiability.

## Action taxonomy

Recipes select a leaf; parent nodes group leaves and cannot be assigned directly. Each leaf description is the action itself, not a claim of effectiveness.

| Parent | Leaves | Definitions |
| --- | --- | --- |
| data_preparation | imputation, filtering, resampling | Fill missing values; remove/select rows; change sampling distribution |
| feature_engineering | encoding, lag_features, aggregation, transformation | Encode variables; use past observations; summarize groups/windows; transform features |
| model_choice | family_selection | Choose a model family |
| training | regularization, objective, optimization | Constrain fit; choose loss; adjust optimization procedure |
| validation | split | Choose evaluation split/protocol |
| ensemble | blending, stacking | Combine predictions directly; fit a combining model |
| prediction | calibration, clipping | Adjust prediction calibration; bound predictions |

Canonical leaf names join parent and leaf with a dot, e.g. `feature_engineering.encoding`, `feature_engineering.lag_features`, `validation.split`, `ensemble.stacking`. These are independently authored project definitions; no external taxonomy is copied.
