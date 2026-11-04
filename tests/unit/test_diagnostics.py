"""Tests for diagnostic construction, sorting, JSON Pointer escaping, error-over-incomplete precedence, and text rendering."""

from aimx_recipes.models import Diagnostic
from aimx_recipes.diagnostics import (
    escape_pointer,
    render_text,
    sort_and_deduplicate_diagnostics,
    build_validation_result,
)


def test_escape_pointer():
    assert escape_pointer([]) == ""
    assert escape_pointer(["foo"]) == "/foo"
    assert escape_pointer(["foo", "bar"]) == "/foo/bar"
    # RFC 6901 escaping: ~ -> ~0, / -> ~1
    assert escape_pointer(["a/b", "c~d"]) == "/a~1b/c~0d"
    assert escape_pointer([0, "items"]) == "/0/items"


def test_diagnostic_sorting_and_deduplication():
    d1 = Diagnostic(
        entity_type="problem",
        record_id="prob-1",
        input_index=0,
        pointer="/title",
        code="field.required",
        message="Required field is missing.",
        check="required",
        severity="error",
    )
    d2 = Diagnostic(
        entity_type=None,
        record_id=None,
        input_index=0,
        pointer="",
        code="parse.invalid_json",
        message="Invalid JSON syntax.",
        check="json_syntax",
        severity="error",
    )
    d3 = Diagnostic(
        entity_type="problem",
        record_id="prob-1",
        input_index=0,
        pointer="/kind",
        code="value.invalid",
        message="Value is invalid.",
        check="enum",
        severity="error",
    )
    # Duplicate of d1
    d4 = Diagnostic(
        entity_type="problem",
        record_id="prob-1",
        input_index=0,
        pointer="/title",
        code="field.required",
        message="Required field is missing.",
        check="required",
        severity="error",
    )

    sorted_diags = sort_and_deduplicate_diagnostics([d1, d2, d3, d4])
    assert len(sorted_diags) == 3
    # Sorting key: (entity_type or '', record_id or '', input_index, pointer, code, check, severity)
    # d2 has entity_type="", record_id="" -> should come first
    assert sorted_diags[0] == d2
    assert sorted_diags[1] == d3  # pointer /kind < /title
    assert sorted_diags[2] == d1


def test_error_over_incomplete_precedence():
    d_error = Diagnostic(
        entity_type="problem",
        record_id="prob-1",
        input_index=0,
        pointer="/title",
        code="field.required",
        message="Missing title.",
        check="required",
        severity="error",
    )
    d_incomplete = Diagnostic(
        entity_type="evidence",
        record_id="ev-1",
        input_index=1,
        pointer="/quote",
        code="context.document_text_missing",
        message="Missing document text.",
        check="quote_span",
        severity="incomplete",
    )

    # When both error and incomplete are present, status MUST be 'invalid'
    res = build_validation_result(
        level="contextual",
        diagnostics=[d_error, d_incomplete],
        structurally_valid=False,
        contextual_complete=False,
    )
    assert res.status == "invalid"
    assert res.structurally_valid is False
    assert res.contextual_complete is False
    assert len(res.diagnostics) == 2

    # When only incomplete is present
    res_inc = build_validation_result(
        level="contextual",
        diagnostics=[d_incomplete],
        structurally_valid=True,
        contextual_complete=False,
    )
    assert res_inc.status == "incomplete"
    assert res_inc.structurally_valid is True
    assert res_inc.contextual_complete is False


def test_render_text_verdict_matches_json():
    diag = Diagnostic(
        entity_type="problem",
        record_id="prob-1",
        input_index=0,
        pointer="/kind",
        code="value.invalid",
        message="Value is invalid.",
        check="enum",
        severity="error",
    )
    res = build_validation_result(
        level="structural",
        diagnostics=[diag],
        structurally_valid=False,
        contextual_complete=False,
    )
    text_out = render_text(res)
    assert "Status: invalid" in text_out
    assert "Level: structural" in text_out
    assert "value.invalid" in text_out
    assert "/kind" in text_out
    assert "prob-1" in text_out
    # No ANSI escape codes
    assert "\033" not in text_out
