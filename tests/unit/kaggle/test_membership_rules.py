"""Unit tests for P0 membership rules and reviewed list loading."""

import pytest
from aimx_recipes.cli.output import (
    ERR_REVIEWED_LIST_INVALID,
    ERR_REVIEWED_LIST_SLUG_MISMATCH,
    ERR_REVIEWED_LIST_UNKNOWN_COMPETITION,
    ERR_RULE_FILE_INVALID,
)
from aimx_recipes.sources.kaggle.membership import (
    MembershipError,
    load_and_validate_reviewed_list,
    load_and_validate_rule_file,
)


def test_packaged_rule_and_reviewed_list_validate():
    rule = load_and_validate_rule_file()
    assert rule["rule_version"] == "1.0.0"
    assert "tag_rule" in rule
    assert "heuristic" in rule

    reviewed = load_and_validate_reviewed_list()
    assert "entries" in reviewed
    assert isinstance(reviewed["entries"], list)


def test_strict_yaml_duplicate_keys():
    bad_rule_yaml = """
    rule_version: "1.0.0"
    rule_version: "2.0.0"
    """
    with pytest.raises(MembershipError) as exc_info:
        load_and_validate_rule_file(text_or_path=bad_rule_yaml)
    assert exc_info.value.code == ERR_RULE_FILE_INVALID

    bad_reviewed_yaml = """
    entries: []
    entries: []
    """
    with pytest.raises(MembershipError) as exc_info:
        load_and_validate_reviewed_list(text_or_path=bad_reviewed_yaml)
    assert exc_info.value.code == ERR_REVIEWED_LIST_INVALID


def test_invalid_reviewed_list_entries():
    # Bad decision
    bad_decision_yaml = """
    entries:
      - competition_id: "101"
        slug: "comp-101"
        decision: "maybe"
        reason: "reason"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(text_or_path=bad_decision_yaml)
    assert exc.value.code == ERR_REVIEWED_LIST_INVALID

    # Duplicate competition_id
    duplicate_comp_yaml = """
    entries:
      - competition_id: "101"
        slug: "comp-101"
        decision: "include"
        reason: "reason"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
      - competition_id: "101"
        slug: "comp-101"
        decision: "exclude"
        reason: "reason 2"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(text_or_path=duplicate_comp_yaml)
    assert exc.value.code == ERR_REVIEWED_LIST_INVALID


def test_cross_check_unknown_competition_and_slug_mismatch():
    known_comps = {
        101: "comp-101-tag-in",
    }
    # Unknown competition
    unknown_yaml = """
    entries:
      - competition_id: "999"
        slug: "comp-999"
        decision: "include"
        reason: "reason"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(
            text_or_path=unknown_yaml, known_competitions=known_comps
        )
    assert exc.value.code == ERR_REVIEWED_LIST_UNKNOWN_COMPETITION

    # Slug mismatch
    slug_mismatch_yaml = """
    entries:
      - competition_id: "101"
        slug: "wrong-slug"
        decision: "include"
        reason: "reason"
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(
            text_or_path=slug_mismatch_yaml, known_competitions=known_comps
        )
    assert exc.value.code == ERR_REVIEWED_LIST_SLUG_MISMATCH


def test_blank_reason_or_reviewed_by_rejected():
    known_comps = {101: "comp-101-tag-in"}
    blank_reason_yaml = """
    entries:
      - competition_id: "101"
        slug: "comp-101-tag-in"
        decision: "include"
        reason: "   "
        reviewed_by: "curator"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(
            text_or_path=blank_reason_yaml, known_competitions=known_comps
        )
    assert exc.value.code == ERR_REVIEWED_LIST_INVALID

    blank_reviewer_yaml = """
    entries:
      - competition_id: "101"
        slug: "comp-101-tag-in"
        decision: "include"
        reason: "Valid reason"
        reviewed_by: "   \t"
        reviewed_on: "2026-11-03"
    """
    with pytest.raises(MembershipError) as exc:
        load_and_validate_reviewed_list(
            text_or_path=blank_reviewer_yaml, known_competitions=known_comps
        )
    assert exc.value.code == ERR_REVIEWED_LIST_INVALID
