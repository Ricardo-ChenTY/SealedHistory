# Oral Limitations & Negative Impacts (vNext)

This page is intended to prevent “over-claiming” in oral and to give reviewers a clear place to audit limitations.

## Limitations (3–5)

1. White-box threat model is not solved by sealing alone.
   - Evidence: `runs/EXP-022/main_results.csv` (white-box leakage remains high for most setups).
2. Budgeted / adaptive attacks can remain strong even after defenses.
   - Evidence: `runs/EXP-023/tradeoff_curve.json` (utility-vs-leakage curve shows tradeoffs; no free lunch).
3. Human-eval agreement is low on the current sheet.
   - Evidence: `runs/EXP-024/human_eval_report.json` (`cohen_kappa`, `krippendorff_alpha_nominal_binary`).
4. Leakage metrics are offline lexical proxies (Jaccard retrieval + keyword recovery), not a full LLM attacker.
   - Evidence: `provetok/scripts/run_oral_adaptive_attack_vnext.py` (explicitly heuristic).
5. Data licensing constraints limit what can be redistributed (snapshots/codebooks must remain private).
   - Evidence: dataset export structure under `runs/exports/**/public` vs `private`.

## Potential Negative Impacts / Misuse (2–3)

1. De-anonymization guidance could be misused to attack “sealed” releases.
   - Mitigation: keep private codebooks internal; publish only public artifacts; keep attacks as documentation and require explicit opt-in to run LLM-backed attacks.
2. False sense of security: readers may assume sealing provides privacy guarantees.
   - Mitigation: present results as empirical leakage audits, always include white-box/budgeted failure cases.
3. Dataset collection could inadvertently include copyrighted or restricted text.
   - Mitigation: keep raw fulltext snapshots private by default; document provenance; enforce conservative export rules.

## Mitigation Checklist (For Slide/Q&A)

- Explicit threat models: black-box vs white-box vs budget.
- Explicit failure-first slide (white-box + human-eval agreement).
- Reproducible artifacts with deterministic paths (`runs/EXP-*`).
- Clear separation of public vs private exports.

