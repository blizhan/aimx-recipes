"""Diagnostic helpers, pointer escaping, diagnostic sorting, and text rendering."""

from __future__ import annotations

import unicodedata
from typing import Literal, Sequence
from aimx_recipes.models import Diagnostic, ValidationResult


def escape_pointer(parts: Sequence[str | int]) -> str:
    """Format path parts into an RFC 6901 JSON Pointer string."""
    if not parts:
        return ""
    escaped = []
    for part in parts:
        s = str(part)
        s = s.replace("~", "~0").replace("/", "~1")
        escaped.append(s)
    return "/" + "/".join(escaped)


def sort_and_deduplicate_diagnostics(
    diagnostics: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Sort diagnostics by documented key and collapse exact duplicates."""
    seen: set[tuple[str | None, str | None, int, str, str, str, str, str]] = set()
    unique_diags: list[Diagnostic] = []
    for d in diagnostics:
        key = (
            d.entity_type,
            d.record_id,
            d.input_index,
            d.pointer,
            d.code,
            d.message,
            d.check,
            d.severity,
        )
        if key not in seen:
            seen.add(key)
            unique_diags.append(d)

    return sorted(unique_diags, key=lambda d: d.sort_key())


def build_validation_result(
    level: Literal["structural", "contextual"],
    diagnostics: Sequence[Diagnostic],
    structurally_valid: bool = True,
    contextual_complete: bool = False,
    result_version: str = "2.0.0",
) -> ValidationResult:
    """Construct a canonical ValidationResult enforcing error-over-incomplete precedence."""
    sorted_diags = sort_and_deduplicate_diagnostics(diagnostics)

    has_error = any(d.severity == "error" for d in sorted_diags)
    has_incomplete = any(d.severity == "incomplete" for d in sorted_diags)

    if has_error:
        status: Literal["valid", "invalid", "incomplete"] = "invalid"
        structurally_valid = False
        contextual_complete = False
    elif has_incomplete:
        status = "incomplete"
        # Incomplete bundle checks mean contextual_complete is False
        contextual_complete = False
    else:
        status = "valid"
        if level == "contextual":
            structurally_valid = True
            contextual_complete = True
        else:
            structurally_valid = True
            contextual_complete = False

    return ValidationResult(
        result_version=result_version,
        level=level,
        status=status,
        structurally_valid=structurally_valid,
        contextual_complete=contextual_complete,
        diagnostics=sorted_diags,
    )


def _display(value: str) -> str:
    """Escape control, formatting, and surrogate characters in dynamic fields."""
    return "".join(
        char.encode("unicode_escape").decode("ascii")
        if unicodedata.category(char).startswith("C")
        else char
        for char in value
    )


def render_text(result: ValidationResult) -> str:
    """Render a deterministic, human-readable summary of ValidationResult without ANSI escapes."""
    lines = [
        f"Validation Result (v{result.result_version})",
        f"Level: {result.level}",
        f"Status: {result.status}",
        f"Structurally Valid: {result.structurally_valid}",
        f"Contextual Complete: {result.contextual_complete}",
    ]

    if not result.diagnostics:
        lines.append("Diagnostics: none")
    else:
        lines.append(f"Diagnostics ({len(result.diagnostics)}):")
        for d in result.diagnostics:
            entity_part = f"[{d.entity_type or 'unknown'}:{d.record_id or 'unknown'}]"
            lines.append(
                f"  - {d.severity.upper()} {entity_part} pointer={d.pointer or '<root>'} "
                f"code={d.code} check={d.check}: {d.message}"
            )

    return "\n".join(_display(line) for line in lines)
