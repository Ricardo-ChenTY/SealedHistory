# Mohu

## Missing
- [x] Missing-021: Add AST-based no-try gate script (`gate_no_try`) and use it for EXP-005
  - Location: `provetok/scripts/gate_no_try.py`, `docs/experiment.md` (EXP-005), `docs/verify_log.md`, `docs/claim_evidence.md`
  - Acceptance:
    - `python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match` exits `0` and reports `0` `ast.Try` nodes.
    - `docs/experiment.md` EXP-005 is updated to use the AST gate command (not `rg`).
  - Evidence:
    - `docs/plan.md` (CLAIM-004) specifies an AST-based gate command: `python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match`.
    - Before this change, the repo proved CLAIM-004 via `rg` (see `docs/experiment.md` EXP-005 and `docs/verify_log.md`) and had no AST gate script.
  - Implementation:
    - Added AST gate script: `provetok/scripts/gate_no_try.py` (walks Python files, counts `ast.Try`, prints file:line spans).
    - Updated EXP-005 command in `docs/experiment.md` to use `gate_no_try.py`.
  - Next:
    - `python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match > runs/EXP-005/gate_no_try.log`
  - Verified: 2026-02-10 via `./.venv/bin/python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match` (PASS)
  - Notes:

- [x] Missing-022: Make CLAIM-001 “fresh checkout” benchmark command executable as written
  - Location: `provetok/src/provetok/cli.py` (`run` subcommand)
  - Acceptance:
    - From repo root, this command runs without requiring `--sealed/--raw` and writes a valid eval report:
      - `python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval.json`
    - Output JSON includes top-level keys `rubric`, `audit`, `pareto`.
  - Evidence:
    - `docs/plan.md` (CLAIM-001) includes this exact command sequence; before this change the CLI required `--sealed`/`--raw` and used `--agent`/`--output` only.
  - Implementation:
    - Updated CLI `run` to accept `--baseline` as an alias of `--agent`, and `--out` as an alias of `--output` (`provetok/src/provetok/cli.py`).
    - Made `--sealed/--raw` optional; when omitted, `provetok run` defaults to the included demo Track A (`provetok/data/{sealed,raw}/micro_history_a*`).
    - Restored demo micro-history fixtures (raw + sealed + synthetic codebooks) under `provetok/data/{raw,sealed}/` to make the fresh-checkout smoke runnable.
  - Next:
    - `./.venv/bin/python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval.json`
  - Verified: 2026-02-10 via `./.venv/bin/python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval.json` (PASS)
  - Notes:

- [x] Missing-023: Restore CLAIM-007 snapshot contract for OpenAlex placeholder files (offline rebuild compatibility)
  - Location: `provetok/src/provetok/dataset/pipeline.py`, `docs/experiment.md` (EXP-008)
  - Acceptance:
    - Offline exports include these paths (may be empty) for both tracks:
      - `private/raw_snapshots/openalex/works_track_{A,B}.jsonl`
      - `private/raw_snapshots/openalex/requests_track_{A,B}.jsonl`
    - `EXP-008` snapshot contract check passes on the offline manual-decisions export (`runs/EXP-006/...`).
  - Evidence:
    - `docs/plan.md` (CLAIM-007) specifies OpenAlex `works_track_{A,B}.jsonl` for legacy offline compatibility.
    - Before this change, rerunning EXP-008 failed because `runs/EXP-006/.../private/raw_snapshots/openalex/*` was missing (see `runs/EXP-008/snapshot_contract.log`).
  - Implementation:
    - `provetok/src/provetok/dataset/pipeline.py`: always materialize `private/raw_snapshots/openalex/{works,requests}_track_{A,B}.jsonl` as empty placeholder files during online-pipeline runs (incl. offline mode).
  - Next:
    - `./.venv/bin/python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both`
    - `./.venv/bin/python -c \"<EXP-008 snapshot assertions>\"`
  - Verified: 2026-02-10 via `./.venv/bin/python -c \"<EXP-008 snapshot assertions>\"` (PASS)
  - Notes:

- [x] Missing-024: Export a public-safe scale bundle (no codebooks, no internal paths) for reproducibility
  - Location: `provetok/scripts/export_oral_scale_public_bundle.py`, `docs/reproducibility_statement.md`, `docs/oral_story.md`, `docs/experiment.md`
  - Acceptance:
    - `python provetok/scripts/export_oral_scale_public_bundle.py --dataset_dir runs/EXP-021/dataset --out_dir runs/EXP-031/public --overwrite` succeeds.
    - `runs/EXP-031/public/` contains no `*.codebook.json`.
    - `runs/EXP-031/public/public_dataset_manifest.json` lists sha256/bytes/n_records for each exported JSONL and does not include internal input paths.
    - A smoke rerun on the bundle works: `python provetok/scripts/run_oral_main_table_vnext.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-031/repro_main_table_smoke --seeds 11 --attack_max_observed 50 --attack_seed 42`.
  - Implementation:
    - Added exporter script and bundle manifest/README generation (explicitly forbids codebooks): `provetok/scripts/export_oral_scale_public_bundle.py`.
    - Updated reproducibility docs to use the public bundle by default: `docs/reproducibility_statement.md`, `docs/oral_story.md`, `docs/plan.md`.
  - Verified: 2026-02-11 via `./.venv/bin/python provetok/scripts/export_oral_scale_public_bundle.py --dataset_dir runs/EXP-021/dataset --out_dir runs/EXP-031/public --overwrite` (PASS)
  - Evidence:
    - `runs/EXP-031/public/public_dataset_manifest.json`
    - `runs/EXP-031/repro_main_table_smoke/main_results.csv`

