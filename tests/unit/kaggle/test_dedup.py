"""Unit tests for writeup whitespace deduplication and mirror resolution."""

from aimx_recipes.sources.kaggle.normalize import (
    build_adapter_tables,
    compute_dedup_key,
)


def test_compute_dedup_key():
    t1 = "  Line 1   \r\n Line  2  "
    t2 = "Line 1 Line 2"
    assert compute_dedup_key(t1) == compute_dedup_key(t2)


def test_dedup_grouping_and_mirrors():
    text1 = "Unique content in writeup 1001"
    text2 = "  Unique  content  in  writeup  1001  "  # duplicate with whitespace
    text3 = "Different content 1003"

    raw_refs = [
        {
            "topic_id": 1002,
            "team_id": 2,
            "competition_id": 102,
            "disposition": "ingested",
            "message_id": 20,
            "raw_markdown": text2,
            "message": "",
        },
        {
            "topic_id": 1001,
            "team_id": 1,
            "competition_id": 101,
            "disposition": "ingested",
            "message_id": 10,
            "raw_markdown": text1,
            "message": "",
        },
        {
            "topic_id": 1003,
            "team_id": 3,
            "competition_id": 101,
            "disposition": "ingested",
            "message_id": 30,
            "raw_markdown": text3,
            "message": "",
        },
    ]

    comps = [
        {"competition_id": 101, "slug": "c101"},
        {"competition_id": 102, "slug": "c102"},
    ]

    c_rows, r_rows, w_rows, d_rows = build_adapter_tables(raw_refs, comps)

    # 1001 is canonical (lowest topic id) even though 1002 appeared first in raw_refs
    by_topic = {r["topic_id"]: r for r in r_rows}
    assert by_topic[1001]["disposition"] == "ingested"
    assert by_topic[1001]["source_id"] == "kaggle:writeup:1001"

    assert by_topic[1002]["disposition"] == "mirror"
    assert by_topic[1002]["source_id"] == "kaggle:writeup:1001"

    # In writeups table: only canonical exists
    w_topics = {w["topic_id"]: w for w in w_rows}
    assert 1001 in w_topics
    assert 1002 not in w_topics
    assert w_topics[1001]["mirror_topic_ids"] == [1002]
    assert w_topics[1001]["dedup_key"] == compute_dedup_key(text1)

    # Stored text in documents is unchanged text1
    d_docs = {d["document_id"]: d for d in d_rows if d["section"] == "writeup_body"}
    assert len(d_docs) == 2  # 1001 and 1003
    doc_1001 = [d for d in d_docs.values() if d["source_id"] == "kaggle:writeup:1001"][
        0
    ]
    assert doc_1001["text"] == text1
