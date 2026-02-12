# Repo Inventory — SealedHistory / ProveTok (2026-02-11)

## Tree

- `README.md`: quickstart + repo rules (no `try/except/finally`)
- `plan.md`: dataset collection/build proposal (high-level)
- `docs/`: doc-driven state machine + contracts
- `docs/neurips_strengthening.md`: NeurIPS rebuttal-style “weaknesses → fixes” method/experiment design notes
- `provetok/`: Python package (configs/scripts/tests/src)
- `S17_pdf-download/`: Semantic Scholar PDF downloader helper
- `runs/`: generated artifacts/logs (gitignored)
- `.env`: local env (do not commit secrets)
- `.venv/`: local virtualenv (optional)

## Entry Points

- Unified CLI: `provetok/src/provetok/cli.py`
  - Benchmark: `python -m provetok.cli run ...`
  - Dataset: `python -m provetok.cli dataset build ...`
- Benchmark script (no LLM): `provetok/scripts/run_benchmark.py`
- Dataset build helper: `provetok/scripts/build_sealed_dataset.py`
- Dataset collection helper (S2-first): `provetok/scripts/collect_data.py`
- Leakage audit (v2): `provetok/scripts/run_audit_v2.py`
- Repo gate (no try/except/finally): `provetok/scripts/gate_no_try.py`
- Offline manual-decision experiment: `provetok/scripts/run_exp_manual_decisions_offline.py`
- Oral evidence pack:
  - main table: `provetok/scripts/run_oral_main_table.py`
  - adaptive attacks: `provetok/scripts/run_oral_adaptive_attack.py`
  - ablations: `provetok/scripts/run_oral_ablations.py`
  - cross-domain summary: `provetok/scripts/run_oral_cross_domain.py`
  - significance/CI: `provetok/scripts/run_oral_stats_significance.py`
  - budget curves: `provetok/scripts/run_oral_budget_attack.py`
  - holdout generalization: `provetok/scripts/run_oral_holdout_generalization.py`
  - human-eval kappa: `provetok/scripts/compute_human_eval_kappa.py`
- Oral vNext (scale-up pack):
  - scale dataset builder: `provetok/scripts/build_oral_scale_dataset.py`
  - scale main table: `provetok/scripts/run_oral_main_table_vnext.py`
  - defense knob sweep: `provetok/scripts/run_oral_defense_knob_sweep_vnext.py`
  - scalable attack helper: `provetok/scripts/run_oral_adaptive_attack_vnext.py`
  - scale ablations: `provetok/scripts/run_oral_ablations_vnext.py`
  - scale white-box defense: `provetok/scripts/run_oral_whitebox_defense_vnext.py`
  - scale budget curves: `provetok/scripts/run_oral_budget_attack_vnext.py`
  - scale holdout: `provetok/scripts/run_oral_holdout_generalization_vnext.py`
- Validity / invariance diagnostic: `provetok/scripts/run_validity_invariance.py` (EXP-039)

## Core Modules

- `provetok/src/provetok/dataset/`: selection, fulltext policy, record building, QA, manifest, sealed worlds, attack suite
- `provetok/src/provetok/sdg/`: sealer + codebook (public sealed text vs private mappings)
- `provetok/src/provetok/sources/`: S2/OpenAlex/OpenCitations/arXiv clients + snapshot/provenance
- `provetok/src/provetok/eval/`: rubric + report schema + visualization
- `provetok/src/provetok/audit/`: leakage attacks and audit harness
- `provetok/src/provetok/utils/`: config loader + LLM client wrapper

## Config & Data

- Configs (YAML):
  - Benchmark defaults: `provetok/configs/default.yaml`
  - Dataset online: `provetok/configs/dataset.yaml`
  - Dataset legacy/offline: `provetok/configs/dataset_legacy.yaml`
  - SDG/sealing knobs: `provetok/configs/sdg.yaml`
- Included demo data (for offline smoke tests):
  - raw: `provetok/data/raw/*.jsonl`
  - sealed: `provetok/data/sealed/*.sealed.jsonl`
  - demo codebooks: `provetok/data/sealed/*.sealed.codebook.json` (synthetic only)
- Environment variables (expected by strict/online flows):
  - `LLM_API_KEY` (or config-specified env var name; see `docs/plan.md` preflight order)

## How To Run

Install:
```bash
python -m venv .venv
./.venv/bin/python -m pip install -r provetok/requirements.txt
```

Tests:
```bash
./.venv/bin/python -m pytest -q
```

Benchmark smoke (no LLM):
```bash
./.venv/bin/python provetok/scripts/run_benchmark.py \
  --sealed provetok/data/sealed/micro_history_a.sealed.jsonl \
  --raw provetok/data/raw/micro_history_a.jsonl \
  --agent random \
  --output runs/EXP-001/eval_report_a.json
```

Dataset build (offline legacy):
```bash
./.venv/bin/python -m provetok.cli dataset build \
  --config provetok/configs/dataset_legacy.yaml \
  --track both \
  --out runs/exports
```

Dataset build (online strict; requires API/network/LLM when configured):
```bash
./.venv/bin/python -m provetok.cli dataset build \
  --config provetok/configs/dataset.yaml \
  --track both \
  --out runs/exports
```

## Risks / Unknowns

- Online dataset pipeline depends on external APIs and their licenses; treat redistribution conservatively (keep raw snapshots/private mappings private by default).
- `S17_pdf-download/` is a separate helper with its own `requirements.txt`; integrate carefully if used in automated pipelines.
- The repo enforces a “no `try/except/finally` in executable code” gate; any new scripts must follow the rule.
