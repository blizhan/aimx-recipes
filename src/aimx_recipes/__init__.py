"""aimx-recipes: Core schemas, facet vocabulary, and offline contract validation."""

from aimx_recipes.contextual import validate_bundle
from aimx_recipes.diagnostics import render_text
from aimx_recipes.models import (
    Attempt,
    Diagnostic,
    Document,
    Evidence,
    ExperimentProposal,
    ParseResult,
    Problem,
    ProblemProfile,
    Recipe,
    Source,
    ValidationContext,
    ValidationResult,
)
from aimx_recipes.validation import parse_record, validate_record

__version__ = "0.1.0"

__all__ = [
    "Attempt",
    "Diagnostic",
    "Document",
    "Evidence",
    "ExperimentProposal",
    "ParseResult",
    "Problem",
    "ProblemProfile",
    "Recipe",
    "Source",
    "ValidationContext",
    "ValidationResult",
    "parse_record",
    "render_text",
    "validate_bundle",
    "validate_record",
]
