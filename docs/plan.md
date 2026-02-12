下面给你一份**“decision-complete、证据闭环、可复现运行”**的增强版 `docs/plan.md`（我把你原文完整保留并在其基础上**加粗补齐/扩写所有缺细节的地方**；同时新增了**数据集收集方案**、**预期数据集形态/规模估算**、以及一个尽可能大的**文献支撑库**，用于把 proposal 的动机与方法论扎在已有研究上）。文中所有外部事实/背景判断，我都尽量用可追溯来源支撑。

---

# Plan — SealedHistory / ProveTok (Doc-Driven)

> **Canonical, decision-complete engineering plan** for proving the project’s claims via reproducible runs.
> **Last updated:** 2026-02-11 (Asia/Singapore)

Related:

* Dataset proposal / spec (human-readable): `plan.md` (this file)
* Data contracts (fields, Public/Private, paths): `docs/data_requirements.md`
* Collection checklist (step-by-step outputs): `docs/collection_checklist.md`
* Gap tracker (blocking list): `docs/mohu.md`
* Experiment matrix + results: `docs/experiment.md`
* Paper experiment map (main vs appendix; micro+scale pairing): `docs/paper_experiment_map.md`

---

## 0. Story / Goal

Build a reproducible dataset pipeline and benchmark harness for **SealedHistory**:

* Produce publishable **v2 paper records** (Public) plus internal mappings/snapshots (Private).
* Produce multi-seed **sealed worlds** (Public records; Private codebooks).
* Provide a runnable benchmark loop (`provetok run`) and leakage-audit scaffolding.

The goal of the doc-driven loop is to make every claim below **provable** by:

1. a concrete command,
2. a deterministic output contract,
3. a recorded run in `docs/experiment.md`.

### 0.1 Why this project exists (motivation, grounded)

LLM evaluation increasingly suffers from **benchmark contamination** (test items appear in training corpora or post-training), which can inflate scores and undermine claims about generalization. This has motivated mitigations ranging from “don’t publish test data in plain text” to dynamic/time-sensitive benchmarks and contamination detection.
At the same time, LMs can **memorize and leak training data** under both black-box and stronger assumptions, motivating systematic leakage auditing and explicit threat models.
Finally, the research community increasingly expects **dataset/model documentation standards** (datasheets, data statements, model cards, etc.) to make artifacts auditable and responsibly reusable.

**SealedHistory / ProveTok** is designed as a *doc-driven, evidence-closed-loop* system that makes (a) dataset construction, (b) evaluation, and (c) leakage audits **reproducible** from recorded commands and deterministic artifacts—while keeping private codebooks and raw snapshots separate from publishable exports.

### 0.2 Terminology (make the doc executable)

**Tracks**

* **Track A / Track B**: two disjoint domains (or two disjoint query programs) that support cross-domain trend checks (ORAL-004).
* Each track has **core** and **extended** subsets:

  * `core`: smaller, higher-confidence, higher-auditability set (paper+record quality bar is stricter).
  * `extended`: larger, broader coverage (allows harder distribution shift and long-tail mechanisms).

**Paper record (v2)**
A normalized, deduplicated “paper-level unit” used to generate evaluation items and dependency graphs. It must be keyed by `paper_key` (CLAIM-006).

**Sealed world**
A deterministic transformation of public records under a seed, producing:

* a **public** sealed representation (safe to export),
* a **private** codebook mapping (never exported) required to decode/verify some leakage/attack outcomes.

**Public vs Private**

* **Public**: publishable dataset artifacts under `public/**` (records, taxonomy, graphs, selection logs, QA summaries, sealed worlds w/out codebooks, attack_suite docs).
* **Private**: raw snapshots, mappings, intermediate caches, private codebooks, and any legally/ethically sensitive material.

### 0.3 Data source policy (what is allowed to ship)

**Metadata sources** like OpenAlex (CC0) can generally be redistributed.
Semantic Scholar data access is governed by its API/data licenses; for any redistribution beyond metadata, enforce conservative rules (e.g., no full text; abstracts only if license permits) and keep raw snapshots private by default.
If you choose to use S2ORC components (abstracts/full text), verify license and “underlying contents” constraints; do not assume all included text is freely redistributable.

---

## 1. Claims (must be proven)

### CLAIM-001: Benchmark CLI smoke runs from a fresh checkout (no LLM)

Running the random baseline produces a valid eval report JSON with top-level keys:
`rubric`, `audit`, `pareto`.

Evidence requirements:

* `EXP-001` and `EXP-002` in `docs/experiment.md` are marked PASS.
* The output JSON files exist at the paths listed in the experiment matrix.

**Implementation detail (fill-in):**

* Define a single “fresh checkout” command sequence:

  * `python -m venv .venv && source .venv/bin/activate`
  * `pip install -r provetok/requirements.txt`
  * `python -m provetok.cli run --config provetok/configs/default.yaml --baseline random --out runs/EXP-001/eval.json`
* The PASS predicate is purely mechanical:

  * file exists
  * JSON loads
  * schema keys exist (§3.1)
  * deterministic hash of file content matches recorded hash in `docs/experiment.md` (optional but recommended).

### CLAIM-002: Offline dataset build can produce the full public artifact set (legacy-milestones mode)

Running the dataset build in offline/legacy mode produces a publishable directory layout:
`{export_root}/{dataset_version}/public/**` and `.../private/**`, including:

* `public/track_{A,B}_{core,extended}_records.jsonl`
* `public/taxonomy.json`
* `public/dependency_graph_{core,extended}.edgelist`
* `public/selection_log_{core,extended}.jsonl`
* `public/qa_report_{core,extended}.jsonl`
* `public/sdg_configs/sdg.json`
* `public/sealed_worlds/{seed}/{core,extended}/records.jsonl` + `manifest.json`
* `public/attack_suite/README.md`
* `public/dataset_manifest.json`

Evidence requirements:

