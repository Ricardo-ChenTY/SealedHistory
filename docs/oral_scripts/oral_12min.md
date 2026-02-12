# Oral Script (12 min) — vNext

This is a time-boxed talk script designed to survive Q&A by always pointing to a concrete artifact path.

Key artifacts:
- Scale main table: `runs/EXP-022/main_results.csv`, `runs/EXP-022/main_results.md`, `runs/EXP-022/summary.json`
- Defense tradeoff curve: `runs/EXP-023/tradeoff_curve.png`, `runs/EXP-023/tradeoff_curve.json`
- Recommended config (knee): `runs/EXP-033/recommended_config.json`
- Budget curves (failure-first): `runs/EXP-029/budget_curves.png`
- LLM attacker calibration (proxy sanity): `runs/EXP-032/summary.json`
- Human agreement: `runs/EXP-024/human_eval_report.json`
- Claim→evidence map: `docs/claim_evidence.md`

## 0:00–0:45 Problem

1. Sealed benchmarks aim to reduce contamination/leakage, but must remain useful.
2. The core question: can we reduce black-box leakage without destroying utility, and be honest about white-box limits?

## 0:45–2:30 Setup / Threat Model

Threat models (show as one slide):
- Black-box: sees sealed public text only.
- White-box: additionally has the codebook mapping.
- Budgeted: attacker increases budget; we report curves.

Evidence pointer:
- Micro evidence chain: `runs/EXP-011..020/`
- Scale evidence chain: `runs/EXP-021..024/` (maintainer build) + public repro bundle `runs/EXP-031/public/`

## 2:30–5:30 Main Result (Scale, Non-toy)

Show `runs/EXP-022/main_results.csv` (one row highlight):
- Utility stays close to raw on scale data (see `runs/EXP-022/summary.json` → `main_vs_raw.utility_gap_raw_minus_main`).
- Black-box leakage improves vs raw (see `runs/EXP-022/summary.json` → `black_box_leakage_gap_raw_minus_main`).
- White-box leakage is not solved by sealing alone (see `runs/EXP-022/main_results.csv` → `leakage_white_box`).

Clarify fairness:
- Same rubric + same offline attack protocol across baselines.
- Added simple baselines:
  - extractive summary baseline
  - naive redaction baseline

## 5:30–7:30 The Tradeoff (Defense Knob Curve)

Show plot `runs/EXP-023/tradeoff_curve.png`.

Explain:
- Increasing defense strength can reduce black-box leakage sharply.
- Utility retention degrades after a point (knee).
- White-box remains the hardest case; we keep it explicit.

Make the shipping decision explicit:
- Recommend `level=2` (knee) under the default black-box narrative.
- If you need black-box leakage=0, the lowest level is `level=4` with a large utility hit (see `runs/EXP-033/recommended_config.json`).

## 7:30–9:00 Human Evidence (Agreement, Not Over-claimed)

Show `runs/EXP-024/human_eval_report.json`:
- `cohen_kappa` and `krippendorff_alpha_nominal_binary` are low.

Narrate the consequence:
- Human eval is treated as *risk-bearing* evidence unless we add raters/training.
- Protocol is documented in `docs/human_eval_protocol.md`.

## 9:00–10:30 Limitations / Negative Impacts

Use a “failure-first” slide:
- White-box remains high.
- Budgeted attacks are strong in many settings.
- Human agreement is low on the current sheet.

Show the actual budget curve plot:
- `runs/EXP-029/budget_curves.png`

Mitigations:
- Scope claims to black-box where appropriate.
- Publish an explicit misuse note and keep codebooks private.

## 10:30–12:00 Repro + Close

One command chain (scale):
```bash
SCALE_DATASET_DIR="runs/EXP-031/public"  # public repro bundle (no internal exports)

./.venv/bin/python provetok/scripts/run_oral_main_table_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-022 --seeds 11 22 33

./.venv/bin/python provetok/scripts/run_oral_defense_knob_sweep_vnext.py \
  --dataset_dir "$SCALE_DATASET_DIR" --output_dir runs/EXP-023 --seeds 11 22 33
```

Close with: “black-box gains + explicit white-box limits + reproducible artifacts.”
