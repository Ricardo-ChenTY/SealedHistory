# Oral Checklist Status (2026-02-11)

Legend:
- `[x]` done
- `[~]` done but still risk-bearing (must be narrated explicitly)

## A. 已有 Oral 基线（ORAL-001..005）

- [x] A1 主结果总表（Sealed vs Raw + 2 强基线，3 seeds，mean±std）
  - Evidence: `runs/EXP-011/main_results.md`, `runs/EXP-011/main_results.csv`
- [x] A2 自适应攻击评测（黑盒 + 白盒）
  - Evidence: `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json`
- [x] A3 关键模块消融（词汇/结构/数值 + manual logging 轴）
  - Evidence: `runs/EXP-013/ablation_results.md`, `runs/EXP-013/manual_logging_ablation.json`
- [x] A4 跨域泛化趋势汇总（Track A/B）
  - Evidence: `runs/EXP-014/cross_domain_summary.md`
  - Note: black-box 趋势通过；white-box gap 显式披露。
- [x] A5 人评一致性流程可执行（双评审 + kappa）
  - Evidence: `docs/templates/human_eval_sheet.csv`, `provetok/scripts/compute_human_eval_kappa.py`, `runs/EXP-015/human_eval_report.md`
  - Note: 扩样后当前 `n_paired_items=36`, `cohen_kappa=0.128`；vNext 也补充了 Krippendorff alpha（见 `runs/EXP-024/human_eval_report.json`）。

## B. 下一版“最小但决定性”实验清单（E1..E5）

- [x] E1 白盒防御增强 + utility tradeoff（防御前后 A/B 对照）
  - Evidence: `provetok/scripts/run_oral_whitebox_defense.py`, `runs/EXP-016/summary.md`
  - Key: `white_box_improves_all_tracks=true`，但 utility retention 存在明显折损。
- [x] E2 统计显著性与置信区间（CI + permutation p-value + effect size）
  - Evidence: `provetok/scripts/run_oral_stats_significance.py`, `runs/EXP-017/summary.md`
- [x] E3 自适应预算攻击曲线（budget sweep，含 defended vs sealed）
  - Evidence: `provetok/scripts/run_oral_budget_attack.py`, `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.png`
- [x] E4 Holdout 泛化评测（时间切分）
  - Evidence: `provetok/scripts/run_oral_holdout_generalization.py`, `runs/EXP-019/summary.md`
  - Key: black-box trend holds on A/B, but white-box leakage remains 1.0 (`runs/EXP-019/summary.json`).
- [x] E5 人评扩样（36 paired items）并重算一致性
  - Evidence: `docs/templates/human_eval_sheet.csv`, `runs/EXP-020/human_eval_report.md`

## C. 下一版“最小但决定性”叙事清单（N1..N5）

- [x] N1 核心主张升级为“结果 + 边界”双句式
  - Evidence: `docs/oral_story.md` §1
- [x] N2 威胁模型页升级为“三层攻击面”（black-box / white-box / budget）
  - Evidence: `docs/oral_story.md` §2
- [x] N3 失败先行页（明确展示最差项：white-box、budget、kappa）
  - Evidence: `docs/oral_story.md` §3
- [x] N4 统计页升级（均值方差 + CI + p-value + effect size）
  - Evidence: `docs/oral_story.md` §4
- [x] N5 复现实验页升级（一键命令链 + artifact 索引 + 伦理边界）
  - Evidence: `docs/oral_story.md` §5

## D. 下一版“冲顶会 oral”最小但决定性补齐清单（E6..E10 + N6..N10）

> 目标：把当前“可复现、可证伪”的 oral 基线升级为“顶会 oral 可信度”级别，即：规模、对比、边界、成本、复现都能在 10-12 分钟内讲清楚，并且 Q&A 扛得住。

### D1. 决定性实验（E6..E10）

- [x] E6 scale-up：在真实规模（非 toy）数据上复跑 ORAL 主链路，并把规模写进 manifest
  - Deliverables:
    - 一个可公开的 export（或可复现的生成脚本）+ 公共 bundle manifest（例如 `runs/EXP-031/public/public_dataset_manifest.json`）包含 `n_records` / `bytes` / `sha256` / `elapsed_sec`
    - main table 仍然输出 `runs/EXP-0xx/main_results.csv` + `summary.json`
  - PASS: “主结论方向”在更大规模下仍成立；若不成立，必须在 oral story 中改为边界条件而不是主张。
  - Evidence:
    - Scale dataset builder: `provetok/scripts/build_oral_scale_dataset.py`
    - Scale public bundle exporter: `provetok/scripts/export_oral_scale_public_bundle.py`, `runs/EXP-031/public/public_dataset_manifest.json`
    - Manifest (n_items/bytes/elapsed): `runs/EXP-021/dataset/dataset_manifest.json`
    - Scale main table: `provetok/scripts/run_oral_main_table_vnext.py`, `runs/EXP-022/main_results.csv`, `runs/EXP-022/summary.json`

- [x] E7 stronger baselines：新增至少 2 个“读者一眼能懂且公平”的 baseline，并纳入 main table + attack suite
  - Examples:
    - naive redaction（删背景/关键词/机制描述）
    - paraphrase / summary（保持语义但打散表述）
  - PASS: baseline 定义清晰、可复现、与 SealedHistory 使用同一 rubric/attack protocol。
  - Evidence:
    - Baselines in table: `runs/EXP-022/main_results.csv` (`sealed_summary_frontier`, `sealed_redact_frontier`)
    - Attack artifacts: `runs/EXP-022/attacks/`