* `EXP-003` in `docs/experiment.md` is marked PASS.
* `public/dataset_manifest.json` lists `public_artifacts` and includes `qa`, `edge_agreement`, and `sealed_worlds`.

**Implementation detail (fill-in):**

* The **legacy** builder is a strictly offline “materialize from snapshots + deterministic transforms” pipeline.
* It must not require OpenAlex/S2 network access or any LLM call; it should consume:

  * `provetok/configs/dataset_legacy.yaml`
  * pre-existing `private/raw_snapshots/**` (may be empty/placeholder for legacy, but paths must exist)
  * pre-authored “milestones” or curated paper lists (legacy mode input) under `private/curation_inputs/**` (you decide exact path; document it in `docs/data_requirements.md`).

### CLAIM-003: Online strict build gates correctly when a real LLM is required

When `record_build.require_llm=true` and the configured env var is empty, the online build must fail early with a clear error.

Evidence requirements:

* `EXP-004` in `docs/experiment.md` is marked PASS (expected-failure test).
* The captured stderr/stdout contains the configured env var name and indicates early failure.

**Implementation detail (fill-in):**

* “Fail early” means: before any network work or expensive compute.
* Preflight check order:

  1. parse config
  2. check `record_build.require_llm`
  3. read env var name from `record_build.llm_api_key_env`
  4. if missing/empty -> `raise RuntimeError(f"Missing required env var: {ENV_NAME} ...")`

### CLAIM-004: Repo-level gates are enforced (no `try/except/finally` in executable code)

Repository code must not contain `try/except/finally` blocks. Failures must surface via exceptions/exit codes and be handled by rerun/parameter adjustment outside the code.

Evidence requirements:

* `EXP-005` in `docs/experiment.md` is marked PASS (gate command).

**Implementation detail (fill-in, robust):**
Prefer an AST-based gate over regex to avoid false positives in strings/comments:

* `python provetok/scripts/gate_no_try.py --paths provetok --fail-on-match`
* Gate logic:

  * parse each `.py` to AST
  * count `ast.Try` nodes
  * print offending file:line spans
  * exit 1 if any found, else exit 0

> Note: this gate can itself avoid `try/except` by letting parse errors raise. The repo should be syntactically valid, so this is acceptable.

### CLAIM-005: Manual selection decisions are auditable in public selection logs

When `selection.manual_decisions_file` is set, any manual include/exclude decision that matches a candidate must be written into:

* `public/selection_log_extended.jsonl`

Each manual decision log row MUST include:

* `action` (`include`/`exclude`)
* `reason_tag`
* `reviewer_id` (anonymized ID like `r1` is allowed)
* `paper_key`

Evidence requirements:

* `EXP-006` in `docs/experiment.md` is marked PASS.

**Implementation detail (fill-in):**

* The selection pipeline must merge manual decisions after canonicalization of identifiers:

  * compute candidate `paper_key`
  * match manual record by priority (CLAIM-006 priority)
  * when applied, emit a **log row with `source="manual"`** plus an optional `decision_id` and timestamp.
* If a manual decision references a non-existent candidate:

  * either emit a warning row in *private* logs (not public), or fail (you choose; document).
  * do **not** fabricate candidate rows.

### CLAIM-006: Canonical `paper_key` is implemented and propagated

Online pipeline mapping rows and selection evidence must include a stable `paper_key` used for dedupe and manual decisions.

Canonical format:

* `doi:{normalized_doi}` when DOI is available
* `arxiv:{normalized_arxiv_id}` when arXiv id is available
* `s2:{paperId}` when S2 paperId is available
* `openalex:{openalex_url}|title_sha256_12:{hash12}` as fallback

Evidence requirements:

* `EXP-006` and `EXP-007` in `docs/experiment.md` are marked PASS.

**Implementation detail (fill-in, normalization rules):**

* `normalized_doi`: lowercase, strip `https://doi.org/`, trim spaces, collapse unicode variants, preserve `/` and `.`.
* `normalized_arxiv_id`: lowercase `2101.12345v2` style, ensure `vN` preserved if present.
* `s2 paperId`: treat as canonical case-sensitive hex string as returned by API.
* `openalex_url`: normalize to full `https://openalex.org/W...`
* `title_sha256_12`: sha256 of normalized title (NFKC, lowercase, collapse whitespace) then take first 12 hex.

### CLAIM-007: Raw snapshot contract is split-file and supports offline rebuild

The canonical raw snapshot layout is per-source and split by purpose (works vs requests):

* `private/raw_snapshots/s2/works_track_{A,B}.jsonl`
* `private/raw_snapshots/s2/requests_track_{A,B}.jsonl`
* `private/raw_snapshots/openalex/works_track_{A,B}.jsonl` (legacy offline compatibility only)

Request snapshot files are required to exist for enabled sources/tracks and may be empty for offline rebuild runs.

Offline rebuild is defined as: with these snapshots present, running the online pipeline with `--offline` must not access network and must produce selection logs and records deterministically.

Evidence requirements:

* `EXP-008` in `docs/experiment.md` is marked PASS.
* `EXP-007` in `docs/experiment.md` is marked PASS (offline build does not use network or LLM calls).

**Implementation detail (fill-in, request snapshot schema):**
Each `requests_*.jsonl` line is a *request ledger* entry:

```json
{
  "request_id": "uuid4",
  "ts_utc": "2026-02-10T08:12:33Z",
  "source": "s2",
  "endpoint": "/graph/v1/paper/search",
  "method": "GET",
  "params": {"query": "...", "limit": 100, "offset": 0, "fields": "..."},
  "response": {"status": 200, "sha256": "…", "n_items": 100},
  "notes": {"rate_limit_bucket": "public", "track": "A"}
}
```

Each `works_*.jsonl` line is a *normalized work payload* (store the minimal fields you need to rebuild deterministically, plus provenance pointers), e.g.:

