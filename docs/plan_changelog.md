# Plan Changelog

## 2026-02-06
- Decision: No `docs/plan.md` rewrite needed.
- Reason: `docs/claim_evidence.md` shows CLAIM-001..009 are all fully supported by rerun evidence (`EXP-001..010`).
- Evidence snapshot:
  - `runs/EXP-001` .. `runs/EXP-010`
  - `runs/exports/0.2.0-legacy/`

## 2026-02-06 (Oral Addendum)
- Decision: Added ORAL-001..005 addendum claims to `docs/plan.md`.
- Reason: Needed executable evidence chain for oral readiness (main table, adaptive attacks, ablations, cross-domain, human-eval consistency).
- Evidence snapshot:
  - `runs/EXP-011/` (main table + adaptive attacks)
  - `runs/EXP-013/` (ablations)
  - `runs/EXP-014/` (cross-domain summary)
  - `runs/EXP-015/` (human-eval agreement tooling output)
- Current residual gaps:
  - None after scope-aligned ORAL-004 acceptance and dual-rater ORAL-005 evidence fill.

## 2026-02-06 (ABC Rerun)
- Decision: No additional `docs/plan.md` rewrite needed.
- Reason: Full rerun of `EXP-001..015` keeps claim verdicts unchanged (`CLAIM-001..009` and `ORAL-001..005` all supported).
- Evidence snapshot:
  - `runs/EXP-007/pytest.log`
  - `runs/EXP-011/main_results.md`
  - `runs/EXP-014/cross_domain_summary.json`
  - `runs/EXP-015/human_eval_report.json`

## 2026-02-06 (Oral vNext Closure)
- Decision: Extended oral addendum with ORAL-006..010; no rollback of existing ORAL-001..005 claims.
- Reason: Needed “冲顶会 oral” minimum decisive closure for defense tradeoff, significance, budgeted attacks, holdout generalization, and scaled human-eval agreement.
- Evidence snapshot:
  - `runs/EXP-016/summary.json`
  - `runs/EXP-017/summary.json`
  - `runs/EXP-018/budget_curves.json`
  - `runs/EXP-019/summary.json`
  - `runs/EXP-020/human_eval_report.json`
- Residual risk notes retained in docs:
  - holdout Track B black-box trend is non-improving (`runs/EXP-019/summary.json`)
  - scaled human-eval kappa remains low (`runs/EXP-020/human_eval_report.json`)

## 2026-02-10 (ABC Rerun)
- Decision: No `docs/plan.md` rewrite needed.
- Reason: Reran `EXP-001..020` + `pytest`; claim verdicts remain supported and evidence docs were refreshed (`docs/experiment.md`, `docs/verify_log.md`, `docs/claim_evidence.md`).
- Evidence snapshot:
  - `runs/EXP-005/gate_no_try.log`
  - `runs/EXP-007/pytest.log`
  - `runs/exports/0.2.0-legacy/public/dataset_manifest.json`
  - `runs/EXP-011/summary.json`
  - `runs/EXP-016/summary.json`
  - `runs/EXP-019/summary.json`
- Notes:
  - ORAL-009 holdout now reports `black_box_trend_holds_all_tracks=true` with `avg_utility_retention=0.9382` (`runs/EXP-019/summary.json`); the 2026-02-06 Track B note above is historical.

## 2026-02-11 (Scale Evidence Map)
- Decision: Updated `docs/plan.md` Evidence Map so oral claims explicitly point to both micro and scale artifacts (micro mechanism + non-toy scale replication).
- Reason: Oral/paper narrative requires micro-history diagnostics AND scale replication for the same analysis blocks (ablations/cross-domain/defense/stats/budget/holdout).
- Evidence snapshot:
  - `runs/EXP-021/dataset/dataset_manifest.json`
  - `runs/EXP-022/main_results.csv`
  - `runs/EXP-023/tradeoff_curve.json`
  - `runs/EXP-025/ablation_results.csv`
  - `runs/EXP-026/cross_domain_summary.json`
  - `runs/EXP-027/summary.json`
  - `runs/EXP-028/summary.json`
  - `runs/EXP-029/budget_curves.json`
  - `runs/EXP-030/summary.json`

## 2026-02-11 (ArXiv-Aligned Oral Closure)
- Decision: No `docs/plan.md` rewrite needed; extended evidence mapping with ORAL-011..015 supported by full runs.
- Reason: `EXP-034..038` all completed with `Smoke=[x], Full=[x]` and machine-checkable summary/run_meta artifacts.
- Evidence snapshot:
  - `runs/EXP-034/summary.json`
  - `runs/EXP-035/summary.json`
  - `runs/EXP-036/summary.json`
  - `runs/EXP-037/summary.json`
  - `runs/EXP-038/summary.json`
- Notes:
  - Updated `docs/experiment.md` mapping states ORAL-011..015 as evidenced.
  - Added ORAL-011..015 rows to `docs/claim_evidence.md` with concrete metric summaries.

## 2026-02-11 (Plan Evidence Map: ORAL-011..015)
- Rationale: User requested formal inclusion of the new arXiv-aligned oral items in `docs/plan.md` Claim/Evidence Map after full runs completed.
- Changes:
  - Before: >
      `docs/plan.md` Evidence Map ended at ORAL-010 and did not define measurable checks for ORAL-011..015.
  - After: >
      Added ORAL-011..015 entries to `docs/plan.md` Evidence Map, each with explicit Metrics/Checks and direct artifact keys/paths mapped to `EXP-034..038`.
- Evidence snapshot:
  - `runs/EXP-034/summary.json`
  - `runs/EXP-035/summary.json`
  - `runs/EXP-036/summary.json`
  - `runs/EXP-037/summary.json`
  - `runs/EXP-038/summary.json`

## 2026-02-11 (Validity / ORAL-016)
- Decision: Added ORAL-016 validity item to `docs/plan.md` and closed it with a runnable invariance experiment (`EXP-039`).
- Reason: Address “validity / metadata shortcut” criticism by measuring raw↔sealed ordering invariance and including metadata-only / structure-only sanity baselines.
- Evidence snapshot:
  - `runs/EXP-039/summary.json`
  - `runs/EXP-039/run_meta.json`

## 2026-02-11 (ORAL-016: LLM Validity / Invariance)
- Decision: Added `EXP-040` as additional evidence for ORAL-016.
- Reason: Re-check invariance + shortcut baselines with a temperature-0 LLM proposer across raw/sealed/structure_only/metadata_only views (not only heuristic agents).
- Evidence snapshot:
  - `runs/EXP-040/summary.json`
  - `runs/EXP-040/run_meta.json`

## 2026-02-12 (ORAL-017: Linkability / Re-identification)
- Decision: Added ORAL-017 and implemented a TF-IDF re-identification diagnostic (`EXP-041`) across public release variants.
- Reason: Make “公开 sealed 是否可被链接回原始条目？”可量化（hit@k/MRR/mean rank），补齐 threat model 的可检验安全性论证入口。
- Evidence snapshot:
  - `runs/EXP-041c/summary.json`
  - `runs/EXP-041c/run_meta.json`
