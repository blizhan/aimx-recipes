# Research: Meta Kaggle Source Adapter & Corpus Normalization

**Date**: 2026-11-03 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Three read-only worker subagents collected evidence. Each ran against one of:
- the local Meta Kaggle download (`~/data/kaggle/meta-kaggle/`, dated 2026-11-01);
- library experiments in scratch directories;
- this repository's 001 contracts and code.

No repository or source file was modified. Figures below are measured unless marked otherwise. Warm-cache timings are from a 20-core aarch64 workstation with 121 GB RAM.

The heuristic's v0 candidate tables for curator review are kept in [research-p0-candidates.md](research-p0-candidates.md).

## R1. Input files and parsing

**Decision**: Read CSVs with DuckDB `read_csv` using an explicit dialect and no sniffing:

```sql
read_csv(<file>, auto_detect=false, header=true, delim=',', quote='"', escape='"',
         columns=<all VARCHAR, from the validated header>, strict_mode=true,
         allow_quoted_nulls=false, max_line_size=8388608)
```

- Validate each header first with stdlib `csv.reader`. A missing or renamed required column fails the run before any write, naming the file and column. Extra upstream columns are tolerated.
- Filter writeups early with semi-joins: Teams → ForumTopics → ForumMessages.
- Fail on the first malformed row. Report file, line, and the row's leading id. Never echo the full row, which is untrusted and can be hundreds of KB.
- Treat both quoted `""` and empty fields as absent; the source cannot distinguish them.
- Do not pass `new_line`.

**Rationale**:
- DuckDB, stdlib `csv`, and pyarrow agree on every row count and on the hash of all 6,276 writeup bodies.
- Row counts: Competitions 12,755; Teams 9,635,813; ForumTopics 513,417; ForumMessages 2,882,918; Tags 836; CompetitionTags 1,313.
- Records are CRLF-terminated, with embedded newlines in 902,234 messages. The largest record is about 751 KB.
- The full strict read plus writeup resolution takes 1.8–5.9 s and 0.9–2.6 GB RSS, depending on threads.

Pitfalls found:
- With sniffing on, malformed fixtures "succeed": the sniffer falls back to a `|` delimiter and one column.
- An explicit `new_line` returns 0 rows silently in DuckDB 1.5.6 and 2.0.0.
- `columns=` does not verify header names.
- A `max_line_size` of 256 MiB exhausts a 1 GB memory limit.

**Alternatives**:
- pyarrow.csv: accepted an unterminated quote silently, errors carry no file or line, and it adds 149 MB.
- stdlib `csv` only: correct and low-memory, but 20–30 s. It is kept as header validator and test oracle.

## R2. Dates and time zone

**Decision**: Parse every date with `%m/%d/%Y %H:%M:%S` (Teams dates are date-only and unused) and interpret it as **UTC**. Parquet stores naive `TIMESTAMP` values documented as UTC. Contract records emit RFC 3339 with `Z`, which common.schema requires. DuckDB connections set `TimeZone='UTC'` and never cast naive values to `TIMESTAMPTZ`.

**Rationale**:
- Kaggle API timestamps (`…Z`) matched the CSV values exactly for 10 of 10 live competitions.
- 88% of deadlines are 23:59:00.
- Casting naive values to `TIMESTAMPTZ` under a non-UTC session zone changed both the stored values and the file bytes.

**Note for 003**: 179 writeups are posted before their competition's `DeadlineDate`. Forecasting and code competitions set the deadline at the end of scoring. As-of filtering must use the writeup's own post date, not the competition deadline.

## R3. Tag rule

**Decision**: Key the tag rule on Tag **ids**, not names or slugs:

| Role | Tag (id) |
| --- | --- |
| In | `tabular` (14101), `time series analysis` (13209) |
| Excluded modality | `image` (14102), `computer vision` (13207), `text` (14104), `nlp` (13204), `audio` (16072), `video` (14105) |

Names are kept beside the ids for readability. Task-level variants such as `image classification` stay **out of the tag rule**, as spec FR-007 lists only these six tags. They act as negative signals in the heuristic (R6).

**Rationale**:
- Slugs differ from names: `computer vision` has slug `image-processing`.
- `FullPath` disagrees with the parent links for 172 tags.
- None of the eight rule tags has child tags, so a hierarchy-aware rule changes nothing.
- Adding the task-level modality tags to the rule changes no P0 membership. Adding `signal processing` would wrongly drop 5 tag-in competitions.