```json
{
  "source": "s2",
  "track": "A",
  "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
  "externalIds": {"DOI": "10.1145/....", "ArXiv": "2101.12345"},
  "title": "...",
  "year": 2024,
  "venue": "...",
  "authors": [{"name": "...", "authorId": "..." }],
  "citationCount": 12,
  "referenceIds": ["..."],
  "openAccessPdf": {"url": "..."},
  "ingested_ts_utc": "2026-02-10T08:12:33Z",
  "raw_sha256": "..." 
}
```

> 为什么要 requests/works 分离：requests 证明“你查过什么、什么时候查的、返回多少”，works 才是可复现构建的“数据面”。这种 ledger 设计是为了后续审计（比如证明 offline 模式未发起新请求）。

**No-network enforcement suggestion (for EXP-007/008):**

* Run the offline pipeline under a network sandbox (`unshare -n` on Linux) or a CI job that blocks outbound connections; the test must fail if any socket is opened.（工具选择你们定；关键是**证据**：日志 + exit code + 生成物 hash。）

### CLAIM-008: `public/attack_suite/` export is documentation that points to repo scripts

Dataset exports must include `public/attack_suite/README.md`, which documents how to run audits using repository scripts. The export does not need to ship runnable scripts.

Evidence requirements:

* `EXP-009` in `docs/experiment.md` is marked PASS.

**Implementation detail (fill-in):**
`public/attack_suite/README.md` must:

* clearly state “This directory contains documentation only”
* link/point to repo scripts:

  * `python provetok/scripts/run_audit_v2.py ...`
  * any oral attack scripts (`run_oral_*`)
* include exact command templates referencing exported `dataset_manifest.json` and sealed world paths.

### CLAIM-009: Demo codebooks are explicitly documented and never copied into exports

The repository may contain synthetic demo codebooks under `provetok/data/sealed/` for smoke tests.
They must be explicitly documented as synthetic and must not be copied into dataset exports under `runs/exports/**`.

Evidence requirements:

* `EXP-010` in `docs/experiment.md` is marked PASS.

**Implementation detail (fill-in):**

* Add a hard “export denylist” rule:

  * forbid copying files matching `*.sealed.codebook.json` into any `runs/exports/**/public/**`
* Add a documentation check:

  * `provetok/data/sealed/README.md` must contain the string `SYNTHETIC DEMO` (or similar invariant) and warn “DO NOT EXPORT”.

---

## 2. Evidence Map (Claim → Experiments → Metrics)

* CLAIM-001 → `EXP-001`, `EXP-002`

  * Metrics: eval report JSON schema (see §3.1)
  * Checks: output file exists + keys present
* CLAIM-002 → `EXP-003`

  * Metrics: dataset manifest + artifact list (see §3.2)
  * Checks: required public/private files exist
* CLAIM-003 → `EXP-004`

  * Metrics: process exit code is non-zero; error message contains env var name
  * Checks: captured log file exists
* CLAIM-004 → `EXP-005`

  * Metrics: repo has zero `try/except/finally` blocks
  * Checks: gate command output indicates 0 matches
* CLAIM-005 → `EXP-006`

  * Metrics: selection_log includes manual rows with reviewer_id + paper_key
  * Checks: grep selection_log for reviewer_id
* CLAIM-006 → `EXP-006`, `EXP-007`

  * Metrics: mapping rows include paper_key; paper_key format stable
  * Checks: mapping JSONL has paper_key field
* CLAIM-007 → `EXP-008`, `EXP-007`

  * Metrics: S2 snapshot files exist at canonical paths; offline build uses no network or LLM calls
  * Checks: snapshot paths exist in export root; offline-no-network test passes
* CLAIM-008 → `EXP-009`

  * Metrics: attack_suite README contains repo-script commands and states it is documentation
  * Checks: file content checks
* CLAIM-009 → `EXP-010`

  * Metrics: repo docs mention synthetic demo codebooks; exports do not contain `*.sealed.codebook.json`
  * Checks: file content + file glob checks
* ORAL-001 → `EXP-011` (micro), `EXP-022` (scale)

  * Metrics: utility mean±std across 3 seeds (A/B tracks), with Sealed vs Raw + two strong baselines (micro), and the same table on a non-toy dataset (scale)
  * Checks:
    * `runs/EXP-011/main_results.csv` exists with required columns (micro)
    * `runs/EXP-031/public/public_dataset_manifest.json` exists (public scale dataset prerequisite; excludes codebooks)
    * (maintainer-only) `runs/EXP-021/dataset/dataset_manifest.json` exists (internal build provenance)
    * `runs/EXP-022/main_results.csv` exists with required columns (scale)
* ORAL-002 → `EXP-012` (micro; materialized under `runs/EXP-011/attacks/*`), `EXP-022` (scale; materialized under `runs/EXP-022/attacks/*`)

  * Metrics: adaptive black-box / white-box leakage metrics
  * Checks: representative attack JSON contains `black_box` and `white_box` objects (micro+scale)
* ORAL-003 → `EXP-013` (micro), `EXP-025` (scale)

  * Metrics: ablation deltas for lexical/structure/numeric and manual logging auditability
  * Checks:
    * `runs/EXP-013/ablation_results.csv` + `runs/EXP-013/manual_logging_ablation.json` (micro)
    * `runs/EXP-025/ablation_results.csv` (scale)
* ORAL-004 → `EXP-014` (micro), `EXP-026` (scale)

  * Metrics: per-track trend summary for A/B
  * Checks:
    * `runs/EXP-014/cross_domain_summary.json` contains trend flags for black-box and white-box (micro)
    * `runs/EXP-026/cross_domain_summary.json` contains trend flags for black-box and white-box (scale)
* ORAL-005 → `EXP-015` (kappa), `EXP-024` (kappa + alpha diagnostics)

  * Metrics: inter-rater agreement metrics from dual-rater sheet
  * Checks: report JSON status is `ok` once ratings are filled; alpha is present in diagnostics runs
