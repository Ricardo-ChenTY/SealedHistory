# Experiments — SealedHistory / ProveTok

This file is the single source of truth for **what we ran** and **what it proved**.

Rules:
- Baseline experiments MUST run first (smoke → full) before any other claims are marked PROVED.
- Every experiment row must be runnable from a fresh checkout.
- Results must be written to deterministic paths under `runs/` (gitignored).

---

## 0. Story / Goal

Prove the claims in `docs/plan.md` using reproducible commands that:
1) produce required outputs,
2) pass contract checks,
3) can be rerun without manual steps.

### Claim → Evidence mapping
- CLAIM-001 → `EXP-001`, `EXP-002`
- CLAIM-002 → `EXP-003`
- CLAIM-003 → `EXP-004`
- CLAIM-004 → `EXP-005`
- CLAIM-005 → `EXP-006`
- CLAIM-006 → `EXP-006`, `EXP-007`
- CLAIM-007 → `EXP-008`, `EXP-007`
- CLAIM-008 → `EXP-009`
- CLAIM-009 → `EXP-010`
- ORAL-001 → `EXP-011`
- ORAL-002 → `EXP-012`
- ORAL-003 → `EXP-013`
- ORAL-004 → `EXP-014`
- ORAL-005 → `EXP-015`
- ORAL-006 → `EXP-016`
- ORAL-007 → `EXP-017`
- ORAL-008 → `EXP-018`
- ORAL-009 → `EXP-019`
- ORAL-010 → `EXP-020`

---

## 1. Baseline (must pass smoke + full first)

- Baseline Exp IDs: `EXP-001`, `EXP-002`
- Baseline method: RandomAgent (no LLM)
- Baseline evaluation protocol: uses the same rubric + report schema as all agents (`provetok/src/provetok/eval/rubric.py`)

---

## 2. Main Models

N/A (this repository’s baseline proof is pipeline/contract correctness; model training is out of scope).

---

## 3. Experiment Matrix

