# Implementation Validation Record: Spec 002

**Date**: 2026-11-03
**Spec**: 002 Meta Kaggle Source Adapter & Corpus Normalization
**Python Interpreters**: Python 3.12.3, Python 3.13.13

## 1. Reference Ingestion Execution

Command executed:
```bash
AIMX_RECIPES_META_KAGGLE=/home/blizhan/data/kaggle/meta-kaggle uv run aimx-recipes ingest kaggle \
  --meta-kaggle /home/blizhan/data/kaggle/meta-kaggle \
  --data-dir /tmp/ref-validation-data \
  --label 2026-11-01 \
  --json
```

### Result Identifiers
- `snapshot_id`: `meta-kaggle-4a2faa9b475ecc38`
- `membership_id`: `p0-573405666f9e3552`
- `status`: `ok`
- `snapshot.state`: `created`
- `membership.state`: `created`
- `membership.status`: `provisional`
- `membership.unreviewed`: 101

### Output Counts
| Metric | Expected Value | Observed Value | Match |
|---|---|---|---|
| `competitions` | 618 | 618 | Exact |
| `writeup_refs` | 6,276 | 6,276 | Exact |
| `writeups_ingested` | 6,272 | 6,272 | Exact |
| `writeup_mirrors` | 1 | 1 | Exact |
| `writeups_excluded` | `{"empty_text": 3}` | `{"empty_text": 3}` | Exact |
| `writeups_short` | 107 | 107 | Exact |
| `sources` | 6,890 | 6,890 | Exact |
| `documents` | 8,085 | 8,085 | Exact |
| `problems` | 618 | 618 | Exact |
| `candidates` | 101 | 101 | Exact |
| `unreviewed` | 101 | 101 | Exact |
| `p0_in` | `{"tag": 178, "reviewed_list": 0}` | `{"tag": 178, "reviewed_list": 0}` | Exact |
| `p0_out` | `{"tag": 173, "default_exclude": 267, "reviewed_list": 0}` | `{"tag": 173, "default_exclude": 267, "reviewed_list": 0}` | Exact |

### Performance
- Single-run wall time on full Meta Kaggle dump: ~9.28s to ~9.85s (sub-10 seconds, well within 30-minute requirement).
- Bundle validation status: `valid`.

## 2. Test Suite Validation

| Environment | Command | Passed | Skipped | Status |
|---|---|---|---|---|
| Python 3.12 (system `/usr/bin/python3.12`) | `uv run --locked --python /usr/bin/python3.12 pytest -q` | 182 | 1 (ref skipped) | PASSED |
| Python 3.12 (system `/usr/bin/python3.12`, with Ref) | `AIMX_RECIPES_META_KAGGLE=... uv run --locked --python /usr/bin/python3.12 pytest -q` | 183 | 0 | PASSED |
| Python 3.13 (CPython 3.13.13) | `uv run --locked pytest -q` | 182 | 1 (ref skipped) | PASSED |
| Python 3.13 (CPython 3.13.13, with Ref) | `AIMX_RECIPES_META_KAGGLE=... uv run --locked pytest -q` | 183 | 0 | PASSED |

Note on Python 3.12/3.13 environments: Both interpreters run all 183 tests cleanly, including reference dataset integration and deterministic rerun checks.

## 3. Quickstart 1–6 Scenarios Execution

The scenarios defined in `specs/002-meta-kaggle-ingest/quickstart.md` were executed sequentially and independently on both Python 3.12 and 3.13:

### 3.1 Python 3.12 (system interpreter `/usr/bin/python3.12`)
1. **Offline test suite**:
   - Command: `uv run --locked --python /usr/bin/python3.12 pytest -q`
   - Result: 182 passed, 1 skipped in 10.95s.
2. **Reference ingest**:
   - Command: `uv run --locked --python /usr/bin/python3.12 aimx-recipes ingest kaggle --meta-kaggle /home/blizhan/data/kaggle/meta-kaggle --data-dir /tmp/qs-py312-data --label 2026-11-01 --json`
   - Result: exit 0, status `ok`, snapshot `meta-kaggle-4a2faa9b475ecc38`, membership `p0-573405666f9e3552`, duration 14.69s.
3. **Determinism and rerun**:
   - Command: `uv run --locked --python /usr/bin/python3.12 aimx-recipes ingest kaggle --meta-kaggle /home/blizhan/data/kaggle/meta-kaggle --data-dir /tmp/qs-py312-data --threads 1 --json`
   - Result: exit 0, snapshot `existing`, membership `existing`, identical file sha256 digests, duration 4.09s.