* ORAL-006 → `EXP-016` (micro), `EXP-023` (scale curve), `EXP-027` (scale snapshot)

  * Metrics: defended vs raw white-box leakage delta + utility retention on A/B
  * Checks:
    * `runs/EXP-016/summary.json` includes `tracks.*.white_box_delta_defended_minus_raw` and `utility_retention_defended_vs_raw` (micro)
    * `runs/EXP-023/tradeoff_curve.json` exists with >= 5 knob points (scale)
    * `runs/EXP-027/summary.json` includes `tracks.*.white_box_delta_defended_minus_raw` and `utility_retention_defended_vs_raw` (scale)
* ORAL-007 → `EXP-017` (micro), `EXP-028` (scale)

  * Metrics: bootstrap 95% CI, permutation p-value, Cohen's d for key utility comparisons
  * Checks:
    * `runs/EXP-017/summary.json` includes `comparisons[*].{ci95_low,ci95_high,p_perm_two_sided,cohen_d}` (micro)
    * `runs/EXP-028/summary.json` includes `comparisons[*].{ci95_low,ci95_high,p_perm_two_sided,cohen_d}` (scale)
* ORAL-008 → `EXP-018` (micro), `EXP-029` (scale)

  * Metrics: top1 budget curves for black-box and white-box, covering sealed and defended variants
  * Checks:
    * `runs/EXP-018/budget_curves.json` includes `curves.{A_sealed,B_sealed,A_defended,B_defended}` (micro)
    * `runs/EXP-029/budget_curves.json` includes `curves.{A_sealed,B_sealed,A_defended,B_defended}` (scale)
* ORAL-009 → `EXP-019` (micro), `EXP-030` (scale)

  * Metrics: holdout utility retention and leakage trends under temporal split
  * Checks:
    * `runs/EXP-019/summary.json` includes `tracks.*.utility_retention` and `tracks.*.black_box_trend_holds` (micro)
    * `runs/EXP-030/summary.json` includes `tracks.*.utility_retention` and `tracks.*.black_box_trend_holds` (scale)
* ORAL-010 → `EXP-020` (scale-up run), `EXP-024` (agreement diagnostics)

  * Metrics: expanded paired human-eval sample size and agreement statistics
  * Checks: `runs/EXP-020/human_eval_report.json` includes `status=ok` and `n_paired_items>=30`
* ORAL-011 → `EXP-034` (ConStat-style contamination statistics)

  * Metrics: contamination score with CI and corrected utility gap between raw vs sealed
  * Checks:
    * `runs/EXP-034/summary.json` includes `overall.mean_contamination_score`, `overall.contamination_score_ci95`, and `overall.mean_corrected_utility_gap_left_minus_right`
    * `runs/EXP-034/run_meta.json` records `n_boot=4000`
* ORAL-012 → `EXP-035` (LatestEval/LiveBench-style dynamic time-window evaluation)

  * Metrics: utility retention and leakage trend stability across historical/rolling/recent windows
  * Checks:
    * `runs/EXP-035/summary.json` includes `overall.avg_utility_retention` and `overall.black_box_trend_holds_all_windows`
    * `runs/EXP-035/summary.json` includes `per_track.{A,B}.{historical,rolling,recent}`
* ORAL-013 → `EXP-036` (DyePack-style contamination tagging traceability)

  * Metrics: traceability coverage, ambiguity rate, and false-positive rate on negative probes
  * Checks:
    * `runs/EXP-036/summary.json` includes `overall.mean_traceable_coverage`, `overall.mean_ambiguity_rate_on_assignable`, and `overall.mean_false_positive_rate_on_negatives`
* ORAL-014 → `EXP-037` (Carlini/Nasr-style extraction stress test)

  * Metrics: budget-sweep extraction curves and defended-vs-sealed deltas under white-box attack
  * Checks:
    * `runs/EXP-037/summary.json` includes `curves.{A_sealed,B_sealed,A_defended,B_defended}`
    * `runs/EXP-037/summary.json` includes `aggregates.*` and `defended_minus_sealed_at_max_budget`
* ORAL-015 → `EXP-038` (LLM-as-a-judge reliability validation)

  * Metrics: judge-human agreement (`cohen_kappa_binary`, `spearman_r`, `mae`) and pass/fail threshold result
  * Checks:
    * `runs/EXP-038/summary.json` includes `metrics.{mae,pearson_r,spearman_r,cohen_kappa_binary}`
    * `runs/EXP-038/summary.json` includes `pass_rule.pass=true`
* ORAL-016 → `EXP-039` (validity: measurement invariance + metadata-only sanity; heuristic agents) + `EXP-040` (LLM proposer invariance)

  * Metrics:
    * rank correlation (Spearman + Kendall) between raw vs sealed ordering across agents
    * sanity baselines: `structure_only` (graph-only) vs `metadata_only` (no graph, no text) utilities
    * LLM proposer utility retention (raw vs sealed) + per-dimension degradation under `structure_only` / `metadata_only`
  * Checks:
    * `runs/EXP-039/summary.json` includes `overall.rank_corr_raw_vs_sealed.{spearman,kendall_tau_a}`
    * `runs/EXP-039/summary.json` includes `per_track.{A,B}.rank_corr_raw_vs_sealed.spearman`
    * `runs/EXP-039/summary.json` includes `overall.mean_utility.{raw,sealed,structure_only,metadata_only}`
    * `runs/EXP-040/summary.json` includes `micro.{A,B}.per_view.{raw,sealed,structure_only,metadata_only}.utility_mean`
    * `runs/EXP-040/summary.json` includes `scale.{A,B}.per_view.{raw,sealed,structure_only,metadata_only}.utility_mean`
    * `runs/EXP-040/summary.json` shows micro sealed utility_mean within `0.08` of raw (A/B), and scale sealed utility_mean >= raw - `0.08` (A/B)
    * `runs/EXP-040/summary.json` shows `sealed` per_dimension_avg.mechanism_class exceeds `metadata_only` and `structure_only` by >= `0.2` (micro+scale, A/B)

