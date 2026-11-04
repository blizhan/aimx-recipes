# Quickstart & Validation Guide: Meta Kaggle Ingest

**Spec**: [spec.md](spec.md) | **Contracts**: [CLI](contracts/cli-ingest-kaggle.md), [raw snapshot](contracts/raw-snapshot.md), [P0 rules](contracts/p0-membership-rules.md)

These are runnable validation scenarios for after implementation. They are not implementation instructions. Nothing below has been run at planning time.

## Prerequisites

- Python 3.12 or 3.13, with `uv sync` run in the repository.
- For the reference scenarios: a local Meta Kaggle download containing the six required CSVs, for example `~/data/kaggle/meta-kaggle/` dated 2026-11-01. Its location is passed explicitly; nothing is downloaded.

## 1. Offline test suites (no Meta Kaggle needed)

```bash
uv run pytest -q    # 001 suites + 002 unit/contract/integration on synthetic fixtures
```

Expected: everything passes with the network blocked. The 002 fixtures under `tests/fixtures/kaggle/` are project-authored synthetic CSVs with their own manifest. They cover each writeup disposition, both body formats, a short body, a whitespace-duplicate pair, every tag class, heuristic candidates, and reviewed include/exclude entries.

## 2. Reference ingest (US1, US3, SC-001, SC-005, SC-008)

```bash
time uv run aimx-recipes ingest kaggle --meta-kaggle ~/data/kaggle/meta-kaggle --label 2026-11-01 --json > /tmp/ingest1.json
```

Expected:

| Field | Value |
| --- | --- |
| Exit code | 0 |
| `status` | `ok` |
| `snapshot.state` | `created` |
| `counts.writeup_refs` | 6276 |
| ingested + mirrors + excluded | 6276 |
| `counts.writeups_excluded` | `{"empty_text": 3}` |
| `counts.writeups_short` | 107 |
| `counts.competitions` | 618 |
| Wall time | under 30 minutes (research measured seconds for resolution) |

Contract validity is checked inside the run (`bundle_invalid` otherwise). It can also be re-checked independently by loading `records/*.jsonl` and `documents.parquet` into `aimx_recipes.validate_bundle`. The `tests/integration` reference test does this when `AIMX_RECIPES_META_KAGGLE` is set.

## 3. Determinism and immutability (US1-4, SC-002)

```bash
uv run aimx-recipes ingest kaggle --meta-kaggle ~/data/kaggle/meta-kaggle --threads 1 --json > /tmp/ingest2.json
```

Expected:
- `snapshot.state = existing` and `membership.state = existing`, with the same `snapshot_id` and `membership_id`.
- Running `sha256sum` over the snapshot directory gives the same values before and after the rerun.

To exercise a changed input, copy the six CSVs to a scratch directory, append one synthetic team row with a writeup reference, and ingest it with `--data-dir` set to a temporary directory. A new `snapshot_id` appears, and the original snapshot is unchanged.

## 4. P0 membership and review loop (US2, SC-003, SC-004, SC-006)

1. Open `membership/<membership_id>/candidate-report.md`. On the reference snapshot with an empty reviewed list, expect 101 candidates, all `unreviewed`, and `membership.status = provisional`.
2. Pick one competition from the heuristic pool. Add a reviewed entry for it in `curation/kaggle/p0-reviewed.yaml`, with a reason and reviewer, then rerun ingest:
   - `snapshot.state = existing`, and no source text is re-normalized.
   - A new `membership_id` with `state = created` appears, and `unreviewed` drops by one.
   - That competition shows `deciding_rule = reviewed_list`. The previous membership directory is unchanged.
3. Introduce a duplicate key, an unknown competition id, or a slug mismatch. The run exits 1 with `reviewed_list_invalid`, `reviewed_list_unknown_competition`, or `reviewed_list_slug_mismatch`, and no new membership directory is created.
4. Answer "why is X in or out?" from `membership.parquet` alone (`p0`, `deciding_rule`, `tag_class`, `signals`, `reviewed_reason`). Do this for a tag-in, a modality-excluded, a reviewed, and an unreviewed competition.
5. P0 can be handed to 003 once `membership.status = final`, which means zero `unreviewed`.

## 5. Failure handling (US1-4, FR-002, FR-014)

Each failure is checked against a scratch copy of the inputs:

| Mutation | Expected |
| --- | --- |
| Rename a header column, for example `RawMarkdown` → `Raw` | exit 1, `column_missing` naming file and column; no directory created under `raw/kaggle/` |
| Truncate a quoted field (unterminated quote) | exit 1, `csv_malformed` with file and line; the message contains no row text |
| Modify a file during the run (simulated in tests) | `input_changed_during_run` |

## 6. Local-only text (SC-007, FR-016)

```bash
git status --porcelain                       # only curation/kaggle/*.yaml changes, if you edited the list
git ls-files -z | xargs -0 grep -l "<a distinctive sentence from a writeup>"   # no results
```

Expected:
- `data/` is untracked.
- The human-readable summary and the JSON report identical counts; a contract test asserts this.
