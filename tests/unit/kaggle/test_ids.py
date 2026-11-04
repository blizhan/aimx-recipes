"""Unit tests for identifier builders and version constants."""

import re
from aimx_recipes.sources.kaggle import ADAPTER_VERSION, NORMALIZATION_VERSION
from aimx_recipes.sources.kaggle.normalize import (
    competition_document_id,
    competition_source_id,
    membership_id,
    problem_id,
    snapshot_id,
    writeup_document_id,
    writeup_source_id,
)

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


def test_version_constants():
    assert ADAPTER_VERSION == "1.0.0"
    assert NORMALIZATION_VERSION == "kaggle-text-1"


def test_writeup_and_competition_source_ids():
    w_id = writeup_source_id(1001)
    assert w_id == "kaggle:writeup:1001"
    assert ID_PATTERN.match(w_id)

    c_id = competition_source_id(101)
    assert c_id == "kaggle:competition:101"
    assert ID_PATTERN.match(c_id)


def test_document_ids():
    text = "Hello world solution"
    w_doc_id = writeup_document_id(1001, text)
    assert w_doc_id.startswith("kaggle:writeup:1001:body:")
    assert len(w_doc_id.split(":")[-1]) == 12
    assert ID_PATTERN.match(w_doc_id)

    c_doc_id = competition_document_id(101, "competition_overview", text)
    assert c_doc_id.startswith("kaggle:competition:101:competition_overview:")
    assert len(c_doc_id.split(":")[-1]) == 12
    assert ID_PATTERN.match(c_doc_id)


def test_problem_id():
    p_id = problem_id(101)
    assert p_id == "kaggle:problem:101"
    assert ID_PATTERN.match(p_id)


def test_snapshot_id_stability_and_order_independence():
    inputs1 = [
        {"name": "Teams.csv", "sha256": "aaaa"},
        {"name": "Competitions.csv", "sha256": "bbbb"},
    ]
    inputs2 = [
        {"name": "Competitions.csv", "sha256": "bbbb"},
        {"name": "Teams.csv", "sha256": "aaaa"},
    ]
    s1 = snapshot_id(inputs1)
    s2 = snapshot_id(inputs2)
    assert s1 == s2
    assert s1.startswith("meta-kaggle-")
    assert len(s1) == len("meta-kaggle-") + 16
    assert ID_PATTERN.match(s1)


def test_membership_id():
    m_id = membership_id(
        rule_sha256="1111",
        list_sha256="2222",
        snapshot_id_val="meta-kaggle-3333",
    )
    assert m_id.startswith("p0-")
    assert len(m_id) == len("p0-") + 16
    assert ID_PATTERN.match(m_id)
