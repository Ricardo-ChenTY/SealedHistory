# Repo Inventory — SealedHistory / ProveTok

## Tree
- `plan.md`: 数据收集与构建 proposal（dataset pipeline 目标/产物）
- `ProveTok_SealedHistory_Proposal.md`: 项目 proposal（SDG + Audit + Benchmark Env）
- `docs/`: 数据侧文档与 schema / backlog
  - `docs/schemas/`: JSON schema（v2 records）
  - `docs/templates/`: 人工裁剪/作者 PDF 覆盖等模板
  - `docs/mohu.md`: plan ↔ 实现差距追踪（Missing/Ambiguous）
- `provetok/`: Python 包（CLI / dataset pipeline / SDG / audit / benchmark env）
  - `provetok/src/provetok/`: 主要实现
  - `provetok/configs/`: YAML 配置（default/audit/dataset/sdg/env）
  - `provetok/scripts/`: 便捷脚本（dataset build / benchmark / audit）
  - `provetok/data/`: 示例 raw/sealed micro-history + 导出根目录
  - `provetok/tests/`: pytest 测试

## Entry Points
- CLI：`provetok/src/provetok/cli.py`（console script: `provetok=provetok.cli:main`）
  - `provetok seal|audit|run|all`: sealed dataset + audit + benchmark
  - `provetok dataset build|export-legacy`: 数据集构建（plan.md 对齐）
- Dataset orchestration：`provetok/src/provetok/dataset/build.py:build_dataset()`
- Dataset online pipeline：`provetok/src/provetok/dataset/pipeline.py:build_online_dataset()`
- Benchmark script：`provetok/scripts/run_benchmark.py`
- v2 泄漏审计：`provetok/src/provetok/dataset/audit_v2.py` + `provetok/scripts/run_audit_v2.py`

## Core Modules
- `provetok/data/`: v1/v2 schema 与 JSONL 读写
- `provetok/dataset/`: selection/fulltext/record_builder/QA/manifest/sealed worlds/attack suite
- `provetok/sources/`: OpenAlex / S2 / OpenCitations / arXiv / author PDF 下载（含 snapshot logging）
- `provetok/sdg/`: Sealed Domain Generator（词汇/结构/数值密封）
- `provetok/audit/`: v1 泄漏审计（对 `PaperRecord`）
- `provetok/env/`: benchmark 环境（fast-mode：read → propose → experiment → review）
- `provetok/agents/`: agent 接口（LLM agent + random baseline）
- `provetok/eval/`: rubric 评分、报告与可视化

## Config & Data
- 配置：
  - `provetok/configs/default.yaml`: seal/audit/run 默认配置
  - `provetok/configs/env.yaml`: benchmark env 配置（budget/fast_mode）
  - `provetok/configs/dataset.yaml`: dataset pipeline（online/strict）配置
- 示例数据：
  - `provetok/data/raw/micro_history_{a,b}.jsonl`: raw micro-history（MVP 样例）
  - `provetok/data/sealed/micro_history_{a,b}.sealed.jsonl`: sealed micro-history（含 `.codebook.json`）
  - dataset 导出：`provetok/data/exports/{dataset_version}/{public|private}/...`（生成物；git 忽略）
- 环境变量（online / LLM 常用）：
  - `LLM_API_KEY`: online 严格 public record 构建与真实 audit/agent LLM 调用所需
  - `S2_API_KEY`: Semantic Scholar API（可选但建议）

## How To Run
```bash
# 依赖安装（editable）
python3 -m venv .venv
./.venv/bin/pip install -e provetok[dev]

# 运行测试
./.venv/bin/python -m pytest -q

# Benchmark: fast-mode 随机 baseline（不需要 LLM）
./.venv/bin/python -m provetok.cli run --agent random \
  --sealed provetok/data/sealed/micro_history_a.sealed.jsonl \
  --raw provetok/data/raw/micro_history_a.jsonl \
  --output output/eval_report.json

# Dataset: legacy/offline 导出（不需要网络/LLM）
./.venv/bin/python -m provetok.cli dataset export-legacy \
  --config provetok/configs/dataset.yaml --track both

# Dataset: online 严格构建（需要网络 + LLM_API_KEY；可选 S2_API_KEY）
export LLM_API_KEY=...
export S2_API_KEY=...   # optional
./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track both
```

## Risks / Unknowns
- `provetok audit` 与 `provetok run --agent llm` 的指标质量依赖真实 LLM endpoint；未配置 `LLM_API_KEY` 时会进入 dummy mode（可跑通但不代表真实泄漏/能力水平）。
- Online dataset build 依赖外部 API 与论文源可用性（OpenAlex/S2/arXiv/author PDF），需关注 rate limit / 超时与可重复性（private snapshots 可缓解但不能消除外部依赖）。
