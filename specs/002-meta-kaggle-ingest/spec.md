# Feature Specification: Meta Kaggle Source Adapter & Corpus Normalization

**Feature Branch**: `main` (existing branch; no branch-creation hook configured)

**Created**: 2026-11-03

**Status**: Draft — validated for planning

**Input**: User description: "咱们继续下一个milestone" — roadmap item 002. Decisions given during specification: P0 membership is decided by tag rule + heuristic candidates + a reviewed list (resolves roadmap Q2); ingest snapshots every resolvable writeup and records P0 membership as a flag.

This specification turns a locally downloaded Meta Kaggle snapshot into a pinned, local-only corpus of writeups and competition context. It also decides which competitions belong to the P0 tabular / time-series subset. The benchmark (003), extraction (005), and index build (006) consume this corpus. Without it, none of them can say exactly which text they saw.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Snapshot writeups and their competition context (Priority: P1)

A data maintainer points the ingest command at a local Meta Kaggle directory. The command produces a pinned local snapshot. It contains every competition writeup that resolves to its text, together with the competition context needed to interpret it: overview, evaluation, dataset description, metric, dates, tags, and the team's outcome.

**Why this priority**: Every later spec needs a fixed, attributable text corpus; without it extraction and evaluation are not reproducible.

**Independent Test**: Run ingest against a small project-authored fixture shaped like Meta Kaggle and against the 2026-11-01 snapshot; inspect the counts, exclusions, and manifest.

**Acceptance Scenarios**:

1. **Given** a Meta Kaggle directory with the required files, **When** ingest runs, **Then** every team writeup reference is accounted for: either it becomes a writeup document linked to its competition, or it is listed as excluded with a stable reason (unresolvable topic, missing first message, empty text).
2. **Given** a writeup whose markdown body is empty but whose rendered body is present, **When** it is ingested, **Then** the rendered body is used and the document records which body format it came from.
3. **Given** a writeup shorter than 200 characters, **When** it is ingested, **Then** it is kept and flagged as short, not silently dropped.
4. **Given** a missing required file or a required column that is absent or renamed, **When** ingest runs, **Then** it fails before writing anything and names the file and column.
5. **Given** the competition behind a writeup, **When** its context is ingested, **Then** overview, evaluation name and description, metric direction, dataset description, enabled and deadline dates, host segment, tags, and the team's medal and public/private rank are available. Missing values stay absent.

---

### User Story 2 - Decide the P0 subset auditably (Priority: P1)

A curator needs to know, for every competition with writeups, whether it is in the P0 tabular / time-series subset and why. The tag rule includes most competitions. A heuristic surfaces likely-tabular competitions that the tags miss (for example older untagged ones). A reviewed list in git makes the final decision.

**Why this priority**: The P0 subset fixes the scope of the benchmark and of extraction cost. The 2026-11-01 snapshot shows that tags alone miss well-known tabular competitions (untagged: 154 competitions / 450 writeups; other tags only: 113 / 1,721).

**Independent Test**: Run ingest with a fixture where competitions fall into each class (tagged in, modality-excluded, heuristic candidate, reviewed include, reviewed exclude, unreviewed candidate), then inspect the membership records and the candidate report.

**Acceptance Scenarios**:

1. **Given** a competition tagged `tabular` or `time series analysis` and not tagged with a non-tabular modality, **When** membership is computed, **Then** it is in P0 with deciding rule `tag`.
2. **Given** an untagged competition that the heuristic proposes and the reviewed list does not mention, **When** membership is computed, **Then** it is **not** in P0. It appears in the candidate report as `unreviewed`, and the heuristic alone never includes it.
3. **Given** a reviewed-list entry that includes or excludes a competition, with a reason, **When** membership is computed, **Then** the entry wins over the tag rule and the heuristic, and the record cites the list entry as its deciding rule.
4. **Given** a changed reviewed list and an unchanged Meta Kaggle snapshot, **When** membership is recomputed, **Then** P0 membership changes without re-reading or re-normalizing source text. The new membership carries a new rule version.
5. **Given** a reviewed-list entry that names a competition absent from the snapshot or lacks a reason, **When** membership is computed, **Then** it is reported as an error, not ignored.

---

### User Story 3 - Emit contract-valid Source, Document, and Problem records (Priority: P2)

