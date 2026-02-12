# Claim → Evidence Map

Assessment date: 2026-02-11  
Rerun confirmation: 2026-02-11 (reran `EXP-001..020` + `pytest`; plus scale extensions `EXP-025..030`; plus arXiv-aligned full runs `EXP-034..038`)  
Source claims: `docs/plan.md`  
Source experiment results: `docs/experiment.md`, `runs/EXP-*/`

| Claim ID | Verdict | Evidence (Exp IDs) | Key artifacts |
|---|---|---|---|
| CLAIM-001 | Yes | EXP-001, EXP-002 | `runs/EXP-001/eval_report_a.json`, `runs/EXP-002/eval_report_b.json` |
| CLAIM-002 | Yes | EXP-003 | `runs/exports/0.2.0-legacy/public/dataset_manifest.json`, `runs/EXP-003/check.log` |
| CLAIM-003 | Yes | EXP-004 | `runs/EXP-004/dataset_build_online.log`, `runs/EXP-004/exit_code.txt` |
| CLAIM-004 | Yes | EXP-005 | `runs/EXP-005/gate_no_try.log`, `runs/EXP-005/exit_code.txt` |
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

## Oral Addendum Coverage (micro + scale) (2026-02-11)

| Oral ID | Verdict | Evidence | Notes |
|---|---|---|---|
| ORAL-001 (main table) | Yes | `runs/EXP-011/main_results.csv` (micro), `runs/EXP-022/main_results.csv` (scale) | micro diagnostic + non-toy scale main table both exist (seeds=3) |
| ORAL-002 (adaptive attacks) | Yes | `runs/EXP-011/attacks/A_sealed.json` (micro), `runs/EXP-022/attacks/` (scale) | black-box and white-box metrics both reported (micro+scale) |
| ORAL-003 (ablations) | Yes | `runs/EXP-013/ablation_results.csv` (micro), `runs/EXP-025/ablation_results.csv` (scale) | lexical/structure/numeric/manual logging axes replicated on scale |
| ORAL-004 (cross-domain) | Yes | `runs/EXP-014/cross_domain_summary.json` (micro), `runs/EXP-026/cross_domain_summary.json` (scale) | BB trend holds; WB gap explicitly disclosed |
| ORAL-005 (human eval consistency) | Yes | `docs/templates/human_eval_sheet.csv`, `runs/EXP-015/human_eval_report.json`, `runs/EXP-024/human_eval_report.json` | dual-rater pipeline executable; agreement diagnostics include kappa + alpha |
| ORAL-006 (white-box defense tradeoff) | Yes | `runs/EXP-016/summary.json` (micro), `runs/EXP-023/tradeoff_curve.json` + `runs/EXP-027/summary.json` (scale) | defended WB deltas + utility retention; scale tradeoff curve is slide-ready |
| ORAL-007 (statistical confidence) | Yes | `runs/EXP-017/summary.json` (micro), `runs/EXP-028/summary.json` (scale) | CI + permutation p-value + Cohen's d materialized (micro+scale) |
| ORAL-008 (budget attack curves) | Yes | `runs/EXP-018/budget_curves.json` (micro), `runs/EXP-029/budget_curves.json` (scale) | budget sweeps reported for BB/WB and sealed/defended (micro+scale) |
| ORAL-009 (holdout generalization) | Yes | `runs/EXP-019/summary.json` (micro), `runs/EXP-030/summary.json` (scale) | temporal holdout utility retention + leakage trend flags on both scales |
| ORAL-010 (human-eval scale-up) | Yes | `runs/EXP-020/human_eval_report.json`, `runs/EXP-024/human_eval_report.json` | scale-up run reproducible; diagnostics include alpha and near-threshold stats |

## Oral ArXiv-Aligned Coverage (2026-02-11)

