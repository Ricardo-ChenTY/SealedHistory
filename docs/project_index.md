# Project Index — SealedHistory / ProveTok

This index documents the repository’s runnable entry points, configs, and artifact contracts. It is used by the doc-driven loop (`docs/plan.md`, `docs/mohu.md`, `docs/experiment.md`).

---

## 1. Directory map (curated)

- `README.md`: top-level runnable instructions
- `plan.md`: dataset collection/build proposal (human-readable)
- `docs/`
  - `docs/plan.md`: claims + evidence map + contracts (canonical)
  - `docs/mohu.md`: blocking gap tracker
  - `docs/experiment.md`: experiment matrix + run log
  - `docs/data_requirements.md`: Public/Private artifact contract
  - `docs/collection_checklist.md`: executable release checklist
  - `docs/data_collection_proposal.md`: collection plan (sources/compliance)
  - `docs/schemas/paper_record_v2.schema.json`: v2 record schema (Public)
  - `docs/templates/`: manual decision templates
- `provetok/` (Python package)
  - `provetok/src/provetok/`: implementation
  - `provetok/configs/`: YAML configs (source of truth for CLI/scripts)
  - `provetok/scripts/`: runnable helper scripts
  - `provetok/data/`: included sample micro-history (raw + sealed)
  - `provetok/tests/`: pytest suite

Ignored/generated (see `.gitignore`):
- `provetok/data/exports/`: dataset exports (public/private)
- `output/`: ad-hoc outputs

---

## 2. Entrypoints (what/where/how-to-run)

| What | Path | How to run | Outputs |
|---|---|---|---|
| Unified CLI | `provetok/src/provetok/cli.py` | `python -m provetok.cli ...` | depends on subcommand |
| Benchmark (CLI) | `provetok/src/provetok/cli.py` (`run`) | `python -m provetok.cli run --agent random --sealed ... --raw ... --output runs/.../eval_report.json` | eval report JSON |
| Benchmark (script) | `provetok/scripts/run_benchmark.py` | `python provetok/scripts/run_benchmark.py --agent random ...` | eval report JSON |
| Dataset build (CLI) | `provetok/src/provetok/dataset/build.py` + `provetok/src/provetok/dataset/pipeline.py` | `python -m provetok.cli dataset build --config provetok/configs/dataset.yaml [--offline] [--track A|B|both]` | `{export_root}/{dataset_version}/{public|private}/...` |
| Dataset legacy export (CLI) | `provetok/src/provetok/dataset/build.py` + `provetok/src/provetok/dataset/legacy.py` | `python -m provetok.cli dataset export-legacy --config ... --track both` | tiered public/private layout (no manifest) |
| v2 leakage audit (script) | `provetok/scripts/run_audit_v2.py` | `python provetok/scripts/run_audit_v2.py --sealed_jsonl ... --codebook_json ... --output ...` | audit report JSON |

---

## 3. Configs (source of truth)

- Benchmark defaults: `provetok/configs/default.yaml`
  - `seed`, `env.budget`, `env.fast_mode`, `eval.rubric_weights`, LLM settings
- Dataset (online): `provetok/configs/dataset.yaml`
  - Track definitions (A/B): concepts/keywords/year ranges + target sizes
  - Sources: OpenAlex / S2 / OpenCitations / arXiv / (optional) PWC dump
  - Selection: topic coverage + deterministic selection signals
  - Fulltext policy: per-tier policy + timeouts
  - Record build: strict paraphrase policy + LLM requirements
  - QA gates: schema/consistency/edge coverage thresholds
  - Seeds: public/private sealed-world seeds

---

## 4. Metrics & evaluation (unified)

### 4.1 Benchmark eval report

- Computation: `provetok/src/provetok/eval/rubric.py`
  - `AutoRubricScorer.score_run(...)` produces `rubric`
  - `save_eval_report(...)` writes JSON with keys `rubric`, `audit`, `pareto`
- Saved by:
  - `python -m provetok.cli run --output ...`
  - `python provetok/scripts/run_benchmark.py --output ...`

### 4.2 Dataset QA + manifest

- QA: `provetok/src/provetok/dataset/qa.py` → `public/qa_report_{core,extended}.jsonl`
- Manifest: `provetok/src/provetok/dataset/build.py` writes `public/dataset_manifest.json`
- Artifact hashing: `provetok/src/provetok/dataset/manifest.py`

---

## 5. Artifacts & storage contract (paths)

Dataset export root is controlled by:
- `provetok/configs/dataset.yaml` (`export_root`, `dataset_version`)
- CLI override: `python -m provetok.cli dataset build --out <export_root>`

Outputs:
- Public: `{export_root}/{dataset_version}/public/**`
- Private: `{export_root}/{dataset_version}/private/**`

Canonical contract: `docs/data_requirements.md`

No model checkpoints are produced in this repository (no training loop).

---

## 6. Baseline smoke: end-to-end commands

Benchmark (random baseline, Track A sample):
```bash
python provetok/scripts/run_benchmark.py \
  --sealed provetok/data/sealed/micro_history_a.sealed.jsonl \
  --raw provetok/data/raw/micro_history_a.jsonl \
  --agent random \
  --output runs/EXP-001/eval_report_a.json
```

Offline dataset build (legacy milestones):
```bash
python -m provetok.cli dataset build \
  --config provetok/configs/dataset_legacy.yaml \
  --track both \
  --out runs/exports
```

