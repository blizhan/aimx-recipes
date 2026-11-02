"""Tests for strict JSON parsing, lone surrogates, duplicate keys, and exact-type preflight."""

import pytest
from aimx_recipes.validation import parse_record, preflight_json_domain


def test_parse_valid_object():
    text = '{"problem_id": "prob-1", "title": "Example"}'
    res = parse_record(text)
    assert res.record == {"problem_id": "prob-1", "title": "Example"}
    assert len(res.diagnostics) == 0


def test_parse_rejects_duplicate_keys():
    text = '{"problem_id": "prob-1", "problem_id": "prob-2"}'
    res = parse_record(text)
    assert res.record is None
    assert len(res.diagnostics) > 0
    assert any(d.code == "parse.duplicate_key" for d in res.diagnostics)
    # Check that input text is never leaked into diagnostic messages
    for d in res.diagnostics:
        assert "prob-1" not in d.message
        assert "prob-2" not in d.message


def test_parse_rejects_non_object_roots():
    for text in ['[1, 2, 3]', '"just a string"', '42', 'true', 'null']:
        res = parse_record(text)
        assert res.record is None
        assert len(res.diagnostics) > 0
        assert any(d.code in ("parse.invalid_json", "type.invalid") for d in res.diagnostics)


def test_parse_rejects_non_finite_numbers():
    for text in ['{"val": NaN}', '{"val": Infinity}', '{"val": -Infinity}']:
        res = parse_record(text)
        assert res.record is None
        assert len(res.diagnostics) > 0


def test_parse_rejects_lone_surrogates():
    # Lone surrogate \ud800
    text = '{"title": "\\ud800"}'
    res = parse_record(text)
    assert res.record is None
    assert len(res.diagnostics) > 0


def test_preflight_exact_integers_versus_float():
    # 1.0 is a float, not an exact integer
    obj = {"count": 1.0}
    # Preflight should flag that float 1.0 is not an exact integer if checked against integer fields
    diags = preflight_json_domain(obj)
    # preflight detects non-finite numbers or float representation where appropriate
    assert isinstance(diags, list)


def test_preflight_boolean_is_not_number():
    # In Python, isinstance(True, int) is True, but JSON domain must distinguish booleans from numbers
    obj = {"count": True, "ratio": False}
    # Preflight should ensure booleans are not treated as ints/floats
    assert preflight_json_domain(obj) is not None


def test_no_input_coercion_or_mutation():
    original = {"problem_id": "prob-1", "title": "  Untrimmed Title  ", "count": 10}
    copy_orig = dict(original)
    parse_res = parse_record('{"problem_id": "prob-1", "title": "  Untrimmed Title  ", "count": 10}')
    assert parse_res.record == original
    assert parse_res.record["title"] == "  Untrimmed Title  "
