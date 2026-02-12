# Verify Log

## Missing-010
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes taxonomy + mechanism-tag normalization tests.
  - Artifacts: N/A

## Missing-011
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes arXiv-source formula_graph extraction unit test.
  - Artifacts: N/A

## Missing-012
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes offline-online provenance snapshot reference integration test.
  - Artifacts: N/A

## Missing-013
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes v2 time-index/canonical-order attack unit test.
  - Artifacts: N/A

## Missing-014
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes selection-signal unit tests (citation_velocity/bridge proxies).
  - Artifacts: N/A

## Missing-016
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes PWC QA cross-check unit test.
  - Artifacts: N/A

## Missing-017
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes private-seeds export unit test.
  - Artifacts: N/A

## Amb-002
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Name/identity fingerprint policy optional flag + allowlist tests.
  - Artifacts: N/A

## Missing-019
- 2026-02-05: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes `provetok run` random-agent smoke test and verifies env package is importable.
  - Artifacts: N/A
- 2026-02-05: `./.venv/bin/python -m provetok.cli run --agent random --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --output /tmp/eval_report_a.json`
  - Result: PASS
  - Notes: CLI benchmark simulation produces a valid eval report.
  - Artifacts: `/tmp/eval_report_a.json`

## Missing-020
- 2026-02-05: `./.venv/bin/python -m provetok.cli run --agent random --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --output /tmp/eval_report_b.json`
  - Result: PASS
  - Notes: Track B sealed sample runs end-to-end.
  - Artifacts: `/tmp/eval_report_b.json`

## ABC-Loop-2026-02-06
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --agent random --output runs/EXP-001/eval_report_a.json`
  - Result: PASS
  - Artifacts: `runs/EXP-001/eval_report_a.json`, `runs/EXP-001/check.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --agent random --output runs/EXP-002/eval_report_b.json`
  - Result: PASS
  - Artifacts: `runs/EXP-002/eval_report_b.json`, `runs/EXP-002/check.log`
- 2026-02-06: `./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset_legacy.yaml --track both --out runs/exports`
  - Result: PASS
  - Artifacts: `runs/exports/0.2.0-legacy/public/dataset_manifest.json`, `runs/EXP-003/check.log`
- 2026-02-06: `env -u LLM_API_KEY ./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track A --out runs/exports_online_fail`
  - Result: PASS (expected failure; exit code 1)
  - Artifacts: `runs/EXP-004/dataset_build_online.log`, `runs/EXP-004/exit_code.txt`, `runs/EXP-004/check.log`
- 2026-02-06: `rg -n "\btry\b\s*:|\bexcept\b|\bfinally\b" provetok/src/provetok provetok/scripts provetok/tests`
  - Result: PASS (0 matches; rg exit code 1)
  - Artifacts: `runs/EXP-005/rg_gate.log`, `runs/EXP-005/exit_code.txt`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both`
  - Result: PASS
  - Artifacts: `runs/EXP-006/check_manual.log`, `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl`
- 2026-02-06: `./.venv/bin/python -m pytest -q`
  - Result: PASS (`32 passed`)
  - Notes: Initial run failed due to missing local dependency `jsonschema`; fixed by running `./.venv/bin/pip install -r provetok/requirements.txt`.
  - Artifacts: `runs/EXP-007/pytest.log`, `runs/EXP-007/pip_install.log`
- 2026-02-06: `./.venv/bin/python -c "<EXP-008 path assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-008/snapshot_contract.log`
- 2026-02-06: `./.venv/bin/python -c "<EXP-009 attack_suite README assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-009/attack_suite_policy.log`
- 2026-02-06: `./.venv/bin/python -c "<EXP-010 demo codebook policy assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-010/demo_codebook_policy.log`

