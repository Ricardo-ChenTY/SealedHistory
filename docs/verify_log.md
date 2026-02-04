# Verify Log

## Missing-010
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes taxonomy + mechanism-tag normalization tests.
  - Artifacts: N/A

## Missing-011
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes arXiv-source formula_graph extraction unit test.
  - Artifacts: N/A

## Missing-012
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes offline-online provenance snapshot reference integration test.
  - Artifacts: N/A

## Missing-013
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes v2 time-index/canonical-order attack unit test.
  - Artifacts: N/A

## Missing-014
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes selection-signal unit tests (citation_velocity/bridge proxies).
  - Artifacts: N/A

## Missing-016
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes PWC QA cross-check unit test.
  - Artifacts: N/A

## Missing-017
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes private-seeds export unit test.
  - Artifacts: N/A

## Amb-002
- 2026-02-04: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Name/identity fingerprint policy optional flag + allowlist tests.
  - Artifacts: N/A

## Missing-019
- 2026-02-05: `./.venv/bin/python -m pytest -q`
  - Result: PASS
  - Notes: Includes `provetok run` random-agent smoke test and verifies env package is importable.
  - Artifacts: N/A
- 2026-02-05: `./.venv/bin/python -m provetok.cli run --agent random --sealed provetok/data/sealed/micro_history_a.sealed.jsonl --raw provetok/data/raw/micro_history_a.jsonl --output /tmp/eval_report_a.json`
  - Result: PASS
  - Notes: CLI benchmark simulation produces a valid eval report.
  - Artifacts: `/tmp/eval_report_a.json`

## Missing-020
- 2026-02-05: `./.venv/bin/python -m provetok.cli run --agent random --sealed provetok/data/sealed/micro_history_b.sealed.jsonl --raw provetok/data/raw/micro_history_b.jsonl --output /tmp/eval_report_b.json`
  - Result: PASS
  - Notes: Track B sealed sample runs end-to-end.
  - Artifacts: `/tmp/eval_report_b.json`
