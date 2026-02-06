# Plan — SealedHistory / ProveTok (Doc-Driven)

This file is the canonical, decision-complete engineering plan for proving the project’s claims via reproducible runs.

Related:
- Dataset proposal / spec (human-readable): `plan.md`
- Data contracts (fields, Public/Private, paths): `docs/data_requirements.md`
- Collection checklist (step-by-step outputs): `docs/collection_checklist.md`
- Gap tracker (blocking list): `docs/mohu.md`
- Experiment matrix + results: `docs/experiment.md`

---

## 0. Story / Goal

Build a reproducible dataset pipeline and benchmark harness for **SealedHistory**:
- Produce publishable **v2 paper records** (Public) plus internal mappings/snapshots (Private).
- Produce multi-seed **sealed worlds** (Public records; Private codebooks).
- Provide a runnable benchmark loop (`provetok run`) and leakage-audit scaffolding.

The goal of the doc-driven loop is to make every claim below **provable** by:
1) a concrete command,
2) a deterministic output contract,
3) a recorded run in `docs/experiment.md`.

---

## 1. Claims (must be proven)

### CLAIM-001: Benchmark CLI smoke runs from a fresh checkout (no LLM)
Running the random baseline produces a valid eval report JSON with top-level keys:
`rubric`, `audit`, `pareto`.

Evidence requirements:
- `EXP-001` and `EXP-002` in `docs/experiment.md` are marked PASS.
- The output JSON files exist at the paths listed in the experiment matrix.

### CLAIM-002: Offline dataset build can produce the full public artifact set (legacy-milestones mode)
Running the dataset build in offline/legacy mode produces a publishable directory layout:
`{export_root}/{dataset_version}/public/**` and `.../private/**`, including:
- `public/track_{A,B}_{core,extended}_records.jsonl`
- `public/taxonomy.json`
- `public/dependency_graph_{core,extended}.edgelist`
- `public/selection_log_{core,extended}.jsonl`
- `public/qa_report_{core,extended}.jsonl`
- `public/sdg_configs/sdg.json`
- `public/sealed_worlds/{seed}/{core,extended}/records.jsonl` + `manifest.json`
- `public/attack_suite/README.md`
- `public/dataset_manifest.json`

Evidence requirements:
- `EXP-003` in `docs/experiment.md` is marked PASS.
- `public/dataset_manifest.json` lists `public_artifacts` and includes `qa`, `edge_agreement`, and `sealed_worlds`.

### CLAIM-003: Online strict build gates correctly when a real LLM is required
When `record_build.require_llm=true` and the configured env var is empty, the online build must fail early with a clear error.

Evidence requirements:
- `EXP-004` in `docs/experiment.md` is marked PASS (expected-failure test).
- The captured stderr/stdout contains the configured env var name and indicates early failure.

### CLAIM-004: Repo-level gates are enforced (no `try/except/finally` in executable code)
Repository code must not contain `try/except/finally` blocks. Failures must surface via exceptions/exit codes and be handled by rerun/parameter adjustment outside the code.

Evidence requirements:
- `EXP-005` in `docs/experiment.md` is marked PASS (gate command).

### CLAIM-005: Manual selection decisions are auditable in public selection logs
When `selection.manual_decisions_file` is set, any manual include/exclude decision that matches a candidate must be written into:
- `public/selection_log_extended.jsonl`

Each manual decision log row MUST include:
- `action` (`include`/`exclude`)
- `reason_tag`
- `reviewer_id` (anonymized ID like `r1` is allowed)
- `paper_key`

Evidence requirements:
- `EXP-006` in `docs/experiment.md` is marked PASS.

### CLAIM-006: Canonical `paper_key` is implemented and propagated
Online pipeline mapping rows and selection evidence must include a stable `paper_key` used for dedupe and manual decisions.

Canonical format:
- `doi:{normalized_doi}` when DOI is available
- `arxiv:{normalized_arxiv_id}` when arXiv id is available
- `openalex:{openalex_url}|title_sha256_12:{hash12}` as fallback

Evidence requirements:
- `EXP-006` and `EXP-007` in `docs/experiment.md` are marked PASS.

### CLAIM-007: Raw snapshot contract is split-file and supports offline rebuild
The canonical raw snapshot layout is per-source and split by purpose (works vs requests):
- `private/raw_snapshots/openalex/works_track_{A,B}.jsonl`
- `private/raw_snapshots/openalex/requests_track_{A,B}.jsonl`
- `private/raw_snapshots/s2/requests_track_{A,B}.jsonl` (when enabled)

Request snapshot files are required to exist for enabled sources/tracks and may be empty for offline rebuild runs.

