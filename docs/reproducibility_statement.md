# Reproducibility Statement (vNext)

This repository is doc-driven: each claim in `docs/plan.md` is mapped to a runnable command and a deterministic artifact path.

## Environment

- Python: use the repo venv (`.venv/`) created via `python -m venv .venv`
- Dependencies: `pip install -r provetok/requirements.txt`
- Artifacts: all experiment outputs are written under `runs/` (gitignored) using stable subdirectories `runs/EXP-XXX/`.

## Minimal Reproduction (Plan Claims)

Run baseline chain (no paid APIs required):

```bash
./.venv/bin/python provetok/scripts/run_benchmark.py \
  --sealed provetok/data/sealed/micro_history_a.sealed.jsonl \
  --raw provetok/data/raw/micro_history_a.jsonl \
  --agent random \
  --output runs/EXP-001/eval_report_a.json

./.venv/bin/python provetok/scripts/run_benchmark.py \
  --sealed provetok/data/sealed/micro_history_b.sealed.jsonl \
  --raw provetok/data/raw/micro_history_b.jsonl \
  --agent random \
  --output runs/EXP-002/eval_report_b.json

./.venv/bin/python -m provetok.cli dataset build \
  --config provetok/configs/dataset_legacy.yaml \
  --track both \
  --out runs/exports

env -u LLM_API_KEY ./.venv/bin/python -m provetok.cli dataset build \
  --config provetok/configs/dataset.yaml \
  --track A \
  --out runs/exports_online_fail

./.venv/bin/python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match
./.venv/bin/python -m pytest -q
```

Expected key artifacts:
- `runs/EXP-001/eval_report_a.json`
- `runs/EXP-002/eval_report_b.json`
- `runs/exports/0.2.0-legacy/public/dataset_manifest.json`
- `runs/EXP-005/gate_no_try.log`
- `runs/EXP-007/pytest.log`

## Oral Addendum (micro-history)

```bash
./.venv/bin/python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33
./.venv/bin/python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33
./.venv/bin/python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014
./.venv/bin/python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33
./.venv/bin/python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128
./.venv/bin/python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7
./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020
```

## Oral vNext (scale + tradeoff) — Public Repro Path (no internal exports)

```bash
# Option A (recommended): use the exported public bundle (no codebooks).
# In this repo, it is materialized as:
#   runs/EXP-031/public/public_dataset_manifest.json
# In a public release, this directory should be provided as a tarball/zip.
SCALE_DATASET_DIR="runs/EXP-031/public"

./.venv/bin/python provetok/scripts/run_oral_main_table_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-022 --seeds 11 22 33

./.venv/bin/python provetok/scripts/run_oral_defense_knob_sweep_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-023 --seeds 11 22 33

./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py \
  --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-024
```

## Oral vNext (scale) — Maintainer-only Internal Build

If you have the internal v2 exports, you can rebuild the scale dataset used for `EXP-021..030`:

```bash
./.venv/bin/python provetok/scripts/build_oral_scale_dataset.py \
  --in_internal_a runs/exports_s2_full/0.2.0/private/track_A_extended_records.internal.jsonl \
  --in_internal_b runs/exports_s2_full/0.2.0/private/track_B_extended_records.internal.jsonl \
  --out_dir runs/EXP-021/dataset --seal_seed 42 --numeric_bins 10 --write_l1only
```

## Oral vNext (scale extensions: micro analyses replicated on non-toy)

```bash
# Reuse SCALE_DATASET_DIR from the section above.
./.venv/bin/python provetok/scripts/run_oral_ablations_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-025 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42

./.venv/bin/python provetok/scripts/run_oral_cross_domain.py \
  --input runs/EXP-022/per_run_metrics.json --output_dir runs/EXP-026

./.venv/bin/python provetok/scripts/run_oral_whitebox_defense_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-027 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42

./.venv/bin/python provetok/scripts/run_oral_stats_significance.py \
  --per_run runs/EXP-022/per_run_metrics.json --main_csv runs/EXP-022/main_results.csv \
  --defense_summary runs/EXP-027/summary.json --output_dir runs/EXP-028

./.venv/bin/python provetok/scripts/run_oral_budget_attack_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --defended_dir runs/EXP-027 --output_dir runs/EXP-029 \
  --max_observed 200 --seed 42 --budgets 8 16 32 64 128

./.venv/bin/python provetok/scripts/run_oral_holdout_generalization_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-030 --seeds 11 22 33 \
  --quantile 0.7 --attack_max_observed 200 --attack_seed 42
```

Expected key artifacts:
- `runs/EXP-031/public/public_dataset_manifest.json` (public repro bundle manifest)
- `runs/EXP-022/main_results.csv`
- `runs/EXP-023/tradeoff_curve.png`
- `runs/EXP-024/human_eval_report.json`
- `runs/EXP-025/ablation_results.csv`
- `runs/EXP-026/cross_domain_summary.json`
- `runs/EXP-027/summary.json`
- `runs/EXP-028/summary.json`
- `runs/EXP-029/budget_curves.json`
- `runs/EXP-030/summary.json`

## Optional: LLM Attacker Calibration (requires API key)

This produces an LLM-backed term-recovery report to calibrate heuristic leakage proxies:

```bash
set -a && source .env && set +a
./.venv/bin/python provetok/scripts/run_oral_llm_attacker_calibration.py \
  --out_dir runs/EXP-032 --overwrite --n_samples 20 --top_k 3 --seed 42 \
  --scale_dataset_dir runs/EXP-021/dataset
```

Expected key artifacts:
- `runs/EXP-032/summary.json`
- `runs/EXP-032/run_meta.json`