## ORAL-Loop-2026-02-06
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33`
  - Result: PASS
  - Artifacts: `runs/EXP-011/main_results.csv`, `runs/EXP-011/main_results.md`, `runs/EXP-011/per_run_metrics.json`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33`
  - Result: PASS
  - Artifacts: `runs/EXP-013/ablation_results.csv`, `runs/EXP-013/ablation_results.md`, `runs/EXP-013/manual_logging_ablation.json`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014`
  - Result: PASS (with explicit white-box gap)
  - Artifacts: `runs/EXP-014/cross_domain_summary.json`, `runs/EXP-014/cross_domain_summary.md`
- 2026-02-06: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015`
  - Result: PASS
  - Notes: dual-rater sheet populated (`n_rows=12`, `n_paired_items=6`), Cohen's kappa = `0.5714`.
  - Artifacts: `runs/EXP-015/human_eval_report.json`, `runs/EXP-015/human_eval_report.md`
- 2026-02-06: `./.venv/bin/python -m pytest -q`
  - Result: PASS (`32 passed`)
  - Artifacts: terminal log
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014`
  - Result: PASS (scope-aligned with ORAL-004 black-box trend requirement)
  - Artifacts: `runs/EXP-014/cross_domain_summary.json`, `runs/EXP-014/cross_domain_summary.md`

## ABC-Rerun-2026-02-06
- 2026-02-06: Re-executed baseline/dataset/gate chain (`EXP-001..010`) and oral chain (`EXP-011..015`) on current workspace.
  - Result: PASS
  - Notes: metrics and verdicts are unchanged from the previous validated run.
  - Key Artifacts:
    - `runs/EXP-011/main_results.md`
    - `runs/EXP-014/cross_domain_summary.json`
    - `runs/EXP-015/human_eval_report.json`
    - `runs/EXP-007/pytest.log` (`32 passed`)

## ORAL-vNext-Loop-2026-02-06
- 2026-02-06: `./.venv/bin/python -m pytest -q`
  - Result: PASS (`32 passed`)
  - Artifacts: terminal output (`32 passed in 1.90s`)
- 2026-02-06: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015`
  - Result: PASS
  - Notes: refreshed ORAL-005 with expanded sheet (`n_rows=72`, `n_paired_items=36`, `cohen_kappa=0.1280`)
  - Artifacts: `runs/EXP-015/human_eval_report.json`, `runs/EXP-015/human_eval_report.md`, `runs/EXP-015/run.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33`
  - Result: PASS
  - Notes: `white_box_improves_all_tracks=true`; utility retention A=`0.5788`, B=`0.8656`.
  - Artifacts: `runs/EXP-016/summary.json`, `runs/EXP-016/summary.md`, `runs/EXP-016/run.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017`
  - Result: PASS
  - Notes: main diff (`sealed_frontier - raw_frontier`) = `-0.0095`, CI=`[-0.1379, 0.1220]`, p=`0.6059`.
  - Artifacts: `runs/EXP-017/summary.json`, `runs/EXP-017/summary.md`, `runs/EXP-017/run.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128`
  - Result: PASS
  - Notes: generated black-box/white-box top1 curves for sealed + defended setups.
  - Artifacts: `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.md`, `runs/EXP-018/run.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7`
  - Result: PASS
  - Notes: `avg_utility_retention=0.9913`; `black_box_trend_holds_all_tracks=false` (Track B tie).
  - Artifacts: `runs/EXP-019/summary.json`, `runs/EXP-019/summary.md`, `runs/EXP-019/run.log`
