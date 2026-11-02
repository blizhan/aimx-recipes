"""Data models, TypedDict interfaces, and validation result types."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Literal, Mapping, NotRequired, Sequence, TypedDict

JSONValue = Any


@dataclass(frozen=True)
class Diagnostic:
    """Diagnostic entry for a single validation or parsing issue."""

    entity_type: str | None
    record_id: str | None
    input_index: int
    pointer: str
    code: str
    message: str
    check: str
    severity: Literal["error", "incomplete"]

    def sort_key(self) -> tuple[str, str, int, str, str, str, str]:
        """Return the documented sort key for deterministic ordering."""
        return (
            self.entity_type or "",
            self.record_id or "",
            self.input_index,
            self.pointer,
            self.code,
            self.check,
            self.severity,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "record_id": self.record_id,
            "input_index": self.input_index,
            "pointer": self.pointer,
            "code": self.code,
            "message": self.message,
            "check": self.check,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Envelope representing the outcome of record or bundle validation."""

    result_version: str = "2.0.0"
    level: Literal["structural", "contextual"] = "structural"
    status: Literal["valid", "invalid", "incomplete"] = "valid"
    structurally_valid: bool = True
    contextual_complete: bool = False
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_version": self.result_version,
            "level": self.level,
            "status": self.status,
            "structurally_valid": self.structurally_valid,
            "contextual_complete": self.contextual_complete,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    def to_json(self) -> str:
        """Serialize result canonically: UTF-8, sorted keys, no NaN, compact separators."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing raw JSON record text."""

    record: dict[str, Any] | None
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationContext:
    """Read-only contextual data supplied to bundle validation."""

    document_texts: Mapping[str, str] = field(default_factory=dict)


# --- TypedDict interfaces for entities ---


class Problem(TypedDict):
    """Shared Problem entity definition."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["problem"]
    problem_id: str
    kind: Literal["competition", "benchmark_case", "caller_task"]
    title: str
    source_ids: list[str]
    description: NotRequired[str]
    as_of: NotRequired[str | None]


class Condition(TypedDict):
    """Condition representation for recipes and profiles."""

    condition_id: str
    facet: str
    op: Literal[
        "eq",
        "ne",
        "in",
        "not_in",
        "lt",
        "lte",
        "gt",
        "gte",
        "contains",
        "not_contains",
        "present",
        "absent",
    ]
    operand: Any
    description: NotRequired[str]


class FacetSource(TypedDict):
    """Provenance pointer for an asserted facet value."""

    kind: Literal["document", "caller", "annotation"]
    ref: str


class FacetAssertion(TypedDict):
    """Facet assertion with basis, value, source, confidence, and conflicts."""

    value: Any
    basis: Literal["observed", "reported", "inferred", "unknown"]
    source: NotRequired[FacetSource]
    confidence: NotRequired[Literal["low", "medium", "high"]]
    conflicts: NotRequired[list[FacetAssertion]]


class CostProfile(TypedDict):
    """Implementation and compute cost categories."""

    implementation: Literal["low", "medium", "high", "unknown"]
    compute: Literal["low", "medium", "high", "unknown"]


class SourceLicense(TypedDict):
    """License metadata for an external research source."""

    status: Literal["permissive", "restricted", "unknown"]
    identifier: str | None
    attribution: str | None


class Source(TypedDict):
    """Source entity representing an external artifact or reference."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["source"]
    source_id: str
    kind: Literal[
        "writeup",
        "competition_page",
        "forum_post",
        "notebook",
        "paper",
        "repository",
        "openml_run",
        "local_result",
        "synthetic",
    ]
    canonical_ref: str
    license: SourceLicense
    snapshot_id: str
    content_sha256: str
    published_at: NotRequired[str | None]
    mirrors: NotRequired[list[str]]