Offline rebuild is defined as: with these snapshots present, running the online pipeline with `--offline` must not access network and must produce selection logs and records deterministically.

Evidence requirements:
- `EXP-008` in `docs/experiment.md` is marked PASS.
- `EXP-007` in `docs/experiment.md` is marked PASS (offline build does not use network or LLM calls).

### CLAIM-008: `public/attack_suite/` export is documentation that points to repo scripts
Dataset exports must include `public/attack_suite/README.md`, which documents how to run audits using repository scripts.
The export does not need to ship runnable scripts.

Evidence requirements:
- `EXP-009` in `docs/experiment.md` is marked PASS.

### CLAIM-009: Demo codebooks are explicitly documented and never copied into exports
The repository may contain synthetic demo codebooks under `provetok/data/sealed/` for smoke tests.
They must be explicitly documented as synthetic and must not be copied into dataset exports under `runs/exports/**`.

Evidence requirements:
- `EXP-010` in `docs/experiment.md` is marked PASS.

---

## 2. Evidence Map (Claim → Experiments → Metrics)

- CLAIM-001 → `EXP-001`, `EXP-002`
  - Metrics: eval report JSON schema (see §3.1)
  - Checks: output file exists + keys present

- CLAIM-002 → `EXP-003`
  - Metrics: dataset manifest + artifact list (see §3.2)
  - Checks: required public/private files exist

- CLAIM-003 → `EXP-004`
  - Metrics: process exit code is non-zero; error message contains env var name
  - Checks: captured log file exists

- CLAIM-004 → `EXP-005`
  - Metrics: repo has zero `try/except/finally` blocks
  - Checks: gate command output indicates 0 matches

- CLAIM-005 → `EXP-006`
  - Metrics: selection_log includes manual rows with reviewer_id + paper_key
  - Checks: grep selection_log for reviewer_id

- CLAIM-006 → `EXP-006`, `EXP-007`
  - Metrics: mapping rows include paper_key; paper_key format stable
  - Checks: mapping JSONL has paper_key field

- CLAIM-007 → `EXP-008`, `EXP-007`
  - Metrics: snapshot files exist at canonical paths; offline build uses no network or LLM calls
  - Checks: snapshot paths exist in export root; offline-no-network test passes

- CLAIM-008 → `EXP-009`
  - Metrics: attack_suite README contains repo-script commands and states it is documentation
  - Checks: file content checks

- CLAIM-009 → `EXP-010`
  - Metrics: repo docs mention synthetic demo codebooks; exports do not contain `*.sealed.codebook.json`
  - Checks: file content + file glob checks

- ORAL-001 → `EXP-011`
  - Metrics: utility mean±std across 3 seeds (A/B tracks), with Sealed vs Raw + two strong baselines
  - Checks: `runs/EXP-011/main_results.csv` exists with required columns

- ORAL-002 → `EXP-012` (materialized under `runs/EXP-011/attacks/*`)
  - Metrics: adaptive black-box / white-box leakage metrics
  - Checks: attack JSON contains `black_box` and `white_box` objects

- ORAL-003 → `EXP-013`
  - Metrics: ablation deltas for lexical/structure/numeric and manual logging auditability
  - Checks: `runs/EXP-013/ablation_results.csv` + `runs/EXP-013/manual_logging_ablation.json`

- ORAL-004 → `EXP-014`
  - Metrics: per-track trend summary for A/B
  - Checks: `runs/EXP-014/cross_domain_summary.json` contains trend flags for black-box and white-box

- ORAL-005 → `EXP-015`
  - Metrics: Cohen's kappa from dual-rater sheet
  - Checks: report JSON status is `ok` once ratings are filled

- ORAL-006 → `EXP-016`
  - Metrics: defended vs raw white-box leakage delta + utility retention on A/B
  - Checks: `runs/EXP-016/summary.json` includes `tracks.*.white_box_delta_defended_minus_raw` and `utility_retention_defended_vs_raw`

- ORAL-007 → `EXP-017`
  - Metrics: bootstrap 95% CI, permutation p-value, Cohen's d for key utility comparisons
  - Checks: `runs/EXP-017/summary.json` includes `comparisons[*].{ci95_low,ci95_high,p_perm_two_sided,cohen_d}`

- ORAL-008 → `EXP-018`
  - Metrics: top1 budget curves for black-box and white-box, covering sealed and defended variants
  - Checks: `runs/EXP-018/budget_curves.json` includes `curves.{A_sealed,B_sealed,A_defended,B_defended}`

- ORAL-009 → `EXP-019`
  - Metrics: holdout utility retention and leakage trends under temporal split
  - Checks: `runs/EXP-019/summary.json` includes `tracks.*.utility_retention` and `tracks.*.black_box_trend_holds`

