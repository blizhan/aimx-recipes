"""Unit tests for writeup resolution, competition context, and normalization."""

from datetime import datetime
import pytest
from aimx_recipes.sources.kaggle.inputs import (
    create_input_views,
    verify_inputs,
)
from aimx_recipes.sources.kaggle.normalize import (
    map_medal,
    normalize_competition_row,
    normalize_writeup_row,
    parse_kaggle_datetime,
)
from aimx_recipes.sources.kaggle.resolve import (
    resolve_competition_context,
    resolve_writeup_references,
)
from aimx_recipes.sources.kaggle.snapshot import open_session


@pytest.fixture
def manifest_mini(load_fixture) -> dict:
    return load_fixture("kaggle/manifest.json")


def test_resolve_dispositions_and_exclusions(kaggle_fixture_dir, manifest_mini):
    inputs = verify_inputs(kaggle_fixture_dir)
    con = open_session()
    create_input_views(con, kaggle_fixture_dir, inputs)

    refs = resolve_writeup_references(con)
    # Check counts match manifest
    assert len(refs) == manifest_mini["counts"]["writeup_refs"]

    by_topic = {r["topic_id"]: r for r in refs}
    assert by_topic[1001]["disposition"] == "ingested"
    assert by_topic[9999]["disposition"] == "excluded"
    assert by_topic[9999]["exclusion_reason"] == "topic_not_found"
    assert by_topic[1007]["disposition"] == "excluded"
    assert by_topic[1007]["exclusion_reason"] == "first_message_missing"
    assert by_topic[1008]["disposition"] == "excluded"
    assert by_topic[1008]["exclusion_reason"] == "message_not_found"
    assert by_topic[1009]["disposition"] == "excluded"
    assert by_topic[1009]["exclusion_reason"] == "empty_text"
    con.close()


def test_body_selection_and_short_flag(kaggle_fixture_dir, manifest_mini):
    inputs = verify_inputs(kaggle_fixture_dir)
    con = open_session()
    create_input_views(con, kaggle_fixture_dir, inputs)
    refs = resolve_writeup_references(con)

    by_topic = {r["topic_id"]: r for r in refs if r["disposition"] == "ingested"}
    # 1001: markdown preferred over html
    w1001 = normalize_writeup_row(by_topic[1001])
    assert w1001["body_format"] == "markdown"
    assert w1001["is_short"] is False

    # 1003: html only
    w1003 = normalize_writeup_row(by_topic[1003])
    assert w1003["body_format"] == "html"
    assert w1003["is_short"] is False

    # 1004: 199 code points -> short
    w1004 = normalize_writeup_row(by_topic[1004])
    assert w1004["char_count"] == 199
    assert w1004["is_short"] is True

    # 1005: 200 code points with non-ascii -> not short
    w1005 = normalize_writeup_row(by_topic[1005])
    assert w1005["char_count"] == 200
    assert w1005["is_short"] is False
    con.close()


def test_date_parsing():
    dt = parse_kaggle_datetime("04/15/2024 23:59:00")
    assert dt == datetime(2024, 4, 15, 23, 59, 0)

    from aimx_recipes.sources.kaggle.normalize import DateParseError

    with pytest.raises(DateParseError):
        parse_kaggle_datetime("invalid-date-string")


def test_medal_mapping():
    assert map_medal("1") == "gold"
    assert map_medal("2") == "silver"
    assert map_medal("3") == "bronze"
    assert map_medal("0") is None
    assert map_medal("") is None
    assert map_medal(None) is None


def test_competition_context_resolution(kaggle_fixture_dir):
    inputs = verify_inputs(kaggle_fixture_dir)
    con = open_session()
    create_input_views(con, kaggle_fixture_dir, inputs)

    comps = resolve_competition_context(con)
    by_id = {c["competition_id"]: c for c in comps}

    # 101: LogLoss (non-numeric abbr), higher_is_better False, tag 14101
    c101 = normalize_competition_row(by_id[101])
    assert c101["metric_label"] == "LogLoss"
    assert c101["higher_is_better"] is False
    assert c101["tag_ids"] == ["14101"]
    assert c101["tag_names"] == ["tabular"]
    assert c101["competition_data_license"] == "CC BY-SA 4.0"

    # 104: numeric abbr 99999 -> fallback to EvaluationAlgorithmName
    c104 = normalize_competition_row(by_id[104])
    assert c104["metric_label"] == "Santa Optimization Metric"

    con.close()


def test_missing_and_invalid_metric_direction_and_date():
    import pytest
    from aimx_recipes.sources.kaggle.normalize import DateParseError

    # Absent metric direction remains None (not disguised as False)
    comp_missing_dir = normalize_competition_row(
        {"competition_id": 999, "slug": "slug-missing-dir", "eval_is_max": None}
    )
    assert comp_missing_dir["higher_is_better"] is None

    comp_empty_dir = normalize_competition_row(
        {"competition_id": 999, "slug": "slug-empty-dir", "eval_is_max": "   "}
    )
    assert comp_empty_dir["higher_is_better"] is None

    # Invalid metric direction explicitly raises DateParseError with column and file
    with pytest.raises(DateParseError) as exc_info:
        normalize_competition_row(
            {"competition_id": 999, "slug": "slug-bad", "eval_is_max": "INVALID_BOOL"}
        )
    assert exc_info.value.column == "EvaluationAlgorithmIsMax"
    assert exc_info.value.file == "Competitions.csv"
    assert exc_info.value.record_id == "999"

    # Bad date raises DateParseError with column and record_id, without leaking text
    with pytest.raises(DateParseError) as exc_date:
        normalize_competition_row(
            {
                "competition_id": 999,
                "slug": "slug-bad-date",
                "enabled_date": "CORRUPT_DATE_MARKER",
            }
        )
    assert exc_date.value.column == "EnabledDate"
    assert exc_date.value.file == "Competitions.csv"
    assert "CORRUPT_DATE_MARKER" not in exc_date.value.message
