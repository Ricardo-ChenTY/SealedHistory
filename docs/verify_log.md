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