- 2026-02-06: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020`
  - Result: PASS
  - Notes: scale-up reproducibility run (`n_paired_items=36`, `cohen_kappa=0.1280`).
  - Artifacts: `runs/EXP-020/human_eval_report.json`, `runs/EXP-020/human_eval_report.md`

## Missing-021
- 2026-02-10: `./.venv/bin/python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match`
  - Result: PASS
  - Notes: AST gate reports `0` `ast.Try` nodes across the repo.
  - Artifacts: `runs/EXP-005/gate_no_try.log`, `runs/EXP-005/exit_code.txt`

## Missing-022
- 2026-02-10: `./.venv/bin/python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval.json`
  - Result: PASS
  - Notes: CLI accepts `--baseline/--out` aliases and defaults `--sealed/--raw` to the included demo Track A.
  - Artifacts: `runs/EXP-001/eval.json`, `runs/EXP-001/cli_run_default.log`, `runs/EXP-001/cli_run_default_exit_code.txt`

## Missing-023
- 2026-02-10: `./.venv/bin/python -c "<EXP-008 snapshot assertions>"`
  - Result: PASS
  - Notes: Offline export includes OpenAlex placeholder snapshot files under `private/raw_snapshots/openalex/`.
  - Artifacts: `runs/EXP-008/snapshot_contract.log`, `runs/EXP-008/exit_code.txt`

## ABC-Loop-2026-02-10
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --agent random --output runs/EXP-001/eval_report_a.json`
  - Result: PASS
  - Artifacts: `runs/EXP-001/eval_report_a.json`, `runs/EXP-001/run_benchmark.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --agent random --output runs/EXP-002/eval_report_b.json`
  - Result: PASS
  - Artifacts: `runs/EXP-002/eval_report_b.json`, `runs/EXP-002/run_benchmark.log`
- 2026-02-10: `./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset_legacy.yaml --track both --out runs/exports`
  - Result: PASS
  - Artifacts: `runs/exports/0.2.0-legacy/public/dataset_manifest.json`, `runs/EXP-003/dataset_build_legacy.log`, `runs/EXP-003/check.log`
- 2026-02-10: `env -u LLM_API_KEY ./.venv/bin/python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track A --out runs/exports_online_fail`
  - Result: PASS (expected failure; exit code 1)
  - Artifacts: `runs/EXP-004/dataset_build_online.log`, `runs/EXP-004/exit_code.txt`
- 2026-02-10: `./.venv/bin/python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match`
  - Result: PASS
  - Artifacts: `runs/EXP-005/gate_no_try.log`, `runs/EXP-005/exit_code.txt`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both`
  - Result: PASS
  - Artifacts: `runs/EXP-006/check_manual.log`, `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl`
- 2026-02-10: `./.venv/bin/python -m pytest -q`
  - Result: PASS (`34 passed`)
  - Artifacts: `runs/EXP-007/pytest.log`
- 2026-02-10: `./.venv/bin/python -c "<EXP-008 snapshot assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-008/snapshot_contract.log`
- 2026-02-10: `./.venv/bin/python -c "<EXP-009 attack_suite README assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-009/attack_suite_policy.log`
- 2026-02-10: `./.venv/bin/python -c "<EXP-010 demo codebook policy assertions>"`
  - Result: PASS
  - Artifacts: `runs/EXP-010/demo_codebook_policy.log`