Downstream specs need records in the shape fixed by spec 001, so they can cite sources, compute quote offsets, and attribute licenses without re-reading Meta Kaggle.

**Why this priority**: Spec 001's contracts are the interface; records that do not validate would push repair work into extraction.

**Independent Test**: Validate every emitted record with the 001 validators, including contextual reference checks against the emitted documents.

**Acceptance Scenarios**:

1. **Given** an ingested writeup, **When** its records are validated, **Then** one Source (kind `writeup`) and one Document reference each other and the snapshot. The Source carries a canonical Kaggle reference, the Meta Kaggle license with attribution, and the content fingerprint.
2. **Given** an ingested competition, **When** its records are validated, **Then** one Source (kind `competition_page`), one Document per non-empty context section, and one Problem (kind `competition`) exist. The Problem lists the competition and writeup Sources.
3. **Given** two writeup references whose normalized text is identical, **When** they are ingested, **Then** they resolve to one Source identity, with the other reference recorded as a mirror.
4. **Given** the same Meta Kaggle input, **When** ingest is run twice, **Then** every identifier and every content fingerprint is identical. Identifiers come from source identity, never from row order or run time.

---

### User Story 4 - Reproduce and compare snapshots (Priority: P3)

A maintainer can tell exactly which input produced a snapshot. They can rerun ingest without changing it and add a newer Meta Kaggle download without overwriting the old one.

**Why this priority**: Frozen extraction (005) and temporal evaluation (003) key on snapshot identity. Incremental refresh itself belongs to 009.

**Independent Test**: Ingest the same input twice and a modified input once; compare manifests.

**Acceptance Scenarios**:

1. **Given** a completed snapshot, **When** its manifest is inspected, **Then** it lists each input file with size, row count, and sha256; each output with sha256 and row count; and the normalization, membership-rule, and code versions.
2. **Given** an unchanged input, **When** ingest runs again, **Then** it produces byte-identical outputs and reports that the snapshot already exists.
3. **Given** a changed input, **When** ingest runs, **Then** a new snapshot identity is created and the previous snapshot is left untouched.

### Edge Cases

- A writeup body may contain markup, links, embedded code, or text that reads like instructions. It is stored as inert text: no link is followed, no markup is executed, and no content changes ingest behavior.
- Very long fields and embedded line breaks in source rows must parse without truncation; a row that cannot be parsed is reported with its file and identifier.
- A competition may lack an overview, evaluation description, or dataset description; the missing section yields no Document, never an empty one.
- A competition's dataset license (for example CC BY-NC) is about the competition data, which this project does not ingest. It is recorded as informational competition metadata, not as the Source license of Meta Kaggle text.
- Dates in Meta Kaggle carry no time zone; they are interpreted consistently and the convention is documented, not guessed per row.
- A competition tagged both `tabular` and a non-tabular modality (for example `image`) is excluded by the tag rule; only a reviewed-list entry can include it.
- A competition with writeups but no tags at all is a heuristic candidate only if the heuristic proposes it; otherwise it is out with deciding rule `default_exclude`.
- Team medal value `0` and empty both mean no medal; ranks may be absent for unverified leaderboards.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001 — Explicit, local, offline command**: Provide `aimx-recipes ingest kaggle --meta-kaggle <dir>` as an explicit write-capable command. It reads only the given local directory, writes only inside the project data directory's raw layer, makes no network or model calls, and never downloads Meta Kaggle. It must fail before writing when required inputs are missing.
- **FR-002 — Input verification**: Check that the required files (competitions, teams, forum topics, forum messages, tags, competition tags) and columns exist. Record each input file's size, row count, and sha256. Rows that cannot be parsed are reported with file and identifier; the run fails if any required relationship cannot be evaluated.
- **FR-003 — Writeup resolution**: Resolve writeups through team writeup topic → topic's first message → message body. Every team writeup reference ends as exactly one of: ingested document, or exclusion with a stable reason. Exclusions are part of the output, not just logs.
- **FR-004 — Text selection**: Use the markdown body when present, otherwise the rendered body, and record which one was used. Text is stored exactly as found; normalization for search or extraction is a separately versioned step and keeps a way to recover the stored text. Empty bodies are excluded; bodies under 200 characters are flagged as short.
- **FR-005 — Competition context**: For every competition with at least one ingested writeup, capture title, slug, canonical URL, host segment, enabled and deadline dates, metric name, abbreviation and direction, evaluation description, overview, dataset description, tags, and competition data license name. For each writeup, capture its team's medal, public and private rank, post date, and topic title. Absent values remain absent.
- **FR-006 — Ingest scope**: Ingest every competition that has a resolvable writeup, regardless of P0 membership; the 2026-11-01 snapshot has 618 competitions and 6,276 writeup references. P0 membership is a recorded attribute. Downstream consumers select P0 through it; non-P0 records are not deleted.
- **FR-007 — P0 membership rule**: For every ingested competition, record membership (`in` / `out`), the deciding rule, and the rule version. Precedence:
  1. **Reviewed list** — a version-controlled list of competition decisions (include / exclude), each with a reason. It overrides everything else.
  2. **Tag rule** — tagged `tabular` or `time series analysis` and not tagged `image`, `computer vision`, `text`, `nlp`, `audio`, or `video` → `in`; tagged with any of those modalities → `out`.
  3. **Default** — everything else is `out`.

  The heuristic never decides membership.
