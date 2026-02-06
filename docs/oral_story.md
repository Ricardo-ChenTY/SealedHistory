# Oral Story Pack (2026-02-06)

## 1) One-Sentence Claim

Under 3 seeds × 2 tracks, the SealedHistory main setup keeps utility close to raw (`Δutility = 0.0094`) while reducing black-box leakage (`Δleakage = -0.2001`), but remains vulnerable under stronger white-box assumptions.

## 2) Threat Model

```text
Data publisher -> releases public sealed records
                -> keeps private codebook internal

Attacker A (black-box):
  - sees: sealed public records only
  - goal: recover raw identity/terms/timeline

Attacker B (white-box):
  - sees: sealed records + codebook mapping
  - goal: same as A, but with stronger side information
```

Evaluation mapping:
- Black-box metrics: `runs/EXP-011/attacks/*_sealed.json` (`black_box.*`)
- White-box metrics: `runs/EXP-011/attacks/*_sealed.json` (`white_box.*`)

## 3) Failure Cases

1. White-box vulnerability remains high.
   - Evidence: `runs/EXP-014/cross_domain_summary.json` (`trend_holds_all_tracks_white_box=false`).
2. Track-level record identity leakage is still strong in black-box retrieval.
   - Evidence: `runs/EXP-011/attacks/A_sealed.json` (`retrieval_top1=1.0`).
3. Human agreement is moderate rather than high.
   - Evidence: `runs/EXP-015/human_eval_report.json` (`cohen_kappa=0.5714`).

## 4) Statistical Rigor

- Main table uses 3 random seeds (`11,22,33`) × 2 tracks (A/B), aggregated as mean±std.
- Sources:
  - per-run metrics: `runs/EXP-011/per_run_metrics.json`
  - aggregated table: `runs/EXP-011/main_results.csv`
  - cross-domain rollup: `runs/EXP-014/cross_domain_summary.json`
  - human agreement: `runs/EXP-015/human_eval_report.json`
- Current limitation:
  - No significance test is reported yet (only descriptive mean±std).

## 5) Reproducibility & Ethics

Repro commands:
```bash
python provetok/scripts/run_oral_main_table.py --output_dir runs/EXP-011 --seeds 11 22 33
python provetok/scripts/run_oral_ablations.py --output_dir runs/EXP-013 --seeds 11 22 33
python provetok/scripts/run_oral_cross_domain.py --input runs/EXP-011/per_run_metrics.json --output_dir runs/EXP-014
python provetok/scripts/compute_human_eval_kappa.py --ratings_csv docs/templates/human_eval_sheet.csv --output_dir runs/EXP-015
```

Ethics and misuse notes:
- Demo codebooks remain synthetic and are documented in `provetok/data/sealed/README.md`.
- White-box results are reported explicitly to avoid overstating security guarantees.
- Human evaluation requires anonymized reviewer IDs and stored rating sheets.