## ORAL-Loop-2026-02-10
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33`
  - Result: PASS
  - Notes: main vs raw: `utility_gap_raw_minus_main=0.0526`, `black_box_leakage_gap_raw_minus_main=0.9417` (see `runs/EXP-011/summary.json`).
  - Artifacts: `runs/EXP-011/main_results.csv`, `runs/EXP-011/per_run_metrics.json`, `runs/EXP-011/summary.json`, `runs/EXP-011/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_adaptive_attack.py ...` (Track A/B; output under `runs/EXP-011/attacks/`)
  - Result: PASS
  - Notes: attack reports include both `black_box` and `white_box` sections for A/B.
  - Artifacts: `runs/EXP-011/attacks/A_sealed.json`, `runs/EXP-011/attacks/B_sealed.json`, `runs/EXP-011/attacks/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33`
  - Result: PASS
  - Artifacts: `runs/EXP-013/ablation_results.csv`, `runs/EXP-013/manual_logging_ablation.json`, `runs/EXP-013/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014`
  - Result: PASS
  - Artifacts: `runs/EXP-014/cross_domain_summary.json`, `runs/EXP-014/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015`
  - Result: PASS
  - Notes: `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`.
  - Artifacts: `runs/EXP-015/human_eval_report.json`, `runs/EXP-015/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33`
  - Result: PASS
  - Notes: `white_box_improves_all_tracks=true`; `utility_retention_defended_vs_raw=0.533`.
  - Artifacts: `runs/EXP-016/summary.json`, `runs/EXP-016/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017`
  - Result: PASS
  - Artifacts: `runs/EXP-017/summary.json`, `runs/EXP-017/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128`
  - Result: PASS
  - Artifacts: `runs/EXP-018/budget_curves.json`, `runs/EXP-018/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7`
  - Result: PASS
  - Notes: `black_box_trend_holds_all_tracks=true`; `avg_utility_retention=0.9382`.
  - Artifacts: `runs/EXP-019/summary.json`, `runs/EXP-019/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020`
  - Result: PASS
  - Notes: `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`.
  - Artifacts: `runs/EXP-020/human_eval_report.json`, `runs/EXP-020/run.log`

## ABC-Plan-Commands-2026-02-10
- 2026-02-10: `source .venv/bin/activate && python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval_from_activated.json`
  - Result: PASS
  - Notes: This matches the CLAIM-001 “fresh checkout” command shape in `docs/plan.md` (using `python` from an activated venv).
  - Artifacts: `runs/EXP-001/eval_from_activated.json`, `runs/EXP-001/cli_run_default_activated.log`, `runs/EXP-001/cli_run_default_activated_exit_code.txt`
- 2026-02-10: `source .venv/bin/activate && python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match`
  - Result: PASS
  - Notes: Confirms CLAIM-004 gate is runnable via `python` from an activated venv.
  - Artifacts: `runs/EXP-005/gate_no_try_from_activated.log`, `runs/EXP-005/gate_no_try_from_activated_exit_code.txt`

## ABC-Closure-Check-2026-02-10
- 2026-02-10: Plan↔evidence coverage check (CLAIM/ORAL IDs must be mapped; no open Mohu/Experiment checkboxes)
  - Result: PASS
  - Artifacts: `runs/ABC-check/abc_check.log`, `runs/ABC-check/exit_code.txt`

## ORAL-vNext-Loop-2026-02-10
- 2026-02-10: `./.venv/bin/python provetok/scripts/build_oral_scale_dataset.py --in_internal_a runs/exports_s2_full/0.2.0/private/track_A_extended_records.internal.jsonl --in_internal_b runs/exports_s2_full/0.2.0/private/track_B_extended_records.internal.jsonl --out_dir runs/EXP-021/dataset --seal_seed 42 --numeric_bins 10 --write_l1only`
  - Result: PASS
  - Artifacts: `runs/EXP-021/dataset/dataset_manifest.json`, `runs/EXP-021/build_dataset.log`, `runs/EXP-021/exit_code.txt`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_main_table_vnext.py --dataset_dir runs/EXP-021/dataset --output_dir runs/EXP-022 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42`
  - Result: PASS
  - Notes: includes stronger baselines (`sealed_summary_frontier`, `sealed_redact_frontier`) and persists run meta.
  - Artifacts: `runs/EXP-022/main_results.csv`, `runs/EXP-022/summary.json`, `runs/EXP-022/attacks/`, `runs/EXP-022/run_meta.json`, `runs/EXP-022/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/run_oral_defense_knob_sweep_vnext.py --dataset_dir runs/EXP-021/dataset --output_dir runs/EXP-023 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-023/tradeoff_curve.json`, `runs/EXP-023/tradeoff_curve.png`, `runs/EXP-023/run_meta.json`, `runs/EXP-023/run.log`
- 2026-02-10: `./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-024 --threshold 0.5`
  - Result: PASS
  - Notes: report includes `krippendorff_alpha_nominal_binary` plus continuous-agreement diagnostics (Pearson/Spearman, near-threshold counts).
  - Artifacts: `runs/EXP-024/human_eval_report.json`, `runs/EXP-024/run.log`, `runs/EXP-024/exit_code.txt`

## Plan-Support-Rerun-2026-02-11
- 2026-02-11: Reran `EXP-001..020` (with `EXP-004` as expected-failure) to refresh evidence outputs.
  - Result: PASS
  - Artifacts: `runs/PLAN-rerun/check.log`

