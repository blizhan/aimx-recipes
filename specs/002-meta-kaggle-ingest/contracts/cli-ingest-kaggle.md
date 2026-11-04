# Contract: `aimx-recipes ingest kaggle`

**Spec**: FR-001, FR-002, FR-012, FR-015 | **Data model**: [data-model.md](../data-model.md)

## Synopsis

```text
aimx-recipes ingest kaggle --meta-kaggle <dir>
                           [--data-dir <dir>]        # default: ./data
                           [--label <text>]          # recorded in manifest only
                           [--threads <n>]           # default: min(8, CPU count)
                           [--memory-limit <size>]   # default: 4GB
                           [--json]
```

- It is an explicit, write-capable command. It writes only under `<data-dir>/raw/kaggle/`.
- It reads only the six required Meta Kaggle files in `<dir>`: `Competitions.csv`, `Teams.csv`, `ForumTopics.csv`, `ForumMessages.csv`, `Tags.csv`, `CompetitionTags.csv`.
- It makes no network or model calls and never downloads data. DuckDB extension autoinstall and autoload are disabled.
- `--threads` and `--memory-limit` affect speed only, never output bytes.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success: the snapshot was created or already existed, and membership was computed |
| 1 | input, validation, or conflict error; nothing new was written |
| 2 | usage error |

An unreviewed candidate does **not** fail the run: it sets `p0.status = provisional` and adds a warning.

## JSON envelope (`--json`, stdout, one object plus a newline)

Keys are sorted, the output contains no ANSI codes, and it is UTF-8 with `ensure_ascii=false`.

```json
{
  "command": "ingest kaggle",
  "output_version": "1.0.0",
  "status": "ok",
  "run_started_at": "2026-11-03T09:00:00Z",
  "snapshot": {
    "snapshot_id": "meta-kaggle-1a2b3c4d5e6f7a8b",
    "state": "created",
    "path": "data/raw/kaggle/meta-kaggle-1a2b3c4d5e6f7a8b",
    "label": "2026-11-01"
  },
  "counts": {
    "competitions": 618,
    "writeup_refs": 6276,
    "writeups_ingested": 6272,
    "writeup_mirrors": 1,
    "writeups_excluded": {"empty_text": 3},
    "writeups_short": 107,
    "sources": 6890, "documents": 8085, "problems": 618
  },
  "membership": {
    "membership_id": "p0-0f1e2d3c4b5a6978",
    "state": "created",
    "rule_version": "1.0.0",
    "p0_in": {"reviewed_list": 0, "tag": 178},
    "p0_out": {"reviewed_list": 0, "tag": 173, "default_exclude": 267},
    "candidates": 101,
    "unreviewed": 101,
    "status": "provisional",
    "candidate_report": "data/raw/kaggle/meta-kaggle-…/membership/p0-…/candidate-report.md"
  },
  "warnings": [{"code": "p0_provisional", "message": "101 heuristic candidates are unreviewed"}],
  "errors": []
}
```

The counts in this example are illustrative. `sources` and `documents` are exact only after implementation; the reference-snapshot acceptance test pins them.

Field rules:

| Field | Rule |
| --- | --- |
| `status` | `ok` or `error`. On `error`, `snapshot` and `membership` may be null, and `errors` is non-empty. |
| `snapshot.state` | `created` or `existing` |
| `membership.state` | `created` or `existing` |
| `membership.status` | `final` or `provisional` |
| `run_started_at` | the **only** wall-clock value. It is never written into the snapshot or its hashed content (FR-015). |
| `p0_in` / `p0_out` | always contain every applicable deciding rule key, with zero counts kept |
| Paths | relative to the current directory when inside it, otherwise absolute |

`warnings[]` and `errors[]` items are `{code, message, file?, line?, record_id?, column?}`, sorted by `(code, file, line, record_id)`.

- Messages never embed source rows or body text. A malformed row is identified by file, line, and its leading id field.

Stable codes:

| Kind | Codes |
| --- | --- |
| Errors | `input_missing`, `column_missing`, `csv_malformed`, `date_unparseable`, `input_changed_during_run`, `bundle_invalid`, `snapshot_conflict`, `reviewed_list_invalid`, `reviewed_list_unknown_competition`, `reviewed_list_slug_mismatch`, `rule_file_invalid`, `write_failed` |
| Warnings | `p0_provisional`, `writer_version_differs`, `reviewed_list_entry_not_candidate` (an informational entry overriding a tag decision) |

## Human-readable output (default, stdout)

It carries the same facts as the JSON, in a fixed order:
1. snapshot id and state;
2. counts;
3. exclusions by reason;
4. membership id, state, and status;
5. P0 in/out by deciding rule;
6. candidates and unreviewed count, with the report path;
7. warnings;
8. errors.

Errors also go to stderr. A test asserts that every count in the text equals the JSON (SC-007).

## Invariants tested

- Identical input, rule, and list across two runs (with different `--threads`): the second run reports `existing` for both, and every output file is byte-identical.
- A missing required column fails before any directory is created under `raw/kaggle/`.
- A changed reviewed list with the same snapshot creates a new `membership_id` and leaves the old membership directory untouched.
- No file outside `<data-dir>/raw/kaggle/` is created or modified, and no git-tracked path is written.
