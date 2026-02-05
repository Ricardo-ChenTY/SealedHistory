# Mohu / Gap Tracker

This file lists **only blocking items** for the doc-driven loop (`docs/plan.md` ↔ implementation).

Rules:
- Exactly two sections: (1) Gap, (2) Ambiguity.
- Both sections must be **empty of unchecked items** before marking claims as PROVED in `docs/experiment.md`.
- Once an item is closed, remove it (history lives in `docs/verify_log.md` and git).

---

## 1. Gap (not implemented)

- [x] GAP-001: Snapshot contract mismatch: request snapshots are missing from offline exports
  - Source: `docs/plan.md` CLAIM-007; `docs/experiment.md` EXP-008; `provetok/src/provetok/dataset/pipeline.py` snapshot writers
  - Impact scope (files):
    - `provetok/src/provetok/sources/http.py`
    - `provetok/src/provetok/dataset/pipeline.py`
    - `docs/plan.md`
    - `docs/experiment.md`
  - Acceptance Criteria:
    1) For every enabled source+track, the export root contains the canonical request snapshot path(s) (empty JSONL is allowed):
       - `private/raw_snapshots/openalex/requests_track_{A,B}.jsonl`
       - `private/raw_snapshots/s2/requests_track_{A,B}.jsonl` (when enabled)
       - `private/raw_snapshots/opencitations/requests_track_{A,B}.jsonl` (when enabled)
    2) OpenAlex works snapshots exist as documented:
       - `private/raw_snapshots/openalex/works_track_{A,B}.jsonl`
  - Verification:
    - Command: `python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006 --track both`
    - Expected: all canonical snapshot paths required by the chosen contract exist under `runs/EXP-006/exports/**/private/raw_snapshots/**`.
  - Evidence:
    - 2026-02-05: PASS (offline export contains empty request snapshot files + works snapshots for A/B)
    - Artifacts:
      - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_A.jsonl`
      - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_B.jsonl`
      - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_A.jsonl`
      - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_B.jsonl`
    - Changes:
      - `provetok/src/provetok/dataset/pipeline.py` (touch/truncate request snapshot files deterministically)
      - `provetok/scripts/run_exp_manual_decisions_offline.py` (write works snapshots + config for Track A/B)

- [x] GAP-002: EXP-008 evidence is under-checking CLAIM-007 (only validates OpenAlex works A)
  - Source: `docs/plan.md` CLAIM-007; `docs/experiment.md` EXP-008
  - Impact scope (files):
    - `docs/experiment.md`
    - `docs/plan.md`
  - Acceptance Criteria:
    1) Update EXP-008 to validate *all* snapshot paths promised by CLAIM-007 (including request snapshots and Track B when applicable).
    2) EXP-008 produces a log artifact under `runs/EXP-008/` listing every checked path.
  - Verification:
    - Command: run EXP-006 then EXP-008 as documented
    - Expected: EXP-008 PASS only if every required path exists.
  - Evidence:
    - 2026-02-05: PASS
    - Artifact: `runs/EXP-008/snapshot_contract.log`
    - Changes: `docs/experiment.md` (EXP-008 now checks OpenAlex works+requests for A/B and S2 request snapshots for A/B)

- [x] GAP-003: Offline rebuild “no network access” is not proven
  - Source: `docs/plan.md` CLAIM-007 (offline rebuild definition)
  - Impact scope (files):
    - `provetok/src/provetok/dataset/pipeline.py`
    - `provetok/src/provetok/sources/http.py`
    - `docs/experiment.md`
  - Acceptance Criteria:
    1) Add an automated check (test or experiment) that fails if any network call is attempted during an `--offline` dataset build when snapshots exist.
    2) Record the check result in `docs/experiment.md` (new EXP row or extend EXP-008/EXP-007).
  - Verification:
    - Command: `python -m pytest -q`
    - Expected: an explicit offline-no-network test passes; evidence is saved under `runs/EXP-00x/`.
  - Evidence:
    - 2026-02-05: PASS (see `runs/EXP-007/pytest.log`)
    - Changes:
      - `provetok/src/provetok/dataset/pipeline.py` (offline disables LLM usage)
      - `provetok/tests/test_offline_no_network.py` (blocks urlopen + LLMClient.chat; asserts offline build completes)
      - `docs/plan.md` / `docs/experiment.md` (CLAIM-007 now also evidenced by EXP-007)