Class counts are confirmed:

| Class | Competitions | Writeups |
| --- | --- | --- |
| Tag-in | 178 | 1,570 |
| Modality-excluded | 173 | 2,535 |
| Other tags only | 113 | 1,721 |
| Untagged | 154 | 450 |

## R4. Competition context fields

**Decision**: Competition context is three Documents with **exact source text**:

| Section | Source column | Notes |
| --- | --- | --- |
| `competition_overview` | `Overview` | Markdown headers wrapping HTML; 441 of 618 contain HTML. It contains the competition-specific `# Evaluation` page for 611 of 618. |
| `competition_evaluation_metric` | `EvaluationAlgorithmDescription` | Generic metric blurb; median 49 characters, empty for 38. |
| `competition_dataset_description` | `DatasetDescription` | Empty for 3. |

Empty values produce no Document.

The spec's "evaluation description" therefore resolves into two parts. The generic metric description becomes its own Document. The competition-specific evaluation text stays inside the overview Document and is not split out. Splitting markdown would create synthesized text whose offsets do not match the source, and 001 forbids quote normalization. Locating the `# Evaluation` page for the context bundle is a 005 concern.

Metric fields:
- Use `EvaluationAlgorithmAbbreviation` when it is non-numeric, else `EvaluationAlgorithmName`. 126 competitions from 2023 on carry a numeric id as abbreviation.
- `EvaluationAlgorithmIsMax` maps to `higher_is_better`; it is never empty for the 618.

Other fields:
- `HostName` is empty for all 618 and is not used.
- `LicenseName` is the competition **data** license (for example CC BY-NC). It is stored only as informational metadata (spec FR-011).

**Alternatives**:
- Splitting `# Evaluation` out of the overview: rejected, because it is synthesized text and loses offset fidelity.
- `EvaluationAlgorithmName` + description as one text: rejected, because it is also synthesized.

## R5. Writeups, identity, and de-duplication

**Decision**:
- **Body**: `RawMarkdown` if non-empty (`body_format = markdown`), else `Message` (`body_format = html`). Neither present means exclusion with reason `empty_text`.
  - Counts: 6,120 use markdown, 153 use HTML, 3 are empty.
  - "Short" means fewer than 200 Unicode code points in the selected body: **107** writeups (92 markdown, 15 HTML). The spec's earlier 65 measured the HTML body for every writeup and has been corrected.
- **Canonical reference**: `https://www.kaggle.com/competitions/<slug>/discussion/<topicId>`. It was verified live: it 301-redirects to `/writeups/<writeup-slug>` for writeups from 2010–2026. The writeup slug cannot be derived from Meta Kaggle.
- **De-duplication key**: sha256 of the body with every whitespace run collapsed to one space and the ends trimmed.
  - Byte-identical duplicates: 0. Whitespace-collapsed duplicates: 1 pair, topics 95174 and 95176. That pair is the same author and title, cross-posted to `landmark-retrieval-2019` and `landmark-recognition-2019` 7 minutes apart.
  - The lowest topic id is canonical; the other reference becomes a mirror (its canonical URL is listed in `Source.mirrors`).
  - The key is used **only** for grouping. Stored text is never altered.
- **Team outcome**: Medal `1/2/3` → gold/silver/bronze; `0` or empty → none. 31 writeup teams have no leaderboard ranks; those stay absent.
- No column marks new-style 2024+ writeups (`ForumTopics.KernelId` is always empty), so no such flag is recorded.

## R6. P0 heuristic (candidate proposal only)

**Decision**: The heuristic runs over competitions that are `out` by tag rule or default and are not modality-excluded: 267 competitions / 2,171 writeups. It uses five deterministic signals computed from snapshot fields:

| Signal | Definition (summary) | Pool hits (competitions / writeups) |
| --- | --- | --- |
| S1 tabular metric | Metric (abbreviation, or name when the abbreviation is numeric) in an allow-list of tabular / time-series metric families | 187 / 1,118 |
| S2 tabular files | Dataset description mentions `.csv/.parquet/.feather/.tsv/.xls(x)` and no media file extension (after stripping images and URLs) | 178 / 1,447 |
| S3 no media | No media extension in the dataset description, no image/audio/video/text keyword ≥ 6 times there, and none in title or subtitle | 183 / 1,361 |
| S4 positive tag | A tag from a tabular task or domain allow-list, and no negative tag | 37 / 418 |
| S5 hard negative | Non-tabular metric (optimization, simulation, detection, segmentation, text generation, ARC, CTF, …) or a negative technique/task tag (simulations, reinforcement learning, optimization, signal processing, multimodal, image-/text-/audio-/video- task tags, …) | 90 / 1,280 |

