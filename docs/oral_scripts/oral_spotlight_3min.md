# Spotlight Script (~3 min) — vNext

Constraint: 3 slides, no jargon, each claim points to a file path.

## Slide 1 (0:00–0:50) Problem + Setup

One sentence:
“We want sealed benchmarks that reduce leakage without destroying utility, and we explicitly quantify white-box limits.”

Threat model:
- black-box (no codebook)
- white-box (has codebook)

Evidence pointer:
- `docs/claim_evidence.md`

## Slide 2 (0:50–2:10) Main Result (Scale) + Baselines

Show a small table screenshot from:
- `runs/EXP-022/main_results.md`

Say:
- Utility ~ raw at scale (see `runs/EXP-022/summary.json`).
- Black-box leakage improves vs raw.
- White-box remains hard (we do not hide this).
- Added simple baselines (summary, redaction) to sanity-check fairness.

## Slide 3 (2:10–3:00) Tradeoff Curve + Close

Show the plot:
- `runs/EXP-023/tradeoff_curve.png`

Say:
- Defense strength gives a utility-vs-leakage curve (knee point).
- Shipping decision is explicit: recommended `level=2` (see `runs/EXP-033/recommended_config.json`).
- We keep human-eval agreement explicit and do not over-claim:
  - `runs/EXP-024/human_eval_report.json`
- Failure-first: budget attacks can still be strong:
  - `runs/EXP-029/budget_curves.png`

Close:
“Reproducible artifacts, honest threat models, and explicit limitations.”