- [x] GAP-004: Manual decisions + paper_key audit evidence only covers Track A
  - Source: `docs/plan.md` CLAIM-005/006; `docs/experiment.md` EXP-006
  - Impact scope (files):
    - `provetok/scripts/run_exp_manual_decisions_offline.py`
    - `docs/experiment.md`
  - Acceptance Criteria:
    1) Decide whether CLAIM-005/006 require Track B coverage; if yes, add a reproducible run for Track B (or `--track both`) and record it in `docs/experiment.md`.
    2) The exported `public/selection_log_extended.jsonl` for Track B contains manual-decision rows with `reviewer_id`, `reason_tag`, and `paper_key`.
  - Verification:
    - Command: `python provetok/scripts/run_exp_manual_decisions_offline.py --run_dir runs/EXP-006B --track B`
    - Expected: logs and mapping rows contain `paper_key`, and manual rows contain `reviewer_id`.
  - Evidence:
    - 2026-02-05: PASS (ran Track B-only and Track A/B)
    - Artifacts:
      - `runs/EXP-006B/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` (contains `reviewer_id` rows for `track_id` B)
      - `runs/EXP-006B/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_B_extended.jsonl` (contains `paper_key`)
      - `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` (contains `reviewer_id` rows for `track_id` A and B)
      - `runs/EXP-006/exports/exp-006-manual-decisions/private/mapping_key/paper_id_map_track_B_extended.jsonl` (contains `paper_key`)
    - Changes:
      - `provetok/scripts/run_exp_manual_decisions_offline.py` (adds manual decisions for W3/W4)
      - `docs/experiment.md` (EXP-006 now uses `--track both`)

- [x] GAP-005: Doc contracts disagree about `reviewer_id`/`paper_key` in public selection logs
  - Source: `docs/plan.md` CLAIM-005; `docs/data_requirements.md` and `docs/collection_checklist.md` selection-log text
  - Impact scope (files):
    - `docs/plan.md`
    - `docs/data_requirements.md`
    - `docs/collection_checklist.md`
    - `docs/templates/manual_decisions.jsonl`
  - Acceptance Criteria:
    1) Resolve `reviewer_id` policy (see AMB-001) and make all docs consistent.
    2) Explicitly list `paper_key` as a required field wherever selection-log/mapping contracts are defined.
  - Verification:
    - Command: docs review + rerun EXP-006
    - Expected: docs do not contradict each other; generated logs match the documented contract.
  - Evidence:
    - 2026-02-05: PASS
    - Docs:
      - `docs/data_requirements.md` (selection_log requires paper_key; reviewer_id allowed if anonymized)
      - `docs/collection_checklist.md` (same policy wording)
    - Run artifacts:
      - `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl`

- [x] GAP-006: Missing JSON schema(s) for selection logs and mapping JSONL
  - Source: `docs/plan.md` §3.4 (contracts); `docs/schemas/` currently only contains `paper_record_v2.schema.json`
  - Impact scope (files):
    - `docs/schemas/`
    - `docs/plan.md`
    - `docs/experiment.md`
  - Acceptance Criteria:
    1) Add JSON schema(s) for:
       - `public/selection_log_{core,extended}.jsonl` rows
       - `private/mapping_key/paper_id_map_track_{A,B}_{core,extended}.jsonl` rows
    2) Add a runnable validation command (test or script) that checks a produced export against these schemas.
  - Verification:
    - Command: `python -m pytest -q` (or a dedicated schema-check command recorded in `docs/experiment.md`)
    - Expected: schema validation passes for `runs/exports/**` and `runs/EXP-006/**`.
  - Evidence:
    - 2026-02-05: PASS (see `runs/EXP-007/pytest.log`)
    - Schemas:
      - `docs/schemas/selection_log_row.schema.json`
      - `docs/schemas/paper_id_map_row.schema.json`
    - Tests:
      - `provetok/tests/test_export_schema_validation.py`

- [x] GAP-007: Manual decisions accepted key forms are implemented but not documented
  - Source: `docs/plan.md` CLAIM-006 canonical `paper_key`; `docs/templates/manual_decisions.jsonl` uses OpenAlex URLs; implementation normalizes/aliases
  - Impact scope (files):
    - `docs/plan.md`
    - `docs/templates/manual_decisions.jsonl`
    - `provetok/src/provetok/dataset/selection.py`
  - Acceptance Criteria:
    1) Document which key forms are accepted in `selection.manual_decisions_file` (canonical and allowed aliases).
    2) Provide at least one example row per accepted key form.
  - Verification:
    - Command: `python -m pytest -q`
    - Expected: a test covers alias matching; docs/examples reflect the tested behavior.
  - Evidence:
    - 2026-02-05: PASS (see `runs/EXP-007/pytest.log`)
    - Docs:
      - `docs/plan.md` (§3.4 manual decisions input contract + key forms)
      - `docs/templates/manual_decisions.jsonl` (examples for OpenAlex/DOI/arXiv/key-from-fields)
    - Tests:
      - `provetok/tests/test_manual_decisions_logging.py` (OpenAlex URL alias matching)
      - `provetok/tests/test_manual_decisions_conflict.py` (conflict detection)