Candidate rule `¬S5 ∧ S1 ∧ S3 ∧ (S2 ∨ S4)` → **101 competitions / 670 writeups**. Review flags (`bioseq`, `non_english`, `thin_dataset_desc`, `signal`) pre-sort them for curators.

- Known tabular classics are caught: TalkingData, Santander Value, Zillow, Recruit Restaurant, Microsoft Malware, Criteo, Avazu, Amazon Employee Access, March Mania ×9, WiDS, and others.
- About 10 likely false positives remain: images with non-English subtitles, product images, RNA/protein/molecule sequences, and text.
- About 30 borderline rejections are worth review: old, thin descriptions without file mentions, plus signal-processing time series such as LANL Earthquake.

The signal allow-lists and patterns are **versioned rule data** in git, not code constants. The heuristic only proposes candidates (C-16).

**Rationale**:
- All 16 Santa/optimization, 17 simulation/RL, 3 ARC, and 2 CTF competitions are hard-excluded correctly.
- Subject tags such as `games` are not negative: excluding them would drop `data-science-bowl-2019` and the MCTS game-strength competition.

**Alternatives**:
- Automatic inclusion by heuristic: rejected by the user and C-16.
- Adding `signal processing` to the tag rule: rejected (R3).

## R7. Deterministic output

**Decision**: Write every Parquet output with:

```sql
COPY (<query> ORDER BY <unique key>) TO '<tmp>' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 122880)
```

Connection and file settings:
- `SET TimeZone='UTC'`.
- `SET autoinstall_known_extensions=false; SET autoload_known_extensions=false;` keeps the run offline.
- Explicit column casts.
- Write to a temporary directory, then rename it atomically.

Contract records and other JSON outputs are canonical JSON Lines: `sort_keys`, `ensure_ascii=False`, compact separators, sorted by id.

Each output has two hashes in the manifest:
- `file_sha256`, over the file bytes;
- `content_sha256`, a logical hash computed in Python over canonical JSON lines of the rows, sorted by key.

The manifest also records the writer (`duckdb` version and Parquet `created_by`), Python version, package version, and `uv.lock` sha256.

**FR-012 interpretation**:
- Byte identity is guaranteed for the same locked writer version.
- If a rerun finds the snapshot directory with equal `content_sha256` values but different file bytes (only possible after a writer upgrade), the existing snapshot is left untouched. The run reports `snapshot.state = existing` with warning `writer_version_differs`.
- Unequal content under the same snapshot id is an error: `snapshot_conflict`, nothing written.

**Rationale**:
- With a total `ORDER BY`, output was byte-identical across runs and at 1, 4, and 20 threads. Without it, 20 threads gave 3 different files in 4 runs.
- DuckDB 1.5.6 and 2.0.0 write different data pages for identical data, while the logical hash is equal.

**Alternatives**:
- pyarrow writer: deterministic and more stable across versions, but adds 149 MB, which neither 002 nor 006 needs.
- JSONL-only raw layer: rejected, because ARCHITECTURE §3 and constitution VII fix Parquet for the raw layer.

## R8. Input fingerprints

**Decision**: Compute sha256 of every required input on every run with `hashlib.file_digest`. There is no size/mtime cache. `stat` (size, `st_mtime_ns`, inode) is checked before hashing and after parsing; any change fails the run with `input_changed_during_run`. The manifest records name, size, sha256, and row count.

**Rationale**: The six required files total 2.82 GB and hash in about 1.4 s (cold reads are SHA-bound at about 2 s). A cache could be fooled by `cp -p` or by a re-download.

## R9. Dependencies and CLI

**Decision**: Add two runtime dependencies:
- `duckdb>=2.0,<3`: MIT, abi3 wheels for Python 3.12–3.14, no transitive dependencies.
- `pyyaml>=6.0.3,<7`: MIT.

No pyarrow. Exact versions are pinned by `uv.lock`.

The CLI uses stdlib **argparse**:
- nested subparsers (`ingest` → `kaggle`);
- `main(argv: list[str] | None = None) -> int`;
- `exit_on_error=False` plus an overridden `error()`, so usage errors still produce the JSON error envelope under `--json`;
- console entry point `aimx-recipes = "aimx_recipes.cli:main"`.

