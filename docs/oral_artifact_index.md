# Oral Artifact Index (One Page)

Use this as the oral/Q&A “map”: every claim points to a concrete artifact path.

## A. Plan Claims (CLAIM-001..009)

| Claim | Evidence | Key Artifacts |
|---|---|---|
| CLAIM-001 | EXP-001, EXP-002 | `runs/EXP-001/eval_report_a.json`, `runs/EXP-002/eval_report_b.json` |
| CLAIM-002 | EXP-003 | `runs/exports/0.2.0-legacy/public/dataset_manifest.json` |
| CLAIM-003 | EXP-004 | `runs/EXP-004/dataset_build_online.log` |
| CLAIM-004 | EXP-005 | `runs/EXP-005/gate_no_try.log` |
| CLAIM-005 | EXP-006 | `runs/EXP-006/check_manual.log` |
| CLAIM-006 | EXP-006, EXP-007 | `runs/EXP-007/pytest.log` |
| CLAIM-007 | EXP-008, EXP-007 | `runs/EXP-008/snapshot_contract.log` |
| CLAIM-008 | EXP-009 | `runs/EXP-009/attack_suite_policy.log` |
| CLAIM-009 | EXP-010 | `runs/EXP-010/demo_codebook_policy.log` |

Source-of-truth map:
- `docs/claim_evidence.md`

## B. Oral Addendum (ORAL-001..010, micro-history)

| Oral ID | Evidence | Key Artifacts |
|---|---|---|
| ORAL-001 | EXP-011 | `runs/EXP-011/main_results.csv`, `runs/EXP-011/summary.json` |
| ORAL-002 | EXP-012 | `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json` |
| ORAL-003 | EXP-013 | `runs/EXP-013/ablation_results.csv` |
| ORAL-004 | EXP-014 | `runs/EXP-014/cross_domain_summary.json` |
| ORAL-005 | EXP-015 | `runs/EXP-015/human_eval_report.json` |
| ORAL-006 | EXP-016 | `runs/EXP-016/summary.json` |
| ORAL-007 | EXP-017 | `runs/EXP-017/summary.json` |
| ORAL-008 | EXP-018 | `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.png` |
| ORAL-009 | EXP-019 | `runs/EXP-019/summary.json` |
| ORAL-010 | EXP-020 | `runs/EXP-020/human_eval_report.json` |

## C. Oral vNext (Scale + Baselines + Tradeoff)

| Item | Purpose | Key Artifacts |
|---|---|---|
| EXP-021 | build scale dataset | `runs/EXP-021/dataset/dataset_manifest.json` |
| EXP-022 | scale main table + baselines | `runs/EXP-022/main_results.csv`, `runs/EXP-022/attacks/`, `runs/EXP-022/run_meta.json` |
| EXP-023 | defense knob sweep curve | `runs/EXP-023/tradeoff_curve.png`, `runs/EXP-023/tradeoff_curve.json`, `runs/EXP-023/run_meta.json` |
| EXP-024 | human agreement (kappa + alpha) | `runs/EXP-024/human_eval_report.json` |
| EXP-025 | scale ablations (ORAL-003 on non-toy) | `runs/EXP-025/ablation_results.csv`, `runs/EXP-025/attacks/` |
| EXP-026 | scale cross-domain summary | `runs/EXP-026/cross_domain_summary.json` |
| EXP-027 | scale white-box defense | `runs/EXP-027/summary.json`, `runs/EXP-027/defended_A.jsonl`, `runs/EXP-027/defended_B.jsonl` |
| EXP-028 | scale stats (CI/p/d) | `runs/EXP-028/summary.json` |
| EXP-029 | scale budget curves | `runs/EXP-029/budget_curves.json`, `runs/EXP-029/budget_curves.png` |
| EXP-030 | scale holdout generalization | `runs/EXP-030/summary.json` |
| EXP-031 | scale public bundle export (no codebooks) | `runs/EXP-031/public/public_dataset_manifest.json` |
| EXP-032 | LLM attacker calibration (term recovery) | `runs/EXP-032/summary.json`, `runs/EXP-032/run_meta.json` |
| EXP-033 | recommended release config (knee) | `runs/EXP-033/recommended_config.json`, `runs/EXP-033/recommended_config.md` |

Scripts:
- `provetok/scripts/build_oral_scale_dataset.py`
- `provetok/scripts/export_oral_scale_public_bundle.py`
- `provetok/scripts/run_oral_llm_attacker_calibration.py`
- `provetok/scripts/derive_recommended_release_config.py`
- `provetok/scripts/plot_budget_curves.py`
- `provetok/scripts/run_oral_main_table_vnext.py`
- `provetok/scripts/run_oral_defense_knob_sweep_vnext.py`
- `provetok/scripts/compute_human_eval_kappa.py`
