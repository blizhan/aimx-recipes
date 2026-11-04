"""Unit tests for snapshot writer primitives and DuckDB session management."""

import hashlib
import pytest
from aimx_recipes.sources.kaggle.snapshot import (
    atomic_publish,
    canonical_json_line,
    content_sha256,
    is_incomplete_dir,
    open_session,
    write_parquet,
)


def test_session_settings(tmp_path):
    con = open_session(threads=2, memory_limit="1GB", temp_dir=tmp_path)
    # Check TimeZone
    res = con.execute("SELECT current_setting('TimeZone')").fetchall()
    assert res[0][0] == "UTC"
    # Check extensions setting
    res_ai = con.execute(
        "SELECT current_setting('autoinstall_known_extensions')"
    ).fetchall()
    assert str(res_ai[0][0]).lower() == "false"
    res_al = con.execute(
        "SELECT current_setting('autoload_known_extensions')"
    ).fetchall()
    assert str(res_al[0][0]).lower() == "false"
    con.close()


def test_write_parquet_determinism(tmp_path):
    # 10k-row synthetic table with strings, lists, and naive timestamps
    q_create = """
    CREATE TABLE synthetic AS
    SELECT
        i AS id,
        'str_' || (i % 100) AS s_val,
        ['tag_' || (i % 5), 'tag_' || (i % 10)] AS list_val,
        '2024-01-01 00:00:00'::TIMESTAMP + INTERVAL (i) SECOND AS ts_val
    FROM range(10000) tbl(i);
    """
    path_t1 = tmp_path / "t1.parquet"
    path_t4 = tmp_path / "t4.parquet"

    con1 = open_session(threads=1, memory_limit="1GB")
    con1.execute(q_create)
    write_parquet(con1, "SELECT * FROM synthetic", "id", path_t1)
    con1.close()

    con4 = open_session(threads=4, memory_limit="1GB")
    con4.execute(q_create)
    write_parquet(con4, "SELECT * FROM synthetic", "id", path_t4)
    con4.close()

    h1 = hashlib.sha256(path_t1.read_bytes()).hexdigest()
    h4 = hashlib.sha256(path_t4.read_bytes()).hexdigest()
    assert h1 == h4, "Parquet bytes differ across thread counts"


def test_canonical_json_line():
    obj = {"b": 2, "a": "text", "c": [1, 2]}
    line = canonical_json_line(obj)
    assert line == '{"a":"text","b":2,"c":[1,2]}'


def test_content_sha256_order_independence():
    rows1 = [
        {"id": "b", "val": 2},
        {"id": "a", "val": 1},
    ]
    rows2 = [
        {"id": "a", "val": 1},
        {"id": "b", "val": 2},
    ]
    h1 = content_sha256(rows1, key="id")
    h2 = content_sha256(rows2, key="id")
    assert h1 == h2

    # Changes when value changes
    rows3 = [
        {"id": "a", "val": 999},
        {"id": "b", "val": 2},
    ]
    assert content_sha256(rows3, key="id") != h1


def test_atomic_publish_and_incomplete_dir(tmp_path):
    assert is_incomplete_dir(".tmp-12345") is True
    assert is_incomplete_dir("meta-kaggle-12345") is False

    tmp_dir = tmp_path / ".tmp-12345"
    tmp_dir.mkdir()
    (tmp_dir / "test.txt").write_text("hello", encoding="utf-8")

    final_dir = tmp_path / "final-12345"
    atomic_publish(tmp_dir, final_dir)
    assert final_dir.exists()
    assert not tmp_dir.exists()
    assert (final_dir / "test.txt").read_text(encoding="utf-8") == "hello"

    # Publishing again when target exists raises FileExistsError
    new_tmp = tmp_path / ".tmp-67890"
    new_tmp.mkdir()
    with pytest.raises(FileExistsError):
        atomic_publish(new_tmp, final_dir)
