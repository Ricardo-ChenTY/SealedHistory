# Mohu

## Missing
- [x] Missing-001: Create a single-source backlog (`docs/mohu.md`)
  - Location: `docs/mohu.md`
  - Acceptance: File exists with Missing/Ambiguous/Log; future gap tracking updates this file (IDs are stable).
  - Evidence: No `docs/mohu.md` existed before this change.
  - Notes:

- [x] Missing-002: Online build can require a real LLM (strict paraphrase; no key => fail)
  - Location: `provetok/src/provetok/dataset/pipeline.py`, `provetok/src/provetok/dataset/record_builder.py`
  - Acceptance: When enabled, missing `LLM_API_KEY` (or configured env var) fails the online build with a clear error.
  - Evidence: `record_build.require_llm=true` now errors early when the API key/client is missing.
  - Notes: Enforced via `record_build.require_llm` + `LLMClient.is_configured()`.

- [x] Missing-003: Strict paraphrase validation + retry/exclude/backfill
  - Location: `provetok/src/provetok/dataset/record_builder.py`, `provetok/src/provetok/dataset/pipeline.py`, `provetok/src/provetok/dataset/qa.py`
  - Acceptance: Public `background` must be paraphrase; forbidden fingerprints (URL/DOI/arXiv/year/venue/etc) trigger retry; persistent failure => exclude and backfill to hit target sizes.
  - Evidence: Strict mode now retries LLM extraction and raises on policy failure; pipeline excludes failed rows and backfills from a larger OpenAlex pool.
  - Notes: Implemented with `record_build.strict_paraphrase` + `record_build.max_retries` + pool backfill in online pipeline.

- [x] Missing-004: Strict fulltext policy (Extended/Core must download successfully; missing => exclude/backfill)
  - Location: `provetok/src/provetok/dataset/fulltext.py`, `provetok/src/provetok/dataset/pipeline.py`
  - Acceptance: When enabled, `fulltext_index_{core,extended}.jsonl` has no `missing`/`error:*` for selected papers; failures are excluded and replaced until targets are met (or a controlled shortfall is reported).
  - Evidence: Online selection now requires successful downloads when `fulltext.*.require_success=true`; failures are excluded and replaced from the candidate pool.
  - Notes: arXiv source is best-effort; PDF download is the success requirement; arXiv failure falls back to `author_pdf_url` when policy allows.

- [x] Missing-005: Selection log records *all* excludes with reason tags (esp. fulltext/paraphrase failures)
  - Location: `provetok/src/provetok/dataset/pipeline.py`
  - Acceptance: `public/selection_log_{core,extended}.jsonl` contains both `include` and `exclude` events with stable `reason_tag` + evidence.
  - Evidence: Online pipeline now emits `exclude_fulltext_*` and `exclude_record_build_failed` rows (plus core subset include/exclude).
  - Notes:

- [x] Missing-006: Export final paper lists per track (`track_{A,B}_papers.jsonl`)
  - Location: `provetok/src/provetok/dataset/pipeline.py`, `provetok/src/provetok/dataset/paths.py`
  - Acceptance: Export per-track final selection lists including `paper_id` and internal IDs (OpenAlex/DOI/arXiv/S2) and timestamps (private).
  - Evidence: `private/track_{A,B}_papers.jsonl` is now exported per build.
  - Notes:

- [x] Missing-007: Integrate OpenCitations into the online pipeline with snapshot logging
  - Location: `provetok/src/provetok/sources/opencitations_client.py`, `provetok/src/provetok/dataset/pipeline.py`
  - Acceptance: `private/raw_snapshots/opencitations/requests_track_{A,B}.jsonl` exists and records best-effort citation responses/errors.
  - Evidence: Online pipeline now calls OpenCitations `references()` for core DOIs (configurable), with SnapshotWriter logs.
  - Notes:

- [x] Missing-008: Compute cross-source edge coverage/agreement (OpenAlex/S2/OpenCitations) and report in manifest
  - Location: (new) `provetok/src/provetok/dataset/edge_agreement.py`, `provetok/src/provetok/dataset/build.py`
  - Acceptance: `public/dataset_manifest.json` includes edge counts + overlap metrics + coverage rates; optionally gate via thresholds.
  - Evidence: Build now computes `edge_agreement` for core/extended and writes it into the public manifest.
  - Notes:

- [x] Missing-009: Make QA thresholds enforceable (fail build when thresholds not met)
  - Location: `provetok/src/provetok/dataset/build.py`, `provetok/src/provetok/dataset/qa.py`
  - Acceptance: When enabled, schema/consistency/edge-coverage thresholds produce non-zero exit/failure with a clear reason recorded in the manifest.
  - Evidence: Build now enforces schema/consistency rates and (when cross-source edges exist) core edge-coverage threshold.
  - Notes:

