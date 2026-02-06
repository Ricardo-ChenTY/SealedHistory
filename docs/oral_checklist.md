# Oral Checklist Status (2026-02-06)

Legend:
- `[x]` done
- `[~]` partial / ready but not fully closed

## A. 决定性实验

- [x] A1 主结果总表（Sealed vs Raw + 2 强基线，3 seeds，mean±std）
  - Evidence: `runs/EXP-011/main_results.md`, `runs/EXP-011/main_results.csv`
- [x] A2 自适应攻击评测（黑盒 + 白盒）
  - Evidence: `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json`
- [x] A3 关键模块消融（词汇/结构/数值 + manual logging 轴）
  - Evidence: `runs/EXP-013/ablation_results.md`, `runs/EXP-013/manual_logging_ablation.json`
- [x] A4 跨域泛化（Track A/B）
  - Evidence: `runs/EXP-014/cross_domain_summary.md`
  - Note: ORAL-004 按 black-box 跨域趋势为通过条件；white-box 结果已显式披露。
- [x] A5 人评一致性（双评审 + kappa）
  - Evidence: `docs/templates/human_eval_sheet.csv`, `provetok/scripts/compute_human_eval_kappa.py`, `runs/EXP-015/human_eval_report.md`
  - Note: 当前样本 `n_paired_items=6`, `cohen_kappa=0.5714`.

## B. 决定性叙事

- [x] B1 一句话主张（可证伪）
  - Evidence: `docs/oral_story.md` §1
- [x] B2 威胁模型图
  - Evidence: `docs/oral_story.md` §2
- [x] B3 失败案例页
  - Evidence: `docs/oral_story.md` §3
- [x] B4 统计严谨性页
  - Evidence: `docs/oral_story.md` §4
- [x] B5 复现与伦理页
  - Evidence: `docs/oral_story.md` §5