---

## 3. Metrics / Artifacts Contract

### 3.1 Benchmark eval report (`provetok run` / `scripts/run_benchmark.py`)

Output JSON MUST contain:

* `rubric` (object)

  * `total` (float)
  * `n_proposals` (int)
  * `n_accepted` (int)
  * `breakdown` (list of objects)
  * `per_dimension_avg` (object with keys: `problem_shift`, `mechanism_class`, `dependency`, `claim_validity`, `ablation`, `clarity`)
* `audit` (object; may be empty for random baseline)
* `pareto` (list of objects with keys: `config`, `leakage`, `utility`)

**Fill-in (tighten schema):**

* `breakdown[*]` must include:

  * `dimension` (string in the above set)
  * `avg` (float)
  * `n` (int)
* `pareto[*]` must include:

  * `config` (string or object; if object must be JSON-serializable)
  * `leakage` (float; lower is better)
  * `utility` (float; higher is better)

### 3.2 Dataset build export (Public/Private)

Canonical paths and required outputs are defined in:

* `docs/data_requirements.md` (§3 Public artifacts / §4 Private artifacts)
* `docs/collection_checklist.md`

Minimum required proof artifact:

* `public/dataset_manifest.json` exists and includes:

  * `dataset_version`, `build_mode`, `track`
  * `public_artifacts` (list with sha256 entries)
  * `qa` summary and pass rates
  * `sealed_worlds` summary and codebook sha256 references

**Fill-in (manifest shape建议固定):**

```json
{
  "dataset_version": "v2.0.0",
  "build_mode": "legacy_offline" ,
  "created_ts_utc": "2026-02-10T09:01:11Z",
  "tracks": ["A","B"],
  "subsets": ["core","extended"],
  "seeds": [11,23,42],
  "public_artifacts": [
    {"path":"public/taxonomy.json","sha256":"...","bytes":12345},
    {"path":"public/track_A_core_records.jsonl","sha256":"...","bytes":...,"n_records":300}
  ],
  "qa": {
    "core": {"n_items":300,"pass_rate":0.94,"checks":["schema","key_uniqueness","edge_consistency"]},
    "extended": {"n_items":1000,"pass_rate":0.91,"checks":["schema","key_uniqueness","edge_consistency"]}
  },
  "edge_agreement": {
    "core": {"kappa": 0.72, "n_edges_rated": 120},
    "extended": {"kappa": 0.68, "n_edges_rated": 200}
  },
  "sealed_worlds": {
    "seeds":[
      {"seed":11,"core":{"public_records_sha256":"...","private_codebook_sha256":"..."},
               "extended":{"public_records_sha256":"...","private_codebook_sha256":"..."}}
    ]
  },
  "provenance": {
    "sources": ["openalex","s2"],
    "raw_snapshot_paths": [
      "private/raw_snapshots/s2/works_track_A.jsonl",
      "private/raw_snapshots/s2/requests_track_A.jsonl"
    ]
  }
}
```

### 3.3 Gate outputs

The “no try/except” gate produces:

* a command log (saved by experiment runner) showing 0 matches or PASS status.

### 3.4 Canonical keys and selection logs

`paper_key` format is defined in CLAIM-006. The online pipeline must write:

* `paper_key` in private mapping rows: `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`
* `paper_key` in public selection logs: `public/selection_log_{core,extended}.jsonl`
* manual decisions (when configured) must include `reviewer_id` (CLAIM-005)

Manual decisions file (`selection.manual_decisions_file`) input contract:

* Required: `action` (`include`/`exclude`), `reason_tag`, `reviewer_id`
* Keying: provide `paper_key` OR one of `s2_id` / `openalex_id` / `doi` / `arxiv_id`
* Accepted `paper_key` forms (normalized):

  * DOI: `10.x/...`, `doi:10.x/...`, `https://doi.org/10.x/...`
  * arXiv: `2101.12345v2`, `arxiv:2101.12345v2`, `arXiv:2101.12345v2`
  * S2: `649def34f8be52c8b66281af98ae884c09aef38b`, `s2:649def34f8be52c8b66281af98ae884c09aef38b`
  * OpenAlex: `https://openalex.org/W...`, `W...`, `openalex:https://openalex.org/W...`, or `openalex:https://openalex.org/W...|title_sha256_12:{hash12}`
* Matching priority: candidate canonical `paper_key` first, then DOI, then arXiv, then S2 aliases, then OpenAlex aliases.
* Conflicts: if multiple keys match the same candidate with different actions, the build fails fast with a `ValueError`.

**Fill-in (public selection log row schema建议固定):**

```json
{
  "ts_utc":"2026-02-10T09:02:33Z",
  "track":"A",
  "subset":"extended",
  "paper_key":"doi:10.1145/3458723",
  "action":"include",
  "source":"manual",
  "reason_tag":"core_relevance",
  "reviewer_id":"r1",
  "candidate_rank": 17,
  "evidence": {
    "matched_by":"paper_key",
    "aliases":{"doi":"10.1145/3458723","openalex":"https://openalex.org/W....","s2":"..."}
  }
}
```

---

## 4. Evaluation Protocol (determinism + reproducibility)

* Python: `>=3.11`
* Dependencies: `provetok/requirements.txt`
* Randomness:

  * Benchmark baseline uses fixed seed (default `seed: 42` in `provetok/configs/default.yaml`).
  * Fast-mode benchmark is deterministic for the random baseline.
* Network:

  * `EXP-001..003` are network-free.
  * `EXP-004` is network-free (expected early failure with missing env var).
* Secrets:

  * Online build LLM key is read from the env var configured in `provetok/configs/dataset.yaml` (`record_build.llm_api_key_env`).

**Fill-in (determinism hardening checklist):**