- ORAL-010 → `EXP-020`
  - Metrics: expanded paired human-eval sample size and agreement statistics
  - Checks: `runs/EXP-020/human_eval_report.json` includes `status=ok` and `n_paired_items>=30`

---

## 3. Metrics / Artifacts Contract

### 3.1 Benchmark eval report (`provetok run` / `scripts/run_benchmark.py`)
Output JSON MUST contain:
- `rubric` (object)
  - `total` (float)
  - `n_proposals` (int)
  - `n_accepted` (int)
  - `breakdown` (list of objects)
  - `per_dimension_avg` (object with keys: `problem_shift`, `mechanism_class`, `dependency`, `claim_validity`, `ablation`, `clarity`)
- `audit` (object; may be empty for random baseline)
- `pareto` (list of objects with keys: `config`, `leakage`, `utility`)

### 3.2 Dataset build export (Public/Private)
Canonical paths and required outputs are defined in:
- `docs/data_requirements.md` (§3 Public artifacts / §4 Private artifacts)
- `docs/collection_checklist.md`

Minimum required proof artifact:
- `public/dataset_manifest.json` exists and includes:
  - `dataset_version`, `build_mode`, `track`
  - `public_artifacts` (list with sha256 entries)
  - `qa` summary and pass rates
  - `sealed_worlds` summary and codebook sha256 references

### 3.3 Gate outputs
The “no try/except” gate produces:
- a command log (saved by experiment runner) showing 0 matches or PASS status.

### 3.4 Canonical keys and selection logs
`paper_key` format is defined in CLAIM-006. The online pipeline must write:
- `paper_key` in private mapping rows: `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`
- `paper_key` in public selection logs: `public/selection_log_{core,extended}.jsonl`
- manual decisions (when configured) must include `reviewer_id` (CLAIM-005)

Manual decisions file (`selection.manual_decisions_file`) input contract:
- Required: `action` (`include`/`exclude`), `reason_tag`, `reviewer_id`
- Keying: provide `paper_key` OR one of `openalex_id` / `doi` / `arxiv_id` (optionally `title` for OpenAlex fallback)
- Accepted `paper_key` forms (normalized):
  - DOI: `10.x/...`, `doi:10.x/...`, `https://doi.org/10.x/...`
  - arXiv: `2101.12345v2`, `arxiv:2101.12345v2`, `arXiv:2101.12345v2`
  - OpenAlex: `https://openalex.org/W...`, `W...`, `openalex:https://openalex.org/W...`, or `openalex:https://openalex.org/W...|title_sha256_12:{hash12}`
- Matching priority: candidate canonical `paper_key` first, then DOI, then arXiv, then OpenAlex aliases.
- Conflicts: if multiple keys match the same candidate with different actions, the build fails fast with a `ValueError`.

---

## 4. Evaluation Protocol (determinism + reproducibility)

- Python: `>=3.11`
- Dependencies: `provetok/requirements.txt`
- Randomness:
  - Benchmark baseline uses fixed seed (default `seed: 42` in `provetok/configs/default.yaml`).
  - Fast-mode benchmark is deterministic for the random baseline.
- Network:
  - `EXP-001..003` are network-free.
  - `EXP-004` is network-free (expected early failure with missing env var).
- Secrets:
  - Online build LLM key is read from the env var configured in `provetok/configs/dataset.yaml` (`record_build.llm_api_key_env`).

---

## 5. Engineering Deliverables (must exist in repo)

- State files:
  - `docs/plan.md` (this file)
  - `docs/mohu.md` (blocking gaps/ambiguities)
  - `docs/experiment.md` (experiment matrix + run results)
  - `README.md` (top-level runnable instructions)
- Configs:
  - `provetok/configs/default.yaml` (benchmark defaults)
  - `provetok/configs/dataset.yaml` (online dataset config)
  - `provetok/configs/dataset_legacy.yaml` (offline legacy-milestones build; created/maintained by this workflow)
- Entry points:
  - `python -m provetok.cli run|dataset ...`
  - `python provetok/scripts/run_benchmark.py`
  - `python provetok/scripts/run_audit_v2.py`

- Documentation / compliance:
  - `provetok/data/sealed/README.md` documents demo codebooks as synthetic

---

## 5A. Oral Addendum Claims (2026-02-06)

These claims complement CLAIM-001..009 for oral-readiness.

### ORAL-001: Main-table evidence includes Sealed vs Raw + two strong baselines with 3 seeds
- Required evidence:
  - `runs/EXP-011/main_results.csv` and `runs/EXP-011/main_results.md`
  - `runs/EXP-011/per_run_metrics.json`

