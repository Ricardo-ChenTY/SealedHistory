# Oral Story Pack (2026-02-11, vNext)

## 1) One-Sentence Claim

On a scale (non-toy) run, SealedHistory keeps utility near raw (gap `raw - sealed = 0.0006`) while reducing black-box composite leakage (`1.0 -> 0.6667`), but white-box leakage remains high unless stronger defenses; we quantify the utility-vs-leakage tradeoff curve.

Shipping decision (explicit): recommend `level=2` (knee) for high utility retention with low black-box leakage; `level=4` achieves black-box leakage `0.0` with larger utility loss (see `runs/EXP-033/recommended_config.json`).

## 2) Threat Model

```text
Data publisher -> releases public sealed records
                -> keeps private codebook internal

Attacker A (black-box):
  - sees: sealed public records only
  - attack: retrieval/keyword matching

Attacker B (white-box):
  - sees: sealed records + codebook mapping
  - attack: reverse-map + retrieval

Attacker C (budgeted adaptive):
  - sees: same as A/B
  - attack: gradually increases token/query budget to maximize re-identification
```

Evaluation mapping:
- Main A/B attack: `runs/EXP-011/attacks/*_sealed.json`
- White-box defense tradeoff: `runs/EXP-016/summary.json`
- Budget curves: `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.png`
- Scale main table + attacks: `runs/EXP-022/main_results.csv`, `runs/EXP-022/attacks/`
- Defense knob sweep curve: `runs/EXP-023/tradeoff_curve.png`
- Scale ablations: `runs/EXP-025/ablation_results.csv`
- Scale cross-domain summary: `runs/EXP-026/cross_domain_summary.json`
- Scale strong defense (defended vs raw): `runs/EXP-027/summary.json`
- Scale stats (CI/p/d): `runs/EXP-028/summary.json`
- Scale budget curves: `runs/EXP-029/budget_curves.json`, `runs/EXP-029/budget_curves.png`
- Scale holdout: `runs/EXP-030/summary.json`
- LLM attacker calibration (term recovery): `runs/EXP-032/summary.json`

## 3) Failure-First Page

1. White-box budget attacks remain strong after defense transforms.
   - Evidence: `runs/EXP-029/budget_curves.png` (`A_defended` and `B_defended` white-box `top1` remains high).
2. Holdout improves black-box but does not address white-box leakage.
   - Evidence: `runs/EXP-030/summary.json` (black-box trend holds on A/B; white-box remains high).
3. Expanded human-eval agreement is low.
   - Evidence: `runs/EXP-020/human_eval_report.json` (`n_paired_items=36`, `cohen_kappa=0.1280`).
   - Added diagnostics: `runs/EXP-024/human_eval_report.json` (`krippendorff_alpha_nominal_binary=0.1372`, `pearson_r_overall=0.6449`, and many items are within `±0.05` of the threshold).
4. Defense reduces leakage but can cost utility.
   - Evidence: `runs/EXP-027/summary.json` (utility retention `~0.815` on scale; micro run is harsher at `0.533`).

## 4) Statistical Rigor

- Main table: 3 seeds (`11,22,33`) × 2 tracks (A/B), reported as mean±std (`runs/EXP-011/main_results.csv`).
- Significance layer (`runs/EXP-017/summary.json`):
  - `sealed_frontier - raw_frontier`: diff `-0.0526`, CI `[-0.0528, -0.0524]`, permutation `p=0.0010`, Cohen's d `-226.3544`.
  - `sealed_frontier - sealed_dependency`: diff `0.0005`, CI `[0.0002, 0.0008]`, `p=0.0384`.
  - `sealed_frontier - sealed_copylast`: diff `0.0090`, CI `[0.0084, 0.0095]`, `p=0.0010`.
- Scale significance layer (`runs/EXP-028/summary.json`): same CI/p/d scaffold on the non-toy dataset.
- Holdout summary (`runs/EXP-019/summary.json`):
  - `avg_utility_retention=0.9382`.
  - black-box trend holds on both tracks; white-box is explicitly disclosed as remaining high.

## 5) Reproducibility & Ethics

Repro commands:
```bash
python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33
python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33
python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017
python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128
python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7
python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020

 # scale vNext (public repro bundle; no internal exports required)
 SCALE_DATASET_DIR="runs/EXP-031/public"
 python provetok/scripts/run_oral_main_table_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-022 --seeds 11 22 33
 python provetok/scripts/run_oral_defense_knob_sweep_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-023 --seeds 11 22 33
 python provetok/scripts/run_oral_ablations_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-025 --seeds 11 22 33
 python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-022/per_run_metrics.json --output_dir runs/EXP-026
 python provetok/scripts/run_oral_whitebox_defense_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-027 --seeds 11 22 33
 python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-022/per_run_metrics.json --main_csv runs/EXP-022/main_results.csv --defense_summary runs/EXP-027/summary.json --output_dir runs/EXP-028
 python provetok/scripts/run_oral_budget_attack_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --defended_dir runs/EXP-027 --output_dir runs/EXP-029 --max_observed 200 --seed 42 --budgets 8 16 32 64 128
 python provetok/scripts/run_oral_holdout_generalization_vnext.py --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-030 --seeds 11 22 33 --quantile 0.7 --attack_max_observed 200 --attack_seed 42
 python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-024
```

Ethics and misuse notes:
- Demo codebooks remain synthetic and documented in `provetok/data/sealed/README.md`.
- White-box and budget vulnerabilities are explicitly exposed to avoid over-claiming security.
- Human ratings are tracked with anonymized reviewer IDs (`r1`,`r2`) and persisted as auditable CSV artifacts.
