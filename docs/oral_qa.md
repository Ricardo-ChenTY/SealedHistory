# Oral Q&A Prep (vNext)

Each answer is anchored to an artifact path so we can “show, not tell”.

## Q1. What is your main claim in one sentence?

We can reduce black-box leakage while keeping utility near raw, but white-box leakage remains a hard limit and we quantify the tradeoff.

Artifacts:
- `runs/EXP-022/summary.json`
- `runs/EXP-023/tradeoff_curve.png`

## Q2. Is this just a toy demo?

No: we also run a scale (non-toy) dataset pipeline and rerun the oral table and attacks there.

Artifacts:
- `runs/EXP-031/public/public_dataset_manifest.json` (public repro bundle manifest)
- (maintainer-only provenance) `runs/EXP-021/dataset/dataset_manifest.json` (n_items, bytes, elapsed)
- `runs/EXP-022/main_results.csv`

## Q3. How do you define “leakage”?

Offline lexical proxies: Jaccard retrieval (top1/top3) + keyword recovery; we report black-box vs white-box.

Artifacts:
- `provetok/scripts/run_oral_adaptive_attack_vnext.py`
- `runs/EXP-022/attacks/`

## Q4. Why should I trust these attacks (LLM attacker)?

We run deterministic heuristic proxies for reproducibility, and we additionally calibrate the proxy with an LLM-backed term-recovery attacker (hit@1/hit@3) to check for “easy inversion” beyond the proxy.

Artifacts:
- `runs/EXP-032/summary.json`
- `docs/oral_limitations_negative_impacts.md`

## Q5. What happens under white-box?

White-box remains high in most settings; that is presented as a limitation, not hidden.

Artifacts:
- `runs/EXP-022/main_results.csv`
- `runs/EXP-023/tradeoff_curve.json`

## Q6. What is the best baseline comparison?

We include transparent baselines like extractive summary and naive redaction, and we keep the same rubric/attack protocol.

Artifacts:
- `runs/EXP-022/main_results.csv` (`sealed_summary_frontier`, `sealed_redact_frontier`)

## Q7. What is the cost?

We persist elapsed time + memory for key runs.

Artifacts:
- `runs/EXP-022/run_meta.json`
- `runs/EXP-023/run_meta.json`
- `runs/EXP-021/dataset/dataset_manifest.json`

## Q8. Why is human evaluation credible if agreement is low?

It is not claimed as a strong result yet; we explicitly report agreement and mark it as risk-bearing until we add raters/training.

Artifacts:
- `runs/EXP-024/human_eval_report.json`
- `docs/human_eval_protocol.md`

## Q9. How is the dataset released safely?

We separate public exports from private snapshots/codebooks and do not ship private codebooks in exports.

Artifacts:
- `runs/exports/0.2.0-legacy/public/dataset_manifest.json`
- `runs/EXP-010/demo_codebook_policy.log`

## Q10. Can I reproduce everything from a fresh checkout?

Yes for the documented baseline experiments; scale/oral vNext runs can be reproduced from the exported public bundle (white-box results still require private codebooks). Maintainer-only internal rebuild still requires the internal v2 JSONL source files.

Artifacts:
- `docs/reproducibility_statement.md`
- `docs/experiment.md`
