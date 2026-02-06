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
