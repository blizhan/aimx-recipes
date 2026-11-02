# Experiment Proposal Compatibility Contract

Proposal schema version: `2.0.0`. Upstream alignment pin: aimx `1b2dd98b6621aa893c056013cd0dd06fff7ca405`. Reference paths in that repository: `specs/007-research-state/contracts/research-update.schema.json` and `src/aimx/research/validation.py`. The implementation must preserve a compatibility fixture and reference manifest with this revision; tests must not require a sibling checkout or installed aimx.

## Envelope and ownership

The envelope is defined in [data-model.md](../data-model.md). `review_status` is always `requires_lead_review`, including when all fields are populated. `experiment_contract` is a suggestion shaped like aimx's execution contract with explicitly nullable decisions. Passing recipe validation does not imply aimx admission. No conversion, attachment, state resolution, file inspection, execution, or proposal generation is implemented here.

## Contract fields and nullability

All fields in this table are required, including null-valued decisions; extensions is required here to keep the baseline and cost metadata explicit. Extra fields are forbidden outside extensions.

| Field | Proposal type | Null policy |
| --- | --- | --- |
| contract_version | exact integer 1 | Never null; distinct from schema_version |
| question | non-whitespace text | Never null |
| interventions | nonempty array of non-whitespace text | Never null |
| fixed_controls | nonempty array of non-whitespace text | Never null; describes proposed controls, not completed local setup |
| expected_evidence | nonempty array of non-whitespace text | Never null |
| disconfirmation | nonempty array of non-whitespace text | Never null |
| confounders | array of non-whitespace text | Never null; nonempty when interventions has more than one entry |
| evaluation | object with all six fields below | Object required; individual decisions nullable |
| data | object with all four fields below | Object required; individual decisions nullable |
| resources | nonempty resource array or null | Null means no caller budget supplied |
| failure_policy | stop_pending, continue_independent, or null | Unknown stays null |
| extensions | object containing aimx_recipes | Never null |

Evaluation fields:

- `protocol_id`: non-whitespace string or null.
- `protocol_sha256`: lowercase SHA-256 or null.
- `argv`: nonempty array of non-whitespace strings or null; never a shell command string.
- `metric`: non-whitespace string or null, preserving upstream semantics rather than restricting to the recipe metric enum.
- `acceptance_rule`: non-whitespace string or null. This is the upstream threshold/decision expression field; do not introduce a numeric acceptance-threshold field.
- `preflight_evidence`: nonempty array of preflight references or null. A populated list requires at least one local_artifact, matching aimx's file-backed preflight expectation. Validating its structure does not verify its files.

Data fields:

- `scope_ids`: unique array of non-whitespace entity-reference strings or null. An empty supplied array is structurally representable; aimx owns actual scope sufficiency and resolution.
- `phase`: `exploratory|independent_confirmation` or null.
- `candidate_fingerprint`: non-whitespace string or null, not necessarily SHA-256.
- `observation_revision`: nonnegative exact integer or null.

A resource requires `kind` and `unit` as non-whitespace strings, `planned` as finite nonnegative number or null, `verification` as `verified|unverified`, and `enforcement` as `executor_enforced|declared_only|unknown`. Optional `actual` is a finite nonnegative number; optional `source` is non-whitespace text. Verified resources require actual and source; executor_enforced requires verified. Boolean, negative, non-finite, and qualitative budgets are rejected. Unknown planned budget remains null and cannot imply readiness.

`extensions.aimx_recipes` requires `baseline_run` (non-whitespace string or null) and `qualitative_cost` (`{implementation, compute}`, each `low|medium|high|unknown`). Baseline is not a field of the pinned aimx top-level execution contract. This namespace may have additional JSON metadata without affecting authoritative envelope fields. Other namespaced extension keys are permitted as JSON objects; they never override contract fields.

## Preflight reference shapes

These references describe intended aimx inputs; the library does not read the referenced files or runs.

- `local_artifact`: required `kind=local_artifact`, `location` (non-whitespace path text), `sha256` (lowercase SHA-256), `size_bytes` (nonnegative exact integer), `evidence_type`, `purpose`, `source_activity_id` (non-whitespace strings). Version 1 supports this required-field subset only; additional properties are rejected. Expanding that subset requires a contract revision.
- `aim_run`: required `kind=aim_run`, `run_hash` (non-whitespace string); optional `role`, `note`, `evidence_type`, `purpose`, `source_activity_id` (non-whitespace strings). No dereferencing.

These reference types are separate from recipes Evidence IDs, which trace external claims. Proposal `evidence_ids` resolve to recipe Evidence records; preflight references concern a future local execution protocol.

## Boundary tests

1. Null execution decisions are accepted and remain null after validation.
2. Fully populated well-typed suggestions still report requires_lead_review.
3. `contract_version: 1.0`, boolean observation_revision, numeric acceptance_rule, and `planned: "low"` fail with stable field diagnostics.
4. Null baseline stays under extensions; no top-level baseline is injected.
5. An incomplete evaluation object missing required keys fails; a complete object containing explicitly nullable decisions passes structure.
6. Runtime admission concerns are not evaluated: registered scopes, digest/size resolution, activity references, host verification for continue_independent, candidate freezing, and independent-confirmation history stay with aimx.
7. A supplied hard-condition violation remains visible and cannot be presented as a satisfied condition or approval to execute.
