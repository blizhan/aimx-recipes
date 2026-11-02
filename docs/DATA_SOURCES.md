# Data Sources

Status: source register as of 2026-11-02. Licenses are recorded **as checked**
and must be re-checked before any public data release. Policy comes from
Principle V of the [constitution](../CONSTITUTION.md).

## 1. Storage And Release Policy

| Layer | Contains | Published? |
| --- | --- | --- |
| `data/raw/` | source snapshots as Parquet, including full text | **no**, local only |
| `data/extracted/` | structured records, source IDs/URLs, short verbatim quotes | yes, as versioned artifacts (after license check) |
| `recipes/`, `schemas/`, `evals/` | project-authored content | yes, in git (Apache-2.0) |
| `data/index.duckdb` | built locally | no |

Rules:

- No full writeup, forum, or notebook text is redistributed. Quotes are
  limited to what is needed as evidence; spec 001 sets the length cap.
- Every Source carries a `license` field at ingest time.
- Sources that are non-commercial, share-alike, or unlicensed are never
  bundled into released artifacts and never become runtime dependencies. They
  may be used locally for cross-checking.
- Duplicate copies of one document resolve to one Source identity.

## 2. Source Register

| Source | Content | License (as checked) | Role | Phase |
| --- | --- | --- | --- | --- |
| [Meta Kaggle](https://www.kaggle.com/datasets/kaggle/meta-kaggle) | competitions, teams, forum topics/messages, tags; daily | apache-2.0 (Kaggle API metadata, 2026-11-02; moved from CC BY-NC-SA in Aug 2023) | **P0 corpus backbone** | P0 |
| [Meta Kaggle Code](https://www.kaggle.com/datasets/kaggle/meta-kaggle-code) | notebook source | not verified; local download returned 404 | implementation evidence | P2 (needs-info) |
| [Kaggle Chronicles corpus](https://www.kaggle.com/datasets/kevinbnisch/competition-writeups-with-technologies-and-summary) ([paper](https://arxiv.org/abs/2511.06304)) | 4,419 writeups with technology tags and summaries; 2025-06 snapshot | apache-2.0 (Kaggle API metadata, 2026-11-02) | cross-check of coverage and technique tags | P0 (cross-check) |
| [Kaggle Writeups Clean (HF)](https://huggingface.co/datasets/t2ance/mle-skills-kaggle-writeups-clean) | 815 writeups | none stated; no provenance | local cross-check only | — |
| [100 Kaggle First Place Solutions](https://github.com/juliusuhlmann/kaggle-first-place-solutions) | 98 readable writeups; 1,161 LLM-generated technique rows; `stage` (8 values), `canonical` (41 slugs, about half filled); 40 of 100 competitions structured | no LICENSE file (all rights reserved) | reference for `action_type` design and an extraction comparison; not ground truth, not bundled | P0 (reference) |
| [faridrashidi/kaggle-solutions](https://github.com/faridrashidi/kaggle-solutions) | index of 721 competitions, 4,768 solution links, per-competition `metric` | MIT | cross-check of writeup coverage and metrics | P0 (cross-check) |
| [Kaggle Knowledge Graph](https://github.com/IssunDB/kaggle-knowledge-graph) | 2.55M nodes / 7.41M edges (2026-10-19); 375 competitions since 2020; no writeup text node | CC BY-NC-SA 4.0 | **not used**; relations rebuilt from Meta Kaggle | — |
| [OpenML](https://www.openml.org/) | tasks, flows, setups, runs, evaluations | no blanket license for runs | standardized-split attempts; derived data stays local | P2 (spec 011) |
| [KGTorrent](https://github.com/collab-uniba/KGTorrent) | notebooks + metadata up to 2020; unmaintained since 2021 | — | related work only | — |
| Tabloom cases (local) | 3 cases: bike demand, electricity price, grid carbon intensity | project data, non-commercial use | benchmark problems and end-to-end scenarios; only project-authored profiles and judgments are stored (C-14) | P0 (eval) |
| Papers / GitHub | ablations, implementations | per source | future adapter | P3 |
| aimx local experiments | runs, findings, agenda outcomes, retros | private | explicit local evidence export | P3 (spec 013) |

Tools that came up during design:

| Tool | License | Position |
| --- | --- | --- |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Apache-2.0 (0.x, fast-moving) | optional extraction comparison; fixed taxonomy, no custom fields, no `.ipynb` |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | PolyForm Noncommercial | optional user-installed tool only, never a dependency. (`nxpatterns/gitnexus`, cited in the draft, is a stale fork.) |

License decisions (see [ROADMAP](../ROADMAP.md)):

- **C-13:** Meta Kaggle is apache-2.0 and so is this project. Released
  extraction artifacts are published under Apache-2.0 with attribution to Meta
  Kaggle, and still carry no full text.
- **C-14:** the project is non-commercial, consistent with the Tabloom cases'
  use class. The public benchmark holds project-authored profiles,
  constraints, and judgments for those cases, not Tabloom's underlying data.

## 3. Meta Kaggle In P0

### 3.1 Snapshot

Local copy: 41 CSVs, snapshot 2026-11-01. Relevant files:

| File | Size |
| --- | --- |
| `Teams.csv` | 0.79 GB |
| `ForumMessages.csv` | 1.77 GB |
| `ForumTopics.csv` | 72 MB |
| `Competitions.csv` | 183 MB |
| `CompetitionTags.csv`, `Tags.csv` | small |

### 3.2 Writeup Resolution

```text
Teams.WriteUpForumTopicId
  → ForumTopics.Id  (FirstForumMessageId)
  → ForumMessages.Id  (RawMarkdown, Message, PostDate)
Teams.CompetitionId → Competitions (Overview, EvaluationAlgorithmName,
                                    EvaluationAlgorithmDescription,
                                    DatasetDescription, EnabledDate, DeadlineDate)
Competitions.Id → CompetitionTags → Tags
```

Spike results (2026-11-02):

- 12,755 competitions; 6,276 teams with a `WriteUpForumTopicId` across 618
  competitions.
- **6,276 / 6,276** writeups resolve to a first message; 6,211 have more than
  200 characters. New-style 2024+ writeups are included, so no web scraping is
  needed.
- Median writeup length grows over time: 2,691 characters (2019), 4,387 (2023),
  5,250 (2025), 10,739 (2026).
- Top tags among competitions with writeups: tabular 177, image 110,
  beginner 61, binary classification 51, multiclass classification 43,
  text 38, regression 36, time series analysis 24.

Parsing notes: `ForumMessages.csv` needs a raised `max_line_size`. Dates use
`%m/%d/%Y %H:%M:%S`.

### 3.3 P0 Subset

A first tag filter (`tabular` or `time series analysis`, excluding `image`,
`computer vision`, `text`, `nlp`) gives:

| Competitions | Writeups | Characters | ≈ Tokens |
| --- | --- | --- | --- |
| 179 | 1,582 | 7.67M | 1.9M |

The filter misses older competitions that were never tagged. Spec 002 decides
the final rule, for example adding metric-based or manual inclusion (Q2).

At this size, full batch extraction of the subset is cheap. The design
therefore uses batch extraction of the whole P0 subset instead of the
on-demand extraction proposed in the v0.2 draft. On-demand extraction may
return later as an explicit command for forum threads, never as a side effect
of a query.

## 4. Adding A Source

Before an adapter is merged, its spec records:

1. what the source contains and how it is fetched;
2. its license and the date it was checked;
3. what is stored locally vs released;
4. how its records map to Source / Document / Problem / Attempt / Evidence;
5. how it de-duplicates against existing sources;
6. its untrusted-input handling.
