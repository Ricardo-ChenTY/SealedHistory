# Oral Checklist Status (2026-02-06)

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
  - Note: 扩样后当前 `n_paired_items=36`, `cohen_kappa=0.128`。

## B. 下一版“最小但决定性”实验清单（E1..E5）

- [x] E1 白盒防御增强 + utility tradeoff（防御前后 A/B 对照）
  - Evidence: `provetok/scripts/run_oral_whitebox_defense.py`, `runs/EXP-016/summary.md`
  - Key: `white_box_improves_all_tracks=true`，但 utility retention 存在明显折损。
- [x] E2 统计显著性与置信区间（CI + permutation p-value + effect size）
  - Evidence: `provetok/scripts/run_oral_stats_significance.py`, `runs/EXP-017/summary.md`
- [x] E3 自适应预算攻击曲线（budget sweep，含 defended vs sealed）
  - Evidence: `provetok/scripts/run_oral_budget_attack.py`, `runs/EXP-018/budget_curves.md`
- [x] E4 Holdout 泛化评测（时间切分）
  - Evidence: `provetok/scripts/run_oral_holdout_generalization.py`, `runs/EXP-019/summary.md`
  - Key: A 轨提升，B 轨与 raw 持平（需在 oral 中正面披露）。
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