### ORAL-002: Adaptive attacks are reported under black-box and white-box assumptions
- Required evidence:
  - `runs/EXP-011/attacks/A_sealed.json`
  - `runs/EXP-011/attacks/B_sealed.json`
  - each report includes `black_box` and `white_box` metrics

### ORAL-003: Component ablations quantify the effect of removing key sealing parts
- Required evidence:
  - `runs/EXP-013/ablation_results.csv`
  - `runs/EXP-013/ablation_results.md`
  - manual logging axis: `runs/EXP-013/manual_logging_ablation.json`

### ORAL-004: Cross-domain trend check is explicit (Track A/B)
- Required evidence:
  - `runs/EXP-014/cross_domain_summary.json`
  - `runs/EXP-014/cross_domain_summary.md`
- Pass condition:
  - at least black-box trend is verified across tracks; white-box gaps must be stated explicitly if present

### ORAL-005: Human-eval consistency is executable and auditable
- Required evidence:
  - rating template: `docs/templates/human_eval_sheet.csv`
  - agreement script: `provetok/scripts/compute_human_eval_kappa.py`
  - report artifact: `runs/EXP-015/human_eval_report.json`
- Pass condition:
  - `human_eval_report.json` has `status=ok` with paired dual-rater items.

### ORAL-006: White-box defense + utility tradeoff is quantified (A/B tracks)
- Required evidence:
  - script: `provetok/scripts/run_oral_whitebox_defense.py`
  - summary: `runs/EXP-016/summary.json`, `runs/EXP-016/summary.md`
- Pass condition:
  - both tracks report defended-vs-raw white-box leakage delta and utility retention
  - negative tradeoffs must be explicitly retained (no hidden filtering)

### ORAL-007: Statistical confidence is reported (CI + p-value + effect size)
- Required evidence:
  - script: `provetok/scripts/run_oral_stats_significance.py`
  - summary: `runs/EXP-017/summary.json`, `runs/EXP-017/summary.md`
- Pass condition:
  - key pairwise utility comparisons include bootstrap CI, permutation p-value, and Cohen's d

### ORAL-008: Adaptive budget attacks are profiled across defended and non-defended setups
- Required evidence:
  - script: `provetok/scripts/run_oral_budget_attack.py`
  - summary: `runs/EXP-018/budget_curves.json`, `runs/EXP-018/budget_curves.md`
- Pass condition:
  - budgets are swept at multiple levels and reported for both black-box and white-box

### ORAL-009: Holdout temporal generalization is explicitly evaluated
- Required evidence:
  - script: `provetok/scripts/run_oral_holdout_generalization.py`
  - summary: `runs/EXP-019/summary.json`, `runs/EXP-019/summary.md`
- Pass condition:
  - per-track holdout utility retention and leakage trend flags are reported
  - any non-improving track must be disclosed in the oral narrative

### ORAL-010: Human-eval scaling check (>=30 paired items) is completed
- Required evidence:
  - rating sheet: `docs/templates/human_eval_sheet.csv`
  - report: `runs/EXP-020/human_eval_report.json`, `runs/EXP-020/human_eval_report.md`
- Pass condition:
  - report `status=ok` and `n_paired_items>=30`

---

## 6. Change Log (before/after, do not delete)

- 2026-02-05:
  - Before: No doc-driven state files (`docs/plan.md`, `docs/experiment.md`) and no top-level `README.md`.
  - After: Added doc-driven state files and wired the evidence loop (claims → experiments → contracts).

- 2026-02-05:
  - Before: Repo did not satisfy CLAIM-001..004 gates/evidence loop.
  - After: Closed blocking gaps and recorded PASS runs for `EXP-001..005` in `docs/experiment.md`.

- 2026-02-05:
  - Before: `plan.md` backlog items (Missing-021..025, Amb-004..006) were not executable claims.
  - After: Promoted a subset into CLAIM-005..009 with runnable experiments (`EXP-006..010`) and implemented `paper_key` + manual decision logging.

- 2026-02-06:
  - Before: Oral-readiness checklist (main-table/adaptive-attack/ablation/cross-domain/human-eval) was not executable in repo.
  - After: Added ORAL-001..005 claims and runnable scripts with artifacts under `runs/EXP-011`, `runs/EXP-013`, `runs/EXP-014`, `runs/EXP-015`.

- 2026-02-06:
  - Before: “冲顶会 oral” 的下一版决定性补齐项（防御tradeoff、统计显著性、budget攻击、holdout、扩样人评）没有统一验收口径。
  - After: Added ORAL-006..010 claims and corresponding experiment contracts with artifacts under `runs/EXP-016`..`runs/EXP-020`.