* Set and record:

  * `PYTHONHASHSEED=0`
  * locale `LC_ALL=C.UTF-8`
  * timezone `TZ=UTC` for runs (even if author timezone is Asia/Singapore)
* Canonical JSON writing:

  * sorted keys
  * utf-8
  * no trailing spaces
  * stable float formatting (e.g., `repr` not `str` if needed)
* Stable ordering:

  * always sort record output by `paper_key`
  * always sort edges in edgelists (`src_key`, `dst_key`, `edge_type`)
* Deterministic hashing:

  * sha256 computed on exact bytes written to disk
  * record sha256 in manifest and in `docs/experiment.md`

---

## 5. Engineering Deliverables (must exist in repo)

* State files:

  * `docs/plan.md` (this file)
  * `docs/mohu.md` (blocking gaps/ambiguities)
  * `docs/experiment.md` (experiment matrix + run results)
  * `README.md` (top-level runnable instructions)
* Configs:

  * `provetok/configs/default.yaml` (benchmark defaults)
  * `provetok/configs/dataset.yaml` (online dataset config)
  * `provetok/configs/dataset_legacy.yaml` (offline legacy-milestones build; created/maintained by this workflow)
* Entry points:

  * `python -m provetok.cli run|dataset ...`
  * `python provetok/scripts/run_benchmark.py`
  * `python provetok/scripts/run_audit_v2.py`
* Documentation / compliance:

  * `provetok/data/sealed/README.md` documents demo codebooks as synthetic

**Fill-in (CI / gates建议):**

* `make gate` runs:

  * schema validation on configs
  * `gate_no_try`
  * minimal smoke runs (`EXP-001` equivalent)
  * export denylist check (`*.sealed.codebook.json` not in exports)
* `make exp EXP=003` runs the experiment runner that:

  * creates run dir
  * captures stdout/stderr to `runs/EXP-003/log.txt`
  * writes `runs/EXP-003/status.json` with exit code + artifact hashes

---

## 5A. Oral Addendum Claims (2026-02-06)

(原文保留，略)

> 你原文 ORAL-001..010 我这里不删不改；建议在实现层面把“口头证据”也纳入统一 manifest（例如 `runs/EXP-0xx/summary.json` 都收敛成同结构），这样审稿/答辩时只要展示一个 index 页即可。

---

## 6. Dataset Collection Plan (你最关心的：怎么收集、收集到什么样、预期多大)

> 这一节是我新增的“可执行收集方案”，目标是把 `docs/collection_checklist.md` 从“步骤列表”提升为“**可复现实验程序**”。

### 6.1 Sources & why (可追溯、可复现、可离线重建)

**Primary metadata graph: OpenAlex**

* 覆盖面大、API/快照完善，数据 CC0 可再分发，适合做“公开可发布”的 paper registry 与引用关系骨架。

**Secondary/augmentation: Semantic Scholar (S2) API / S2AG**

* 提供 paperId、引用边、作者/venue disambiguation 等；S2 Open Data Platform 描述了其知识图谱与处理管线，可作为 snapshot 合理性与字段选择依据。
* 但 API 使用受许可协议约束，且 S2 网站本身不授予你转载论文内容的权限；因此默认策略是：**只公开发布你们生成的“records”与派生标注**，不直接打包分发任何可能涉及版权的全文/长摘要。

> 你也可以反过来：公开发布只含 OpenAlex 元数据 + 你们的派生结构；S2 数据只用于 private snapshot 重建与内部审计。

### 6.2 Track A/B 的“查询程序”设计（决定你收集什么）

把 Track 定义成**固定查询程序**（query program），而不是“口头描述的领域”，这样才能离线重放并审计。

**建议：每个 track 由一个 YAML 查询文件定义（可版本化）**
路径建议：`private/query_programs/track_A.yaml`、`private/query_programs/track_B.yaml`

每个 track YAML 至少包含：

* `source_priority`: `[openalex, s2]`
* `openalex.filters`: （概念/关键词/时间窗/语言/开放获取/类型）
* `s2.query`: （可选，用于补齐 paperId / 引用边）
* `time_range`: `[from, to]`（用于 temporal holdout 或 LatestEval-style “recent window” 构造，降低污染风险）
* `deterministic_paging`: `sort=publication_date:desc` + `cursor`/`page` 固定规则（OpenAlex 有文档化实体与用法）

**Track 拆分原则（强建议）**

* Track A 与 Track B 的 query program 要保证：

  * **概念集合尽量不重叠**（便于 cross-domain trend）
  * **来源/venue 分布差异明显**（让 sealing/defense 的效果更有说服力）
* 同时必须在 `docs/data_requirements.md` 写清楚：Track 的定义是“查询程序 + deterministic materialization”，而不是“主观领域”。

### 6.3 Snapshot 阶段（你应该怎么抓数据，抓到什么文件）

目标：产出 CLAIM-007 的 canonical snapshot。

#### 6.3.1 OpenAlex snapshot（推荐作为公开 registry 的基座）

OpenAlex `works` 实体字段与使用方式在官方文档中清晰定义。

**产物：**

* `private/raw_snapshots/openalex/works_track_A.jsonl`
* `private/raw_snapshots/openalex/works_track_B.jsonl`
* （可选）`private/raw_snapshots/openalex/requests_track_*.jsonl`

**works JSONL 行建议最小字段（可复现又不臃肿）：**

* `id`（OpenAlex work id）
* `doi`（如有）
* `title`
* `publication_year`
* `type`
* `primary_location.source.id`（venue/source）
* `concepts`（可只留 concept ids + scores）
* `referenced_works`（引用边骨架）
* `open_access.is_oa` + `best_oa_location.url`（若要允许用户自己取 OA PDF）
* `updated_date`（用于审计快照时间）

#### 6.3.2 S2 snapshot（补齐 paperId / 引用图 / 某些字段）

