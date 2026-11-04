# Tasks: Meta Kaggle Source Adapter & Corpus Normalization

**Input**: Design documents from `specs/002-meta-kaggle-ingest/`

**Prerequisites**:
- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)
- [contracts/cli-ingest-kaggle.md](contracts/cli-ingest-kaggle.md), [contracts/raw-snapshot.md](contracts/raw-snapshot.md), [contracts/p0-membership-rules.md](contracts/p0-membership-rules.md)
- Heuristic sources: [research-heuristic-v0.md](research-heuristic-v0.md), [research-p0-candidates.md](research-p0-candidates.md)

**Tests**: Included. The spec gives every user story an independent test and acceptance scenarios. SC-001–SC-008 require verifiable counts, determinism, validity, and text/JSON agreement. The constitution asks for determinism and CLI-contract tests.

For each story, write its listed tests first and confirm they fail for the intended reason before implementing. Import or setup errors do not count as that evidence.

**Organization**:
- Shared setup and foundation come first.
- Four story increments follow. US1 is the MVP. US2 and US3 both build on US1's snapshot and may proceed in parallel, except where they share files (see Parallel Opportunities). US4 hardens reproducibility.
- Cross-cutting acceptance comes last.

This file schedules implementation; no task is complete merely because its design exists.

## Format: `[ID] [P?] [Story] Description`

- `[P]`: the task touches disjoint files and may run concurrently once its prerequisites are complete. It does not waive phase gates.
- `[US1]`–`[US4]` map to the user stories in spec.md. Setup, foundation, and polish tasks have no story label.
- All paths are relative to the repository root.
- Shared files have one writer at a time: `src/aimx_recipes/sources/kaggle/__init__.py`, `src/aimx_recipes/cli/output.py`, `src/aimx_recipes/sources/kaggle/snapshot.py`, `tests/integration/test_ingest_kaggle.py`, and `tests/fixtures/kaggle/manifest.json`.
- Every test writes only to `tmp_path`, never to `data/`. The network stays blocked by the existing `tests/conftest.py` fixture.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the dependencies, entry point, packaged curation resources, and the synthetic Meta Kaggle fixture set.

- [X] T001 In `pyproject.toml`:
  - add runtime dependencies `duckdb>=2.0,<3` and `pyyaml>=6.0.3,<7`;
  - add `[project.scripts] aimx-recipes = "aimx_recipes.cli:main"`;
  - add a wheel `force-include` mapping `"curation" = "aimx_recipes/_curation"`;
  - exclude `src/aimx_recipes/_curation` from `packages`, mirroring `_schemas`.

  Then update `uv.lock` with `uv lock`, verify `uv sync --locked`, and confirm the existing 108 tests still pass with `uv run pytest -q`.
- [X] T002 [P] Create `curation/kaggle/p0-reviewed.yaml` containing only `entries: []` and a header comment that points to [contracts/p0-membership-rules.md](contracts/p0-membership-rules.md). Create the tracked relative symlink `src/aimx_recipes/_curation -> ../../curation` exactly as `src/aimx_recipes/_schemas` is done.
- [X] T003 [P] Create package skeletons under `src/aimx_recipes/cli/` and `src/aimx_recipes/sources/kaggle/`, with module docstrings and no behavior:
  - `src/aimx_recipes/cli/__init__.py` and `src/aimx_recipes/cli/output.py`;
  - `src/aimx_recipes/sources/__init__.py`;
  - `src/aimx_recipes/sources/kaggle/` with `__init__.py`, `inputs.py`, `resolve.py`, `normalize.py`, `membership.py`, `snapshot.py`;
  - the test directory `tests/unit/kaggle/` with `__init__.py` if the existing test layout needs one.