- [x] Missing-010: Upgrade `taxonomy.json` beyond a scaffold, and enforce tags belong to taxonomy
  - Location: `provetok/src/provetok/dataset/legacy.py`, `provetok/src/provetok/dataset/record_builder.py`
  - Acceptance: Taxonomy includes defined tag sets; record builder restricts/normalizes tags; QA reports `other_ratio` and can gate it for Core.
  - Evidence: Current taxonomy is mostly `unknown_*` / `other`.
  - Implementation:
    - Expanded `default_taxonomy()` (version=2) with a non-trivial starter taxonomy + aliases.
    - Normalized `mechanism_tags` to taxonomy vocab in `build_record_v2_from_abstract(..., taxonomy=...)` (unknown/out-of-taxonomy → `other`).
    - Added optional Core-only QA gate `qa.taxonomy_other_ratio_max_core` (disabled by default).
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-011: Build `formula_graph` from arXiv sources + maintain `manual_formula_queue`
  - Location: (new) `provetok/src/provetok/dataset/formula_graph.py`, `provetok/src/provetok/dataset/pipeline.py`
  - Acceptance: For arXiv-source papers, `formula_graph` is non-empty for a meaningful subset; failures are appended to `private/manual_formula_queue.jsonl` with reasons and reported in manifest.
  - Evidence: Current `formula_graph` is always empty and there is no failure queue.
  - Implementation:
    - Added best-effort TeX formula extraction (`provetok/src/provetok/dataset/formula_graph.py`) and populate `public.formula_graph` for arXiv-source rows.
    - Append extraction failures to `private/manual_formula_queue.jsonl` with reason + source paths.
    - Report aggregated extraction status in `public/dataset_manifest.json` (`formula_graph.*`).
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-012: Add field-level provenance (at least source type + snapshot references)
  - Location: `provetok/src/provetok/dataset/pipeline.py`, `provetok/src/provetok/dataset/record_builder.py`
  - Acceptance: Provenance includes `abstract_source` and `fulltext_source` and links to raw snapshot request logs (by sha256 or URL).
  - Evidence: `abstract_source` and `fulltext_source` are now added for online builds.
  - Notes: Still missing snapshot references (e.g., request-log sha256) in public provenance.
  - Implementation:
    - Added `provenance.snapshot_refs` with `openalex_work_sha256` and (when available) `s2_meta_sha256` for online builds.
    - Added an offline-online integration test to ensure `snapshot_refs` is present without network.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`

- [x] Missing-013: Expand v2 attack suite with a time-index/canonical-order test (script + docs)
  - Location: `provetok/src/provetok/dataset/audit_v2.py`, `provetok/scripts/run_audit_v2.py`, `provetok/src/provetok/dataset/attack_suite.py`
  - Acceptance: `public/attack_suite/` documents a runnable command producing metrics for at least one additional order/time-based test.
  - Evidence: Current v2 suite has term recovery + order bias proxy only.
  - Implementation:
    - Added `TimeIndexPairwiseAttackV2` (pairwise "which comes earlier" accuracy) and wired it into `run_audit_v2.py`.
    - Updated public `attack_suite/README.md` template to document new metrics.
    - Added unit test for the new v2 attack.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-014: Implement additional selection signals (burst/community/bridge) *or* downgrade plan claims
  - Location: `provetok/src/provetok/dataset/selection.py`, `plan.md`
  - Acceptance: Either add deterministic computations and include them in evidence/logs, or revise plan.md to mark them as future work.
  - Evidence: Plan mentions these signals; code does not implement them.
  - Implementation:
    - Added deterministic selection signals in `compute_selection_signals()`:
      - `citation_velocity` (burst/growth proxy: citations-per-year normalized)
      - `bridge` (bridge proxy: cross-community neighbor ratio using OpenAlex concept community proxy)
    - Wired signals into scoring via `selection.centrality_weights.*` and persisted them into `selection_log_extended.jsonl` evidence (`selection_signals`).
    - Updated `provetok/configs/dataset.yaml` to include non-zero default weights and added unit tests.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-015: Record git commit hash + dirty state in dataset manifest
  - Location: `provetok/src/provetok/dataset/build.py`
  - Acceptance: `public/dataset_manifest.json` includes `git_commit` and `git_dirty` when `.git` exists.
  - Evidence: Build now writes `git_commit` and `git_dirty` when run inside a git repo.
  - Notes:

- [x] Missing-016: Integrate Papers-with-Code dump as an auxiliary QA cross-check *or* downgrade plan claims
  - Location: (new) `provetok/src/provetok/sources/pwc_dump.py`, `provetok/src/provetok/dataset/qa.py`, `plan.md`
  - Acceptance: Either (a) ingest PWC dump for paper↔task/dataset/metric hints and emit mismatch warnings in `qa_report_*.jsonl`, or (b) revise plan.md to state PWC is future work.
  - Evidence: Plan lists PWC dumps as a source for cross-checking, but no code currently consumes it.
  - Implementation:
    - Added optional PWC dump ingestion (`provetok/src/provetok/sources/pwc_dump.py`) supporting JSON/JSONL (+ `.gz`) and DOI-based hint mapping.
    - Plumbed dataset config into `run_qa(..., cfg=...)` and emit PWC hint/mismatch warnings (by DOI via private internal mapping).
    - Added `sources.pwc_dump` config stanza and unit test covering hint warnings.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-017: Support private (hidden) SDG seeds for leaderboard use
  - Location: `provetok/src/provetok/dataset/sealed_worlds.py`, `provetok/configs/dataset.yaml`
  - Acceptance: `seeds.private_seeds` are generated into `private/` only (no public sealed worlds), with codebooks saved and referenced in the dataset manifest.
  - Evidence: Config has `private_seeds`, but export only uses `public_seeds`.
  - Implementation:
    - Added `seeds.private_seeds` handling: export worlds under `private/sealed_worlds_private/{seed}/...` only.
    - Keep codebooks under `private/mapping_key/seed_{seed}.codebook.json` and include `sealed_worlds.private_seeds` entries in `public/dataset_manifest.json`.
    - Added unit test asserting private seeds never appear under `public/sealed_worlds/`.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Missing-018: Report tier shortfalls vs target sizes with reason breakdown
  - Location: `provetok/src/provetok/dataset/build.py`, `provetok/src/provetok/dataset/pipeline.py`
  - Acceptance: If a tier ends with `< target_size`, `public/dataset_manifest.json` records actual counts and a stable breakdown of exclusions (e.g., `fulltext_missing`, `fulltext_error`, `llm_policy_fail`).
  - Evidence: Build now records `targets`, `actuals`, and `selection_exclusions` (overall + per-track) in the manifest.
  - Notes:

## Ambiguous
- [x] Amb-001: Define "public fulltext accessible" verification precisely
  - Location: `plan.md` Phase 4; implementation in `provetok/src/provetok/dataset/fulltext.py`
  - Question: For arXiv papers, must both PDF and source download? For author PDFs, must GET succeed fully? How many retries/timeouts?
  - Needed: A crisp policy per tier and a deterministic retry/timeout strategy.
  - Proposed spec: Require PDF download success for all; fetch arXiv source best-effort; for arXiv failure, fall back to author PDF when policy allows.
  - Notes: Implemented in `cache_fulltext_for_mapping_rows()` + strict selection in the online pipeline.

- [x] Amb-002: Name/identity fingerprint policy in public text
  - Location: `provetok/src/provetok/dataset/record_builder.py`, `provetok/src/provetok/dataset/qa.py`
  - Question: Do we forbid person-name patterns in public `background`, or only forbid explicit author fields?
  - Needed: A concrete allow/deny rule (regex + allowlist) to reduce false positives.
  - Proposed spec: Start with URL/DOI/arXiv/year/venue bans; make name-ban optional behind a config flag.
  - Resolution:
    - Add optional `record_build.forbid_names` (default false) to forbid *citation-like* name fingerprints in public text:
      - `Surname et al.` and `A. Surname` patterns (case-insensitive).
    - Add `record_build.name_allowlist` (list of substrings) to suppress false positives by match-span substring checks.
    - When enabled:
      - Strict build treats matches as policy violations (retry/exclude/backfill).
      - Non-strict mode redacts these patterns from public text.
      - QA reports `forbidden_name_*` hits under the existing forbidden-text check.
  - Implementation:
    - Implemented optional patterns in record builder + QA, wired via `provetok/configs/dataset.yaml` (`record_build.forbid_names`, `record_build.name_allowlist`).
    - Added unit tests covering default allow, forbid, and allowlist behavior.
  - Next: `./.venv/bin/python -m pytest -q`
  - Verified: 2026-02-04 via `./.venv/bin/python -m pytest -q`
  - Notes:

- [x] Amb-003: Edge agreement alignment key for S2/OpenCitations
  - Location: (new) `provetok/src/provetok/dataset/edge_agreement.py`
  - Question: Should edge agreement be computed only on DOI-mapped edges, or allow title-similarity fallbacks?
  - Needed: Decision on denominator and fallback strategy.
  - Proposed spec: DOI-only for OpenCitations agreement; S2 agreement uses S2 paperId mapping.
  - Notes: Implemented as DOI-only OC edges + internal ID mapping for S2 edges.

## Log
- 2026-02-04: Initialized Mohu backlog for plan.md alignment.
- 2026-02-04: Marked Missing-001 complete; added Missing-016..018 for PWC/private seeds/shortfall reporting gaps.
- 2026-02-04: Completed Missing-002..009, Missing-015, Missing-018; resolved Amb-001/Amb-003 by implementing strict fulltext + edge agreement.
- 2026-02-04: Refreshed `docs/repo_inventory.md`; reviewed Mohu against `plan.md` (no new IDs added).
- 2026-02-04: Closed all remaining Missing/Ambiguous items; verification PASS recorded in `docs/verify_log.md`.