- [x] Missing-025: Add LLM-backed attacker calibration to validate heuristic leakage proxies
  - Location: `provetok/scripts/run_oral_llm_attacker_calibration.py`, `docs/oral_checklist.md`, `docs/oral_qa.md`
  - Acceptance:
    - Running with API key settings produces a summary report:
      - `set -a && source .env && set +a && python provetok/scripts/run_oral_llm_attacker_calibration.py --out_dir runs/EXP-032 --overwrite --n_samples 20 --top_k 3 --seed 42 --scale_dataset_dir runs/EXP-021/dataset`
    - `runs/EXP-032/summary.json` records hit@1/hit@3 and includes `run_meta.json` with model+endpoint (no secrets).
  - Implementation:
    - Added attacker calibration script: `provetok/scripts/run_oral_llm_attacker_calibration.py`.
    - Fixed JSON-list parsing in LLM attack helpers so term-recovery evaluation is meaningful:
      - `provetok/src/provetok/audit/attacks.py`
      - `provetok/src/provetok/dataset/audit_v2.py`
    - Updated oral docs to cite the calibration artifact: `docs/oral_story.md`, `docs/oral_checklist.md`, `docs/oral_qa.md`.
  - Verified: 2026-02-11 via `set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_oral_llm_attacker_calibration.py --out_dir runs/EXP-032 --overwrite --n_samples 20 --top_k 3 --seed 42 --scale_dataset_dir runs/EXP-021/dataset` (PASS)
  - Evidence:
    - `runs/EXP-032/summary.json`
    - `runs/EXP-032/run_meta.json`

- [x] Missing-026: Make the recommended configuration (knee / shipping decision) explicit and machine-derived
  - Location: `provetok/scripts/derive_recommended_release_config.py`, `docs/paper_experiment_map.md`, `docs/oral_story.md`, `plan.md`
  - Acceptance:
    - `python provetok/scripts/derive_recommended_release_config.py --curve_json runs/EXP-023/tradeoff_curve.json --out_dir runs/EXP-033 --overwrite` succeeds and writes `runs/EXP-033/recommended_config.json`.
    - Paper/oral text explicitly states the recommended level and references the artifact.
  - Implementation:
    - Added deterministic derivation script: `provetok/scripts/derive_recommended_release_config.py`.
    - Added artifact-backed recommendation evidence: `runs/EXP-033/recommended_config.json`, referenced from `plan.md` and oral docs.
  - Verified: 2026-02-11 via `./.venv/bin/python provetok/scripts/derive_recommended_release_config.py --curve_json runs/EXP-023/tradeoff_curve.json --out_dir runs/EXP-033 --overwrite` (PASS)

- [x] Missing-027: Make budget attacks “failure-first” slide/paper-ready (plots)
  - Location: `provetok/scripts/plot_budget_curves.py`, `docs/oral_story.md`, `plan.md`
  - Acceptance:
    - `python provetok/scripts/plot_budget_curves.py --in_json runs/EXP-029/budget_curves.json --out_png runs/EXP-029/budget_curves.png` succeeds.
    - `python provetok/scripts/plot_budget_curves.py --in_json runs/EXP-018/budget_curves.json --out_png runs/EXP-018/budget_curves.png` succeeds.
    - Oral/paper narrative cites the plot path for failure-first.
  - Implementation:
    - Added plotting script and generated slide-ready PNGs for micro+scale budget curves.
    - Updated narrative references to use `*.png` for failure-first.
  - Verified: 2026-02-11 via `./.venv/bin/python provetok/scripts/plot_budget_curves.py --in_json runs/EXP-029/budget_curves.json --out_png runs/EXP-029/budget_curves.png` (PASS)
  - Evidence:
    - `runs/EXP-029/budget_curves.png`
    - `runs/EXP-018/budget_curves.png`