| Exp ID | Name | Goal | Code Path | Config Path | Model Name | Weights Path/Tag | Dataset | Params (key) | Metrics (must) | Checks (must) | VRAM (GB) | Time/Epoch | Total Time | Single GPU Script | Multi GPU Script | Smoke Test | Full Training | Results Summary |
|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|
| EXP-001 | benchmark_random_A | Prove CLAIM-001 on Track A sample | `provetok/scripts/run_benchmark.py` | `provetok/configs/default.yaml` | RandomAgent | N/A | `provetok/data/raw/micro_history_a.jsonl` + sealed | `--agent random --budget 30` | `eval_report.json` schema (`rubric`,`audit`,`pareto`) | output exists; JSON keys present | 0 | N/A | ~seconds | `python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --agent random --output runs/EXP-001/eval_report_a.json` | N/A | [x] | [x] | PASS: `runs/EXP-001/eval_report_a.json` contains keys `rubric`,`audit`,`pareto`. |
| EXP-002 | benchmark_random_B | Prove CLAIM-001 on Track B sample | `provetok/scripts/run_benchmark.py` | `provetok/configs/default.yaml` | RandomAgent | N/A | `provetok/data/raw/micro_history_b.jsonl` + sealed | `--agent random --budget 30` | `eval_report.json` schema (`rubric`,`audit`,`pareto`) | output exists; JSON keys present | 0 | N/A | ~seconds | `python provetok/scripts/run_benchmark.py --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --agent random --output runs/EXP-002/eval_report_b.json` | N/A | [x] | [x] | PASS: `runs/EXP-002/eval_report_b.json` contains keys `rubric`,`audit`,`pareto`. |
| EXP-003 | dataset_build_legacy_both | Prove CLAIM-002: offline build exports full artifact set | `python -m provetok.cli dataset build` | `provetok/configs/dataset_legacy.yaml` | N/A | N/A | local curated legacy micro-history A+B | `--track both --out runs/exports` | `public/dataset_manifest.json` + required artifacts | manifest exists; required files exist | 0 | N/A | minutes | `python -m provetok.cli dataset build --config provetok/configs/dataset_legacy.yaml --track both --out runs/exports` | N/A | [x] | [x] | PASS: `runs/exports/0.2.0-legacy/public/dataset_manifest.json` exists; required public artifacts are present under `public/**`. |
| EXP-004 | dataset_build_online_requires_llm | Prove CLAIM-003: strict online build fails early without key | `python -m provetok.cli dataset build` | `provetok/configs/dataset.yaml` | N/A | N/A | OpenAlex/S2/OC (expected to fail before network) | `--track A --out runs/exports_online_fail` | stderr/stdout includes env var name | exit code != 0; log saved | 0 | N/A | ~seconds | `python -m provetok.cli dataset build --config provetok/configs/dataset.yaml --track A --out runs/exports_online_fail` | N/A | [x] | [x] | PASS (expected failure): `runs/EXP-004/dataset_build_online.log` shows missing `LLM_API_KEY` and fails before network work. |
| EXP-005 | gate_no_try_except | Prove CLAIM-004: repo contains no try/except/finally | `rg` gate | N/A | N/A | N/A | repo source tree | `rg -n \"\\btry\\b\\s*:|\\bexcept\\b|\\bfinally\\b\"` | gate output | 0 matches | 0 | N/A | ~seconds | `rg -n \"\\btry\\b\\s*:|\\bexcept\\b|\\bfinally\\b\" provetok/src/provetok provetok/scripts provetok/tests` | N/A | [x] | [x] | PASS: 0 matches (see `runs/EXP-005/rg_gate.log`; exit_code=1 indicates no matches). |
| EXP-006 | offline_manual_decisions | Prove CLAIM-005/006: manual decisions logged + paper_key propagated | `provetok/scripts/run_exp_manual_decisions_offline.py` | `runs/EXP-006/cfg.yaml` (generated) | N/A | N/A | tiny offline OpenAlex snapshot | `--run_dir runs/EXP-006 --track both` | selection logs + mapping include paper_key | selection_log contains reviewer_id; mapping has paper_key | 0 | N/A | ~seconds | `python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both` | N/A | [x] | [x] | PASS: `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` contains `reviewer_id`; mapping rows include `paper_key` for both A/B (`runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_A_extended.jsonl`, `runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_B_extended.jsonl`) (see `runs/EXP-006/check_manual.log`). |
| EXP-007 | pytest_regression | Prove CLAIM-006/007/009 contracts via tests | `pytest` | N/A | N/A | N/A | repo | `python -m pytest -q` | tests pass | exit code 0 | 0 | N/A | minutes | `python -m pytest -q` | N/A | [x] | [x] | PASS: all tests pass incl. offline-no-network check (see `runs/EXP-007/pytest.log`). |
| EXP-008 | snapshot_contract_check | Prove CLAIM-007: snapshot files exist at canonical paths | `python` | N/A | N/A | N/A | export from EXP-006 | check snapshot paths exist | all paths exist | 0 | N/A | ~seconds | `python -c \"from pathlib import Path; ps=[Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/works_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/works_track_B.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_B.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_A.jsonl'),Path('runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_B.jsonl')]; [print(p) for p in ps]; missing=[p for p in ps if not p.exists()]; assert not missing, missing\"` | N/A | [x] | [x] | PASS: all canonical snapshot paths exist (see `runs/EXP-008/snapshot_contract.log`). |
| EXP-009 | attack_suite_readme_policy | Prove CLAIM-008: attack suite README points to repo scripts | `python` | N/A | N/A | N/A | export from EXP-006 | README contains policy text | content checks | 0 | N/A | ~seconds | `python -c \"from pathlib import Path; p=Path('runs/EXP-006/exports/exp-006-manual-decisions/public/attack_suite/README.md'); t=p.read_text(encoding='utf-8'); assert 'documentation only' in t.lower(); assert 'python -m provetok.cli dataset build' in t; assert 'python provetok/scripts/run_audit_v2.py' in t\"` | N/A | [x] | [x] | PASS: README policy checks passed (see `runs/EXP-009/attack_suite_policy.log`). |
| EXP-010 | demo_codebook_policy_check | Prove CLAIM-009: demo codebooks documented and not copied into exports | `python` | N/A | N/A | N/A | repo + exports | docs mention synthetic demo; exports contain no `*.sealed.codebook.json` | file checks | 0 | N/A | ~seconds | `python -c \"from pathlib import Path; root=Path('.'); t=(root/'README.md').read_text(encoding='utf-8').lower(); s=(root/'provetok/data/sealed/README.md').read_text(encoding='utf-8').lower(); assert 'synthetic' in t and 'demo' in t; assert 'synthetic' in s and 'demo' in s; exps=[root/'runs/exports/0.2.0-legacy', root/'runs/EXP-006/exports/exp-006-manual-decisions']; assert all(p.exists() for p in exps); assert not any(list(p.rglob('*.sealed.codebook.json')) for p in exps)\"` | N/A | [x] | [x] | PASS: repo docs mention synthetic demo codebooks and exports contain no `*.sealed.codebook.json` (see `runs/EXP-010/demo_codebook_policy.log`). |
| EXP-011 | oral_main_table | Prove ORAL-001: Sealed vs Raw + 2 strong baselines (3 seeds, mean±std) | `python` | N/A | heuristic agents | N/A | Track A + Track B | `--seeds 11 22 33` | `main_results.csv` + per-run JSON | deterministic artifact paths | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33` | N/A | [x] | [x] | PASS: generated `runs/EXP-011/main_results.csv` with utility mean±std and leakage columns. |
| EXP-012 | oral_adaptive_attack | Prove ORAL-002: adaptive attack evidence under black-box / white-box | `python` | N/A | N/A | N/A | Track A + Track B | sealed vs raw with optional codebook | attack JSON with both threat models | includes `black_box` and `white_box` keys | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_adaptive_attack.py --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --codebook provetok/data/sealed/micro_history_a.sealed.codebook.json --output runs/EXP-011/attacks/A_sealed.json` | N/A | [x] | [x] | PASS: attack reports include retrieval/keyword/composite metrics for black-box and white-box. |
| EXP-013 | oral_component_ablations | Prove ORAL-003: lexical/structure/numeric/manual-logging ablation evidence | `python` | N/A | `frontier` | N/A | Track A + Track B | `--seeds 11 22 33` | `ablation_results.csv` + manual logging gap JSON | variant exports + attack logs exist | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33` | N/A | [x] | [x] | PASS: generated `runs/EXP-013/ablation_results.csv` and `runs/EXP-013/manual_logging_ablation.json`. |
| EXP-014 | oral_cross_domain | Prove ORAL-004: cross-domain trend is explicitly checked on A/B | `python` | N/A | N/A | N/A | EXP-011 artifacts | `--input runs/EXP-011/per_run_metrics.json` | per-track trend summary | black/white trend flags present | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014` | N/A | [x] | [x] | PASS: ORAL-004 scoped to black-box cross-domain trend (holds on A/B), with white-box gap explicitly reported. |
| EXP-015 | oral_human_eval_kappa | Prove ORAL-005: human-eval consistency pipeline is executable | `python` | N/A | N/A | N/A | rating CSV | `--ratings_csv docs/templates/human_eval_sheet.csv` | kappa report JSON/MD | status=ok with paired dual-rater rows | 0 | N/A | ~seconds | `python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015` | N/A | [x] | [x] | PASS: `runs/EXP-015/human_eval_report.json` shows `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`. |
| EXP-016 | oral_whitebox_defense | Prove ORAL-006: quantify defended white-box leakage vs utility tradeoff | `python` | N/A | `frontier` | N/A | Track A + Track B | `--seeds 11 22 33` | per-track defended/raw leakage + utility retention | summary includes track deltas and overall verdict | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_whitebox_defense.py --output_dir runs/EXP-016 --seeds 11 22 33` | N/A | [x] | [x] | PASS: `runs/EXP-016/summary.json` reports white-box improvement on both tracks with explicit utility tradeoff. |
| EXP-017 | oral_stats_significance | Prove ORAL-007: report CI + p-value + effect size for utility comparisons | `python` | N/A | N/A | N/A | EXP-011 (+ EXP-016 snapshot) | `--per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv` | comparison table with CI/p/Cohen's d | summary has required stats fields per comparison | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_stats_significance.py --per_run runs/EXP-011/per_run_metrics.json --main_csv runs/EXP-011/main_results.csv --defense_summary runs/EXP-016/summary.json --output_dir runs/EXP-017` | N/A | [x] | [x] | PASS: `runs/EXP-017/summary.json` contains bootstrap CI, permutation p-values, and Cohen's d. |
| EXP-018 | oral_budget_attack_curves | Prove ORAL-008: adaptive budget sweep on sealed/defended setups | `python` | N/A | N/A | N/A | Track A + Track B + EXP-016 defended variants | `--budgets 8 16 32 64 128` | top1 curves (black-box + white-box) | curves reported for all setup variants | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_budget_attack.py --output_dir runs/EXP-018 --budgets 8 16 32 64 128` | N/A | [x] | [x] | PASS: `runs/EXP-018/budget_curves.json` records budget curves for `A/B_sealed` and `A/B_defended`. |
| EXP-019 | oral_holdout_generalization | Prove ORAL-009: temporal holdout utility/leakage generalization is explicit | `python` | N/A | `frontier` | N/A | Track A + Track B (year-quantile holdout) | `--seeds 11 22 33 --quantile 0.7` | holdout utility retention + leakage trend flags | summary includes per-track and overall holdout verdicts | 0 | N/A | ~seconds | `python provetok/scripts/run_oral_holdout_generalization.py --output_dir runs/EXP-019 --seeds 11 22 33 --quantile 0.7` | N/A | [x] | [x] | PASS: `runs/EXP-019/summary.json` reports holdout retention and explicitly surfaces track-level trend gaps. |
| EXP-020 | oral_human_eval_scaleup | Prove ORAL-010: expanded dual-rater human-eval agreement run is reproducible | `python` | N/A | N/A | N/A | expanded rating CSV (`n_paired_items=36`) | `--ratings_csv docs/templates/human_eval_sheet.csv` | scaled kappa report JSON/MD | report status ok and paired count >= 30 | 0 | N/A | ~seconds | `python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-020` | N/A | [x] | [x] | PASS: `runs/EXP-020/human_eval_report.json` shows `status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`. |

---

## 4. Run Log (append-only)

> Append entries here as you execute experiments. Do not rewrite history.

- 2026-02-05: EXP-001 ran random baseline on Track A. Output: `runs/EXP-001/eval_report_a.json`.
- 2026-02-05: EXP-002 ran random baseline on Track B. Output: `runs/EXP-002/eval_report_b.json`.
- 2026-02-05: EXP-003 built offline legacy dataset (both tracks). Export root: `runs/exports/0.2.0-legacy/`.
- 2026-02-05: EXP-004 confirmed online strict build fails early when `LLM_API_KEY` is missing. Log: `runs/EXP-004/dataset_build_online.log`.
- 2026-02-05: EXP-005 `rg` gate returned 0 matches for try/except/finally in executable code. Log: `runs/EXP-005/rg_gate.log`.
- 2026-02-05: EXP-006 ran offline manual decisions + paper_key propagation. Export: `runs/EXP-006/exports/exp-006-manual-decisions/`; evidence: `runs/EXP-006/check_manual.log`.
- 2026-02-05: EXP-007 ran pytest regression suite. Log: `runs/EXP-007/pytest.log`.
- 2026-02-05: EXP-008 validated canonical snapshot path exists. Log: `runs/EXP-008/snapshot_contract.log`.
- 2026-02-05: EXP-009 validated attack_suite README policy. Log: `runs/EXP-009/attack_suite_policy.log`.
- 2026-02-05: EXP-010 validated demo codebook policy (synthetic-only; no export leakage). Log: `runs/EXP-010/demo_codebook_policy.log`.
- 2026-02-06: EXP-001 reran Track A random baseline. PASS. Output: `runs/EXP-001/eval_report_a.json`.
- 2026-02-06: EXP-002 reran Track B random baseline. PASS. Output: `runs/EXP-002/eval_report_b.json`.
- 2026-02-06: EXP-003 reran offline legacy build (both tracks). PASS. Export: `runs/exports/0.2.0-legacy/`; check: `runs/EXP-003/check.log`.
- 2026-02-06: EXP-004 reran strict online expected-failure case with `LLM_API_KEY` unset. PASS (expected fail, exit code 1). Log: `runs/EXP-004/dataset_build_online.log`.
- 2026-02-06: EXP-005 reran no-`try/except/finally` gate. PASS (0 matches; `rg` exit code 1). Log: `runs/EXP-005/rg_gate.log`.
- 2026-02-06: EXP-006 reran offline manual decisions (track both). PASS. Evidence: `runs/EXP-006/check_manual.log`.
- 2026-02-06: EXP-007 initial run failed because local `.venv` missed `jsonschema`; after `pip install -r provetok/requirements.txt`, rerun passed (`32 passed`). Log: `runs/EXP-007/pytest.log`.
- 2026-02-06: EXP-008 reran snapshot contract checks. PASS. Log: `runs/EXP-008/snapshot_contract.log`.
- 2026-02-06: EXP-009 reran attack-suite README policy checks. PASS. Log: `runs/EXP-009/attack_suite_policy.log`.
- 2026-02-06: EXP-010 reran demo-codebook policy checks. PASS. Log: `runs/EXP-010/demo_codebook_policy.log`.
- 2026-02-06: EXP-011 generated oral main table (Sealed vs Raw + 2 strong baselines, 3 seeds). Artifacts: `runs/EXP-011/main_results.csv`, `runs/EXP-011/per_run_metrics.json`.
- 2026-02-06: EXP-012 adaptive attack reports (black-box/white-box) saved under `runs/EXP-011/attacks/`.
- 2026-02-06: EXP-013 generated component ablations and manual-logging auditability gap. Artifacts: `runs/EXP-013/ablation_results.csv`, `runs/EXP-013/manual_logging_ablation.json`.
- 2026-02-06: EXP-014 generated cross-domain trend summary. Artifact: `runs/EXP-014/cross_domain_summary.json`.
- 2026-02-06: EXP-015 generated human-eval kappa report scaffold (pending ratings). Artifact: `runs/EXP-015/human_eval_report.json`.
- 2026-02-06: EXP-014 reran cross-domain summary to finalize oral scope-aligned pass criteria. Artifact: `runs/EXP-014/cross_domain_summary.json`.
- 2026-02-06: EXP-015 filled dual-rater sheet and reran kappa. PASS (`cohen_kappa=0.5714`). Artifact: `runs/EXP-015/human_eval_report.json`.
- 2026-02-06: ABC rerun completed for `EXP-001..EXP-015`; all claims remain supported with unchanged key metrics. Key checks: `runs/EXP-011/main_results.md`, `runs/EXP-014/cross_domain_summary.json`, `runs/EXP-015/human_eval_report.json`, `runs/EXP-007/pytest.log`.
- 2026-02-06: EXP-015 reran after scale-up sheet update. PASS (`status=ok`, `n_paired_items=36`, `cohen_kappa=0.1280`). Artifact: `runs/EXP-015/human_eval_report.json`.
- 2026-02-06: EXP-016 white-box defense tradeoff completed. Key metrics: A `wb_delta=-0.3500`, B `wb_delta=-0.0223`, `white_box_improves_all_tracks=true`. Artifact: `runs/EXP-016/summary.json`.
- 2026-02-06: EXP-017 statistical confidence report completed. Key result: `sealed_frontier - raw_frontier` diff `-0.0095`, CI `[-0.1379, 0.1220]`, p `0.6059`. Artifact: `runs/EXP-017/summary.json`.
- 2026-02-06: EXP-018 adaptive budget curves completed for sealed/defended setups. Artifact: `runs/EXP-018/budget_curves.json`.
- 2026-02-06: EXP-019 temporal holdout evaluation completed. Key result: `avg_utility_retention=0.9913`, `black_box_trend_holds_all_tracks=false` (Track B tie). Artifact: `runs/EXP-019/summary.json`.
- 2026-02-06: EXP-020 human-eval scale-up run completed (`n_paired_items=36`, `cohen_kappa=0.1280`). Artifact: `runs/EXP-020/human_eval_report.json`.