class Document(TypedDict):
    """Document entity representing normalized text derived from a Source."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["document"]
    document_id: str
    source_id: str
    snapshot_id: str
    section: str
    content_sha256: str
    normalization_version: str
    title: NotRequired[str | None]


class ProvenanceExtracted(TypedDict):
    origin: Literal["extracted"]
    source_content_sha256: str
    provider: str
    requested_model: str
    served_model: str
    prompt_version: str
    prompt_hash: str
    schema_version: str
    extractor_version: str
    extracted_at: str
    fallback_served: NotRequired[bool]


class ProvenanceHuman(TypedDict):
    origin: Literal["human"]
    source_content_sha256: str
    author_ref: str
    authored_at: str


class ProvenanceSynthetic(TypedDict):
    origin: Literal["synthetic"]
    source_content_sha256: str
    fixture_id: str


Provenance = ProvenanceExtracted | ProvenanceHuman | ProvenanceSynthetic


class Attempt(TypedDict):
    """Attempt entity capturing an experimental intervention and quantitative outcome."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["attempt"]
    attempt_id: str
    problem_id: str
    document_id: str
    recipe_id: str | None
    raw_method_name: str
    baseline_method: str | None
    candidate_method: str
    configuration: dict[str, Any]
    validation_protocol: str | None
    evaluation_scope: Literal["cv", "public_lb", "private_lb", "holdout"] | None
    metric_name: str | None
    metric_direction: Literal["minimize", "maximize"] | None
    baseline_value: float | int | None
    candidate_value: float | int | None
    reported_delta: float | int | None
    joint_change: bool
    joint_changes: list[str]
    outcome: Literal["positive", "negative", "neutral", "mixed", "unclear"]
    confounders: list[str]
    provenance: Provenance
    metric_k: NotRequired[int | None]


class EvidenceComparison(TypedDict):
    baseline: str
    candidate: str


class Evidence(TypedDict):
    """Evidence entity pointing to a verbatim document span supporting an Attempt."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["evidence"]
    evidence_id: str
    attempt_id: str
    document_id: str
    type: Literal[
        "controlled_ablation",
        "reported_gain",
        "reported_failure",
        "used_in_solution",
        "attempted",
        "author_opinion",
        "independently_reproduced",
    ]
    outcome: Literal["positive", "negative", "neutral", "mixed", "unclear"]
    quote: str
    char_start: int
    char_end: int
    uncertainty: list[str]
    comparison: EvidenceComparison | None
    provenance: Provenance


class MatchAssessment(TypedDict):
    owner_type: Literal["recipe", "problem_profile"]
    owner_id: str
    condition_id: str
    facet: str
    state: Literal["satisfied", "violated", "unknown"]
    reason: str


class ProposalMatch(TypedDict):
    level: Literal["L1", "L2", "L3", "L4"]
    transfer_risk: Literal["low", "medium", "high", "unknown"]
    assessments: list[MatchAssessment]


class EvaluationContract(TypedDict):
    protocol_id: str | None
    protocol_sha256: str | None
    argv: list[str] | None
    metric: str | None
    acceptance_rule: str | None
    preflight_evidence: list[dict[str, Any]] | None


class DataContract(TypedDict):
    scope_ids: list[str] | None
    phase: Literal["exploratory", "independent_confirmation"] | None
    candidate_fingerprint: str | None
    observation_revision: int | None


class ResourceContract(TypedDict):
    kind: str
    unit: str
    planned: float | int | None
    verification: Literal["verified", "unverified"]
    enforcement: Literal["executor_enforced", "declared_only", "unknown"]
    actual: NotRequired[float | int]
    source: NotRequired[str]


class ExperimentContract(TypedDict):
    contract_version: Literal[1]
    question: str
    interventions: list[str]
    fixed_controls: list[str]
    expected_evidence: list[str]
    disconfirmation: list[str]
    confounders: list[str]
    evaluation: EvaluationContract
    data: DataContract
    resources: list[ResourceContract] | None
    failure_policy: Literal["stop_pending", "continue_independent"] | None
    extensions: dict[str, Any]


class ExperimentProposal(TypedDict):
    """Experiment Proposal entity encapsulating candidate interventions and execution contracts."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["experiment_proposal"]
    proposal_id: str
    profile_id: str
    recipe_id: str
    evidence_ids: list[str]
    review_status: Literal["requires_lead_review"]
    match: ProposalMatch
    experiment_contract: ExperimentContract


class ProblemProfile(TypedDict):
    """Problem Profile entity representing research constraints and problem characteristics."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["problem_profile"]
    profile_id: str
    problem_id: str
    vocabulary_version: Literal["2.0.0"]
    facets: dict[str, FacetAssertion]
    hard_constraints: list[Condition]


class Recipe(TypedDict):
    """Recipe entity defining a candidate technique intervention."""

    schema_version: Literal["2.0.0"]
    entity_type: Literal["recipe"]
    recipe_id: str
    canonical_name: str
    aliases: list[str]
    vocabulary_version: Literal["2.0.0"]
    taxonomy_version: Literal["2.0.0"]
    action_type: Literal[
        "data_preparation",
        "feature_engineering",
        "model_choice",
        "training",
        "validation",
        "ensemble",
        "prediction",
    ]
    action: str
    description: str
    applicability: list[Condition]
    preconditions: list[Condition]
    hard_constraints: list[Condition]
    contraindications: list[str]
    configuration: dict[str, Any]
    implementation_refs: list[str]
    expected_effect: list[str]
    cost_profile: CostProfile