- **FR-008 — Heuristic candidates and review report**: For competitions that are `out` by tag or default, a deterministic heuristic proposes likely tabular / time-series candidates. It uses signals available in the snapshot: metric family, dataset-description indicators of tabular files, and the absence of non-tabular media indicators. Each run emits a candidate report listing every candidate with its signals and review status (`reviewed_include`, `reviewed_exclude`, `unreviewed`). A summary count of unreviewed candidates is part of the run result.
- **FR-009 — Contract records**: Emit Source, Document, and Problem records that validate against the spec 001 contracts (current version 2.0.0):
  - writeup Sources and competition-page Sources;
  - one Document per writeup body and one per non-empty competition context section (overview, evaluation, dataset description);
  - one `competition` Problem per competition, listing its Sources.
  
  Problem Profiles are not produced here (005).
- **FR-010 — Identity and de-duplication**: Source, Document, and Problem identifiers derive deterministically from Kaggle identifiers and content, never from row order or wall-clock time. Writeup references whose text is identical after whitespace collapsing resolve to one Source; the other references are recorded as mirrors. Repeated runs on identical input produce identical identifiers.
- **FR-011 — License recording**: Every Source records the license of the text as ingested: Meta Kaggle, Apache-2.0, permissive, with attribution to Meta Kaggle (ROADMAP C-13). The license and its check date come from the source register. Competition data licenses are kept as separate informational metadata.
- **FR-012 — Snapshot identity and manifest**: Each run's output belongs to a snapshot whose identity derives from the input file fingerprints and the normalization version. A manifest records inputs (name, size, rows, sha256), outputs (name, rows, sha256), and the normalization, membership-rule, schema, and code versions. An existing snapshot is never overwritten with different content. Rerunning on identical input yields byte-identical outputs.
- **FR-013 — Temporal fields**: Writeup post date and competition enabled and deadline dates are stored in one documented convention, so later specs can filter sources as of a date (003, 006).
- **FR-014 — Untrusted input**: Source text is treated as data. Ingest does not follow links, render or execute markup, or let content influence control flow beyond parsing. Malformed content is reported, not repaired.
- **FR-015 — Output contracts**: The command prints a human-readable summary and, with `--json`, a stable JSON envelope that agrees with it. The envelope carries `status`, `snapshot_id`, counts (competitions, writeups ingested and excluded by reason, short writeups, P0 in and out by deciding rule, unreviewed candidates), output locations, and warnings. Neither output contains wall-clock values other than a run timestamp kept outside the snapshot's hashed content.
- **FR-016 — Local-only text**: Full writeup and competition text exists only in the gitignored raw layer and is never written to git-tracked paths or released artifacts. The reviewed list and rule definitions are the only P0-selection artifacts in git; they contain identifiers, decisions, and reasons, not source text.
- **FR-017 — Scope boundary**: Excluded: forum threads beyond the writeup's first message (009), notebooks (012), extraction and Problem Profiles (005), index build (006), benchmark selection (003), incremental refresh (009), Kaggle API download, and any third-party corpus. Cross-check corpora are not ingested.

### Key Entities *(include if feature involves data)*

