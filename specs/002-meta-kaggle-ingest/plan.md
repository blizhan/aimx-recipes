# Implementation Plan: Meta Kaggle Source Adapter & Corpus Normalization

**Branch**: `main` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-meta-kaggle-ingest/spec.md`

**Note**: The setup script returned `002-meta-kaggle-ingest` as BRANCH from feature discovery. The actual Git branch remains `main`, and `.specify/feature.json` selects this feature.

## Summary

Add the project's first write-capable command, `aimx-recipes ingest kaggle`. It turns a local Meta Kaggle download into an immutable, local-only raw snapshot:

- every resolvable writeup, with its exact text;
- competition context as separate exact-text Documents;
- team outcomes;
- an exclusion record for every unresolvable reference;
- Source / Document / Problem records that validate unchanged against the 001 contracts (2.0.0).

P0 membership is computed separately per (snapshot × rule × reviewed list). A reviewed list wins, then the tag rule (by tag id), then default exclusion. A five-signal heuristic only proposes candidates for review (C-16).

Technical approach:
- DuckDB reads the CSVs with a strict, explicit dialect and writes byte-deterministic Parquet (total `ORDER BY`, UTC, extensions off).
- Contract records are canonical JSON Lines.
- argparse provides the CLI.
- A shared strict YAML loader reads the git-tracked rule file and reviewed list.

Evidence and alternatives are in [research.md](research.md). Entities and identities are in [data-model.md](data-model.md). Interfaces are in [contracts/](contracts/).

## Technical Context

**Language/Version**: Python >=3.12. The acceptance matrix is 3.12 and 3.13, managed with uv.

**Primary Dependencies**:
- Existing: jsonschema, referencing, rfc3339-validator.
- New: **duckdb >=2.0,<3** (MIT; CSV, joins, Parquet; 1.5.6 is a fallback for the same SQL) and **pyyaml >=6.0.3,<7** (MIT; strict loader). Exact versions are pinned in `uv.lock`.
- No pyarrow, no CLI framework, no network or model SDK.

**Storage**:
- Local, gitignored `data/raw/kaggle/<snapshot_id>/`: Parquet adapter tables, canonical JSONL contract records, JSON manifests, and immutable `membership/<membership_id>/` directories.
- Git-tracked `curation/kaggle/`: rule file, reviewed list, and their schemas, packaged through a tracked `_curation` symlink as `schemas/` is.

**Testing**:
- pytest unit, contract, and integration suites on project-authored synthetic CSV fixtures, with their own manifest and the network blocked.
- CLI text/JSON agreement; byte-determinism across `--threads`; immutability and conflict handling; strict-loader and reviewed-list errors; installed-wheel resources.
- An opt-in reference-snapshot test runs when `AIMX_RECIPES_META_KAGGLE` is set.

**Target Platform**: Linux workstation and CI, offline at run time.

**Project Type**: Python library + CLI (first CLI entry point: `aimx-recipes`).

**Performance Goals**:
- Full reference ingest under 30 minutes (SC-008). Research measured 5.9 s for writeup resolution, about 2 s to hash 2.82 GB, and about 1.7 s for 001 bundle validation at this scale.
- Default `--memory-limit 4GB`; resolution peaked at 2.6 GB.

**Constraints**:
- No network, model, or DuckDB extension downloads.
- Writes only under `<data-dir>/raw/kaggle/`, through a temporary directory and atomic rename.
- Exact text: no rewriting, and the hash equals the 001 Document hash.
- No full text in git or in released artifacts.
- No 001 contract change.
- Error messages never echo source rows.

**Scale/Scope**:

| Reference snapshot figure | Value |
| --- | --- |
| Input | 6 files, 2.82 GB |
| Competitions with writeups | 618 |
| Writeup references | 6,276 (6,272 Sources after 3 empty + 1 mirror) |
| Documents | about 8.1k, about 34M characters of writeup text |
| Heuristic pool | 267 |
| Candidates | 101 |

## Constitution Check

*GATE: evaluated before research and again after Phase 1 design. Constitution version 1.0.1.*

| Gate | Before research | Post-design evidence and verdict |
| --- | --- | --- |
| I. Evidence traceability | PASS | PASS: exact text stored with its 001 hash; canonical Kaggle URLs; every reference accounted for with a disposition; deterministic ids join Documents to Sources, Problems, and adapter metadata ([raw-snapshot](contracts/raw-snapshot.md)) |
| II. aimx ownership | PASS | PASS: no aimx or Aim access; writes only to the project data directory |
| III. Query-path determinism | PASS | PASS: ingest is not a query command. Outputs are byte-deterministic for a locked writer and logically hashed across versions. No wall clock enters snapshot content. The membership id is derived from content. |
| IV. Uncertainty and hard constraints | PASS | PASS: absent values stay absent; no inferred facets (Profiles are 005). The heuristic is advisory only; membership records its deciding rule; unreviewed candidates make P0 `provisional`. |
| V. Untrusted input and licenses | PASS | PASS: strict CSV dialect; no link following or rendering; patterns only test for matches; the candidate expression uses a fixed grammar (no `eval`); errors never echo rows. Every Source carries the Meta Kaggle Apache-2.0 license (C-13); competition data licenses are informational; raw text is local-only (C-05). |
| VI. Evaluation before expansion | PASS | PASS: defines the corpus and P0 scope that 003 freezes; 003 must refuse `provisional` membership; no retrieval or extraction tuning |
| VII. CLI-first, progressive complexity | PASS | PASS: non-interactive CLI with a stable JSON envelope; storage limited to Parquet, JSONL, and YAML; one new engine (DuckDB, already in the constitution's stack); no service |
| Workflow disclosures | PASS | PASS: write-capable behavior (FR-001); no LLM use; sources and licenses touched (Meta Kaggle, Apache-2.0); text and JSON output contracts ([CLI](contracts/cli-ingest-kaggle.md)); no schema change, so no regeneration decision is needed |

No violation or exception is required. Writing under `<data-dir>` is the constitution's permitted write class: an explicit `ingest` command inside the project's data directory. `--data-dir` exists for tests and alternative checkouts and defaults to `./data`.

## Project Structure

### Documentation (this feature)

```text
specs/002-meta-kaggle-ingest/
├── spec.md
├── plan.md                       # this file
├── research.md                   # R1–R11 decisions
├── research-p0-candidates.md     # heuristic v0 tables for curator review
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-ingest-kaggle.md
│   ├── raw-snapshot.md
│   └── p0-membership-rules.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
pyproject.toml                    # + duckdb, pyyaml; [project.scripts] aimx-recipes; force-include curation
uv.lock
curation/kaggle/
├── p0-rule.yaml                  # tag ids, heuristic signals, candidate expression, rule_version
├── p0-rule.schema.json
├── p0-reviewed.yaml              # starts with `entries: []`; filled by curator review
└── p0-reviewed.schema.json
src/aimx_recipes/
├── _curation -> ../../curation   # tracked symlink, mirrors _schemas
├── yaml_strict.py                # shared strict YAML loader (reused by 004)
├── cli/
│   ├── __init__.py               # main(argv) -> int; argparse tree
│   └── output.py                 # JSON envelope, text rendering, error/warning codes
└── sources/
    ├── __init__.py
    └── kaggle/
        ├── __init__.py           # ingest(), membership_id()
        ├── inputs.py             # required files/columns, header check, stat + sha256, strict read_csv
        ├── resolve.py            # writeup resolution SQL, dispositions, competition context
        ├── normalize.py          # body selection, dedup groups, ids, contract records, adapter rows
        ├── membership.py         # rule/list loading, tag classes, signals S1–S5, expression grammar, report
        └── snapshot.py           # DuckDB session settings, deterministic writes, manifests, tmp+rename, existing/conflict
