"""Unit tests for the strict YAML loader."""

import pytest
from aimx_recipes.yaml_strict import StrictYAMLError, load_strict_yaml


def test_yaml_strict_duplicate_key(tmp_path):
    yaml_text = """
    key1: value1
    key1: value2
    """
    with pytest.raises(StrictYAMLError) as exc_info:
        load_strict_yaml(yaml_text)
    # Check that error includes line and column information
    assert "line" in str(exc_info.value).lower() or exc_info.value.line is not None


def test_yaml_strict_scalars_as_strings():
    yaml_text = """
    no_val: no
    yes_val: yes
    on_val: on
    octal_val: 0123
    float_val: 1e3
    date_val: 2026-11-03
    bool_val: true
    """
    res = load_strict_yaml(yaml_text)
    assert res["no_val"] == "no"
    assert res["yes_val"] == "yes"
    assert res["on_val"] == "on"
    assert res["octal_val"] == "0123"
    assert res["float_val"] == "1e3"
    assert res["date_val"] == "2026-11-03"
    assert res["bool_val"] == "true"


def test_yaml_strict_null_loads_as_none():
    yaml_text = """
    null_val: null
    tilde_val: ~
    """
    res = load_strict_yaml(yaml_text)
    assert res["null_val"] is None
    assert res["tilde_val"] is None


def test_yaml_strict_nested_structures():
    yaml_text = """
    a:
      - item1
      - b: subval
    """
    res = load_strict_yaml(yaml_text)
    assert res == {"a": ["item1", {"b": "subval"}]}


def test_yaml_strict_non_string_keys_rejected():
    yaml_text = """
    null: value
    """
    with pytest.raises(StrictYAMLError):
        load_strict_yaml(yaml_text)

    yaml_text_seq = """
    [1, 2]: value
    """
    with pytest.raises(StrictYAMLError):
        load_strict_yaml(yaml_text_seq)


def test_yaml_strict_custom_python_tags_rejected():
    yaml_text = """
    obj: !!python/object/apply:os.system ["ls"]
    """
    with pytest.raises(StrictYAMLError):
        load_strict_yaml(yaml_text)


def test_yaml_strict_load_from_path(tmp_path):
    p = tmp_path / "test.yaml"
    p.write_text("hello: world\n", encoding="utf-8")
    assert load_strict_yaml(p) == {"hello": "world"}