| Entity | Meaning and relationships |
| --- | --- |
| Meta Kaggle snapshot (input) | A local directory of Meta Kaggle CSV files from one download date; identified by its file fingerprints. |
| Raw snapshot (output) | The pinned local corpus produced by one ingest: writeups, competition context, exclusions, membership, manifest. |
| Writeup Source / Document | One team's solution writeup: identity, canonical reference, license, fingerprint; its body text, body format, short flag, post date, and team outcome. |
| Competition Source / Documents | One competition page: identity and metadata; one Document per non-empty context section. |
| Problem (`competition`) | The competition as a research problem, referencing its competition and writeup Sources. |
| Exclusion record | A writeup reference that did not become a Document, with its stable reason. |
| P0 membership record | Per competition: `in` / `out`, deciding rule (`reviewed_list`, `tag`, `default_exclude`), rule version, and heuristic signals when present. |
| Reviewed list | Version-controlled competition decisions (include / exclude) with reasons; the final authority over P0 membership. |
| Candidate report | Heuristic candidates with signals and review status, produced for curators. |
| Snapshot manifest | Input and output fingerprints, row counts, and the versions that produced the snapshot. |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the 2026-11-01 snapshot, 100% of the 6,276 team writeup references are accounted for as ingested or excluded with a reason. Zero are silently dropped.
- **SC-002**: Two ingests of the same input produce identical identifiers, fingerprints, and output files. A changed input produces a new snapshot identity and leaves the previous snapshot unchanged.
- **SC-003**: Every ingested competition has exactly one membership record with a deciding rule. Zero competitions are in P0 by heuristic alone. Every reviewed-list decision carries a reason.
- **SC-004**: Before P0 is handed to the benchmark (003), 100% of heuristic candidates on the reference snapshot have a reviewed decision (zero `unreviewed`).
- **SC-005**: 100% of emitted Source, Document, and Problem records pass the spec 001 structural and contextual validation.
- **SC-006**: A curator can answer "why is competition X in or out of P0?" from the run output alone, without reading code, for every competition.
- **SC-007**: Zero git-tracked files contain writeup or competition body text after ingest. The human-readable and JSON summaries agree on every count.
- **SC-008**: A full ingest of the reference snapshot completes in under 30 minutes on a single workstation.

## Assumptions

- Authority is [ROADMAP item 002](../../ROADMAP.md), governed by C-04 and C-05 (with C-13 for the release license), and the [constitution](../../CONSTITUTION.md). Domain context comes from [DATA_SOURCES §3](../../docs/DATA_SOURCES.md#3-meta-kaggle-in-p0) and [ARCHITECTURE §4.1](../../ARCHITECTURE.md#41-ingest).
- Two decisions given by the user during specification change the roadmap entry. Ingest covers all resolvable writeups with P0 as a flag, where the roadmap said "ingest the P0 subset". The membership rule is tags + heuristic candidates + reviewed list, which resolves Q2. The roadmap was synced in version 2.1.0 (decision C-16).
- The reference input is the local Meta Kaggle download dated 2026-11-01. Spike figures from that snapshot (2026-11-03):

  | Spike figure | Value |
  | --- | --- |
  | Competitions with writeups | 618 |
  | Writeup references | 6,276; none shares a topic |
  | Tag classes (competitions / writeups) | tag-in 178 / 1,570; modality-excluded 173 / 2,535; other tags only 113 / 1,721; untagged 154 / 450 |
  | Writeups without a markdown body | 156 (153 use the rendered body; 3 have neither) |
  | Empty writeups | 3 |
  | Writeups under 200 characters (selected body) | 107 |
  | Duplicate-content pair | 1, only after whitespace collapsing (topics 95174 / 95176, sibling competitions) |

  _Corrected 2026-11-03 during planning: the first spike counted 65 short writeups by rendered-body length and reported the duplicate pair without stating the normalization._

  These are planning context, not acceptance thresholds, except SC-001.
- Meta Kaggle is Apache-2.0 (checked 2026-11-02, DATA_SOURCES). Raw text is local-only regardless of license (C-05). This feature releases nothing.
- The initial reviewed list is produced during implementation: the heuristic pre-sorts candidates and a curator reviews them. The list format, the heuristic's exact signals, and file layouts are planning decisions. The tag lists in FR-007 are the starting rule and change only through a versioned rule update.
- Meta Kaggle dates are treated as UTC unless planning finds evidence otherwise; the chosen convention is documented.
- No LLM is used anywhere in this feature. The human-readable and JSON output contracts are those of FR-015; the only write target is the raw data layer.
