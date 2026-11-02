# aimx-recipes

**English | [简体中文](./README.zh-CN.md)**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)

Evidence-backed optimization recipes for autonomous ML research.

> **Status: design phase.** This repository currently contains the project
> constitution, roadmap, architecture, and evaluation protocol. The commands
> below are the **proposed** interface; none of them is implemented yet.

`aimx-recipes` is a problem-aware research retrieval system and recipe pool for
[aimx](https://github.com/blizhan/aimx) and AutoResearch. It answers one
question:

> Given the current research problem, its data and validation conditions, what
> has already been tried, and the compute budget, which optimizations have
> other researchers tried that are worth testing next, and what is the
> evidence?

It is not a leaderboard of winning tricks, a general ML knowledge base, or a
RAG chatbot. It returns **candidates with conditions and evidence**. The aimx
Lead decides what to run, and only local experiments become findings.

---

## How It Works

1. **Problem Profile in.** Describe the problem with facets from a controlled
   vocabulary: task, target, data, temporal setup, validation, metric,
   symptoms, compute, and prior attempts. Each facet says whether it was
   `observed`, `reported`, `inferred`, or is `unknown`.
2. **Deterministic matching.** Hard constraints (no future data at prediction
   time, no target leakage, fixed validation, budget) filter recipes. Facet
   matching, full-text search, and evidence-aware ranking order the rest. Each
   result states its match level (L1–L4), its transfer risk, and which facets
   matched, were unknown, or were violated.
3. **Evidence, not popularity.** Every recipe links to Attempts reported in
   real sources. Each Attempt has typed Evidence records:
   - types: controlled ablation, reported gain, reported failure, used in
     solution, …;
   - outcome and evaluation scope (CV vs public vs private leaderboard);
   - a verbatim quote.
4. **Experiment Proposal out.** A chosen recipe becomes a proposal that uses
   aimx `experiment_contract` field names. Project-specific fields (baseline,
   threshold, protocol) are left `null` for the Lead.

The query path never calls an LLM. Models are used only in an offline
extraction step, and its output is validated against the source text and
frozen.

```text
Meta Kaggle ──ingest──► data/raw ──extract (offline)──► data/extracted ──┐
recipes/*.yaml + schemas/ ───────────────────────────────────────────────┴─build──► data/index.duckdb
                                                                                              │
                       agent: match → evidence → propose  ◄── read-only CLI ──────────────────┘
```

## Python Contract Library

`aimx-recipes` provides an offline contract validation library for eight core research entities:

- **Entity Types**: `source`, `document`, `problem`, `problem_profile`, `recipe`, `attempt`, `evidence`, and `experiment_proposal`.
- **Closed Schema Registry**: Draft 2020-12 schemas packaged under `schemas/2.0.0/` and accessed offline with exact version dispatch.

### Public API

```python
from aimx_recipes import (
    parse_record,
    validate_record,
    validate_bundle,
    render_text,
    ValidationContext,
)

# 1. Parse JSON strictly without coercion or key collisions
parse_result = parse_record('{"schema_version": "2.0.0", "entity_type": "problem", ...}')
assert parse_result.record is not None

# 2. Structural validation of an isolated entity record
record_result = validate_record(parse_result.record)
print(render_text(record_result))

# 3. Contextual bundle validation over a linked graph
ctx = ValidationContext(document_texts={"doc:123": "Normalized document text..."})
bundle_result = validate_bundle([source_record, doc_record, attempt_record, evidence_record], context=ctx)
assert bundle_result.status == "valid"
assert bundle_result.contextual_complete is True
```

### Structural vs. Contextual Validity

- **Structural Validity (`validate_record`)**: Enforces JSON Schema shape, closed properties (`additionalProperties: false`), exact integers vs floats, facet vocabulary membership, action taxonomy leaf assignment, and entity field invariants. Evaluates single records without external references (`level="structural"`).
- **Contextual Validity (`validate_bundle`)**: Enforces referential integrity across related entities (Problem, Source, Document, Attempt, Evidence, Proposal), UTF-8 content SHA-256 hashes, exact quote spans (capped at 500 Unicode code points), and complete proposal hard-constraint assessments.
- **Incomplete vs. Error**: Missing contextual data (such as document text in `ValidationContext`) yields `status="incomplete"`. Structural or referential errors dominate and yield `status="invalid"`.
- **Governance Boundary**: Experiment proposals always retain `review_status="requires_lead_review"`. Validation never mutates records, grants execution admission, or accesses aimx runtime state.

## Proposed CLI

```bash
aimx-recipes match --problem problem.json --json        # candidates + matched/unknown/violated facets
aimx-recipes evidence oof_target_encoding --json         # typed evidence with quotes and sources
aimx-recipes show oof_target_encoding --json             # recipe definition + derived support
aimx-recipes search "extreme price spikes" --json        # full-text search over evidence
aimx-recipes facets                                       # controlled vocabulary
aimx-recipes propose oof_target_encoding --problem problem.json --json
```

Build-side commands (explicit; they write only under `data/`):

```bash
aimx-recipes ingest kaggle --meta-kaggle ~/data/kaggle/meta-kaggle
aimx-recipes extract      # offline, OpenAI-compatible endpoint
aimx-recipes build        # deterministic index
```

## Relationship To aimx

| System | Owns |
| --- | --- |
| **aimx-recipes** | external experience, problem matching, evidence retrieval, recipe candidates, proposals |
| aimx Research | findings, frontier, agenda, research state |
| AutoResearch | planning, dispatch, execution |
| aimx Retro | retrospectives and follow-up options |
| Aim | runs, params, metrics |

`aimx-recipes` never writes aimx or Aim state. A proposal reaches aimx when the
Lead attaches it to an Agenda item as a `local_artifact` evidence reference. No
aimx change is required.

## Scope Of P0

- **Task family:** tabular and tabularized time series, including
  temporal-split validation.
- **Corpus:** official [Meta Kaggle](https://www.kaggle.com/datasets/kaggle/meta-kaggle)
  writeups joined with competition context. A first filter selects about 179
  competitions and 1,582 writeups.
- **Evaluation first:** a frozen benchmark of about 30 problems (3 real
  Tabloom cases plus temporal leave-one-competition-out Kaggle problems)
  compares problem-aware retrieval against BM25 and semantic baselines.

## Documentation

| Document | Contents |
| --- | --- |
| [CONSTITUTION.md](./CONSTITUTION.md) | non-negotiable principles and quality gates |
| [ROADMAP.md](./ROADMAP.md) | decisions, planned specs 001–014, open questions |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | data model, storage layers, extraction, retrieval, aimx integration, CLI |
| [docs/EVALUATION.md](./docs/EVALUATION.md) | benchmark, baselines, metrics, extraction evaluation, P0 exit |
| [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md) | sources, licenses, release policy, Meta Kaggle statistics |

## Development

The project uses [Spec Kit](https://github.com/github/spec-kit) with the pi and
Claude Code integrations and the speckit-roadmap extension. The canonical
constitution lives in `.specify/memory/constitution.md` and is mirrored in
`CONSTITUTION.md`. Spec Kit and agent integration state (`.specify/`, `.pi/`,
`.claude/`) is local and gitignored; `CONSTITUTION.md` and `ROADMAP.md` are the
tracked copies. Python tooling will use `uv`.

## License

Code and project-authored content: [Apache-2.0](./LICENSE). Third-party source
data keeps its own license; see [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md).
