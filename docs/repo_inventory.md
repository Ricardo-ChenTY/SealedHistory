# Repo Inventory — SealedHistory / ProveTok

## Tree
- `plan.md`: 数据收集与构建 proposal（dataset pipeline 目标/产物）
- `ProveTok_SealedHistory_Proposal.md`: 更广义的项目 proposal（SDG + Audit + Benchmark Env）
- `docs/`: 数据侧文档与 schema
  - `docs/schemas/`: JSON schema（v2 records）
  - `docs/templates/`: 人工裁剪/作者 PDF 覆盖等模板
  - `docs/mohu.md`: plan ↔ 实现差距追踪（Missing/Ambiguous）
- `provetok/`: Python 包（CLI / dataset pipeline / SDG / audit）
  - `provetok/src/provetok/`: 主要实现
  - `provetok/configs/`: YAML 配置（default/audit/dataset/sdg/env）
  - `provetok/scripts/`: 便捷脚本（dataset build / benchmark / audit）
  - `provetok/data/`: 示例 raw/sealed 数据与默认导出目录
  - `provetok/tests/`: pytest 测试

## Entry Points
- CLI：`provetok/src/provetok/cli.py`（console script: `provetok=provetok.cli:main`）
  - `provetok seal|audit|run|all`: sealed dataset + audit + benchmark（注意：`run` 依赖 `provetok.env`，目前缺失）
  - `provetok dataset build|export-legacy`: 数据集构建（plan.md 对齐）
- Dataset pipeline：`provetok/src/provetok/dataset/build.py:build_dataset()`
- Dataset online pipeline：`provetok/src/provetok/dataset/pipeline.py:build_online_dataset()`
- SDG（v2 records）：`provetok/src/provetok/sdg/sealer_v2.py`
- v2 泄漏审计：`provetok/src/provetok/dataset/audit_v2.py` + `provetok/scripts/run_audit_v2.py`

## Core Modules
- `provetok/data/`: v1/v2 schema 与 JSONL 读写
- `provetok/dataset/`: 选取（selection）、全文缓存（fulltext）、record 生成（record_builder）、QA、manifest、sealed worlds、attack suite
- `provetok/sources/`: OpenAlex / S2 / OpenCitations / arXiv / author PDF 下载（含 snapshot logging）
- `provetok/sdg/`: Sealed Domain Generator（词汇/结构/数值密封）
- `provetok/audit/`: v1 泄漏审计（对 `PaperRecord`）
- `provetok/eval/`: rubric 评分与报告
- `provetok/agents/`: agent 接口（目前 import 依赖缺失的 `provetok.env`）

## Config & Data
- 配置：
  - `provetok/configs/default.yaml`: seal/audit/run 默认配置
  - `provetok/configs/dataset.yaml`: dataset pipeline（online/strict）配置
- 数据：
  - `provetok/data/raw/micro_history_{a,b}.jsonl`: 本地示例 raw micro-history
  - dataset 导出：`provetok/data/exports/{dataset_version}/{public|private}/...`
- 环境变量（online build 常用）：
  - `LLM_API_KEY`: 严格 public record 构建（require_llm=true）所需
  - `S2_API_KEY`: Semantic Scholar API（可选但建议）

## How To Run
```bash
# (推荐) 依赖安装（editable）
python3 -m venv .venv
./.venv/bin/pip install -e provetok[dev]

# 运行测试
./.venv/bin/python -m pytest -q

# Dataset: legacy/offline 导出（不需要网络/LLM）
./.venv/bin/python -m provetok.cli dataset export-legacy --config provetok/configs/dataset.yaml --track both

# Dataset: online 严格构建（需要网络 + LLM_API_KEY；可选 S2_API_KEY）
export LLM_API_KEY=...
export S2_API_KEY=...   # optional
./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track both
```

## Risks / Unknowns
- `provetok.env` 模块缺失：`provetok/src/provetok/cli.py` 与 `provetok/src/provetok/agents/base.py` 依赖 `provetok.env.environment`，当前会导致 `provetok run` / `run_benchmark.py` 失败（需要补齐环境实现或移除依赖）。
- Online dataset build 依赖外部 API 与论文源可用性（OpenAlex/S2/arXiv/author PDF），需关注 rate limit / 超时与可重复性（通过 private snapshots 缓解）。

