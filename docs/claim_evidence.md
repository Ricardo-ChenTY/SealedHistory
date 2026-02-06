# Claim → Evidence Map

Assessment date: 2026-02-06  
Rerun confirmation: 2026-02-06 (ABC + oral-vNext rerun; evidence updated with `EXP-016..020`)  
Source claims: `docs/plan.md`  
Source experiment results: `docs/experiment.md`, `runs/EXP-*/`

| Claim ID | Verdict | Evidence (Exp IDs) | Key artifacts |
|---|---|---|---|
| CLAIM-001 | Yes | EXP-001, EXP-002 | `runs/EXP-001/eval_report_a.json`, `runs/EXP-002/eval_report_b.json` |
| CLAIM-002 | Yes | EXP-003 | `runs/exports/0.2.0-legacy/public/dataset_manifest.json`, `runs/EXP-003/check.log` |
| CLAIM-003 | Yes | EXP-004 | `runs/EXP-004/dataset_build_online.log`, `runs/EXP-004/exit_code.txt` |
| CLAIM-004 | Yes | EXP-005 | `runs/EXP-005/rg_gate.log`, `runs/EXP-005/exit_code.txt` |
| CLAIM-005 | Yes | EXP-006 | `runs/EXP-006/check_manual.log`, `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` |
| CLAIM-006 | Yes | EXP-006, EXP-007 | `runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_A_extended.jsonl`, `runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_B_extended.jsonl`, `runs/EXP-007/pytest.log` |
| CLAIM-007 | Yes | EXP-008, EXP-007 | `runs/EXP-008/snapshot_contract.log`, `runs/EXP-007/pytest.log` |
| CLAIM-008 | Yes | EXP-009 | `runs/EXP-009/attack_suite_policy.log`, `runs/EXP-006/exports/exp-006-manual-decisions/public/attack_suite/README.md` |
| CLAIM-009 | Yes | EXP-010 | `runs/EXP-010/demo_codebook_policy.log`, `provetok/data/sealed/README.md`, `README.md` |

## Gap Summary (CLAIM-001..009)

- Unsupported claims: 0
- Partial claims: 0
- Plan rewrite required: No

---

## Oral Addendum Coverage (2026-02-06)

| Oral ID | Verdict | Evidence | Notes |
|---|---|---|---|
| ORAL-001 (main table) | Yes | `runs/EXP-011/main_results.csv`, `runs/EXP-011/per_run_metrics.json` | Sealed vs Raw + two strong baselines, 3 seeds, mean±std complete |
| ORAL-002 (adaptive attacks) | Yes | `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json` | black-box and white-box metrics both reported |
| ORAL-003 (ablations) | Yes | `runs/EXP-013/ablation_results.csv`, `runs/EXP-013/manual_logging_ablation.json` | lexical/structure/numeric/manual logging axes covered |
| ORAL-004 (cross-domain) | Yes | `runs/EXP-014/cross_domain_summary.json` | black-box trend holds on A/B and white-box gap is explicitly disclosed per claim scope |
| ORAL-005 (human eval consistency) | Yes | `docs/templates/human_eval_sheet.csv`, `provetok/scripts/compute_human_eval_kappa.py`, `runs/EXP-015/human_eval_report.json` | dual-rater pipeline executable; `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280` |
| ORAL-006 (white-box defense tradeoff) | Yes | `provetok/scripts/run_oral_whitebox_defense.py`, `runs/EXP-016/summary.json` | both tracks report white-box leakage deltas and utility retention (`white_box_improves_all_tracks=true`) |
| ORAL-007 (statistical confidence) | Yes | `provetok/scripts/run_oral_stats_significance.py`, `runs/EXP-017/summary.json` | CI + permutation p-value + Cohen's d all materialized |
| ORAL-008 (budget attack curves) | Yes | `provetok/scripts/run_oral_budget_attack.py`, `runs/EXP-018/budget_curves.json` | budget sweeps reported for black-box/white-box and sealed/defended variants |
| ORAL-009 (holdout generalization) | Yes | `provetok/scripts/run_oral_holdout_generalization.py`, `runs/EXP-019/summary.json` | holdout utility/leakage exposed per-track; Track B non-improvement is explicitly retained |
| ORAL-010 (human-eval scale-up) | Yes | `docs/templates/human_eval_sheet.csv`, `runs/EXP-020/human_eval_report.json` | scale-up run completed with `n_paired_items=36` and reproducible output |

## Residual Oral Risks (Not Claim Gaps)

- White-box leakage remains high under budgeted attacks even after defense transforms (`runs/EXP-018/budget_curves.json`).
- Holdout black-box leakage trend does not strictly improve on Track B (`runs/EXP-019/summary.json`).
- Expanded human-eval agreement is low (`cohen_kappa=0.1280`), so oral narrative must avoid over-claiming consensus (`runs/EXP-020/human_eval_report.json`).
