"""R3 independent probes. Mutations are confined to temporary synthetic data."""
import contextlib
import csv
import hashlib
import io
import json
import platform
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import duckdb
from aimx_recipes.cli import main
import aimx_recipes.sources.kaggle.snapshot as snapshot

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / 'tests/fixtures/kaggle/mini'


def emit(case, **data):
    print(json.dumps({'case': case, **data}, sort_keys=True))


def run(src, dest, text=False):
    out, err = io.StringIO(), io.StringIO()
    args = ['ingest', 'kaggle', '--meta-kaggle', str(src), '--data-dir', str(dest)]
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args + ([] if text else ['--json']))
    return code, out.getvalue() if text else json.loads(out.getvalue()), err.getvalue()


def mutate(src, filename, field, value):
    p = src / filename
    with p.open(newline='') as f:
        r = csv.DictReader(f)
        fields, rows = r.fieldnames, list(r)
    rows[0][field] = value
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


emit('environment', python=platform.python_version(), duckdb=duckdb.__version__)
with tempfile.TemporaryDirectory(prefix='aimx-recipes-r3-') as tmp:
    root = Path(tmp)
    dest = root / 'manifest'
    code, first, _ = run(FIXTURE, dest)
    assert code == 0
    mem = Path(first['membership']['candidate_report']).parent
    snap = Path(first['snapshot']['path'])
    mpath, spath = mem / 'manifest.json', snap / 'manifest.json'
    original, soriginal = mpath.read_bytes(), spath.read_bytes()
    variants = {
        'membership_top_identity': lambda m: m.update(membership_id='p0-wrong'),
        'membership_details_identity': lambda m: m['membership_details'].update(membership_id='p0-wrong'),
        'membership_details_final': lambda m: m['membership_details'].update(status='final', unreviewed=0),
        'membership_details_types': lambda m: m['membership_details'].update(p0_in='not-a-count-map', candidates=-1),
        'membership_output_duplicate': lambda m: m['outputs'].append(m['outputs'][0]),
        'membership_output_nondict': lambda m: m['outputs'].append('bad-entry'),
    }
    for case, change in variants.items():
        m = json.loads(original)
        change(m)
        mpath.write_text(json.dumps(m))
        code, result, _ = run(FIXTURE, dest)
        emit(case, exit=code, errors=result['errors'], membership=result['membership'])
        mpath.write_bytes(original)
    for case, change in {
        'snapshot_identity': lambda m: m.update(snapshot_id='meta-kaggle-wrong'),
        'snapshot_missing_required_output': lambda m: m.update(outputs=[o for o in m['outputs'] if o['path'] != 'records/sources.jsonl']),
        'snapshot_counts': lambda m: m['counts'].update(writeup_refs=999999),
    }.items():
        m = json.loads(soriginal)
        change(m)
        spath.write_text(json.dumps(m))
        code, result, _ = run(FIXTURE, dest)
        emit(case, exit=code, errors=result['errors'], counts=result['counts'])
        spath.write_bytes(soriginal)

    # A malformed message id that still joins must be attributed to its source.
    src = root / 'message-id'
    shutil.copytree(FIXTURE, src)
    mutate(src, 'ForumMessages.csv', 'Id', 'PRIVATE_BODY_MARKER')
    mutate(src, 'ForumTopics.csv', 'FirstForumMessageId', 'PRIVATE_BODY_MARKER')
    code, result, _ = run(src, root / 'message-out')
    emit('malformed_message_id', exit=code, errors=result['errors'], marker_leaked='PRIVATE_BODY_MARKER' in json.dumps(result))

    # Force the actual DuckDB COPY writer to encounter a directory at its file target.
    # This is fault injection at the writer boundary, not a real disk-full experiment.
    original_writer = snapshot.write_parquet
    writer_errors = []
    def directory_collision(con, query, order_by, path):
        Path(path).mkdir()
        try:
            return original_writer(con, query, order_by, path)
        except Exception as exc:
            writer_errors.append(type(exc).__name__)
            raise
    with patch.object(snapshot, 'write_parquet', side_effect=directory_collision):
        code, result, _ = run(FIXTURE, root / 'write-fail')
    emit('native_duckdb_write_failure', exit=code, native_exception_types=writer_errors, errors=result['errors'], remaining_manifests=len(list((root / 'write-fail').rglob('manifest.json'))))

    # Positive native spill: explicit raw location, files observed before connection closes.
    raw = root / 'spill-data/raw/kaggle'
    con = snapshot.open_session(threads=1, memory_limit='32MB', temp_dir=raw / '.tmp-spill')
    con.execute("SELECT i, repeat(md5(i::VARCHAR), 4) AS body FROM range(500000) t(i) ORDER BY body")
    files = [p for p in raw.rglob('*') if p.is_file()]
    emit('explicit_raw_native_spill', file_count=len(files), bytes=sum(p.stat().st_size for p in files), all_inside_raw=all(p.is_relative_to(raw) for p in files))
    con.close()
    emit('native_spill_after_close', files_remaining=len([p for p in raw.rglob('*') if p.is_file()]))
emit('cleanup', removed=not root.exists())