- [x] Missing-028: Add a validity/invariance diagnostic to address metadata-only shortcut concerns (ORAL-016 / EXP-039)
  - Location: `provetok/scripts/run_validity_invariance.py`, `docs/plan.md`, `docs/experiment.md`, `docs/claim_evidence.md`
  - Acceptance:
    - `python provetok/scripts/run_validity_invariance.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-039 --tracks A,B --agents random,copylast,dependency,frontier --seeds 11,22,33` succeeds.
    - `runs/EXP-039/summary.json` includes `overall.rank_corr_raw_vs_sealed.{spearman,kendall_tau_a}` and `overall.mean_utility.{raw,sealed,structure_only,metadata_only}`.
  - Implementation:
    - Added `run_validity_invariance.py` to compute raw↔sealed rank correlations and include structure-only / metadata-only sanity baselines.
    - Added ORAL-016 mapping and evidence rows in plan/experiment/claim-evidence docs.
  - Verified: 2026-02-11 via `./.venv/bin/python provetok/scripts/run_validity_invariance.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-039 --tracks A,B --agents random,copylast,dependency,frontier --seeds 11,22,33` (PASS)
  - Evidence:
    - `runs/EXP-039/summary.json`
    - `runs/EXP-039/run_meta.json`

- [x] Missing-029: Add LLM-backed validity/invariance evidence for ORAL-016 (EXP-040)
  - Location: `provetok/scripts/run_llm_validity_invariance.py`, `docs/plan.md`, `docs/experiment.md`, `docs/claim_evidence.md`, `docs/verify_log.md`, `docs/plan_changelog.md`
  - Acceptance:
    - `set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_llm_validity_invariance.py --out_dir runs/EXP-040 --overwrite` succeeds.
    - `runs/EXP-040/summary.json` includes micro+scale per-view utility + per-dimension averages for `raw,sealed,structure_only,metadata_only` on tracks A/B.
    - ORAL-016 Evidence Map includes `EXP-040` and cites the artifact path(s).
  - Implementation:
    - Ran EXP-040 (micro+scale) and recorded artifacts under `runs/EXP-040/`.
    - Updated ORAL-016 evidence mapping to include EXP-040 in plan/experiment/claim-evidence + verify log.
  - Verified: 2026-02-11 via `set -a && source .env && set +a && ./.venv/bin/python provetok/scripts/run_llm_validity_invariance.py --out_dir runs/EXP-040 --overwrite` (PASS)
  - Evidence:
    - `runs/EXP-040/summary.json`
    - `runs/EXP-040/run_meta.json`

- [x] Missing-030: Add linkability / re-identification diagnostic for threat model completeness (ORAL-017 / EXP-041)
  - Location: `provetok/scripts/run_linkability_reidentification.py`, `docs/plan.md`, `docs/experiment.md`, `docs/claim_evidence.md`, `docs/verify_log.md`, `docs/plan_changelog.md`
  - Acceptance:
    - `python provetok/scripts/run_linkability_reidentification.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-041 --overwrite` succeeds.
    - Output `summary.json` reports per-track hit@k/MRR/mean rank for variants `sealed`, `sealed_l1only`, `sealed_summary`, `sealed_redact`.
    - ORAL-017 is added to the plan Evidence Map and claim→evidence docs.
  - Implementation:
    - Added a TF-IDF re-identification script (public variants → raw): `provetok/scripts/run_linkability_reidentification.py`.
    - Ran the diagnostic and recorded artifacts under `runs/EXP-041c/` (see evidence paths).
    - Updated plan/experiment/claim-evidence/verify logs to include ORAL-017 → EXP-041.
  - Verified: 2026-02-12 via `./.venv/bin/python provetok/scripts/run_linkability_reidentification.py --dataset_dir runs/EXP-031/public --output_dir runs/EXP-041c --overwrite` (PASS)
  - Evidence:
    - `runs/EXP-041c/summary.json`
    - `runs/EXP-041c/run_meta.json`

## Ambiguous


## Log
- 2026-02-10: Refreshed repo inventory; starting plan↔implementation gap closure against `docs/plan.md` (Last updated: 2026-02-10).
- 2026-02-10: Closed Missing-021..023; reran `EXP-001..010` + `pytest` (PASS).
- 2026-02-10: Reran oral evidence pipeline (`EXP-011..020`) and refreshed evidence docs (PASS).
- 2026-02-10: Executed oral vNext scale-up + baselines + knob-sweep + agreement report (`EXP-021..024`) and refreshed oral docs/checklists (PASS).
- 2026-02-11: Reran plan-support experiments `EXP-001..020` (with `EXP-004` as expected-failure) and refreshed evidence artifacts under `runs/` (see `runs/PLAN-rerun/check.log`).
- 2026-02-11: Extended scale evidence by replicating micro analyses on the non-toy dataset (`EXP-025..030`) and updated experiment/evidence docs.
- 2026-02-11: Closed Missing-024..027 (public scale bundle export, LLM attacker calibration, recommended config derivation, budget curve plots) and updated paper/oral docs accordingly.
- 2026-02-11: ABC orchestrator A-loop audit: open `Missing` count=0, open `Ambiguous` count=0; no new implementation gaps detected against current `docs/plan.md`.
