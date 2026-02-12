# Human Eval Protocol (vNext)

Goal: make the human-eval evidence *auditable* and *defensible* in oral/Q&A (not just “the script runs”).

This repo stores human ratings as a CSV:
- Template/example: `docs/templates/human_eval_sheet.csv`
- Agreement metrics: `provetok/scripts/compute_human_eval_kappa.py`

## 1. What To Rate

Each `item_id` corresponds to one evaluated proposal/run fragment (see `proposal_id`, `track_id`, `config_id`).

Raters score the 6 rubric dimensions plus an `overall` score in `[0,1]`:
- `problem_shift`
- `mechanism_class`
- `dependency`
- `claim_validity`
- `ablation`
- `clarity`
- `overall`

## 2. Rater Training (Minimum)

1. Read 10 calibration examples together (mix of accept/reject).
2. Agree on interpretation for each dimension:
   - what constitutes “good enough” vs “clearly failing”
3. Align on the `overall` threshold used for binary agreement metrics:
   - default threshold in tooling: `0.5`
4. Record any special instructions in the `notes` column (e.g., “treat missing ablations as 0”).

## 3. Sampling + Blinding

Recommended:
- Randomly sample items across tracks/configs (do not only sample best-case).
- Shuffle row order for each rater so they cannot infer track/config from adjacency.
- Keep raters blind to each other’s ratings until after the first pass.

## 4. Required Rater Count

For “顶会 oral 可信度” targets:
- Prefer `>= 3` raters (or keep 2 raters but add a strict calibration/training log and treat agreement as risk-bearing).

## 5. How To Add New Raters

Add additional rows with a new `rater_id` (e.g., `r3`) for the same `item_id`s.

## 6. Agreement Metrics (What We Report)

The tool outputs:
- Cohen’s kappa for a chosen rater pair (default: the two raters with most rows)
- Krippendorff’s alpha (nominal, binary) over *all* raters
- Continuous agreement diagnostics on `overall` (pairwise): Pearson/Spearman correlation, mean absolute diff, and how many items fall near the decision threshold (to explain low kappa when many items sit near the cutoff).

Run:

```bash
./.venv/bin/python provetok/scripts/compute_human_eval_kappa.py \
  --ratings_csv docs/templates/human_eval_sheet.csv \
  --output_dir runs/EXP-024 \
  --threshold 0.5
```

Artifacts:
- `runs/EXP-024/human_eval_report.json`
- `runs/EXP-024/human_eval_report.md`
