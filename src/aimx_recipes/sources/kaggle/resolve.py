"""Writeup reference resolution and competition context extraction."""

from typing import Any
import duckdb
from aimx_recipes.cli.output import ERR_CSV_MALFORMED
from aimx_recipes.sources.kaggle.inputs import InputError


def safe_int(
    val: Any,
    file: str,
    column: str,
    record_id: str | None = None,
    line: int | None = None,
) -> int:
    """Safely convert value to int without leaking source string in exception message."""
    try:
        s = str(val).strip()
        return int(s)
    except (ValueError, TypeError):
        raise InputError(
            code=ERR_CSV_MALFORMED,
            file=file,
            column=column,
            record_id=str(record_id) if record_id is not None else None,
            line=line,
            message=f"Invalid integer in column '{column}' of '{file}'",
        ) from None


def resolve_writeup_references(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Semi-join resolution: Teams -> ForumTopics -> ForumMessages.

    Produces one row per team writeup reference with resolution status and dispositions.
    """
    sql = """
    SELECT
        t.Id AS team_id,
        t.CompetitionId AS competition_id,
        t.WriteUpForumTopicId AS topic_id,
        t.Medal AS medal,
        t.PublicLeaderboardRank AS public_rank,
        t.PrivateLeaderboardRank AS private_rank,
        ft.Id AS ft_id,
        ft.Title AS topic_title,
        ft.FirstForumMessageId AS first_message_id,
        fm.Id AS fm_id,
        fm.PostDate AS post_date,
        fm.Message AS message,
        fm.RawMarkdown AS raw_markdown
    FROM v_teams t
    LEFT JOIN v_forumtopics ft ON ft.Id = t.WriteUpForumTopicId
    LEFT JOIN v_forummessages fm ON fm.Id = ft.FirstForumMessageId
    WHERE t.WriteUpForumTopicId IS NOT NULL AND TRIM(t.WriteUpForumTopicId) != ''
    ORDER BY TRY_CAST(t.WriteUpForumTopicId AS BIGINT), TRY_CAST(t.Id AS BIGINT)
    """
    rows = con.execute(sql).fetchall()
    col_names = [desc[0] for desc in con.description]

    results: list[dict[str, Any]] = []
    for r in rows:
        d = dict(zip(col_names, r))
        team_id_raw = d["team_id"]
        team_leading_id = str(team_id_raw) if team_id_raw is not None else None

        team_id_int = safe_int(team_id_raw, file="Teams.csv", column="Id", record_id=team_leading_id)
        comp_id_int = safe_int(d["competition_id"], file="Teams.csv", column="CompetitionId", record_id=team_leading_id)
        topic_id_int = safe_int(d["topic_id"], file="Teams.csv", column="WriteUpForumTopicId", record_id=team_leading_id)

        ft_id = d["ft_id"]
        first_msg_raw = d["first_message_id"]
        fm_id_raw = d["fm_id"]
        raw_md = d["raw_markdown"] or ""
        msg = d["message"] or ""

        # Validate first_message_id if present
        first_msg_int: int | None = None
        if ft_id is not None and first_msg_raw is not None and str(first_msg_raw).strip() != "":
            first_msg_int = safe_int(
                first_msg_raw,
                file="ForumTopics.csv",
                column="FirstForumMessageId",
                record_id=str(topic_id_int),
            )

        # Validate fm_id if present
        fm_id_int: int | None = None
        if fm_id_raw is not None and str(fm_id_raw).strip() != "":
            fm_id_int = safe_int(
                fm_id_raw,
                file="ForumMessages.csv",
                column="Id",
                record_id=str(first_msg_int or topic_id_int),
            )

        # Determine disposition
        if ft_id is None:
            disposition = "excluded"
            exclusion_reason = "topic_not_found"
            msg_id = None
        elif first_msg_int is None:
            disposition = "excluded"
            exclusion_reason = "first_message_missing"
            msg_id = None
        elif fm_id_int is None:
            disposition = "excluded"
            exclusion_reason = "message_not_found"
            msg_id = first_msg_int
        elif raw_md == "" and msg == "":
            disposition = "excluded"
            exclusion_reason = "empty_text"
            msg_id = fm_id_int
        else:
            disposition = "ingested"
            exclusion_reason = None
            msg_id = fm_id_int

        results.append(
            {
                "team_id": team_id_int,
                "competition_id": comp_id_int,
                "topic_id": topic_id_int,
                "message_id": msg_id,
                "disposition": disposition,
                "exclusion_reason": exclusion_reason,
                "topic_title": d["topic_title"] or "",
                "post_date": d["post_date"],
                "raw_markdown": raw_md,
                "message": msg,
                "medal_raw": d["medal"],
                "public_rank_raw": d["public_rank"],
                "private_rank_raw": d["private_rank"],
            }
        )

    return results


def resolve_competition_context(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Resolve competition context for competitions that have at least one writeup reference."""
    # Competitions with references
    sql_comps = """
    SELECT DISTINCT
        c.Id AS competition_id,
        c.Slug AS slug,
        c.Title AS title,
        c.Subtitle AS subtitle,
        c.HostSegmentTitle AS host_segment,
        c.EnabledDate AS enabled_date,
        c.DeadlineDate AS deadline_date,
        c.Overview AS overview,
        c.EvaluationAlgorithmDescription AS eval_desc,
        c.DatasetDescription AS dataset_desc,
        c.EvaluationAlgorithmAbbreviation AS eval_abbr,
        c.EvaluationAlgorithmName AS eval_name,
        c.EvaluationAlgorithmIsMax AS eval_is_max,
        c.LicenseName AS license_name
    FROM v_competitions c
    JOIN (
        SELECT DISTINCT CompetitionId
        FROM v_teams
        WHERE WriteUpForumTopicId IS NOT NULL AND TRIM(WriteUpForumTopicId) != ''
    ) t ON t.CompetitionId = c.Id
    ORDER BY TRY_CAST(c.Id AS BIGINT)
    """
    comp_rows = con.execute(sql_comps).fetchall()
    comp_cols = [desc[0] for desc in con.description]

    # Tags for these competitions (check for dangling foreign keys)
    sql_tags = """
    SELECT
        ct.CompetitionId AS competition_id,
        ct.TagId AS tag_id,
        t.Id AS matched_tag_id,
        t.Name AS tag_name
    FROM v_competitiontags ct
    LEFT JOIN v_tags t ON t.Id = ct.TagId
    ORDER BY TRY_CAST(ct.CompetitionId AS BIGINT), TRY_CAST(ct.TagId AS BIGINT)
    """
    tag_rows = con.execute(sql_tags).fetchall()

    # Check for dangling tag references
    for cid_raw, tid_raw, matched_tag_id, tname in tag_rows:
        cid_str = str(cid_raw) if cid_raw is not None else ""
        tid_str = str(tid_raw) if tid_raw is not None else ""
        safe_int(cid_raw, file="CompetitionTags.csv", column="CompetitionId", record_id=cid_str)
        safe_int(tid_raw, file="CompetitionTags.csv", column="TagId", record_id=cid_str)

        if matched_tag_id is None:
            raise InputError(
                code=ERR_CSV_MALFORMED,
                file="CompetitionTags.csv",
                column="TagId",
                record_id=tid_str,
                message=f"Dangling TagId '{tid_str}' in 'CompetitionTags.csv' missing from 'Tags.csv'",
            )

    tags_by_comp: dict[int, list[tuple[str, str]]] = {}
    for cid_raw, tid_raw, matched_tag_id, tname in tag_rows:
        cid_int = int(cid_raw)
        if cid_int not in tags_by_comp:
            tags_by_comp[cid_int] = []
        tags_by_comp[cid_int].append((str(tid_raw), str(tname or "")))

    results: list[dict[str, Any]] = []
    for r in comp_rows:
        d = dict(zip(comp_cols, r))
        cid_raw = d["competition_id"]
        cid_int = safe_int(
            cid_raw,
            file="Competitions.csv",
            column="Id",
            record_id=str(cid_raw) if cid_raw is not None else None,
        )
        tags_list = tags_by_comp.get(cid_int, [])
        # Sort by tag id numerically
        tags_list.sort(key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
        tag_ids = [t[0] for t in tags_list]
        tag_names = [t[1] for t in tags_list]

        results.append(
            {
                "competition_id": cid_int,
                "slug": d["slug"] or "",
                "title": d["title"] or "",
                "subtitle": d["subtitle"] or None,
                "host_segment": d["host_segment"] or None,
                "enabled_date": d["enabled_date"],
                "deadline_date": d["deadline_date"],
                "overview": d["overview"] or None,
                "eval_desc": d["eval_desc"] or None,
                "dataset_desc": d["dataset_desc"] or None,
                "eval_abbr": d["eval_abbr"] or "",
                "eval_name": d["eval_name"] or "",
                "eval_is_max": d["eval_is_max"] or "",
                "license_name": d["license_name"] or None,
                "tag_ids": tag_ids,
                "tag_names": tag_names,
            }
        )

    return results