Semantic Scholar Open Data Platform 提供其学术图规模与管线说明，适合作为“为什么我们选择这些字段”的依据。

**产物（CLAIM-007 要求）：**

* `private/raw_snapshots/s2/works_track_A.jsonl`
* `private/raw_snapshots/s2/requests_track_A.jsonl`
* `private/raw_snapshots/s2/works_track_B.jsonl`
* `private/raw_snapshots/s2/requests_track_B.jsonl`

**requests JSONL** 用于证明你抓取行为（ledger）并支持 offline audit。

> 注意：S2 API 许可约束要认真遵守；如果你们未来要“公开发布包含 S2 特定字段的再分发数据”，务必先做法务/合规确认。

### 6.4 Canonicalization 阶段（paper_key、去重、映射）

这一步是全 pipeline 的“主键工程”，直接对应 CLAIM-006。

**产物：**

* `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl`

**mapping 行建议包含：**

* `paper_key`（canonical）
* `aliases`（doi/arxiv/s2/openalex）
* `title_norm` + `title_sha256_12`
* `source_confidence`（例如：doi > arxiv > s2 > openalex-fallback）
* `merge_trace`（若多个来源 merge，记录输入 keys 与优先级）

**为什么要强调去重：**
近重复文本会导致训练/评估泄漏与夸大效果，去重与重叠审计是必要的工程卫生。

### 6.5 Selection 阶段（core/extended 的机械口径）

建议把 selection 分成**两层**：

1. **候选池构建（candidate pool）**：完全自动、可复现

* 过滤：年份、类型（article/preprint）、语言、是否有关键字段（title/year/ids）
* 基础评分：引用数分位、概念匹配度、venue 质量 proxy（可选）
* 输出：`private/candidates/track_A_candidates.jsonl`（可选）

2. **入选决策（selection）**：自动 + 可审计的手工覆盖

* 自动规则决定大多数
* 少数争议由 `selection.manual_decisions_file` 输入（CLAIM-005）
* 输出：

  * `public/selection_log_core.jsonl`
  * `public/selection_log_extended.jsonl`

### 6.6 Record build（v2 paper records）阶段（公开可发布的“内容层”）

你要提前决定：公开 records 到底包含什么。建议遵循三条铁律：

1. **公开 records 不依赖任何不可公开的原文长片段**（避免版权/敏感信息风险）
2. records 必须能支撑 benchmark 的 rubric 维度（problem_shift / mechanism_class / dependency / claim_validity / ablation / clarity）
3. records 必须能被 sealed worlds 变换而不破坏 schema

**建议的公开 record schema（示例）**：

```json
{
  "paper_key":"doi:10.1145/3458723",
  "track":"A",
  "subset":"extended",
  "title":"Datasheets for Datasets",
  "year":2018,
  "venue":"Communications of the ACM",
  "ids":{"doi":"10.1145/3458723","openalex":"https://openalex.org/W...","s2":"..."},
  "taxonomy_tags":{
    "mechanism_class":["documentation","governance"],
    "problem_shift":["evaluation_reliability"]
  },
  "claims":[
    {"claim_id":"c1","text":"...short paraphrase...","support_level":"metadata_only"}
  ],
  "dependencies":[
    {"src":"paper_key","dst":"paper_key","type":"cites"}
  ],
  "build_meta":{
    "record_version":"v2",
    "source_priority":["openalex","s2"],
    "determinism":{"seed":42,"canonical_json":true}
  }
}
```

> 这里的 `claims[*].text` 明确建议用“短释义/短摘要式 paraphrase”，而不是复制论文摘要或原句，以便公开发布更稳妥。

### 6.7 Sealed worlds 生成（multi-seed）

**目标：**为每个 seed 生成一份公开 records（sealed）与私有 codebook（不导出）。
这与“防污染、防泄漏”动机一致：公开部分即使被爬走，也不应让模型直接记住可反推出原始敏感映射的内容。类似“不要以明文上传测试集”的思路。

**公开产物：**

* `public/sealed_worlds/{seed}/{core,extended}/records.jsonl`
* `public/sealed_worlds/{seed}/manifest.json`

**私有产物：**

* `private/sealed_codebooks/{seed}/{core,extended}.sealed.codebook.json`
* 仅在 `dataset_manifest.json` 中记录 sha256，不复制文件。

---

## 7. What the dataset will look like (目录、文件内容、大小预期)

### 7.1 Canonical export tree（你最终应该看到的目录）

```
runs/exports/{dataset_version}/
  public/
    dataset_manifest.json
    taxonomy.json
    track_A_core_records.jsonl
    track_A_extended_records.jsonl
    track_B_core_records.jsonl
    track_B_extended_records.jsonl
    dependency_graph_core.edgelist
    dependency_graph_extended.edgelist
    selection_log_core.jsonl
    selection_log_extended.jsonl
    qa_report_core.jsonl
    qa_report_extended.jsonl
    sdg_configs/
      sdg.json
    sealed_worlds/
      11/
        core/records.jsonl
        extended/records.jsonl
        manifest.json
      23/...
      42/...
    attack_suite/
      README.md
  private/
    raw_snapshots/
      s2/
        works_track_A.jsonl
        requests_track_A.jsonl
        works_track_B.jsonl
        requests_track_B.jsonl
      openalex/
        works_track_A.jsonl
        works_track_B.jsonl
    mapping_key/
      paper_id_map_track_A_core.jsonl
      paper_id_map_track_A_extended.jsonl
      paper_id_map_track_B_core.jsonl
      paper_id_map_track_B_extended.jsonl
    sealed_codebooks/
      11/core.sealed.codebook.json
      11/extended.sealed.codebook.json
      ...
```

### 7.2 文件规模（给你一个“可以落地的默认目标”，并附可扩展公式）

你问“预期大小如何”，这里给一个**默认 v2 目标规模**（你可以之后调参扩大）：

* 每 track：

  * `core`: **300** records
  * `extended`: **1000** records
