# Repo Inventory — SealedHistory / ProveTok (2026-02-06)

## 1. Root Layout
- `README.md`: 顶层运行说明（含 demo codebook policy）
- `plan.md`: 原始 proposal（高层说明）
- `docs/`: doc-driven 状态文件与契约文档
  - `docs/plan.md`: canonical claims/spec
  - `docs/mohu.md`: 实现缺口与歧义跟踪（当前无未完成项）
  - `docs/verify_log.md`: 验证记录
  - `docs/experiment.md`: 实验矩阵与结果
  - `docs/schemas/`: `paper_record_v2` + `selection_log_row` + `paper_id_map_row` schema
  - `docs/templates/`: `manual_decisions.jsonl` 等模板
- `provetok/`: Python 包源码、配置、脚本、测试
  - `provetok/src/provetok/`: 业务实现
  - `provetok/configs/`: `default.yaml` / `dataset.yaml` / `dataset_legacy.yaml`
  - `provetok/scripts/`: benchmark/dataset/audit 入口脚本
  - `provetok/tests/`: pytest 测试
  - `provetok/data/`: micro-history 样例与 synthetic sealed demo 数据

## 2. Entrypoints
- CLI 总入口: `provetok/src/provetok/cli.py`
  - `python -m provetok.cli run`
  - `python -m provetok.cli dataset build`
- Dataset 构建入口: `provetok/src/provetok/dataset/build.py`
- Online pipeline 主流程: `provetok/src/provetok/dataset/pipeline.py`
- Benchmark 脚本: `provetok/scripts/run_benchmark.py`
- 审计脚本: `provetok/scripts/run_audit_v2.py`
- 离线人工决策实验脚本: `provetok/scripts/run_exp_manual_decisions_offline.py`
- Oral 主结果脚本: `provetok/scripts/run_oral_main_table.py`
- Oral 攻击评测脚本: `provetok/scripts/run_oral_adaptive_attack.py`
- Oral 消融脚本: `provetok/scripts/run_oral_ablations.py`
- Oral 跨域汇总脚本: `provetok/scripts/run_oral_cross_domain.py`
- 人评一致性脚本: `provetok/scripts/compute_human_eval_kappa.py`
- Oral 白盒防御 tradeoff 脚本: `provetok/scripts/run_oral_whitebox_defense.py`
- Oral 统计显著性脚本: `provetok/scripts/run_oral_stats_significance.py`
- Oral budget 攻击曲线脚本: `provetok/scripts/run_oral_budget_attack.py`
- Oral holdout 泛化脚本: `provetok/scripts/run_oral_holdout_generalization.py`

## 3. Core Modules
- `provetok/src/provetok/dataset/`: selection, fulltext, record_builder, QA, export manifest, sealed worlds, attack suite
- `provetok/src/provetok/sources/`: OpenAlex / S2 / OpenCitations / arXiv / PDF 抓取与 snapshot logging
- `provetok/src/provetok/data/`: schema 与 JSONL IO
- `provetok/src/provetok/env/` + `provetok/src/provetok/agents/` + `provetok/src/provetok/eval/`: benchmark 环境、agent、rubric
- `provetok/src/provetok/audit/`: leakage audit 逻辑

## 4. Verification Surfaces
- Baseline eval outputs: `runs/EXP-001/`, `runs/EXP-002/`
- Legacy export contract: `runs/exports/0.2.0-legacy/`
- Strict online expected-fail: `runs/EXP-004/dataset_build_online.log`
- Repo gate (`no try/except/finally`): `runs/EXP-005/rg_gate.log`
- Manual decision + paper_key evidence: `runs/EXP-006/exports/exp-006-manual-decisions/`
- Regression tests: `runs/EXP-007/pytest.log`
- Oral evidence pack: `runs/EXP-011/`, `runs/EXP-013/`, `runs/EXP-014/`, `runs/EXP-015/`, `runs/EXP-016/`, `runs/EXP-017/`, `runs/EXP-018/`, `runs/EXP-019/`, `runs/EXP-020/`

## 5. Environment Notes
- Python: 当前本地使用 `3.14.2`（`.venv`）
- 必要依赖: `provetok/requirements.txt`（包含 `jsonschema`、`pytest`）
- Online strict build 依赖: `LLM_API_KEY`（缺失时应早失败）
