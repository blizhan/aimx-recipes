# Contract: Kaggle Raw Snapshot (consumer interface)

**Spec**: FR-003–FR-013, FR-016 | **Consumers**: 003 (benchmark), 005 (extraction), 006 (index build) | **Data model**: [data-model.md](../data-model.md)

## Layout

```text
<data-dir>/raw/kaggle/<snapshot_id>/          # immutable once renamed into place
├── manifest.json
├── competitions.parquet
├── writeup_refs.parquet
├── writeups.parquet
├── documents.parquet                         # the only full-text table
├── records/
│   ├── sources.jsonl
│   ├── documents.jsonl
│   └── problems.jsonl
└── membership/<membership_id>/               # immutable once renamed into place
    ├── manifest.json
    ├── membership.parquet
    └── candidate-report.md
```

Directories whose names start with `.tmp-` are incomplete. Consumers must ignore them.

## Guarantees

1. **Immutability.** Files in a snapshot or membership directory never change after the rename. New input yields a new `snapshot_id`; new rules or a new list yield a new `membership_id`.
2. **Contract validity.** `records/*.jsonl` together form a bundle that `aimx_recipes.validate_bundle` reports as `valid` at schema version 2.0.0, given `document_texts` built from `documents.parquet`.
3. **Exact text.** `documents.text` is the stored source text. `sha256(text.encode("utf-8")) == content_sha256`, and character offsets computed against it are the offsets 001 Evidence uses. No consumer may rewrite it in place.
4. **Join keys.**
   - `documents.document_id` = `records/documents.jsonl` `document_id`.
   - `writeups.source_id` and `competitions.source_id` = Source ids.
   - `competitions.problem_id` = Problem id.
   - `membership.competition_id` = `competitions.competition_id`.
5. **Completeness.**
   - Every team writeup reference in the input appears in `writeup_refs` with exactly one disposition.
   - Every competition in `competitions` appears in every membership table.
6. **Order.** Every Parquet file is sorted by its key and every JSONL file by id, so equal content gives equal bytes under the same locked writer version.
7. **Time.** Timestamps are UTC (naive `TIMESTAMP` in Parquet, `…Z` in records). Use `writeups.posted_at` for as-of filtering of writeups and `competitions.deadline_at` / `Problem.as_of` for competitions.

## Selecting P0

A consumer chooses the membership in one of two ways:
- computes it from the current git rule files with `aimx_recipes.sources.kaggle.membership_id(snapshot_id)`;
- receives a `membership_id` explicitly, for example in an extraction run config.

There is no mutable "latest" pointer.

```sql
-- P0 writeup documents for one snapshot + membership
SELECT d.*
FROM documents d
JOIN writeups w USING (document_id)
JOIN membership m ON m.competition_id = w.competition_id
WHERE m.p0 = 'in';
```

Benchmark consumers (003) must refuse a membership whose `manifest.json` has `p0_status != "final"` (C-16, SC-004). Extraction trials and local development may use `provisional` and must record the `membership_id` they used.

## Not provided

The snapshot does not provide:
- Problem Profiles or extraction records (005);
- the index (006);
- forum threads beyond each writeup's first message (009);
- notebooks (012);
- normalized or segmented text such as an extracted `# Evaluation` page. Derived text belongs to the consumer, with its own versioning.

## Release posture

Nothing in this layout is released (C-05, FR-016). Released artifacts in later specs may cite `source_id`, `canonical_ref`, `snapshot_id`, and `content_sha256`, and short quotes within 001 limits. They may not include `documents.text`.
