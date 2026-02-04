# SealedHistory / ProveTok 数据文档

本目录用于承载与 `plan.md`（数据收集与构建 Proposal v1.0）对齐的**数据需求、采集清单与采集 Proposal**。

## 文件一览

- `docs/data_requirements.md`：完整数据需求（字段级、Public/Private 分层、来源与约束）
- `docs/collection_checklist.md`：采集清单（可执行步骤 + 产物路径 + 哈希/日志要求 + 验收）
- `docs/data_collection_proposal.md`：采集 Proposal（合规、复现、风险、里程碑）
- `docs/mohu.md`：plan.md ↔ 实现差距追踪（Missing/Ambiguous backlog）
- `docs/schemas/paper_record_v2.schema.json`：公开发布的 v2 record JSON Schema
- `docs/templates/manual_decisions.jsonl`：人工裁剪输入模板（JSONL）
- `docs/templates/author_pdf_overrides.yaml`：作者公开 PDF 覆盖表模板（YAML）

## 与仓库代码对齐点

- Dataset 管线入口：`provetok dataset build --config provetok/configs/dataset.yaml`
- 导出目录：`provetok/data/exports/{dataset_version}/public` 与 `.../private`
- v2 schema（代码定义）：`provetok/src/provetok/data/schema_v2.py`
- v2 审计脚本（可选）：`provetok/scripts/run_audit_v2.py`