## 2. Ambiguity (plan vs implementation unclear)

- [x] AMB-001: Is `reviewer_id` allowed in public logs, and what anonymization is required?
  - Ambiguity:
    - `docs/plan.md` CLAIM-005 requires `reviewer_id` in `public/selection_log_extended.jsonl`.
    - `docs/data_requirements.md` / `docs/collection_checklist.md` imply `reviewer_id` might be internal-only.
  - Needed decision (must become executable spec):
    - Option A (recommended): Allow `reviewer_id` in public selection logs, but require it to be an anonymized stable label (e.g., `r1`) and forbid reversible identifiers.
    - Option B: Remove `reviewer_id` from public logs; keep it in private logs only; update CLAIM-005 + experiments accordingly.
  - Verification:
    - Rerun EXP-006 and check the relevant log(s) match the chosen policy.
  - Decision:
    - Chosen: Option A (allow anonymized `reviewer_id` in public selection logs; no reversible identifiers)
  - Evidence:
    - `docs/data_requirements.md` / `docs/collection_checklist.md` align with CLAIM-005 wording
    - `runs/EXP-006/exports/exp-006-manual-decisions/public/selection_log_extended.jsonl` contains `reviewer_id`

- [x] AMB-002: Are request snapshot files required to exist even when offline mode makes zero requests?
  - Ambiguity:
    - CLAIM-007 lists canonical `requests_track_*.jsonl` paths, but offline runs may naturally produce no request rows.
  - Needed decision:
    - Option A (recommended): Paths MUST exist (possibly empty JSONL) for enabled sources/tracks to make the export layout deterministic.
    - Option B: Paths are optional; exist only if at least one request was made; docs must say “may be absent”.
  - Verification:
    - Update CLAIM-007 + EXP-008 to match; validate against an offline export like `runs/EXP-006/exports/**`.
  - Decision:
    - Chosen: Option A (paths MUST exist; empty JSONL allowed)
  - Evidence:
    - `docs/plan.md` (CLAIM-007 clarifies empty request snapshots are allowed)
    - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/openalex/requests_track_A.jsonl`
    - `runs/EXP-006/exports/exp-006-manual-decisions/private/raw_snapshots/s2/requests_track_A.jsonl`
    - `runs/EXP-008/snapshot_contract.log`

- [x] AMB-003: Should OpenCitations request snapshots be part of the canonical contract?
  - Ambiguity:
    - Implementation writes `private/raw_snapshots/opencitations/requests_track_{t}.jsonl` (when enabled).
    - CLAIM-007 currently only mentions OpenAlex + S2.
  - Needed decision:
    - Option A (recommended): Include OpenCitations request snapshots in the contract when OpenCitations is enabled by config.
    - Option B: Keep OpenCitations as an optional best-effort source; exclude from contract.
  - Verification:
    - Align docs + EXP-008 checks with the chosen scope.
  - Decision:
    - Chosen: Option B (keep OpenCitations optional best-effort; exclude from the core snapshot contract)
  - Evidence:
    - `docs/data_requirements.md` lists `private/raw_snapshots/opencitations/*.jsonl` as optional
    - `provetok/src/provetok/dataset/pipeline.py` gates OpenCitations on `sources.opencitations.enable=true` and non-offline

- [x] AMB-004: Manual-decision matching priority and conflict handling are undocumented
  - Ambiguity:
    - Manual decisions can be keyed by `paper_key` and various aliases (DOI/arXiv/OpenAlex URL).
    - It is unclear what happens when multiple keys match or decisions conflict.
  - Needed decision:
    - Define matching priority (e.g., canonical `paper_key` first, then DOI, then arXiv, then OpenAlex).
    - Define conflict behavior (e.g., fail build if a single work matches multiple conflicting decisions).
  - Verification:
    - Add unit tests for priority and conflict behavior and record them under EXP-007.
  - Decision:
    - Matching priority: candidate canonical `paper_key` first, then DOI, then arXiv, then OpenAlex aliases
    - Conflict behavior: if multiple matching keys disagree on `action`, fail fast with `ValueError`
  - Evidence:
    - `provetok/src/provetok/dataset/selection.py` (`match_manual_decision`)
    - `provetok/src/provetok/dataset/pipeline.py` (uses `match_manual_decision`)
    - `provetok/tests/test_manual_decisions_conflict.py`
    - `runs/EXP-007/pytest.log`
