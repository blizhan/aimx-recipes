# aimx-recipes

**[English](./README.md) | 简体中文**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)

为自主机器学习研究提供有证据支撑的优化 Recipe。

> **状态：设计阶段。** 仓库目前只有项目宪章、路线图、架构和评测协议。下文列出的命令都是**拟议接口**，还没有实现。

`aimx-recipes` 是为 [aimx](https://github.com/blizhan/aimx) 和 AutoResearch 设计的问题感知检索系统与 Recipe 池。它要回答的问题是：

> 结合当前研究问题、数据与验证条件、已经做过的尝试以及算力预算，别人试过的哪些优化值得接着验证？证据是什么？

它不是冠军技巧排行榜，不是通用 ML 知识库，也不是 RAG 聊天机器人。它返回的是**附带适用条件和证据的候选**，具体跑哪个由 aimx Lead 决定，只有本地实验的结果才能成为 Finding。

---

## 工作方式

1. **输入 Problem Profile。** 用受控词表中的 facet 描述问题，包括任务、目标、数据、时间结构、验证方式、指标、症状、算力和已有尝试。每个 facet 都要注明依据：`observed`、`reported`、`inferred` 或 `unknown`。
2. **确定性匹配。** 先用硬约束过滤 Recipe，例如预测时不能用未来数据、不能有目标泄漏、验证方式固定、预算上限。剩下的再按 facet 匹配度、全文检索和证据强度排序。每条结果都会给出匹配层级（L1–L4）、迁移风险，以及哪些 facet 匹配、哪些未知、哪些违反约束。
3. **看证据，不看热度。** 每条 Recipe 都关联到真实来源中报告的 Attempt。每个 Attempt 带有分类的 Evidence 记录：
   - 证据类型：受控消融、报告的提升、报告的失败、在方案中使用等；
   - 结果方向和评测范围（CV、公榜还是私榜）；
   - 原文引用。
4. **输出 Experiment Proposal。** 选中的 Recipe 会转成一份实验提案，字段名沿用 aimx `experiment_contract`。基线、阈值、评测协议这类和具体项目相关的字段保持 `null`，交给 Lead 填写。

查询过程不调用 LLM。模型只在离线抽取步骤中使用，抽取结果要先对照原文校验，校验通过后冻结保存。

```text
Meta Kaggle ──ingest──► data/raw ──extract（离线）──► data/extracted ──┐
recipes/*.yaml + schemas/ ─────────────────────────────────────────────┴─build──► data/index.duckdb
                                                                                          │
                     agent: match → evidence → propose  ◄── 只读 CLI ─────────────────────┘
```

## Python 合约验证库

`aimx-recipes` 提供了针对八种核心研究实体的离线契约验证库：

- **实体类型**：`source`、`document`、`problem`、`problem_profile`、`recipe`、`attempt`、`evidence` 以及 `experiment_proposal`。
- **封闭 Schema 注册表**：位于 `schemas/2.0.0/` 的 Draft 2020-12 结构化定义，采用精确版本分发并完全离线解析。

### 公共 API

```python
from aimx_recipes import (
    parse_record,
    validate_record,
    validate_bundle,
    render_text,
    ValidationContext,
)

# 1. 严格解析 JSON，杜绝键重复、非有限数字与隐式转换
parse_result = parse_record('{"schema_version": "2.0.0", "entity_type": "problem", ...}')
assert parse_result.record is not None

# 2. 单实体记录的结构化校验
record_result = validate_record(parse_result.record)
print(render_text(record_result))

# 3. 关联实体图的上下文 Bundle 校验
ctx = ValidationContext(document_texts={"doc:123": "归一化后的文档正文..."})
bundle_result = validate_bundle([source_record, doc_record, attempt_record, evidence_record], context=ctx)
assert bundle_result.status == "valid"
assert bundle_result.contextual_complete is True
```

### 结构有效性与上下文完整性

- **结构有效性 (`validate_record`)**：校验 JSON Schema 规范、封闭对象（`additionalProperties: false`）、严格整数与浮点数边界、受控词表成员限制、动作分类叶子节点合法性以及实体字段约束。单记录校验级别为 `level="structural"`。
- **上下文有效性 (`validate_bundle`)**：校验关联实体间的引用完整性（Problem、Source、Document、Attempt、Evidence、Proposal）、UTF-8 正文 SHA-256 哈希一致性、原文严格字符切片（上限 500 个 Unicode 代码点）以及提案的硬约束评估覆盖度。
- **Incomplete 与 Error 判定**：若缺失上下文数据（如 `ValidationContext` 中未提供对应文档全文），结果为 `status="incomplete"`。任何结构或引用错误均占优，判定为 `status="invalid"`。
- **治理边界**：实验提案必须保持 `review_status="requires_lead_review"`。验证器绝不修改或补充字段，不授予运行准入，亦不读写 aimx 的任何状态。

## 拟议 CLI

```bash
aimx-recipes match --problem problem.json --json        # 候选 + 匹配 / 未知 / 违反的 facet
aimx-recipes evidence oof_target_encoding --json         # 带原文引用和来源的分类证据
aimx-recipes show oof_target_encoding --json             # Recipe 定义 + 派生的支持度统计
aimx-recipes search "extreme price spikes" --json        # 在证据上做全文检索
aimx-recipes facets                                       # 受控词表
aimx-recipes propose oof_target_encoding --problem problem.json --json
```

构建类命令需要显式调用，只会写入 `data/`：

```bash
aimx-recipes ingest kaggle --meta-kaggle ~/data/kaggle/meta-kaggle
aimx-recipes extract      # 离线抽取，调用 OpenAI 兼容接口
aimx-recipes build        # 确定性构建索引
```

## 与 aimx 的关系

| 系统 | 负责 |
| --- | --- |
| **aimx-recipes** | 外部经验、问题匹配、证据检索、Recipe 候选、实验提案 |
| aimx Research | Finding、Frontier、Agenda、Research State |
| AutoResearch | 规划、分派、执行 |
| aimx Retro | 复盘与后续方向 |
| Aim | Run、参数、指标 |

`aimx-recipes` 不写入 aimx 或 Aim 的任何状态。提案进入 aimx 的方式是：Lead 把它作为 `local_artifact` 证据引用挂到 Agenda 条目上。aimx 本身不需要任何改动。

## P0 范围

- **任务族：** 表格数据和表格化时间序列，包括按时间切分的验证。
- **语料：** 官方 [Meta Kaggle](https://www.kaggle.com/datasets/kaggle/meta-kaggle) 中的 writeup，关联竞赛背景信息。初步筛选得到约 179 场竞赛、1,582 篇 writeup。
- **先建评测：** 冻结一套约 30 个问题的基准，包括 3 个真实的 Tabloom 案例，以及按时间留一竞赛法构造的 Kaggle 问题，用来比较问题感知检索和 BM25、语义检索两个基线。

## 文档

| 文档 | 内容 |
| --- | --- |
| [CONSTITUTION.md](./CONSTITUTION.md) | 不可妥协的原则与质量门槛 |
| [ROADMAP.md](./ROADMAP.md) | 决策记录、规划中的 spec 001–014、待定问题 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 数据模型、存储分层、抽取、检索、与 aimx 的集成、CLI |
| [docs/EVALUATION.md](./docs/EVALUATION.md) | 基准、基线、指标、抽取评测、P0 验收 |
| [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md) | 数据来源、许可证、发布策略、Meta Kaggle 统计 |

以上文档以英文为准。

## 开发

项目使用 [Spec Kit](https://github.com/github/spec-kit)，接入了 pi 和 Claude Code 两个集成，并安装了 speckit-roadmap 扩展。宪章的权威版本是 `.specify/memory/constitution.md`，`CONSTITUTION.md` 是它的镜像。Spec Kit 和各 Agent 集成的目录（`.specify/`、`.pi/`、`.claude/`）只保留在本地，不进 git；仓库里跟踪的是 `CONSTITUTION.md` 和 `ROADMAP.md`。Python 工具链将使用 `uv`。

## 许可证

代码和项目自己编写的内容采用 [Apache-2.0](./LICENSE)。第三方数据沿用各自的许可证，详见 [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md)。
