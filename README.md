# SealedHistory / ProveTok

Reproducible dataset pipeline + benchmark harness for **SealedHistory** (sealed micro-history records, leakage audits, and evaluation).

## Docs (state machine)

This repo follows a doc-driven workflow. The four state files are:
- `docs/plan.md`: claims + evidence map + contracts (canonical)
- `docs/mohu.md`: blocking gaps/ambiguities (must be empty to proceed)
- `docs/experiment.md`: experiment matrix + run log (what we ran, what it proved)
- `README.md`: runnable entry points (this file)

Additional specs:
- `plan.md`: dataset collection/build proposal (human-readable spec)
- `docs/data_requirements.md`: Public/Private artifact contract
- `docs/collection_checklist.md`: executable checklist for dataset release

## Quickstart

### 1) Install
```bash
python -m venv .venv
# Windows (PowerShell)
./.venv/Scripts/python -m pip install -r provetok/requirements.txt

# macOS/Linux
./.venv/bin/python -m pip install -r provetok/requirements.txt

# Optional: install console script `provetok`
python -m pip install -e provetok
```

### 2) Run tests
```bash
python -m pytest -q
```

### 3) Benchmark smoke (no LLM)
```bash
python provetok/scripts/run_benchmark.py \
  --sealed provetok/data/sealed/micro_history_a.sealed.jsonl \
  --raw provetok/data/raw/micro_history_a.jsonl \
  --agent random \
  --output runs/EXP-001/eval_report_a.json
```

### 4) Offline dataset build (legacy-milestones mode)
```bash
python -m provetok.cli dataset build \
  --config provetok/configs/dataset_legacy.yaml \
  --track both \
  --out runs/exports
```

Outputs land under `runs/exports/{dataset_version}/{public|private}/...` (see `docs/data_requirements.md`).

## Key entry points

- Benchmark CLI: `python -m provetok.cli run --agent {random|copylast|dependency|frontier|llm} --sealed ... --raw ... --output ...`
- Dataset build: `python -m provetok.cli dataset build --config provetok/configs/dataset.yaml [--offline] [--track A|B|both]`
- Legacy export only: `python -m provetok.cli dataset export-legacy --config provetok/configs/dataset.yaml --track both`
- v2 leakage audit: `python provetok/scripts/run_audit_v2.py --sealed_jsonl ... --codebook_json ... --output ...`

## Oral evidence pack

```bash
python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33
python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33
python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014
python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015
```

Narrative pack:
- `docs/oral_checklist.md`
- `docs/oral_story.md`

## Demo codebooks (synthetic)

This repo includes demo sealed datasets under `provetok/data/sealed/` for offline smoke tests.
The matching `*.sealed.codebook.json` files in that folder are **synthetic demo mappings** used only for examples/tests.

Real dataset exports produced by `provetok dataset build` write private codebooks under:
- `runs/exports/{dataset_version}/private/mapping_key/seed_{seed}.codebook.json`

Do not publish or commit real codebooks from exports.

## Repo rules (gates)

- Do not add `try/except/finally` blocks in executable code.
- Keep outputs under `runs/` (gitignored).