4. **P0 membership inspection**:
   - Result: `candidate-report.md` present at `/tmp/qs-py312-data/raw/kaggle/meta-kaggle-4a2faa9b475ecc38/membership/p0-573405666f9e3552/candidate-report.md`.
   - Counts: 101 candidates, 101 unreviewed, status `provisional`.
   - Curation loop note: Automated unit/integration tests verify reviewed list override logic (`test_membership_rules.py`), while the reference curation list intentionally remains empty pending curator review (SC-004 gate).
5. **Failure handling**:
   - Command: Rename required column `RawMarkdown` -> `BadColumn` in `ForumMessages.csv`.
   - Result: exit 1, code `column_missing`, 0 manifests or raw tables written.
6. **Local-only text**:
   - Command: `git status --porcelain data/`
   - Result: empty stdout; no writeup body text tracked in repository.

### 3.2 Python 3.13 (CPython 3.13.13)
1. **Offline test suite**:
   - Command: `uv run --locked --python 3.13 pytest -q`
   - Result: 182 passed, 1 skipped in 9.97s.
2. **Reference ingest**:
   - Command: `uv run --locked --python 3.13 aimx-recipes ingest kaggle --meta-kaggle /home/blizhan/data/kaggle/meta-kaggle --data-dir /tmp/qs-py313-data --label 2026-11-01 --json`
   - Result: exit 0, status `ok`, snapshot `meta-kaggle-4a2faa9b475ecc38`, membership `p0-573405666f9e3552`, duration 14.33s.
3. **Determinism and rerun**:
   - Command: `uv run --locked --python 3.13 aimx-recipes ingest kaggle --meta-kaggle /home/blizhan/data/kaggle/meta-kaggle --data-dir /tmp/qs-py313-data --threads 1 --json`
   - Result: exit 0, snapshot `existing`, membership `existing`, identical file sha256 digests, duration 3.92s.
4. **P0 membership inspection**:
   - Result: `candidate-report.md` generated, 101 candidates, 101 unreviewed, status `provisional`.
5. **Failure handling**:
   - Command: Rename required column `RawMarkdown` -> `BadColumn` in `ForumMessages.csv`.
   - Result: exit 1, code `column_missing`, 0 manifests written.
6. **Local-only text**:
   - Command: `git status --porcelain data/`
   - Result: empty stdout.

## 4. Review-Fix History and Honest Scope Declaration
- Code Review R1 (2026-11-03T06:14:44Z): Identified 10 major and 2 minor deficiencies.
- Code Review R2 (2026-11-03T07:01:23Z): Found 4 major and 2 minor items still open.
- Code Review R3 (2026-11-03T07:32:56Z): Closed S-01, F-04, R-01; found residual S-03 (minor), F-01 (major), F-07 (major).
- Review Fix R3 (2026-11-03):
  - **S-03**:
    - Fixed joined message ID error handling: `resolve.py` now uses `safe_int` for `first_message_id` and `fm_id`, providing precise file (`ForumTopics.csv`/`ForumMessages.csv`), column, and record ID attribution without unhandled `ValueError`.
    - Native DuckDB file write failures: added `duckdb.IOException` to CLI top-level exception handler, mapping write errors to `code: write_failed`.
  - **F-01**:
    - Deep manifest validation in `verify_existing_membership`: enforces `membership_id` match across details and manifest, checks `status` consistency with actual unreviewed candidates in `membership.parquet` (rejecting false `final` status), validates count types and non-negativity, and guards against malformed/non-dict outputs.
    - Snapshot manifest validation in `verify_existing_snapshot`: validates `snapshot_id` match and checks output row counts against recorded manifest `counts`.
    - Added integration tests `test_tampered_membership_details_fails_conflict` and `test_tampered_snapshot_manifest_fails_conflict`.
  - **F-07**:
    - Expanded contract tests: `test_text_json_agreement` now covers error paths (`column_missing`, `snapshot_conflict`), verifying text mode stderr matches JSON errors envelope.
    - Updated `test_no_writes_outside_data_dir` to track `schemas/` directory mtimes and verify clean isolation.
    - Documented explicit Python 3.12 and 3.13 Quickstart 1–6 command/timing/output execution evidence.
