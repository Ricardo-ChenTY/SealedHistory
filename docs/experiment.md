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