* seeds：**3**（例如 11/23/42，满足 ORAL-001 的 3 seeds）
* 合计公开 records：`(300+1000)*2 tracks = 2600`（非 sealed）
* sealed worlds 公共 records：`2600 * 3 seeds = 7800`

**粗略磁盘估算（JSONL 典型大小范围）**

* public 原始 records：约 1.8KB/record（含 tags/依赖/少量 claims 的短释义）
* sealed records：约 2.2KB/record（多一点 sealed 字段/校验字段）

按上述默认：

* public 非 sealed records：`2600 * 1.8KB ≈ 4.7MB`
* sealed worlds records：`7800 * 2.2KB ≈ 16.4MB`
* taxonomy/graphs/logs/manifest 合计：通常 < 5MB（取决于依赖边数量）

> **因此默认公开包通常在 ~20–30MB 量级**（非常好发布、也利于复现实验）。

**private 体量（取决于候选池规模）**

* 假设每 track 候选池抓取 50k works（OpenAlex/S2 综合），每条 work snapshot 平均 4.5KB：

  * `50k * 4.5KB ≈ 215MB`/track
  * 两 track ≈ 430MB
* requests ledger 通常几 MB 级

> **因此 private 目录通常在 ~0.3–1.0GB 量级**（主要由 snapshot 决定）。

### 7.3 攻击/审计输出的预期结构（ORAL-002 等）

建议固定攻击报告 JSON schema（这样对外讲清楚）：

```json
{
  "dataset_version":"v2.0.0",
  "track":"A",
  "seed":11,
  "variant":"sealed",
  "black_box":{
    "top1_success_rate":0.12,
    "budget_curve":{"budgets":[1,2,5,10],"top1":[0.02,0.04,0.09,0.12]},
    "notes":"..."
  },
  "white_box":{
    "codebook_recovery_rate":0.03,
    "prompt_leakage_asr":0.05
  },
  "provenance":{"script":"provetok/scripts/run_oral_budget_attack.py","sha256":"..."}
}
```

---

## 8. Attack suite documentation (public/attack_suite/README.md 应该写什么)

`public/attack_suite/README.md` 必须明确“这里只是文档”，并指向 repo 脚本（CLAIM-008）。

建议 README 至少包含：

1. 目录说明：此目录不含可执行脚本
2. 运行前提：需要 repo checkout + python env
3. 典型命令（模板）：

* 黑盒审计（示例）：

  * `python provetok/scripts/run_audit_v2.py --dataset runs/exports/v2.0.0/public --track A --seed 11 --out runs/attacks/A_11.json`
* 白盒审计（示例，若需要 private codebook）：

  * `python provetok/scripts/run_oral_whitebox_defense.py --public runs/exports/v2.0.0/public --private runs/exports/v2.0.0/private --out runs/EXP-016/summary.json`

并在 README 里解释 black-box/white-box 的假设与指标——可以引用已有 prompt leakage / prompt injection / privacy auditing 相关研究来“站稳”威胁模型。

---

## 9. Related Work / Evidence Library (尽可能多的“支撑文章”，按主题分组)

> 你说“越多越好”，我这里给你两层：
> (A) **强相关核心必读**（直接支撑你们的动机/方法/威胁模型/工程选择）
> (B) **扩展库**（更多论文索引与持续更新列表）

### 9.1 核心：数据集/模型的可审计文档标准（你们“公开 artifacts + manifest”的理论根）

* Datasheets for Datasets (Gebru et al.)
* Data Statements for NLP (Bender & Friedman)
* Model Cards for Model Reporting (Mitchell et al.)
* Dataset Nutrition Label (Holland et al.)

### 9.2 核心：污染（contamination）与“不要明文发布测试集”（你们 sealed worlds 的关键动机）

* Stop Uploading Test Data in Plain Text (Jacovi et al., EMNLP 2023)
* LatestEval (Li et al., dynamic/time-sensitive)
* LiveCodeBench (continuous, contamination-free style)
* ConStat contamination detection (Dekoninck et al., 2024)
* Benchmark Data Contamination Survey (Xu et al., 2024)
* “Static → Dynamic evaluation” survey / trend summary

### 9.3 核心：训练数据记忆与可提取泄漏（你们 audit / attack suite 的必要性）

* Extracting Training Data from Large Language Models (Carlini et al., USENIX Sec 2021)
* Scalable Extraction from (Production) Language Models (Nasr et al., 2023)
* Membership inference attacks against LMs (Mattern et al., 2023)
* Privacy Auditing of Large Language Models (Panda et al., 2025)
* Deduplicating Training Data Makes LMs Better (Lee et al.)
* Measuring memorization via extraction-style methods (NAACL 2025)

### 9.4 核心：评测框架与“可复现 harness”（你们 `provetok run` 的工程类比）

* Language Model Evaluation Harness (lm-eval) paper (Biderman et al., 2024)
* lm-evaluation-harness repo (EleutherAI)
* HELM (Holistic Evaluation of Language Models)
* MMLU
* BIG-bench
* TruthfulQA

### 9.5 Scholarly graph / metadata sources（你们 snapshot 的数据源“站得住”）

* OpenAlex paper (Priem et al., 2022)
* OpenAlex Works entity docs
* OpenAlex CC0 license statement
* Semantic Scholar Open Data Platform (S2AG)
* Semantic Scholar API docs
* S2ORC (Lo et al., 2020)
* S2ORC license note

### 9.6 扩展库（更多论文索引，方便你继续“越多越好”）

* “awesome-data-contamination” 持续更新的污染/泄漏论文列表（非常适合你们扩写 related work）
* LLM security & privacy survey（大综述，适合写威胁模型与攻击面）
* Text watermarking survey / Nature watermarking work（若你们后续考虑“标记/追踪泄漏”方向）

---

## 10. Change Log (before/after, do not delete)

（你原文完整保留，略）
