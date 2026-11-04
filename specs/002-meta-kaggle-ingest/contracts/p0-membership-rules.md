# Contract: P0 Membership Rule And Reviewed List

**Spec**: FR-007, FR-008, US2 | **Decision**: ROADMAP C-16 | **Research**: [R3](../research.md#r3-tag-rule), [R6](../research.md#r6-p0-heuristic-candidate-proposal-only), [R10](../research.md#r10-reviewed-list-format)

Both files live in `curation/kaggle/`. They are git-tracked, reviewed like code, read with the strict YAML loader, and validated against their JSON Schemas. Neither may contain source text.

## Precedence (normative)

| Step | Condition | Result | `deciding_rule` |
| --- | --- | --- | --- |
| 1 | Reviewed-list entry exists for the competition | the entry's decision | `reviewed_list` |
| 2 | `tag_class = tag_in` | `in` | `tag` |
| 3 | `tag_class = modality_excluded` | `out` | `tag` |
| 4 | otherwise | `out` | `default_exclude` |

The heuristic's `candidate` flag never appears in this table.

Tag classes, computed from tag ids:

| Tag class | Condition |
| --- | --- |
| `modality_excluded` | any modality id present |
| `tag_in` | no modality id, and any in-id present |
| `other_tags` | tags, but none of the above |
| `untagged` | no tags |

## `p0-rule.yaml` (shape)

```yaml
rule_version: "1.0.0"
tag_rule:
  include:   # Tag ids (names are documentation; ids decide)
    - {id: "14101", name: "tabular"}
    - {id: "13209", name: "time series analysis"}
  modality_exclude:
    - {id: "14102", name: "image"}
    - {id: "13207", name: "computer vision"}
    - {id: "14104", name: "text"}
    - {id: "13204", name: "nlp"}
    - {id: "16072", name: "audio"}
    - {id: "14105", name: "video"}
heuristic:
  pool: [other_tags, untagged]
  candidate: "not S5 and S1 and S3 and (S2 or S4)"   # fixed grammar: S1..S5, and/or/not, parentheses
  signals:
    S1: {metric_families: [...], name_patterns: [...]}           # tabular metric allow-list
    S2: {file_patterns: [...], media_patterns: [...], strip_patterns: [...]}
    S3: {media_patterns: [...], keywords: {...}, keyword_threshold: "6"}
    S4: {positive_tag_ids: [...], negative_tag_ids: [...]}
    S5: {negative_metric_patterns: [...], negative_tag_ids: [...]}
  review_flags: {bioseq: {...}, non_english: {...}, thin_dataset_desc: {...}, signal: {...}}
```

Rules:
- Every scalar is a string (strict loader). Numbers such as thresholds are parsed explicitly by the rule loader against the schema.
- Patterns are case-insensitive regular expressions, applied only to snapshot fields:
  - the metric label,
  - the dataset description Document text,
  - the title and subtitle.
- Matching only tests for a match; no captured text is stored.
- The candidate expression is parsed by a small fixed grammar. It is never `eval`ed.
- Any change to this file must bump `rule_version`. Its sha256 enters `membership_id`.

## `p0-reviewed.yaml` (shape)

```yaml
entries:
  - competition_id: "<Competitions.Id>"   # illustrative entry
    slug: "talkingdata-adtracking-fraud-detection"
    decision: include
    reason: "Click-log tabular classification; AUC; untagged."
    reviewed_by: "<curator>"
    reviewed_on: "2026-11-04"
```

Rules:
- Entries are sorted by numeric `competition_id`, and duplicates are an error.
- `decision` is `include` or `exclude`. `reason` and `reviewed_by` are required and non-blank. `reviewed_on` is `YYYY-MM-DD`.
- An unknown `competition_id` or a slug that does not match the snapshot is an error (US2-5).
- An entry may override a tag decision, for example by excluding a tag-in competition that is really image data.
- Entries are made by a person. Agent or heuristic suggestions belong in the candidate report, never in this file. A seed list prepared with agent help must be confirmed entry by entry by the named reviewer.

## Candidate report (generated, local)

`candidate-report.md` lists every competition in the heuristic pool that is either a candidate or matches S1 without S5. Columns:

```text
slug | competition_id | year | tag_class | metric | writeups | signals | review_flags | review_status | deciding_rule | p0
```

Rows are sorted by `review_status` (unreviewed first), then by writeups descending, then by `competition_id`. The report is regenerated per `membership_id`. It is a review aid, not an input.
