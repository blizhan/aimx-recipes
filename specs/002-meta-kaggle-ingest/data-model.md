# Data Model: Meta Kaggle Source Adapter & Corpus Normalization

**Date**: 2026-11-03 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

This feature adds two kinds of data:

- **Contract records** (Source, Document, Problem) that conform unchanged to the 001 contracts, version 2.0.0.
- **Adapter tables** that hold Kaggle-specific metadata, keyed by contract ids. Contract records reject unknown fields, so these live separately ([research R11](research.md#r11-integration-with-the-001-contracts)).

All raw outputs are local-only, under the gitignored data directory. Only the rule files and the reviewed list are git-tracked; they contain identifiers, decisions, and reasons, never source text. Consumer-facing layout and guarantees are in [contracts/raw-snapshot.md](contracts/raw-snapshot.md).

## 1. Identities

| Identity | Format | Derived from | Stable across snapshots |
| --- | --- | --- | --- |
| `snapshot_id` | `meta-kaggle-<h16>` | first 16 hex characters of sha256 over canonical JSON `{inputs: [{name, sha256}] sorted by name, normalization_version, adapter_version}` | no: a new input, normalization, or adapter version gives a new id |
| Writeup `source_id` | `kaggle:writeup:<topicId>` | canonical (lowest) forum topic id of the de-duplication group | yes |
| Competition `source_id` | `kaggle:competition:<competitionId>` | `Competitions.Id` | yes |
| Writeup `document_id` | `kaggle:writeup:<topicId>:body:<t12>` | source id + first 12 hex characters of the text's sha256 | only while the text is unchanged |
| Competition `document_id` | `kaggle:competition:<competitionId>:<section>:<t12>` | source id + section + text hash | only while the text is unchanged |
| `problem_id` | `kaggle:problem:<competitionId>` | `Competitions.Id` | yes |
| `membership_id` | `p0-<h16>` | sha256 over the canonical rule file, the canonical reviewed list, and `snapshot_id` | per rule, list, and snapshot |

All ids match the 001 id pattern `^[A-Za-z0-9][A-Za-z0-9._:/-]*$`. Ids never depend on row order or wall-clock time (FR-010). Contract records carry `snapshot_id`, so a record is identified by `(id, snapshot_id)` across snapshots.

Versions:

| Version | Starts at | Bumped when |
| --- | --- | --- |
| `adapter_version` | `1.0.0` | any change to output content for the same input |
| `normalization_version` | `kaggle-text-1` | stored text changes. Text is exact source text after CSV decoding; empty means absent. |
| Rule `rule_version` | `1.0.0` | inside the rule file (§5) |

## 2. Contract records (001 v2.0.0)

### Source (writeup)

| Field | Value |
| --- | --- |
| `source_id` | `kaggle:writeup:<topicId>` |
| `kind` | `writeup` |
| `canonical_ref` | `https://www.kaggle.com/competitions/<slug>/discussion/<topicId>` |
| `license` | `{status: permissive, identifier: Apache-2.0, attribution: "Meta Kaggle (Kaggle), Apache-2.0"}` |
| `snapshot_id` | current snapshot |
| `content_sha256` | sha256 of the stored body text (UTF-8); equals its Document's hash |
| `published_at` | `ForumMessages.PostDate` as UTC `…Z` |
| `mirrors` | canonical refs of the other references in the de-duplication group, sorted; `[]` if none |

### Source (competition page)

| Field | Value |
| --- | --- |
| `source_id` | `kaggle:competition:<competitionId>` |
| `kind` | `competition_page` |
| `canonical_ref` | `https://www.kaggle.com/competitions/<slug>` |
| `license` | as for writeups |
| `content_sha256` | sha256 of canonical JSON `{section: text_sha256}` over its Documents |
| `published_at` | `EnabledDate` as UTC |
| `mirrors` | `[]` |

### Document

| Field | Value |
| --- | --- |
| `document_id`, `source_id`, `snapshot_id` | per §1 |
| `section` | `writeup_body`, `competition_overview`, `competition_evaluation_metric`, or `competition_dataset_description` |
| `content_sha256` | `sha256(text.encode("utf-8"))`, exactly as 001 contextual validation checks |
| `normalization_version` | `kaggle-text-1` |
| `title` | writeup topic title, or competition title for competition sections |

A section with absent text produces no Document. Sections are defined in [research R4](research.md#r4-competition-context-fields).

### Problem

| Field | Value |
| --- | --- |
| `problem_id` | `kaggle:problem:<competitionId>` |
| `kind` | `competition` |
| `title` | competition title |
| `source_ids` | the competition Source, plus every writeup Source whose de-duplication group has a reference in this competition, sorted |
| `description` | competition subtitle, or null |
| `as_of` | `DeadlineDate` as UTC, or null |

Every record carries `schema_version: "2.0.0"` and its `entity_type`. One Problem exists per ingested competition, regardless of P0 membership. Problem Profiles are out of scope (005).

## 3. Adapter tables (snapshot, immutable)

Each table is written once per snapshot and sorted by its key. Timestamps are naive `TIMESTAMP` values documented as UTC.

### `competitions` — key `competition_id`

One row per competition with at least one writeup reference.

| Column group | Columns |
| --- | --- |
| Identity | `competition_id`, `slug`, `source_id`, `problem_id`, `title`, `subtitle`, `url` |
| Context | `host_segment`, `enabled_at`, `deadline_at` |
| Metric | `metric_abbreviation`, `metric_name`, `metric_label` (abbreviation unless numeric, then name), `higher_is_better` |
| Licensing | `competition_data_license` (informational, FR-011) |
| Tags | `tag_ids` (sorted list), `tag_names` |
| Counts | `writeup_refs`, `writeups_ingested` |

### `writeup_refs` — key `topic_id`

One row per team writeup reference: 6,276 on the reference snapshot (SC-001).

| Column | Meaning |
| --- | --- |
| `topic_id`, `team_id`, `competition_id` | reference identity |
| `message_id` | first forum message id, null if unresolved |
| `disposition` | `ingested`, `mirror`, or `excluded` |
| `exclusion_reason` | when `excluded`: `topic_not_found`, `first_message_missing`, `message_not_found`, `empty_text` |
| `source_id` | the writeup Source this reference belongs to; null when excluded |

`mirror` means the reference is part of an ingested Source whose canonical topic is another reference. Each reference therefore ends as exactly one of: ingested (directly or as a mirror), or excluded with a reason (FR-003).

### `writeups` — key `source_id`

One row per writeup Source.

| Column group | Columns |
| --- | --- |
| Identity | `source_id`, `document_id`, `topic_id`, `message_id`, `team_id`, `competition_id` |
| Text facts | `topic_title`, `posted_at`, `body_format` (`markdown` or `html`), `char_count` (code points), `is_short` (`char_count < 200`) |
| Team outcome | `medal` (`gold`, `silver`, `bronze`, or null), `public_rank`, `private_rank` (null when absent) |
| Grouping | `dedup_key` (sha256 of whitespace-collapsed text), `mirror_topic_ids` (sorted list) |

### `documents` — key `document_id`

| Column | Meaning |
| --- | --- |
| `document_id`, `source_id`, `section` | identity |
| `text` | exact stored text; the only place full text lives |
| `content_sha256` | sha256 of `text` |
| `char_count` | length in code points |

Text round-trips byte-for-byte, because 005 computes quote offsets against it.

### `records/` — contract records

`sources.jsonl`, `documents.jsonl`, and `problems.jsonl` hold canonical JSON Lines sorted by id. These are what 001 validates as one bundle.

## 4. Membership (per snapshot × rule × reviewed list)

Written under `membership/<membership_id>/`. Each membership directory is immutable, and a new rule file or reviewed list yields a new `membership_id` (US2-4).

### `membership` — key `competition_id`

One row per ingested competition (SC-003).

| Column | Meaning |
| --- | --- |
| `competition_id`, `slug` | identity |
| `p0` | `in` or `out` |
| `deciding_rule` | `reviewed_list`, `tag`, or `default_exclude` |
| `tag_class` | `tag_in`, `modality_excluded`, `other_tags`, or `untagged` |
| `reviewed_decision`, `reviewed_reason` | from the list entry, null if not listed |
| `heuristic_pool` | true if `tag_class` is `other_tags` or `untagged` |
| `signals` | sorted list from S1–S5 that fired |
| `candidate` | heuristic rule result: `¬S5 ∧ S1 ∧ S3 ∧ (S2 ∨ S4)` |
| `review_flags` | sorted list |
| `review_status` | `reviewed_include`, `reviewed_exclude`, `unreviewed`, or `not_candidate` |

Precedence (FR-007):

```text
reviewed list entry? → its decision        (deciding_rule = reviewed_list)
tag_class = tag_in → in                    (deciding_rule = tag)
tag_class = modality_excluded → out        (deciding_rule = tag)
otherwise → out                            (deciding_rule = default_exclude)
```

The heuristic never decides membership.

### `candidate-report.md`

A human-readable table of every candidate and borderline competition with signals, flags, and review status. It holds slugs, titles, and metrics, never body text.

### `manifest.json`

Records the membership id, snapshot id, rule and list sha256, rule version, counts, `p0_status`, and output hashes. `p0_status` is `final` only when no candidate is `unreviewed`; otherwise it is `provisional` (SC-004).

## 5. Git-tracked rule data

Location: `curation/kaggle/`. It is packaged like `schemas/`, through the tracked symlink `src/aimx_recipes/_curation -> ../../curation` and a wheel force-include.

| File | Content |
| --- | --- |
| `p0-rule.yaml` | `rule_version`; tag-rule ids with names; heuristic signal definitions (metric allow-list, tabular-file and media patterns, keyword threshold, positive/negative tag lists, hard-negative metrics); the candidate expression |
| `p0-rule.schema.json` | JSON Schema for the rule file |
| `p0-reviewed.yaml` | `entries:` sorted by `competition_id` |
| `p0-reviewed.schema.json` | JSON Schema for the reviewed list |

Each reviewed-list entry has:

| Field | Meaning |
| --- | --- |
| `competition_id` | decimal string |
| `slug` | checked against the snapshot |
| `decision` | `include` or `exclude` |
| `reason` | non-empty |
| `reviewed_by` | non-empty; a person, never a model |
| `reviewed_on` | `YYYY-MM-DD` string |

Validation rules:
- Both YAML files are read with the strict loader: duplicate keys are rejected and scalars stay strings.
- Both are then validated against their schemas.
- An entry whose id is not in the snapshot, whose slug mismatches, or that is duplicated is an error (US2-5).

## 6. Manifest (snapshot)

`data/raw/kaggle/<snapshot_id>/manifest.json`, canonical JSON:

| Field | Content |
| --- | --- |
| `snapshot_id`, `adapter_version`, `normalization_version`, `contract_schema_version` | `"2.0.0"` for the contract version |
| `inputs[]` | `{name, size_bytes, sha256, rows}` for the six required files |
| `outputs[]` | `{path, rows, file_sha256, content_sha256}` |
| `counts` | competitions, refs, ingested, mirrors, excluded by reason, short, sources/documents/problems |
| `environment` | `{package_version, python, duckdb, parquet_created_by, uv_lock_sha256}` |
| `label` | optional user-supplied label (for example the download date), not part of the id |

The manifest contains no wall-clock time. The run timestamp appears only in CLI output.

## 7. State transitions

```text
ingest run
  ├─ verify inputs (headers, stat, sha256)        ── fail → no write
  ├─ compute snapshot_id
  │    ├─ dir exists, content hashes equal ──► snapshot.state = existing (untouched;
  │    │                                        warning writer_version_differs if bytes differ)
  │    ├─ dir exists, content differs     ──► error snapshot_conflict (no write)
  │    └─ absent → resolve, normalize, validate bundle (must be `valid`)
  │              → write to .tmp-<random>/ → fsync → rename ──► snapshot.state = created
  └─ compute membership_id (rule + list + snapshot)
       ├─ exists with equal content ──► membership.state = existing
       └─ absent → evaluate rule, heuristic, list → write tmp → rename ──► membership.state = created
```

Membership can be recomputed without re-reading text: a changed list on an existing snapshot only reads adapter tables. Input hashing still runs, because it determines the snapshot id.
