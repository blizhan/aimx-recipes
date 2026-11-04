"""Read-only re-review probes; only isolated synthetic fixtures are mutated."""
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
from unittest.mock import patch

from aimx_recipes.cli import main
import aimx_recipes.sources.kaggle as kaggle
import aimx_recipes.sources.kaggle.membership as membership
import aimx_recipes.sources.kaggle.snapshot as snapshot

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / 'tests/fixtures/kaggle/mini'

def emit(case, **data):
    print(json.dumps({'case': case, **data}, sort_keys=True))

def run(src, dest, *extra):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(['ingest', 'kaggle', '--meta-kaggle', str(src), '--data-dir', str(dest), '--json', *extra])
    return code, json.loads(out.getvalue())

def mutate(src, filename, field, value):
    p = src / filename
    with p.open(newline='') as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    rows[0][field] = value
    with p.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

# Re-run the supplied twelve probes, with cleanup added externally.
created = []
original_mkdtemp = tempfile.mkdtemp

def tracked_mkdtemp(*args, **kwargs):
    p = original_mkdtemp(*args, **kwargs)
    created.append(Path(p))
    return p

try:
    with patch.object(tempfile, 'mkdtemp', side_effect=tracked_mkdtemp):
        runpy.run_path(str(Path(__file__).with_name('fix-verification-20261103T070000Z-probes.py')))
finally:
    for p in created:
        shutil.rmtree(p)
emit('prior_probe_cleanup', all_removed=all(not p.exists() for p in created))

with tempfile.TemporaryDirectory(prefix='aimx-recipes-002-rereview-') as tmp:
    root = Path(tmp)
    # Actual malformed numeric input, not an injected exception.
    src = root / 'badnumber'
    shutil.copytree(FIXTURE, src)
    mutate(src, 'Teams.csv', 'CompetitionId', 'PRIVATE_BODY_MARKER')
    code, result = run(src, root / 'badnumber-out')
    emit('numeric_diagnostic', exit=code, errors=result['errors'], marker_leaked='PRIVATE_BODY_MARKER' in json.dumps(result))

    code, result = run(FIXTURE, root / 'manifest')
    mem = Path(result['membership']['candidate_report']).parent
    manpath = mem / 'manifest.json'
    original = json.loads(manpath.read_text())
    changed = json.loads(json.dumps(original))
    changed['outputs'] = [o for o in changed['outputs'] if o['path'] != 'membership.parquet']
    manpath.write_text(json.dumps(changed))
    (mem / 'membership.parquet').unlink()
    code, result = run(FIXTURE, root / 'manifest')
    emit('missing_output_omitted_from_manifest', exit=code, status=result['status'], membership=result['membership'], missing_membership_file=not (mem / 'membership.parquet').exists())

    # Failure after snapshot publication: rollback must remove all published manifests.
    with patch.object(kaggle, 'evaluate_and_write_membership', side_effect=OSError('synthetic disk failure')):
        code, result = run(FIXTURE, root / 'disk-fail')
    emit('membership_write_failure', exit=code, errors=result['errors'], remaining_manifests=len(list((root / 'disk-fail').rglob('manifest.json'))))

    # Record actual ingest session settings; default spill is relative to cwd.
    sessions = []
    orig_open = snapshot.open_session
    def record_session(*args, **kwargs):
        con = orig_open(*args, **kwargs)
        sessions.append({'explicit_temp_dir': str(kwargs.get('temp_dir')), 'actual_temp_directory': con.execute("SELECT current_setting('temp_directory')").fetchone()[0]})
        return con
    with patch.object(kaggle, 'open_session', side_effect=record_session), patch.object(snapshot, 'open_session', side_effect=record_session), patch.object(membership, 'open_session', side_effect=record_session):
        code, result = run(FIXTURE, root / 'sessions')
        code2, result2 = run(FIXTURE, root / 'sessions')
    emit('actual_ingest_session_settings', exits=[code, code2], sessions=sessions)

    # Demonstrate default-session spill with synthetic data in isolated cwd.
    cwd = Path.cwd()
    os.chdir(root)
    try:
        con = orig_open(threads=1, memory_limit='32MB')
        query_error = None
        try:
            cur = con.execute("SELECT i, repeat(md5(i::VARCHAR), 4) AS body FROM range(500000) t(i) ORDER BY body")
        except Exception as exc:
            query_error = type(exc).__name__
        spill = [str(p.relative_to(root)) for p in (root / '.tmp').rglob('*') if p.is_file()]
        emit('default_session_synthetic_spill', query_error=query_error, outside_data_raw_files=spill, bytes=sum(p.stat().st_size for p in (root / '.tmp').rglob('*') if p.is_file()))
        con.close()
    finally:
        os.chdir(cwd)

    # Full byte comparison of independent rebuilds, with distinct thread counts.
    results = []
    for i, threads in enumerate(['1', '4']):
        code, result = run(FIXTURE, root / f'rebuild-{i}', '--threads', threads)
        snap = Path(result['snapshot']['path'])
        results.append({str(p.relative_to(snap)): hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.rglob('*') if p.is_file()})
    emit('independent_all_file_bytes', equal=results[0] == results[1], file_count=len(results[0]))

    # Existing Tag row with unknown Name is not a dangling TagId.
    src = root / 'nulltagname'
    shutil.copytree(FIXTURE, src)
    mutate(src, 'Tags.csv', 'Name', '')
    code, result = run(src, root / 'nulltagname-out')
    emit('existing_tag_with_missing_name', exit=code, errors=result['errors'])

    # Installed-layout simulation: no package uv.lock, unrelated cwd lock present.
    unrelated = root / 'unrelated'
    unrelated.mkdir()
    (unrelated / 'uv.lock').write_text('unrelated project lock')
    os.chdir(unrelated)
    try:
        with patch.object(snapshot, '__file__', str(root / 'venv/lib/python3.13/site-packages/aimx_recipes/sources/kaggle/snapshot.py')):
            con = orig_open()
            meta = snapshot.get_environment_metadata(con)
            con.close()
        emit('installed_layout_unrelated_lock', simulated_layout=True, recorded_unrelated_lock=meta['uv_lock_sha256'] == hashlib.sha256(b'unrelated project lock').hexdigest())
    finally:
        os.chdir(cwd)
emit('new_probe_cleanup', removed=not root.exists())