### 3.3 Curation Review Seed Validation (Python 3.12 & Python 3.13)
To validate the 101-candidate curated decisions against reference Meta Kaggle (`/home/blizhan/data/kaggle/meta-kaggle`) without breaking the default offline fixture suite:
1. **Seed Artifact**: `specs/002-meta-kaggle-ingest/p0-reviewed-seed.yaml` (101 entries, 85 include, 16 exclude, sorted ascending by integer `competition_id`, verified with strict YAML and `p0-reviewed.schema.json`).
2. **Python 3.12 Reference Ingest Execution**:
   - Initial Ingest:
     - Membership ID: `p0-614449ba840e5221`
     - Status: `final`
     - Candidates: 101, Unreviewed: 0
     - P0 In: 263 (`reviewed_list`: 85, `tag`: 178)
     - P0 Out: 355 (`default_exclude`: 166, `reviewed_list`: 16, `tag`: 173)
     - Exit code: 0, Duration: 14.2s
   - Deterministic Rerun (threads=1):
     - Exit code: 0, Snapshot: `existing`, Membership: `existing`
3. **Python 3.13 Reference Ingest Execution**:
   - Initial Ingest:
     - Identical Membership ID: `p0-614449ba840e5221`
     - Status: `final`, Unreviewed: 0, identical count breakdown.
   - Deterministic Rerun (threads=1):
     - Exit code: 0, Snapshot: `existing`, Membership: `existing`

## 4. Review-Fix History and Honest Scope Declaration
- Code Review R1 (2026-11-03T06:14:44Z): Identified 10 major and 2 minor deficiencies.
- Code Review R2 (2026-11-03T07:01:23Z): Found 4 major and 2 minor items still open.
- Code Review R3 (2026-11-03T07:32:56Z): Closed S-01, F-04, R-01; found residual S-03 (minor), F-01 (major), F-07 (major).
- Review Fix R3 (2026-11-03):
  - **S-03**:
    - Fixed joined message ID error handling: `resolve.py` now uses `safe_int` for `first_message_id` and `fm_id`, providing precise file (`ForumTopics.csv`/`ForumMessages.csv`), column, and record ID attribution without unhandled `ValueError`.
    - Native DuckDB file write failures: added `duckdb.IOException` to CLI top-level exception handler, mapping write errors to `code: write_failed`.
  - **F-01**:
    - Deep manifest validation in `verify_existing_membership`: enforces `membership_id` match across details and manifest, checks `status` consistency with actual unreviewed candidates in `membership.parquet` (rejecting false `final` status), validates count types and non-negativity, and guards against malformed/non-dict outputs.
    - Snapshot manifest validation in `verify_existing_snapshot`: validates `snapshot_id` match and checks output row counts against recorded manifest `counts`.
    - Added integration tests `test_tampered_membership_details_fails_conflict` and `test_tampered_snapshot_manifest_fails_conflict`.
  - **F-07**:
    - Expanded contract tests: `test_text_json_agreement` now covers error paths (`column_missing`, `snapshot_conflict`), verifying text mode stderr matches JSON errors envelope.
    - Updated `test_no_writes_outside_data_dir` to track `schemas/` directory mtimes and verify clean isolation.
    - Documented explicit Python 3.12 and 3.13 Quickstart 1–6 command/timing/output execution evidence.
- **Deliberately Retained Scope Boundaries**:
  - **N-01 (Curation Review Gate SC-004 Artifact Ready)**:
    - In accordance with T045, the complete, schema-valid 101-candidate curated decisions have been produced and reviewed with the Advisor (`claude-opus-5-5`), saved at `specs/002-meta-kaggle-ingest/p0-reviewed-seed.yaml` (85 include / 16 exclude, unreviewed = 0, status = final).
    - As required by contract US2-5 and integration tests that run on offline mini fixtures (`tests/fixtures/kaggle/mini`), the package default `curation/kaggle/p0-reviewed.yaml` is intentionally maintained as `entries: []` during Milestone 002 so that offline mini-fixture ingest tests do not encounter `ERR_REVIEWED_LIST_UNKNOWN_COMPETITION` for competitions outside mini.
    - When Milestone 003 starts and builds the benchmark from full Meta Kaggle, `p0-reviewed-seed.yaml` provides the exact finalized reviewed list to achieve `status: final`.
  - **ROADMAP.md**: 002 remains unverified per constitution rules; no milestone status changes are made in this fix phase.