- [x] E8 white-box 退火曲线：把 defense 做成“可调强度”的 knob，输出 utility-retention vs leakage 的 tradeoff curve
  - PASS: 至少 5 个 knob 点；输出曲线 JSON + 一张可直接进 slide 的图。
  - Evidence:
    - Script: `provetok/scripts/run_oral_defense_knob_sweep_vnext.py`
    - Curve + plot: `runs/EXP-023/tradeoff_curve.json`, `runs/EXP-023/tradeoff_curve.png`

- [~] E9 human-eval 可信度升级：把人评从“管线可跑”升级为“协议可信”
  - Deliverables:
    - 3+ raters 或者更严格的双评审培训协议
    - 报告 Cohen’s kappa 之外再补充 Krippendorff’s alpha（或明确为何不适用）
  - PASS: 一致性达到可解释阈值；若达不到，必须把 human-eval 降级为辅助证据并明确限制。
  - Evidence:
    - Added alpha + diagnostics: `provetok/scripts/compute_human_eval_kappa.py`, `runs/EXP-024/human_eval_report.json` (includes alpha, Pearson/Spearman, near-threshold counts)
  - Remaining:
    - Need additional raters (3+) or a documented training protocol to reduce agreement risk.

- [x] E10 cost/profile：补齐 compute/cost profile，让 Q&A 能回答“你这个方法到底贵不贵”
  - Deliverables:
    - 关键实验（main + attacks + build）记录 `elapsed_sec`、硬件、峰值内存/显存、（如有）API token/费用
  - PASS: `runs/EXP-0xx/` 里有机器可读的 `run_meta.json`（或 manifest 字段）。
  - Evidence:
    - Build manifest runtime: `runs/EXP-021/dataset/dataset_manifest.json`
    - Main-table run meta: `runs/EXP-022/run_meta.json`
    - Knob-sweep run meta: `runs/EXP-023/run_meta.json`

- [x] E11 scale replicate：把 micro 的关键诊断链路也在 non-toy 上复现（更硬叙事）
  - Scope: ORAL-003/004/006/007/008/009 的 scale 版（ablation/cross-domain/defense/stats/budget/holdout）
  - Evidence:
    - Ablations (scale): `runs/EXP-025/ablation_results.csv`
    - Cross-domain (scale): `runs/EXP-026/cross_domain_summary.json`
    - Strong defense (scale): `runs/EXP-027/summary.json`
    - Stats (scale): `runs/EXP-028/summary.json`
    - Budget curves (scale): `runs/EXP-029/budget_curves.json`
    - Holdout (scale): `runs/EXP-030/summary.json`

- [x] E12 LLM attacker calibration：用真实 LLM 攻击校准“heuristic leakage proxy”
  - Deliverables:
    - term-recovery hit@1/hit@3（micro A/B；可选 scale A/B）+ 记录模型与 endpoint
    - 与现有 heuristic attack 的 composite leakage 并列（用于校准/对齐）
  - PASS: 产物可复现并明确指出 LLM 攻击强度与命中率（不再停留在启发式 proxy）
  - Evidence:
    - Script: `provetok/scripts/run_oral_llm_attacker_calibration.py`
    - Artifacts: `runs/EXP-032/summary.json`, `runs/EXP-032/run_meta.json`

### D2. 决定性叙事（N6..N10）

- [x] N6 两套时间框架脚本：12-min main talk + 4-min spotlight 版（同一套 story）
  - PASS: 12-min 版本严格时间分配（问题/方法/结果/局限/总结）；4-min 版本只保留 4 张“可视化”主信息。
  - Evidence: `docs/oral_scripts/oral_12min.md`, `docs/oral_scripts/oral_spotlight_3min.md`

- [x] N7 一页“Claim → Evidence → Artifact”索引图（用于 oral 现场+Q&A 指路）
  - PASS: 每个 CLAIM/ORAL 都能指到一个具体 artifact 文件路径。
  - Evidence: `docs/oral_artifact_index.md`

- [x] N11 推荐配置（knee / shipping decision）明确写进主文与口头叙事
  - PASS: 明确给出“推荐 level=2（knee）”以及“黑盒 0 泄漏 level=4”的代价取舍，并指向可机器复现的选择依据。
  - Evidence: `runs/EXP-033/recommended_config.json`, `runs/EXP-023/tradeoff_curve.json`, `plan.md` §4.4/§4.8

- [x] N8 限制与负面影响页升级（把风险讲清楚，不被 reviewer 认为“回避”）
  - PASS: 清楚写出 3-5 条限制 + 2-3 条潜在滥用/负面影响 + 对应 mitigation。
  - Evidence: `docs/oral_limitations_negative_impacts.md`

- [x] N9 Reproducibility Statement（论文级）+ Repro Slide（口头级）
  - PASS: 论文末尾有 reproducibility statement（指向 code/data/appendix）；slide 里有“一条命令复现最关键结果”。
  - Evidence: `docs/reproducibility_statement.md` (statement + command chain), `docs/oral_scripts/oral_12min.md` (repro slide block)

- [x] N10 Q&A 预案：预写 10 个最可能被问到的问题，并准备备份页（含数字/图）
  - PASS: 覆盖 cost、white-box、scale、baseline 公平性、human-eval 可信度、数据许可/伦理、失败案例。
  - Evidence: `docs/oral_qa.md`