**Rationale**:
- DuckDB covers strict CSV, joins, and deterministic Parquet, and 006 builds its index on it.
- DuckDB 2.0.0 is 13 days old and removed `DuckDBPyRelation.fetchone()`. Code uses `con.execute(...).fetchone()`. 1.5.6 is a drop-in fallback for the SQL used here.
- Avoid `.arrow()` and `register(<arrow>)`, which require pyarrow. Load Python records into DuckDB through canonical NDJSON and `read_json`: 0.06 s for 7,000 rows.
- argparse adds no dependency and leaves stdout under program control.

**Alternatives**:
- click: acceptable and light, but unnecessary for about 9 subcommands.
- typer: rejected; it pulls in rich and is pre-1.0 with a vendored click.

## R10. Reviewed list format

**Decision**: Use YAML read by one shared **strict loader** (`aimx_recipes.yaml_strict`): a PyYAML `SafeLoader` subclass that rejects duplicate keys and keeps every scalar except `null` as a string. A JSON Schema then validates the result. Spec 004 reuses the same loader for recipes.

**Rationale**:
- PyYAML `safe_load` silently keeps the last duplicate key and turns `no` into False, `0123` into 83, and dates into `date` objects.
- ruamel.yaml rejects duplicate keys but still types dates and numbers.
- JSON Schema cannot see duplicate keys.
- YAML allows curator comments, and one entry per block diffs cleanly.

**Alternatives**:
- JSON: no comments, noisier diffs.
- CSV/TSV: quoting of free-text reasons, and a second format beside 004's YAML.

## R11. Integration with the 001 contracts

**Decision**: Keep contract version **2.0.0 unchanged**:
- Source, Document, and Problem records carry only contract fields.
- Kaggle-specific metadata lives in adapter tables keyed by contract ids: medal, ranks, tags, metric, dates, body format, short flag, data license, membership, and exclusions.

The adapter validates every record set with `aimx_recipes.validate_bundle(records, context=ValidationContext(document_texts=...))` and requires status `valid`.

Facts from 001 that shape the design:
- `Document.content_sha256` must equal `sha256(text.encode("utf-8"))` with no normalization.
- All contract records reject unknown fields (`additionalProperties: false`).
- ids match `^[A-Za-z0-9][A-Za-z0-9._:/-]*$`.
- `snapshot_id` is non-empty text.
- License requires `{status, identifier, attribution}`, with a non-blank identifier when the status is `permissive`.
- `Source.kind` already has `writeup` and `competition_page`.
- `Source.mirrors` is a list of unique strings.
- `Document.section` is free text.
- `Problem.as_of` may be a timestamp or null.

A synthetic bundle of 7,000 Sources, 8,000 Documents (43M characters), and 618 Problems validates in about 1.65 s.

Things 002 must not break:
- The installed-wheel test compares every file under `schemas/` with the wheel, so adapter schemas stay out of `schemas/`.
- Fixture case ids starting with `source_` / `document_` / `problem_` are auto-classified as 001 single-record cases, so 002 fixtures use their own manifest.
- `test_versions.py` pins release 2.0.0.
- A conftest fixture blocks network access in every test.

**Alternatives**: Adding Kaggle metadata to the contract records was rejected. It would need a 3.0.0 or 2.1.0 contract release, a release declaration, and version-test updates for no downstream benefit, since 005 and 006 can join the adapter tables by id.

**Conflict noted for 005**: ARCHITECTURE §5.3 says quote matching tolerates whitespace and markdown-escape normalization, but 001 forbids quote normalization. 002 stores exact text, which supports either resolution; the decision belongs to 005.

## Open items handed forward

| Item | Owner |
| --- | --- |
| Review of the 101 candidates plus borderlines, to reach zero `unreviewed` before handing P0 to the benchmark (SC-004) | curator; capacity is roadmap Q7 |
| Locating the `# Evaluation` page inside the overview Document for context bundles | 005 |
| Whitespace and markdown-escape tolerance in quote matching (ARCHITECTURE vs 001) | 005 |
| As-of semantics for writeups posted before the deadline | 003 |
| Roadmap 002 notes still say 65 short writeups and do not state the duplicate normalization | next `/speckit.roadmap.write` (PATCH) |
| DuckDB `fts` extension is not bundled and autoinstall would hit the network | 006 |