tests/
├── fixtures/kaggle/              # synthetic CSV sets + rule/list variants + manifest.json (own prefix)
├── unit/kaggle/                  # inputs, body selection, dedup, ids, tag classes, signals, grammar, strict YAML
├── contract/test_cli_ingest_contract.py     # envelope, codes, text/JSON agreement, exit codes
└── integration/
    ├── test_ingest_kaggle.py     # end-to-end on fixtures: bundle valid, determinism, immutability, membership recompute
    └── test_ingest_reference.py  # opt-in: AIMX_RECIPES_META_KAGGLE; SC-001/005/008 figures
```

**Structure Decision**:
- This follows the target layout in ARCHITECTURE §11 (`sources/kaggle/`, `cli/`), adding only the modules this spec needs.
- The 001 modules stay flat and unchanged. 002 consumes them only through the public `validate_bundle` API.
- Rule data lives outside `schemas/`, because the installed-wheel test compares that tree byte-for-byte and the files are not 001 contracts. It is still packaged so the installed CLI works.
- The installed-wheel test gains a check that `_curation` resources match `curation/`.

## Phase 0: Research Closure

Three read-only worker subagents covered:
1. the Meta Kaggle data and the heuristic;
2. the technology choices (CSV parsing, deterministic Parquet, dependencies, CLI, YAML, hashing);
3. integration with the 001 contracts and code.

[research.md](research.md) records the 11 decisions with rationale and alternatives. No `NEEDS CLARIFICATION` remains.

Planning-time decisions taken without asking, each grounded in evidence:

| Decision | Choice | Research |
| --- | --- | --- |
| Evaluation text | The competition-specific evaluation text stays inside the exact overview Document; the generic metric description is its own Document | R4 |
| De-duplication | Whitespace-collapsed grouping key; text never altered | R5 |
| Tag rule keying | By tag id; task-level modality tags are heuristic negatives, not rule tags | R3 |
| Parse errors | Fail-fast on the first malformed row | R1 |
| Writer upgrades | A writer-version-only byte difference leaves the snapshot untouched, with a warning | R7 |
| DuckDB line | 2.0.x | R9 |
| Empty fields | `""` and empty both mean absent | R1 |
| Times | UTC | R2 |

The spec's spike table was corrected for two figures: 107 short writeups, and the duplicate pair being whitespace-collapsed (R5).

## Phase 1: Design and Implementation Sequence

1. **Foundation**:
   - add dependencies, the entry point, the `_curation` symlink, and wheel force-include;
   - add the strict YAML loader with tests (duplicate keys, `no`, `0123`, dates stay strings);
   - set up the CLI skeleton with the JSON envelope and error codes ([CLI contract](contracts/cli-ingest-kaggle.md)).
2. **Inputs**:
   - required-file and column table; stdlib header validation;
   - stat → sha256 → stat-after-parse;
   - strict `read_csv` with explicit dialect and all-VARCHAR columns;
   - error mapping without row echo.
   - Fixtures: missing column, unterminated quote, extra column.
3. **Resolution and normalization**:
   - semi-join resolution, dispositions and exclusion reasons;
   - body selection, short flag, dedup groups and mirrors;
   - UTC dates, metric label and direction, medal mapping;
   - ids, contract records, adapter rows ([data model](data-model.md)).
   - Validate the bundle with `validate_bundle`; anything other than `valid` fails the run.
4. **Snapshot writing**:
   - DuckDB session settings (UTC, extensions off, threads and memory limit);
   - ordered `COPY` with zstd and a fixed row-group size;
   - canonical JSONL; manifest with file and content hashes and environment;
   - tmp directory, fsync, rename; existing, conflict, and writer-difference handling.
   - Determinism tests across thread counts.
5. **Membership**:
   - rule and list schemas and loaders;
   - tag classes by id; signals S1–S5 over snapshot fields;
   - fixed-grammar candidate expression; precedence; review status;
   - `membership_id`, immutable directory, candidate report, `final`/`provisional`.
   - Author `p0-rule.yaml` v1.0.0 from the R6 definitions and start `p0-reviewed.yaml` empty.
6. **Acceptance**:
   - text/JSON agreement; immutability; no writes outside the data directory or to git-tracked paths;
   - installed-wheel resources;
   - the opt-in reference test on the 2026-11-01 snapshot, checking SC-001/005/008 figures (6,276 refs, 3 empty, 107 short, 1 mirror, 618 competitions, 178 tag-in, 101 candidates);
   - run [quickstart.md](quickstart.md) on Python 3.12 and 3.13.

The reviewed list is curated **after** implementation: a curator works through the candidate report, seeded by [research-p0-candidates.md](research-p0-candidates.md). Implementation is complete with an empty list and `provisional` P0. Reaching `final` (SC-004) is the hand-off gate to 003 and depends on curator capacity (roadmap Q7).

## Acceptance and Traceability

| Requirements | Planned evidence |
| --- | --- |
| FR-001, FR-002, FR-014 | Fixture failures before any write; header and dialect checks; stat/hash guard; network-blocked tests; no row echo in errors |
| FR-003, FR-004, FR-005, FR-013 | Every disposition and exclusion reason in fixtures; markdown/HTML selection; short flag; context fields and absent values; UTC conversion and as-of fields |
| FR-006, FR-007, FR-008 | Every tag class; reviewed include/exclude overriding tags; unreviewed candidate stays out; list errors; membership recompute without re-normalization; candidate report contents |
| FR-009, FR-010, FR-011 | `validate_bundle` = `valid` on fixtures and reference; id stability across runs; whitespace-duplicate → one Source with a mirror; license object on every Source; data license only in adapter table |
| FR-012, FR-015 | Byte-identical reruns at different thread counts; `existing`, `conflict`, and writer-difference paths; manifest completeness; JSON envelope and text agreement |
| FR-016, FR-017 | No git-tracked text; outputs only under the data directory; no forum-thread, notebook, extraction, or index outputs |
| SC-001 – SC-008 | Opt-in reference test plus quickstart scenarios 2–6. SC-004 is verified when curation reaches `final`, not at implementation completion. |

Planning verification:
- Seven design artifacts were written: plan, research, candidate tables, data model, quickstart, and three contracts.
- Links are relative. No `tasks.md` was created.
- No implementation tests have been run.
- `.specify/extensions.yml` registers no `before_plan` or `after_plan` hooks.

## Complexity Tracking

No constitutional violations to justify.

The design adds two dependencies, DuckDB (already the constitution's index engine) and PyYAML (needed by 004), and one small expression grammar so that rule data never needs `eval`. Per-membership directories replace a mutable "latest" pointer; that costs a few KB per rule revision.
