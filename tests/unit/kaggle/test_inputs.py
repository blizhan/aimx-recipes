"""Unit tests for Meta Kaggle input verification and CSV loading."""

import pytest
from aimx_recipes.cli.output import (
    ERR_COLUMN_MISSING,
    ERR_CSV_MALFORMED,
    ERR_INPUT_CHANGED,
    ERR_INPUT_MISSING,
)
from aimx_recipes.sources.kaggle.inputs import (
    InputError,
    create_input_views,
    verify_inputs,
    verify_stat_after,
)
from aimx_recipes.sources.kaggle.snapshot import open_session


def test_missing_input_file(tmp_path):
    # Empty dir
    with pytest.raises(InputError) as exc_info:
        verify_inputs(tmp_path)
    assert exc_info.value.code == ERR_INPUT_MISSING
    assert exc_info.value.file in [
        "Competitions.csv",
        "Teams.csv",
        "ForumTopics.csv",
        "ForumMessages.csv",
        "Tags.csv",
        "CompetitionTags.csv",
    ]


def test_missing_required_column(kaggle_fixture_dir):
    # Rename a required column in Competitions.csv: Overview -> OverviewRenamed
    comp_path = kaggle_fixture_dir / "Competitions.csv"
    lines = comp_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header = lines[0].replace('"Overview"', '"OverviewRenamed"')
    comp_path.write_text(header + "".join(lines[1:]), encoding="utf-8")

    with pytest.raises(InputError) as exc_info:
        verify_inputs(kaggle_fixture_dir)
    assert exc_info.value.code == ERR_COLUMN_MISSING
    assert exc_info.value.file == "Competitions.csv"
    assert exc_info.value.column == "Overview"


def test_extra_upstream_columns_tolerated(kaggle_fixture_dir):
    # Add an extra column to Tags.csv
    tags_path = kaggle_fixture_dir / "Tags.csv"
    lines = tags_path.read_text(encoding="utf-8").splitlines(keepends=True)
    header = lines[0].rstrip("\r\n") + ',"ExtraColumn"\r\n'
    new_lines = [header]
    for row in lines[1:]:
        new_lines.append(row.rstrip("\r\n") + ',"extra_val"\r\n')
    tags_path.write_text("".join(new_lines), encoding="utf-8")

    inputs = verify_inputs(kaggle_fixture_dir)
    assert len(inputs) == 6
    con = open_session()
    row_counts = create_input_views(con, kaggle_fixture_dir, inputs)
    assert row_counts["Tags.csv"] == 10
    con.close()


def test_malformed_csv_unterminated_quote(kaggle_fixture_dir):
    # Introduce an unterminated quote in ForumMessages.csv
    msg_path = kaggle_fixture_dir / "ForumMessages.csv"
    content = msg_path.read_text(encoding="utf-8")
    # Break a quote on a row
    broken = content.replace('"UNIQUE_MARKER_1001_MD', "UNIQUE_MARKER_1001_MD")
    msg_path.write_text(broken, encoding="utf-8")

    inputs = verify_inputs(kaggle_fixture_dir)
    con = open_session()
    with pytest.raises(InputError) as exc_info:
        create_input_views(con, kaggle_fixture_dir, inputs)
    assert exc_info.value.code == ERR_CSV_MALFORMED
    assert exc_info.value.file == "ForumMessages.csv"
    # Ensure error message does not leak the marker string
    assert "UNIQUE_MARKER_1001_MD" not in str(exc_info.value)
    con.close()


def test_input_changed_during_run(kaggle_fixture_dir):
    inputs = verify_inputs(kaggle_fixture_dir)
    # Modify a file after stat before
    teams_path = kaggle_fixture_dir / "Teams.csv"
    teams_path.write_text(
        teams_path.read_text(encoding="utf-8") + "\r\n", encoding="utf-8"
    )

    with pytest.raises(InputError) as exc_info:
        verify_stat_after(inputs)
    assert exc_info.value.code == ERR_INPUT_CHANGED
    assert exc_info.value.file == "Teams.csv"


def test_fingerprints_recorded_for_all_six_files(kaggle_fixture_dir):
    inputs = verify_inputs(kaggle_fixture_dir)
    assert len(inputs) == 6
    for inp in inputs:
        assert inp.name in [
            "Competitions.csv",
            "Teams.csv",
            "ForumTopics.csv",
            "ForumMessages.csv",
            "Tags.csv",
            "CompetitionTags.csv",
        ]
        assert inp.size_bytes > 0
        assert len(inp.sha256) == 64
        assert inp.row_count is None or inp.row_count >= 0