- [X] T004 Author the synthetic Meta Kaggle fixture set in `tests/fixtures/kaggle/mini/`.
  - **Files**: `Competitions.csv`, `Teams.csv`, `ForumTopics.csv`, `ForumMessages.csv`, `Tags.csv`, `CompetitionTags.csv`, with the real headers from [research.md R1](research.md#r1-input-files-and-parsing). Use CRLF records, quoted fields with embedded CRLF, and `""` empty values.
  - **Text**: project-authored only. Use one unique marker string per body so tests can assert it never leaks.
  - **Writeup cases**: one writeup reference per disposition and exclusion reason; a markdown body; an HTML-only body; a body of exactly 199 code points and one of 200 with non-ASCII characters; a whitespace-variant duplicate pair across two competitions.
  - **Competition cases**: one competition per tag class (tag-in by id 14101/13209, tag-in plus modality, other-tags, untagged); a missing overview, empty metric description, and missing dataset description; a numeric metric abbreviation; medals `1/2/3/0/empty`; missing ranks.
  - **Heuristic cases**: a candidate, a hard negative (Santa-style metric), and a borderline non-candidate.

  Record the expected counts and per-row expectations in `tests/fixtures/kaggle/manifest.json`, using case ids prefixed `kaggle_` and not auto-collected by 001 tests. Add a `kaggle_fixture_dir` fixture to `tests/conftest.py` that copies `tests/fixtures/kaggle/mini/` to `tmp_path` for mutation.

**Checkpoint**: The dependencies resolve, the old suite passes, and the fixtures exist.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the strict YAML loader, the CLI shell and envelope, the DuckDB session, deterministic writer primitives, and the ids and versions that every story uses.

- [X] T005 [P] Write failing tests in `tests/unit/test_yaml_strict.py`:
  - a duplicate key raises with line and column;
  - `no`, `yes`, `on`, `0123`, `1e3`, `2026-11-03`, and `true` all load as strings;
  - `null` loads as `None`;
  - nested lists and maps are preserved;
  - non-string mapping keys are rejected;
  - the loader never constructs Python objects (no tags beyond safe ones).
- [X] T006 Implement `src/aimx_recipes/yaml_strict.py` per [research R10](research.md#r10-reviewed-list-format). It is a PyYAML `SafeLoader` subclass that keeps only the null implicit resolver and rejects duplicate keys in the mapping constructor, and it exposes `load_strict_yaml(text_or_path)`. Satisfy T005.
- [X] T007 [P] Write failing tests in `tests/contract/test_cli_ingest_contract.py` for the envelope shape from [contracts/cli-ingest-kaggle.md](contracts/cli-ingest-kaggle.md):
  - sorted keys, `command`, and `output_version = "1.0.0"`;
  - `status` is `ok` or `error`;
  - warning and error items carry `code` and `message`, sorted by `(code, file, line, record_id)`;
  - a usage error (missing `--meta-kaggle`, unknown flag) with `--json` prints an error envelope and returns 2;
  - without `--json`, usage text goes to stderr and the return is 2;
  - output contains no ANSI escapes and uses UTF-8 with `ensure_ascii=False`;
  - `main(argv)` returns an int and never calls `sys.exit`.

  Use a stubbed ingest function where needed.
- [X] T008 Implement `src/aimx_recipes/cli/__init__.py` with `main(argv: list[str] | None = None) -> int`:
  - an argparse tree `ingest` → `kaggle` with `--meta-kaggle` (required), `--data-dir` (default `data`), `--label`, `--threads` (default `min(8, os.cpu_count())`), `--memory-limit` (default `4GB`), and `--json`;
  - `exit_on_error=False` plus an overridden `error()`.

  Implement `src/aimx_recipes/cli/output.py` with:
  - envelope construction, the stable error/warning code constants from the CLI contract, and item sorting;
  - deterministic text rendering in the contract's section order;
  - exit-code mapping 0/1/2;
  - `run_started_at` as the only wall-clock value.

  The `ingest kaggle` handler calls `aimx_recipes.sources.kaggle.ingest(...)`; for now that raises `NotImplementedError`, which is mapped to an error envelope. Satisfy T007.
- [X] T009 [P] Write failing tests in `tests/unit/kaggle/test_snapshot_io.py` for the writer primitives:
  - a session reports `TimeZone='UTC'` and extension autoinstall/autoload disabled;
  - `write_parquet(con, query, order_by, path)` produces identical bytes at `threads=1` and `threads=4` for a 10k-row synthetic table with strings, lists, and naive timestamps;
  - `canonical_json_line(obj)` uses `sort_keys`, `ensure_ascii=False`, and compact separators;
  - `content_sha256(rows, key)` is order-independent of the input and changes when any value changes;
  - `atomic_publish(tmp_dir, final_dir)` renames only when the target is absent;
  - names beginning `.tmp-` are recognized as incomplete.
- [X] T010 Implement the primitives in `src/aimx_recipes/sources/kaggle/snapshot.py` per [research R7](research.md#r7-deterministic-output):
  - `open_session(threads, memory_limit, temp_dir)` with `SET TimeZone='UTC'`, `autoinstall_known_extensions=false`, and `autoload_known_extensions=false`;
  - `write_parquet` using `COPY (<query> ORDER BY <key>) TO <path> (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880)`;
  - canonical JSON helpers, the logical `content_sha256`, `fsync` of files and directories, and `atomic_publish` via `os.rename` of a `.tmp-<random>` sibling directory.

  Use `con.execute(...).fetchall()` and never `DuckDBPyRelation.fetchone()`. Avoid any API that needs pyarrow. Satisfy T009.
- [X] T011 [P] Write failing tests in `tests/unit/kaggle/test_ids.py` for:
  - the id builders from [data-model.md §1](data-model.md#1-identities): writeup and competition source ids, document ids with a 12-hex text-hash suffix, problem ids, `snapshot_id = meta-kaggle-<16 hex>` over canonical inputs plus versions, and `membership_id = p0-<16 hex>`;
  - every id matches the 001 pattern `^[A-Za-z0-9][A-Za-z0-9._:/-]*$`;
  - ids are stable across calls and independent of input order;
  - `ADAPTER_VERSION == "1.0.0"` and `NORMALIZATION_VERSION == "kaggle-text-1"`.
- [X] T012 Implement the id builders and version constants in `src/aimx_recipes/sources/kaggle/normalize.py`, and expose the constants from `src/aimx_recipes/sources/kaggle/__init__.py`. Satisfy T011.

**Checkpoint**: `uv run pytest -q` passes. `aimx-recipes ingest kaggle --meta-kaggle x --json` returns a well-formed error envelope (`NotImplementedError` mapped).

## Phase 3: User Story 1 — Snapshot writeups and their competition context (Priority: P1) 🎯 MVP

**Goal**: One command turns a Meta Kaggle directory into a local snapshot. Every writeup reference is accounted for, exact texts are stored, and competition context and team outcomes are captured.

**Independent Test**: Ingest the `mini` fixture into `tmp_path`. Then:
- refs equal ingested + mirrors + excluded, with stable reasons;
- body format and short flags match the fixture manifest;
- context fields are present or absent as authored;
- document text round-trips byte-for-byte;
- a missing column fails before any directory is created.

### Tests for User Story 1

- [X] T013 [P] [US1] Write failing tests in `tests/unit/kaggle/test_inputs.py`:
  - **Missing inputs**: a missing file → `input_missing`; a renamed required column → `column_missing` naming file and column, raised before any read of data rows.
  - **Malformed CSV**: an unterminated quote or an extra column → `csv_malformed` with file, line, and leading id, where the message never contains the fixture's body marker.
  - **Changed files**: a file changed between stat-before and stat-after → `input_changed_during_run`.
  - **Fingerprints**: size, sha256, and row counts are recorded for all six files.
  - **Empty values**: `""` and an empty field both read as absent.
  - **Upstream columns**: extra columns are tolerated.
- [X] T014 [P] [US1] Write failing tests in `tests/unit/kaggle/test_resolve.py` against the fixture manifest:
  - every writeup disposition and exclusion reason (`topic_not_found`, `first_message_missing`, `message_not_found`, `empty_text`);
  - markdown is preferred, and HTML is used when markdown is absent, with `body_format` recorded;
  - `is_short` at 199 vs 200 code points;
  - UTC naive timestamps parsed from `%m/%d/%Y %H:%M:%S`, and `date_unparseable` on bad input;
  - `metric_label` falls back to the name for numeric abbreviations, and `higher_is_better` comes from `EvaluationAlgorithmIsMax`;
  - medal mapping `1/2/3` → gold/silver/bronze and `0`/empty → null; missing ranks are null;
  - tag ids and names are attached as sorted lists;
  - `competition_data_license` is kept only in competition rows;
  - absent context sections produce no Document rows.
- [X] T015 [US1] Add US1 end-to-end tests to `tests/integration/test_ingest_kaggle.py`, run through `aimx_recipes.cli.main([... "--data-dir", tmp, "--json"])`:
  - exit 0; `snapshot.state = created`;
  - the counts block equals the fixture manifest, and refs equal ingested + mirrors + excluded;
  - `competitions.parquet`, `writeup_refs.parquet`, `writeups.parquet`, and `documents.parquet` exist under `raw/kaggle/<snapshot_id>/` with the expected rows;
  - `documents.text` equals the authored text exactly, with sha256 matching;
  - nothing is created outside `<tmp>/raw/kaggle/`;
  - with a renamed column, the run exits 1 and `raw/kaggle/` contains no snapshot directory.

### Implementation for User Story 1

- [X] T016 [US1] Implement `src/aimx_recipes/sources/kaggle/inputs.py`:
  - a `REQUIRED_INPUTS` table listing the six files and the columns this adapter reads;
  - header validation via stdlib `csv.reader` on the first record;
  - stat (size, `st_mtime_ns`, inode) → `hashlib.file_digest` sha256;
  - DuckDB views via `read_csv(auto_detect=false, header=true, delim=',', quote='"', escape='"', columns=<all VARCHAR from the real header>, strict_mode=true, allow_quoted_nulls=false, max_line_size=8388608)` with no `new_line`;
  - row counts;
  - a stat-after check;
  - DuckDB CSV errors mapped to `csv_malformed` with file, line, and leading id, truncating any row content.

  Satisfy T013.
- [X] T017 [US1] Implement `src/aimx_recipes/sources/kaggle/resolve.py` per [research R1–R5](research.md):
  - semi-join resolution Teams(`WriteUpForumTopicId`) → ForumTopics(`FirstForumMessageId`) → ForumMessages, producing one row per reference with message and dispositions;
  - competition context rows for competitions with at least one reference: slug, title, subtitle, host segment, `strptime` dates, metric fields, `higher_is_better`, data license, tag ids and names via CompetitionTags/Tags, and URL;
  - team outcome: medal and ranks.

  Push filters into scans. Satisfy the resolution parts of T014.
- [X] T018 [US1] Extend `src/aimx_recipes/sources/kaggle/normalize.py` with:
  - body selection (`RawMarkdown` else `Message`, empty → `empty_text` exclusion);
  - `char_count` in code points and `is_short`;
  - competition section Documents (`competition_overview`, `competition_evaluation_metric`, `competition_dataset_description`) with exact text and none when absent;
  - document ids and hashes;
  - adapter rows for `competitions`, `writeup_refs`, `writeups`, and `documents` per [data-model.md §3](data-model.md#3-adapter-tables-snapshot-immutable).

  Satisfy the remaining T014 tests.
- [X] T019 [US1] Extend `src/aimx_recipes/sources/kaggle/snapshot.py` with `write_snapshot(...)`:
  - compute `snapshot_id` from input fingerprints and versions;
  - load normalized rows into DuckDB through canonical NDJSON and `read_json` with explicit columns;
  - write the four Parquet tables ordered by their keys into `.tmp-<random>/`;
  - write `manifest.json` with snapshot id, versions, contract schema version `2.0.0`, inputs, outputs with `file_sha256` and `content_sha256`, counts, and label;
  - publish atomically.

  A failure at any step removes the tmp directory and writes nothing else.
- [X] T020 [US1] Implement `ingest(meta_kaggle, data_dir, label, threads, memory_limit)` in `src/aimx_recipes/sources/kaggle/__init__.py`, orchestrating inputs → resolve → normalize → write_snapshot and returning a result object. In `src/aimx_recipes/cli/output.py`, render `snapshot` and `counts` (competitions, writeup_refs, writeups_ingested, writeups_excluded by reason, writeups_short) in JSON and text. Make T015 pass.

**Checkpoint**: US1 is independently demonstrable on fixtures. The snapshot exists, every reference is accounted for, and text is exact.

## Phase 4: User Story 2 — Decide the P0 subset auditably (Priority: P1)

**Goal**: Every ingested competition gets a recorded P0 decision with its deciding rule. The reviewed list wins, then the tag rule, then default exclusion. The heuristic proposes candidates in a report and never decides membership.

**Independent Test**: Ingest the fixture with reviewed-list variants. Check:
- the tag-in competition is `in` by `tag`; the modality competition is `out` by `tag`;
- the unreviewed candidate is `out` by `default_exclude` and listed as `unreviewed`;
- reviewed include and exclude entries win, including over a tag-in competition;
- a changed list creates a new membership without re-normalizing text;
- invalid lists fail with the contract codes.

**Depends on**: US1 (snapshot tables).

### Tests for User Story 2

- [X] T021 [P] [US2] Write failing tests in `tests/unit/kaggle/test_membership_rules.py`:
  - the rule file and reviewed list validate against their schemas;
  - strict-YAML duplicate keys → `rule_file_invalid` / `reviewed_list_invalid`;
  - a missing `reason` or `reviewed_by`, a bad `decision`, a bad `reviewed_on` format, and duplicate `competition_id` entries → `reviewed_list_invalid`;
  - an unknown competition id → `reviewed_list_unknown_competition`;
  - a slug mismatch → `reviewed_list_slug_mismatch`;
  - a list entry that matches no heuristic candidate is still honored, with warning `reviewed_list_entry_not_candidate`.
- [X] T022 [P] [US2] Write failing tests in `tests/unit/kaggle/test_signals.py`:
  - tag classes are computed by id, including tag-in plus modality → `modality_excluded`;
  - S1–S5 each fire and fail on fixture rows exactly per [research-heuristic-v0.md](research-heuristic-v0.md): numeric-abbreviation fallback to the metric name, `strip` before S2/S3, keyword threshold 6 in the description versus any hit in the title or subtitle, subject tags such as `games` not negative;
  - review flags;
  - the candidate-expression grammar parses `not S5 and S1 and S3 and (S2 or S4)` with correct precedence, rejects unknown identifiers or tokens and Python syntax such as `__import__`, and never calls `eval`.
- [X] T023 [US2] Add US2 integration tests to `tests/integration/test_ingest_kaggle.py`:
  - a run with the empty list → `membership.status = provisional` and `unreviewed` equal to the fixture's candidate count, with `p0_in` / `p0_out` holding all deciding-rule keys including zeros;
  - a second run with a list that includes the candidate and excludes the tag-in competition → `snapshot.state = existing` and a new `membership_id` with `state = created`; both competitions use `deciding_rule = reviewed_list`, and the old membership directory is byte-unchanged;
  - resolve and normalize are not invoked on the second run (monkeypatch spies);
  - `candidate-report.md` lists the candidate with its signals and status, without body text;
  - when every candidate is reviewed → `status = final`.

### Implementation for User Story 2

- [X] T024 [P] [US2] Author `curation/kaggle/p0-rule.schema.json` and `curation/kaggle/p0-reviewed.schema.json` (Draft 2020-12, closed objects, string scalars, enums and patterns) per [contracts/p0-membership-rules.md](contracts/p0-membership-rules.md).
- [X] T025 [US2] Author `curation/kaggle/p0-rule.yaml` with `rule_version: "1.0.0"` by porting [research-heuristic-v0.md](research-heuristic-v0.md):
  - tag rule ids 14101 and 13209 (include) and 14102, 13207, 14104, 13204, 16072, 14105 (modality), each with its name;
  - S1–S5 patterns and allow-lists;
  - positive and negative tags converted to Tag **ids** resolved from the local `Tags.csv`, names kept beside the ids, with `games`, `board games`, `video games`, and `puzzles` excluded from the negatives;
  - keyword threshold `"6"`, review flags, and the candidate expression.

  It must validate against T024's schema.
- [X] T026 [US2] Implement loading in `src/aimx_recipes/sources/kaggle/membership.py`: read both files from the packaged `_curation` resources via `importlib.resources` with `load_strict_yaml`, validate them with jsonschema, and cross-check reviewed entries against the snapshot's `competitions` table. Map errors to the contract codes. Satisfy T021.
- [X] T027 [US2] Implement in `src/aimx_recipes/sources/kaggle/membership.py`:
  - tag classes by id;
  - signals S1–S5 computed only from snapshot fields: metric label and name, the dataset-description Document text read from `documents.parquet`, title, subtitle, and tag ids;
  - review flags;
  - a small recursive-descent parser and evaluator for the candidate grammar (`S1`..`S5`, `and`, `or`, `not`, parentheses).

  Satisfy T022.
- [X] T028 [US2] Implement precedence and output in `src/aimx_recipes/sources/kaggle/membership.py`:
  - compute the reviewed list → tag → `default_exclude` decision per [data-model.md §4](data-model.md#4-membership-per-snapshot--rule--reviewed-list), and `review_status`;
  - `membership_id` from the canonical rule, the canonical list, and `snapshot_id`;
  - write `membership.parquet` ordered by `competition_id`, `candidate-report.md` (columns and order from the contract), and `manifest.json` with rule and list sha256, counts, and `p0_status` (`final` only when zero candidates are unreviewed);
  - publish through `.tmp-` and rename, returning `existing` when the directory already holds equal content.
- [X] T029 [US2] Extend `src/aimx_recipes/sources/kaggle/__init__.py`:
  - when the computed `snapshot_id` directory already exists, reuse it by reading its adapter tables, without resolving or normalizing again, and report `snapshot.state = existing`;
  - always compute membership afterwards.

  Extend `src/aimx_recipes/cli/output.py` with the `membership` block, the `p0_provisional` and `reviewed_list_entry_not_candidate` warnings, and the membership error codes in JSON and text. Make T023 pass.

**Checkpoint**: Any competition's P0 status is explainable from `membership.parquet`, and the review loop works offline.

## Phase 5: User Story 3 — Emit contract-valid Source, Document, and Problem records (Priority: P2)

**Goal**:
- The snapshot carries 001-valid contract records with deterministic ids.
- Whitespace-duplicate writeups collapse into one Source with mirrors.
- Every Source carries the Meta Kaggle license.

**Independent Test**: Load `records/*.jsonl` and `documents.parquet` from a fixture snapshot into `aimx_recipes.validate_bundle` and get `valid`. The duplicate pair gives one Source with a mirror, listed by both competitions' Problems. A rerun gives identical ids.

**Depends on**: US1. It may run in parallel with US2 except for the shared files `__init__.py`, `output.py`, and `snapshot.py`.

### Tests for User Story 3

- [X] T030 [P] [US3] Write failing tests in `tests/unit/kaggle/test_records.py` for each record builder against [data-model.md §2](data-model.md#2-contract-records-001-v200):
  - **Writeup Source**: kind, `canonical_ref` = `https://www.kaggle.com/competitions/<slug>/discussion/<topicId>`, license `{permissive, Apache-2.0, attribution}`, `content_sha256` equal to its Document hash, `published_at` ending in `Z`, sorted mirrors.
  - **Competition Source**: `content_sha256` over the canonical `{section: text_sha256}`.
  - **Document**: `section` and `normalization_version`.
  - **Problem**: `source_ids` sorted and including the deduplicated writeup Source for both competitions, `as_of` = deadline `Z`, `description` = subtitle or null.
  - Each record passes `aimx_recipes.validate_record`, and no record has extra fields.
- [X] T031 [P] [US3] Write failing tests in `tests/unit/kaggle/test_dedup.py`:
  - grouping by sha256 of whitespace-collapsed, trimmed text;
  - the lowest topic id is canonical, and the other reference has disposition `mirror` with the canonical `source_id`;
  - `writeups.mirror_topic_ids` and `dedup_key` are populated;
  - stored text is unchanged;
  - byte-identical texts within one competition are also grouped;
  - group assignment is independent of input row order.
- [X] T032 [US3] Add US3 integration tests to `tests/integration/test_ingest_kaggle.py`:
  - the fixture snapshot's `records/sources.jsonl`, `documents.jsonl`, and `problems.jsonl`, plus `document_texts` from `documents.parquet`, give `validate_bundle(...).status == "valid"`;
  - counts report `writeup_mirrors = 1` and sources, documents, and problems;
  - with a monkeypatched normalizer that corrupts one document text after hashing, the run exits 1 with `bundle_invalid`, no snapshot directory is published, and no diagnostic contains body text.

### Implementation for User Story 3

- [X] T033 [US3] Implement de-duplication in `src/aimx_recipes/sources/kaggle/normalize.py`: the `dedup_key`, canonical selection, `mirror` dispositions, `mirror_topic_ids`, and Source `mirrors` as canonical refs. Writeup Source rows are keyed by the canonical topic. Satisfy T031.
- [X] T034 [US3] Implement contract record builders in `src/aimx_recipes/sources/kaggle/normalize.py`:
  - writeup and competition Sources, Documents, and Problems with `schema_version` `"2.0.0"` and `entity_type`;
  - `published_at` and `as_of` as RFC 3339 `Z`;
  - the license object, with attribution text "Meta Kaggle (Kaggle), Apache-2.0".

  Satisfy T030.
- [X] T035 [US3] Extend `src/aimx_recipes/sources/kaggle/snapshot.py` to write `records/sources.jsonl`, `records/documents.jsonl`, and `records/problems.jsonl` as canonical JSON Lines sorted by id, included in the manifest outputs. Extend `src/aimx_recipes/sources/kaggle/__init__.py` to run `aimx_recipes.validate_bundle(records, context=ValidationContext(document_texts=...))` before publishing:
  - any status other than `valid` → error `bundle_invalid`, reporting diagnostic codes and record ids only;
  - nothing is published.

  Extend `src/aimx_recipes/cli/output.py` with the `writeup_mirrors`, `sources`, `documents`, and `problems` counts. Make T032 pass.

**Checkpoint**: Snapshots are consumable by 003, 005, and 006 through the 001 contracts, and the identity is stable.

## Phase 6: User Story 4 — Reproduce and compare snapshots (Priority: P3)

**Goal**:
- Snapshots are immutable and byte-reproducible for a locked writer.
- A changed input creates a new snapshot.
- Conflicts and writer-only differences are handled as the contract specifies.
- The manifest is complete.

**Independent Test**: Run ingest on the fixture twice with different `--threads` and compare directory hashes. Ingest a mutated copy, then compare manifests. Tamper with an existing snapshot's content and observe the conflict.

**Depends on**: US1. Run it after US3, so that records are included in the determinism checks.

### Tests for User Story 4

- [X] T036 [US4] Write failing tests in `tests/integration/test_ingest_determinism.py`:
  - **Rerun**: two runs at `--threads 1` and `--threads 4` give `existing` / `existing` on the second run, and every file under the snapshot and membership directories keeps the same sha256.
  - **Changed input**: appending a team writeup row to a fixture copy gives a new `snapshot_id`, and the old directory is unchanged.
  - **Conflict**: rewriting one row of an existing snapshot's `writeups.parquet` (different content, same id) → exit 1 `snapshot_conflict`, with nothing written or modified.
  - **Writer-only difference**: rewriting an existing Parquet file with a different compression (same rows) → `existing` plus warning `writer_version_differs`, and the file is left as-is.
  - **Manifest**: it contains the inputs (`name`, `size_bytes`, `sha256`, `rows`), outputs (`path`, `rows`, `file_sha256`, `content_sha256`), counts, and `environment` (package version, Python, duckdb, `parquet_created_by`, `uv_lock_sha256` or null). It contains no timestamp key or value, and `run_started_at` appears only in CLI output.
  - **Temp directories**: `.tmp-` directories left by a simulated crash are ignored and never reported as snapshots.

### Implementation for User Story 4

- [X] T037 [US4] Extend `src/aimx_recipes/sources/kaggle/snapshot.py` for an existing snapshot directory:
  - compare the recomputed logical `content_sha256` of each output with the manifest and the files;
  - equal content and equal bytes → `existing`;
  - equal content and different bytes → `existing` plus `writer_version_differs`;
  - different content → `snapshot_conflict`.

  Also: ignore `.tmp-` siblings, remove the run's own tmp directory on failure, and fsync before rename.
- [X] T038 [US4] Complete the manifest `environment` in `src/aimx_recipes/sources/kaggle/snapshot.py`:
  - `importlib.metadata` package version and `platform.python_version()`;
  - `duckdb.__version__`;
  - the Parquet footer `created_by` via DuckDB `parquet_metadata`;
  - sha256 of `uv.lock` when it is found beside the package's project root, else null.

  Make the membership manifest carry the same environment block.
- [X] T039 [US4] Wire `writer_version_differs` and `snapshot_conflict` through `src/aimx_recipes/sources/kaggle/__init__.py` and `src/aimx_recipes/cli/output.py`, in JSON and text. Make T036 pass.

**Checkpoint**: Snapshots are reproducible and immutable, and the conflict paths are tested.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Contract agreement, packaging, reference acceptance, and documentation.

- [X] T040 [P] Extend `tests/integration/test_installed_wheel.py`:
  - the wheel's `aimx_recipes/_curation/**` files byte-match `curation/**`;
  - the installed `aimx-recipes ingest kaggle --help` runs offline outside the checkout;
  - an installed-wheel ingest of the `mini` fixture into a temp `--data-dir` exits 0, which proves the packaged rule files load.
- [X] T041 [P] Extend `tests/contract/test_cli_ingest_contract.py` with:
  - **Text/JSON agreement**: for success, provisional, and each error path, every count and code in the text output equals the JSON (SC-007).
  - **No leaks**: no output, error, manifest, or candidate report contains any fixture body marker string.
  - **No writes elsewhere**: the set of files outside `--data-dir` is unchanged after a run (snapshot of `tmp_path` siblings and the repository's `curation/` and `schemas/` mtimes).
- [X] T042 [P] Create the opt-in reference test `tests/integration/test_ingest_reference.py`. It is skipped unless `AIMX_RECIPES_META_KAGGLE` is set, and writes into `tmp_path`. It asserts:
  - 6,276 refs, of which 3 are `empty_text`, 1 is a mirror, and 0 are other exclusions;
  - 107 short writeups and 618 competitions;
  - tag classes 178 / 173 / 113 / 154;
  - 101 heuristic candidates with an empty reviewed list, and `membership.status = provisional`;
  - the bundle is `valid`;
  - wall time under 30 minutes (SC-008);
  - a second run reports `existing` with identical file hashes.

  If the candidate count differs from 101, the test fails with a message pointing to [research-heuristic-v0.md](research-heuristic-v0.md).
- [X] T043 Run `AIMX_RECIPES_META_KAGGLE=~/data/kaggle/meta-kaggle uv run pytest tests/integration/test_ingest_reference.py -q` and the [quickstart.md](quickstart.md) scenarios 1–6 on Python 3.12 and 3.13. Record exact commands, counts, timings, snapshot and membership ids, and any deviations in a new `specs/002-meta-kaggle-ingest/checklists/implementation-validation.md`. Do not edit expected figures to match: a mismatch must be explained or fixed.
- [X] T044 [P] Update the docs in `README.md`, `README.zh-CN.md`, `docs/DATA_SOURCES.md`, and `ARCHITECTURE.md`:
  - `README.md` and `README.zh-CN.md`: `ingest kaggle` usage, local-only data, and the review loop;
  - `docs/DATA_SOURCES.md` §3.3: replace "Spec 002 decides the final rule" with the C-16 rule and corrected spike figures (107 short, whitespace-collapsed duplicate);
  - `ARCHITECTURE.md` §4.1: all writeups ingested, P0 as a membership flag, raw layout link.

  Do not touch `ROADMAP.md` (status changes go through `/speckit.roadmap.write`).
- [X] T045 Run the full suite on both interpreters (`uv run --python 3.12 pytest -q`, `uv run --python 3.13 pytest -q`). Confirm that `git status` shows no files under `data/` and no source text in tracked files. Hand the reference `candidate-report.md` path and the [research-p0-candidates.md](research-p0-candidates.md) seed to the curator, and record it in `checklists/implementation-validation.md`. SC-004 (`final`) is a curation gate after implementation, not an implementation task.

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends on |
| --- | --- |
| Setup (T001–T004) | nothing. T002 and T003 are [P] after T001; T004 after T003. |
| Foundational (T005–T012) | Setup. It blocks all stories. |
| US1 (T013–T020) | Foundational |
| US2 (T021–T029) | US1 |
| US3 (T030–T035) | US1 |
| US4 (T036–T039) | US1, and in practice after US3, so records are covered |
| Polish (T040–T045) | all stories |

### User Story Dependencies

```text
Setup → Foundation → US1 ─┬─► US2 ─┐
                          └─► US3 ─┴─► US4 → Polish
```

- US2 needs the snapshot's `competitions` and `documents` tables (dataset descriptions for S2/S3).
- US3 needs normalized rows. It is independent of membership.
- US4 verifies reproducibility over everything a snapshot contains.

### Within Each User Story

1. Tests first, confirmed failing for the intended reason.
2. Then data and loader code: inputs, rules, and records.
3. Then logic: resolution, signals, de-duplication.
4. Then writing and publishing.
5. Then orchestration and CLI wiring last, because `__init__.py` and `output.py` are shared.

### Parallel Opportunities

| Phase | Parallel tasks |
| --- | --- |
| Setup | T002 ∥ T003 |
| Foundation | T005 ∥ T007 ∥ T009 ∥ T011 (four test files); then implementations T006 ∥ T008 ∥ T010 ∥ T012 (disjoint files) |
| US1 | T013 ∥ T014. T015 is serialized because it starts the shared integration file. T016 ∥ T017 are disjoint modules. |
| US2 ∥ US3 | after US1, two developers can proceed side by side. Disjoint: `membership.py` and `curation/` (US2) vs `normalize.py` (US3). Serialized between them: `__init__.py`, `output.py`, `snapshot.py`, and `tests/integration/test_ingest_kaggle.py` (T023, T029 vs T032, T035). |
| Within US2 | T021 ∥ T022 ∥ T024 |
| Within US3 | T030 ∥ T031 |
| Polish | T040 ∥ T041 ∥ T042 ∥ T044 |

## Parallel Example: User Story 1

```text
# Tests together (disjoint files):
T013 tests/unit/kaggle/test_inputs.py
T014 tests/unit/kaggle/test_resolve.py
# Then implementations of disjoint modules together:
T016 src/aimx_recipes/sources/kaggle/inputs.py
T017 src/aimx_recipes/sources/kaggle/resolve.py
# Then serially: T018 normalize.py → T019 snapshot.py → T020 __init__.py + cli/output.py (makes T015 pass)
```

## Parallel Example: User Story 2 ∥ User Story 3

```text
Developer A (US2): T021, T022, T024 → T025 → T026 → T027 → T028
Developer B (US3): T030, T031 → T033 → T034
Then serially: T029 (US2 wiring) → T032/T035 (US3 wiring) [shared __init__/output/snapshot/integration test]
```

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Setup and Foundation.
2. Complete US1 (T013–T020).
3. **Stop and validate**: ingest the `mini` fixture, and optionally the real snapshot by hand, checking that every reference is accounted for and texts are exact.

The MVP gives a pinned local corpus. P0 selection and contract records follow.

### Incremental Delivery

1. Add US2 so P0 membership and the review loop work offline. The curator can start reviewing with a `provisional` membership.
2. Add US3 so contract records are valid, which makes the snapshot usable by 003, 005, and 006.
3. Add US4: reproducibility and immutability guarantees.
4. Polish: reference acceptance on Python 3.12 and 3.13, packaging, and docs.

Implementation is complete with `provisional` P0. Reaching `final` (SC-004) is the curator's gate before handing over to 003 (roadmap Q7).

## Notes

- Never edit `schemas/` or the 001 modules (`validation.py`, `contextual.py`, `models.py`, `schema_registry.py`, `diagnostics.py`). 002 consumes them through the public API only.
- Do not write to `data/` in tests, and never commit snapshot outputs.
- Error and warning messages never include source rows or body text.
- After implementation, run `/speckit.roadmap.debrief`. Its after_implement hook is registered.