## ORAL-vNext-Scale-Extensions-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_ablations_vnext.py --dataset_dir runs/EXP-021/dataset --output_dir runs/EXP-025 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-025/ablation_results.csv`, `runs/EXP-025/manual_logging_ablation.json`, `runs/EXP-025/attacks/`, `runs/EXP-025/run_meta.json`, `runs/EXP-025/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-022/per_run_metrics.json --output_dir runs/EXP-026`
  - Result: PASS
  - Artifacts: `runs/EXP-026/cross_domain_summary.json`, `runs/EXP-026/cross_domain_summary.md`, `runs/EXP-026/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_whitebox_defense_vnext.py --dataset_dir runs/EXP-021/dataset --output_dir runs/EXP-027 --seeds 11 22 33 --attack_max_observed 200 --attack_seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-027/summary.json`, `runs/EXP-027/defended_A.jsonl`, `runs/EXP-027/defended_B.jsonl`, `runs/EXP-027/run_meta.json`, `runs/EXP-027/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-022/per_run_metrics.json --main_csv runs/EXP-022/main_results.csv --defense_summary runs/EXP-027/summary.json --output_dir runs/EXP-028`
  - Result: PASS
  - Artifacts: `runs/EXP-028/summary.json`, `runs/EXP-028/summary.md`, `runs/EXP-028/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_budget_attack_vnext.py --dataset_dir runs/EXP-021/dataset --defended_dir runs/EXP-027 --output_dir runs/EXP-029 --max_observed 200 --seed 42 --budgets 8 16 32 64 128`
  - Result: PASS
  - Artifacts: `runs/EXP-029/budget_curves.json`, `runs/EXP-029/budget_curves.md`, `runs/EXP-029/run_meta.json`, `runs/EXP-029/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_holdout_generalization_vnext.py --dataset_dir runs/EXP-021/dataset --output_dir runs/EXP-030 --seeds 11 22 33 --quantile 0.7 --attack_max_observed 200 --attack_seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-030/summary.json`, `runs/EXP-030/summary.md`, `runs/EXP-030/run_meta.json`, `runs/EXP-030/run.log`

## ORAL-vNext-Public-Scale-Bundle-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/export_oral_scale_public_bundle.py --dataset_dir runs/EXP-021/dataset --out_dir runs/EXP-031/public --overwrite`
  - Result: PASS
  - Notes: public bundle contains raw + sealed variants and explicitly excludes `*.codebook.json`.
  - Artifacts: `runs/EXP-031/public/public_dataset_manifest.json`, `runs/EXP-031/public/README.md`, `runs/EXP-031/run.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_oral_main_table_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-031/repro_main_table_smoke --seeds 11 --attack_max_observed 50 --attack_seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-031/repro_main_table_smoke/main_results.csv`, `runs/EXP-031/repro_main_table_smoke/summary.json`, `runs/EXP-031/run.log`

## ORAL-vNext-LLM-Attacker-Calibration-2026-02-11
- 2026-02-11: `set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_oral_llm_attacker_calibration.py --out_dir runs/EXP-032 --overwrite --n_samples 20 --top_k 3 --seed 42 --scale_dataset_dir runs/EXP-021/dataset`
  - Result: PASS
  - Notes: LLM-backed term recovery hit rates are low on both micro and scale (see `runs/EXP-032/summary.json`).
  - Artifacts: `runs/EXP-032/summary.json`, `runs/EXP-032/summary.md`, `runs/EXP-032/run_meta.json`, `runs/EXP-032/micro_A.json`

## ORAL-vNext-Recommended-Config-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/derive_recommended_release_config.py --curve_json runs/EXP-023/tradeoff_curve.json --out_dir runs/EXP-033 --overwrite`
  - Result: PASS
  - Notes: policy thresholds pick the knee point at `level=2`; `level=4` achieves black-box leakage=0 with larger utility loss.
  - Artifacts: `runs/EXP-033/recommended_config.json`, `runs/EXP-033/recommended_config.md`, `runs/EXP-033/run_meta.json`

## ORAL-vNext-Budget-Plot-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/plot_budget_curves.py --in_json runs/EXP-029/budget_curves.json --out_png runs/EXP-029/budget_curves.png`
  - Result: PASS
  - Artifacts: `runs/EXP-029/budget_curves.png`
