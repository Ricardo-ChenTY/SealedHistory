# Oral Story Pack (2026-02-06, vNext)

## 1) One-Sentence Claim

Under 3 seeds × 2 tracks, SealedHistory keeps utility close to raw (`sealed_frontier - raw_frontier = -0.0095`, `p=0.6059`) while reducing black-box composite leakage (`0.6333` vs `0.8334`), but it is not robust against strong white-box and budgeted attacks.

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
- Budget curves: `runs/EXP-018/budget_curves.json`

## 3) Failure-First Page

1. White-box budget attacks remain strong after defense transforms.
   - Evidence: `runs/EXP-018/budget_curves.json` (`A_defended` and `B_defended` white-box `top1` remains high).
2. Holdout generalization is mixed across tracks.
   - Evidence: `runs/EXP-019/summary.json` (`black_box_trend_holds_all_tracks=false`; Track B is non-improving).
3. Expanded human-eval agreement is low.
   - Evidence: `runs/EXP-020/human_eval_report.json` (`n_paired_items=36`, `cohen_kappa=0.1280`).
4. Defense reduces leakage but can cost utility.
   - Evidence: `runs/EXP-016/summary.json` (Track A utility retention `0.5788`).

## 4) Statistical Rigor

- Main table: 3 seeds (`11,22,33`) × 2 tracks (A/B), reported as mean±std (`runs/EXP-011/main_results.csv`).
- Significance layer (`runs/EXP-017/summary.json`):
  - `sealed_frontier - raw_frontier`: diff `-0.0095`, 95% CI `[-0.1379, 0.1220]`, permutation `p=0.6059`, Cohen's d `-0.0683`.
  - `sealed_frontier - sealed_dependency`: diff `-0.0424`, CI `[-0.1593, 0.0796]`, `p=0.5615`.
  - `sealed_frontier - sealed_copylast`: diff `0.0196`, CI `[-0.1312, 0.1847]`, `p=0.6251`.
- Holdout summary (`runs/EXP-019/summary.json`):
  - `avg_utility_retention=0.9913`.
  - trend caveat is preserved rather than hidden.

## 5) Reproducibility & Ethics

Repro commands:
```bash
python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33
python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33
python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017
python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128
python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7
python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020
```

Ethics and misuse notes:
- Demo codebooks remain synthetic and documented in `provetok/data/sealed/README.md`.
- White-box and budget vulnerabilities are explicitly exposed to avoid over-claiming security.
- Human ratings are tracked with anonymized reviewer IDs (`r1`,`r2`) and persisted as auditable CSV artifacts.