| Oral ID | Verdict | Evidence | Notes |
|---|---|---|---|
| ORAL-011 (ConStat-style contamination stats) | Yes | `runs/EXP-034/summary.json`, `runs/EXP-034/run_meta.json` | contamination_score=0.0085 (CI95 [0.0028, 0.0142]); corrected_utility_gap=-0.0662 |
| ORAL-012 (LatestEval/LiveBench-style dynamic windows) | Yes | `runs/EXP-035/summary.json`, `runs/EXP-035/window_inputs/` | avg_utility_retention=0.9998; black_box_trend_holds_all_windows=true |
| ORAL-013 (DyePack-style contamination tagging) | Yes | `runs/EXP-036/summary.json`, `runs/EXP-036/summary.md` | mean_traceable_coverage=0.9964; mean_false_positive_rate=0.0 |
| ORAL-014 (Carlini/Nasr-style extraction stress) | Yes | `runs/EXP-037/summary.json`, `runs/EXP-037/tmp_budget_views/` | sealed AUC(top1)=1.0 vs defended AUC(top1)=0.0 (A/B); max-budget defended-minus-sealed white-box top1=-1.0 |
| ORAL-015 (LLM-as-a-judge validation) | Yes | `runs/EXP-038/summary.json`, `runs/EXP-038/run_meta.json` | kappa=1.0, spearman=1.0, mae=0.0017, pass_rule=true |
| ORAL-016 (validity invariance + metadata-only sanity) | Yes | `runs/EXP-039/summary.json`, `runs/EXP-040/summary.json` | EXP-039: spearman(raw,sealed)=1.0; metadata_only frontier utility=0.5626 vs sealed=0.8417. EXP-040: micro raw≈sealed utility_mean (A 0.6455 vs 0.6187; B 0.6459 vs 0.6201) and metadata_only/structure_only mechanism_class ≤0.10; scale sealed ≥ raw and metadata_only/structure_only mechanism_class=0.0. |

## Residual Oral Risks (Not Claim Gaps)

- White-box leakage remains high under budgeted attacks even after defense transforms (`runs/EXP-018/budget_curves.json`, `runs/EXP-029/budget_curves.json`).
- Holdout shows black-box trend holds, but white-box leakage remains high (`runs/EXP-019/summary.json`, `runs/EXP-030/summary.json`).
- Expanded human-eval agreement is low (`cohen_kappa=0.1280`), so oral narrative must avoid over-claiming consensus (`runs/EXP-020/human_eval_report.json`, `runs/EXP-024/human_eval_report.json`).
- LLM-backed term-recovery attacker has low hit rates on both micro and scale, supporting that pseudotokens are not trivially invertible beyond the heuristic proxy (`runs/EXP-032/summary.json`).

## Oral vNext Scale Coverage (2026-02-11)

| Item | Verdict | Evidence | Notes |
|---|---|---|---|
| Scale dataset build | Yes | `runs/EXP-021/dataset/dataset_manifest.json` | non-toy dataset materialized for EXP-022..030 |
| Scale public bundle export | Yes | `runs/EXP-031/public/public_dataset_manifest.json` | public repro path without internal exports; excludes `*.codebook.json` |
| Scale main table + baselines | Yes | `runs/EXP-022/main_results.csv`, `runs/EXP-022/summary.json` | non-toy dataset; includes stronger baselines |
| Scale tradeoff curve (knob sweep) | Yes | `runs/EXP-023/tradeoff_curve.png`, `runs/EXP-023/tradeoff_curve.json` | 5 knob points, slide-ready plot |
| Recommended config (knee) | Yes | `runs/EXP-033/recommended_config.json` | explicit shipping decision derived from the tradeoff curve |
| Scale ablations (ORAL-003 on scale) | Yes | `runs/EXP-025/ablation_results.csv` | lexical sealing drives black-box leakage |
| Scale cross-domain summary | Yes | `runs/EXP-026/cross_domain_summary.json` | BB trend holds; WB does not |
| Scale strong defense (defended vs raw) | Yes | `runs/EXP-027/summary.json` | WB deltas + utility retention materialized |
| Scale stats (CI/p/d) | Yes | `runs/EXP-028/summary.json` | same scaffold as EXP-017 on scale main table |
| Scale budget curves | Yes | `runs/EXP-029/budget_curves.json` | sealed reaches top1≈1.0 at moderate budgets; WB remains high after defense |
| Scale holdout | Yes | `runs/EXP-030/summary.json` | holdout retention ≈ 1.0; BB trend holds |