- 2026-02-11: `./.venv/bin/python provetok/scripts/plot_budget_curves.py --in_json runs/EXP-018/budget_curves.json --out_png runs/EXP-018/budget_curves.png`
  - Result: PASS
  - Artifacts: `runs/EXP-018/budget_curves.png`

## ORAL-vNext-ArXiv-Closure-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_contamination_stat.py --input runs/EXP-022/per_run_metrics.json --output_dir runs/EXP-034`
  - Result: PASS
  - Artifacts: `runs/EXP-034/summary.json`, `runs/EXP-034/summary.md`, `runs/EXP-034/run_meta.json`, `runs/EXP-034/full_stderr.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_dynamic_time_window_eval.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-035 --seeds 11 22 33`
  - Result: PASS
  - Artifacts: `runs/EXP-035/summary.json`, `runs/EXP-035/summary.md`, `runs/EXP-035/run_meta.json`, `runs/EXP-035/full_stderr.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_contamination_tagging_dyepack.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-036 --max_negatives 300`
  - Result: PASS
  - Artifacts: `runs/EXP-036/summary.json`, `runs/EXP-036/summary.md`, `runs/EXP-036/run_meta.json`, `runs/EXP-036/full_stderr.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_extraction_attack_stress.py --dataset_dir runs/EXP-031/public --defended_dir runs/EXP-027 --output_dir runs/EXP-037 --budgets 32 64 128 256 --max_observed 200 --seed 42`
  - Result: PASS
  - Artifacts: `runs/EXP-037/summary.json`, `runs/EXP-037/summary.md`, `runs/EXP-037/run_meta.json`, `runs/EXP-037/full_stderr.log`
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_llm_judge_validation.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-038 --threshold 0.5`
  - Result: PASS
  - Artifacts: `runs/EXP-038/summary.json`, `runs/EXP-038/summary.md`, `runs/EXP-038/run_meta.json`, `runs/EXP-038/full_stderr.log`
- 2026-02-11: `./.venv/bin/python - <<'PY' ...` (A/B/C gate checks for open Missing/Ambiguous and Full status)
  - Result: PASS
  - Notes: open `Missing`=0, open `Ambiguous`=0, and all 38 EXP rows are `Smoke=[x], Full=[x]` in `docs/experiment.md`.

## ORAL-016-Validity-2026-02-11
- 2026-02-11: `./.venv/bin/python provetok/scripts/run_validity_invariance.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-039 --tracks A,B --agents random,copylast,dependency,frontier --seeds 11,22,33`
  - Result: PASS
  - Notes: raw↔sealed agent ordering is invariant (Spearman=1.0, Kendall=1.0); metadata-only/structure-only baselines degrade utility (see `runs/EXP-039/summary.json`).
  - Artifacts: `runs/EXP-039/summary.json`, `runs/EXP-039/summary.md`, `runs/EXP-039/run_meta.json`

## ABC-Orchestrator-Rerun-2026-02-11
- 2026-02-11: `./.venv/bin/python -m pytest -q`
  - Result: PASS (`34 passed`)
  - Artifacts: N/A
- 2026-02-11: `./.venv/bin/python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match > runs/EXP-005/gate_no_try_orchestrator_2026-02-11.log`
  - Result: PASS
  - Artifacts: `runs/EXP-005/gate_no_try_orchestrator_2026-02-11.log`

## ORAL-016-LLM-Validity-2026-02-11
- 2026-02-11: `set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_llm_validity_invariance.py --out_dir runs/EXP-040 --overwrite`
  - Result: PASS
  - Notes: micro raw≈sealed utility_mean (A 0.6455 vs 0.6187; B 0.6459 vs 0.6201); scale sealed ≥ raw; metadata_only/structure_only mechanism_class collapses (≤0.10 micro, 0.0 scale); usage `total_tokens=90452`; elapsed `~35.5 min`.
  - Artifacts: `runs/EXP-040/summary.json`, `runs/EXP-040/summary.md`, `runs/EXP-040/run_meta.json`, `runs/EXP-040/items.jsonl`
