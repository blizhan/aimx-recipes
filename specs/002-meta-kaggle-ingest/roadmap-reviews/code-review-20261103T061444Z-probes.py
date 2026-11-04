import contextlib, csv, io, json, shutil, tempfile
from pathlib import Path
from unittest.mock import patch
from aimx_recipes.cli import main
import aimx_recipes.sources.kaggle.membership as membership
import aimx_recipes.sources.kaggle.snapshot as snapshot
from aimx_recipes.sources.kaggle.normalize import build_writeup_source, normalize_competition_row

root = Path(tempfile.mkdtemp(prefix='aimx-recipes-002-review-'))
fixture = Path('tests/fixtures/kaggle/mini').resolve()
def run(src, dest):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(['ingest','kaggle','--meta-kaggle',str(src),'--data-dir',str(dest),'--json'])
    return code, json.loads(out.getvalue())
def emit(name, **data):
    print(json.dumps({'case':name, **data}, sort_keys=True))
def mutate(src, filename, change):
    path = src / filename
    with path.open(newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    rows = change(rows)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

code, first = run(fixture, root/'a')
code, second = run(fixture, root/'a')
mem = Path(first['membership']['candidate_report']).parent
emit('rerun_state', exit=code, snapshot=second['snapshot']['state'], membership=second['membership']['state'])
(mem/'membership.parquet').write_bytes(b'corrupt')
code, corrupt = run(fixture, root/'a')
emit('corrupt_membership', exit=code, status=corrupt['status'], warnings=corrupt['warnings'])

with patch.object(membership, 'load_reviewed_list_text', return_value='entries: [{competition_id: "999999", slug: missing, decision: include, reason: review, reviewed_by: human, reviewed_on: "2026-11-03"}]'):
    code, badlist = run(fixture, root/'badlist')
emit('invalid_review_leaves_snapshot', exit=code, errors=badlist['errors'], manifests=len(list((root/'badlist').rglob('manifest.json'))))

original = tempfile.NamedTemporaryFile
seen=[]
def track(*args, **kwargs):
    f = original(*args, **kwargs); seen.append(f.name); return f
with patch.object(tempfile, 'NamedTemporaryFile', side_effect=track):
    code, tracked = run(fixture, root/'tracked')
emit('temporary_files', exit=code, paths=seen, outside_raw=all(not p.startswith(str(root/'tracked'/'raw')) for p in seen))

code, fresh = run(fixture, root/'b')
a = json.loads((mem/'manifest.json').read_text())
b = json.loads((Path(fresh['membership']['candidate_report']).parent/'manifest.json').read_text())
emit('fresh_manifest_determinism', same_membership_id=first['membership']['membership_id']==fresh['membership']['membership_id'], manifests_equal=a==b, a_path=a['membership_details']['candidate_report'], b_path=b['membership_details']['candidate_report'])

quoted = root/"input's"; shutil.copytree(fixture,quoted)
code, quote = run(quoted, root/'quoteout')
emit('apostrophe_input_path', exit=code, errors=quote['errors'])

src = root/'missingtag'; shutil.copytree(fixture,src)
mutate(src,'Tags.csv',lambda rows:[r for r in rows if r['Id']!='14102'])
code, tag = run(src, root/'tagout')
import duckdb
con=duckdb.connect()
rows=con.execute('SELECT competition_id,tag_class,p0 FROM read_parquet(?) ORDER BY competition_id',[str(Path(tag['membership']['candidate_report']).parent/'membership.parquet')]).fetchall() if code==0 else []
emit('missing_modality_tag', exit=code, memberships=rows, errors=tag['errors'])
con.close()

src=root/'baddate'; shutil.copytree(fixture,src)
def bad_date(rows):
    for r in rows: r['PostDate']='PRIVATE_BODY_MARKER'
    return rows
mutate(src,'ForumMessages.csv',bad_date)
code, date = run(src,root/'dateout')
emit('bad_date_diagnostic',exit=code,errors=date['errors'])

emit('missing_values',published_at=build_writeup_source(1,'a','s','body',None)['published_at'],higher_is_better=normalize_competition_row({'competition_id':1,'slug':'a'})['higher_is_better'])
import copy
rule = membership.load_and_validate_rule_file()
rule['heuristic']['signals']['S1']['metric_families'].append('^CUSTOM_METRIC$')
rule['heuristic']['signals']['S5']['negative_tag_ids'].append({'id':'999999','name':'custom negative'})
validated = membership.load_and_validate_rule_file(json.dumps(rule))
emit('ignored_rule_fields', custom_metric_signals=membership.compute_signals('CUSTOM_METRIC','','train.csv','Forecast','',[],validated), negative_tag_signals=membership.compute_signals('RMSE','','train.csv','Forecast','',['999999'],validated))
blank = membership.load_and_validate_reviewed_list('entries: [{competition_id: "101", slug: tabular-comp, decision: include, reason: "   ", reviewed_by: "   ", reviewed_on: "2026-11-03"}]')
emit('blank_review_accepted', reason=blank['entries'][0]['reason'], reviewer=blank['entries'][0]['reviewed_by'])
import aimx_recipes.sources.kaggle as kaggle
try:
    kaggle.membership_id(first['snapshot']['snapshot_id'])
except TypeError as exc:
    emit('consumer_membership_api', error=str(exc))
print(json.dumps({'scratch_root':str(root)}))
