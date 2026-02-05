"""Dataset QA checks (plan.md §8)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import PaperRecordV2, load_records_internal_v2, load_records_v2
from provetok.dataset.paths import DatasetPaths


FORBIDDEN_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("url", r"https?://"),
    ("doi", r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b"),
    ("arxiv", r"\barxiv\b|\b\d{4}\.\d{4,5}(v\d+)?\b"),
    ("year", r"\b(19|20)\d{2}\b"),
    ("venue", r"\b(NeurIPS|ICML|ICLR|CVPR|ICCV|ECCV|ACL|EMNLP|NAACL|COLING)\b"),
]

NAME_FINGERPRINT_PATTERNS: List[Tuple[str, str]] = [
    ("name_initial_surname", r"\b[A-Z]\.\s*[A-Z][a-z]{2,}\b"),
    ("name_surname_et_al", r"\b[A-Z][a-z]{2,}\s+et\s+al\.?\b"),
]


def _find_forbidden(
    text: str,
    *,
    patterns: Optional[List[Tuple[str, str]]] = None,
    name_allowlist: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    pats = patterns if patterns is not None else FORBIDDEN_TEXT_PATTERNS
    allow = [str(x).strip().lower() for x in (name_allowlist or []) if str(x).strip()]
    for code, pat in pats:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        if code.startswith("name_") and allow:
            span = str(m.group(0) or "").lower()
            if any(a in span for a in allow):
                continue
        issues.append({"code": f"forbidden_{code}", "message": f"Matched pattern: {pat}"})
    return issues


def validate_record_schema(
    rec: PaperRecordV2,
    *,
    forbidden_patterns: Optional[List[Tuple[str, str]]] = None,
    name_allowlist: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    if not rec.paper_id:
        issues.append({"code": "missing_paper_id", "message": "paper_id is empty"})
    if not rec.track_id:
        issues.append({"code": "missing_track_id", "message": "track_id is empty"})

    if not isinstance(rec.dependencies, list):
        issues.append({"code": "bad_dependencies_type", "message": "dependencies must be a list"})

    if not isinstance(rec.background, str):
        issues.append({"code": "bad_background_type", "message": "background must be a string"})
    if len(rec.background) > 2000:
        issues.append({"code": "background_too_long", "message": "background exceeds 2000 chars"})
    issues.extend(_find_forbidden(rec.background, patterns=forbidden_patterns, name_allowlist=name_allowlist))

    # basic nested presence checks
    if rec.formula_graph is None:
        issues.append({"code": "missing_formula_graph", "message": "formula_graph missing"})
    if rec.protocol is None:
        issues.append({"code": "missing_protocol", "message": "protocol missing"})
    if rec.results is None:
        issues.append({"code": "missing_results", "message": "results missing"})
    return issues


def dependency_graph_issues(records: List[PaperRecordV2]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    ids = {r.paper_id for r in records}

    # dep -> paper edges
    edges: List[Tuple[str, str]] = []
    for r in records:
        for dep in r.dependencies:
            if dep == r.paper_id:
                issues.append({"code": "self_dependency", "message": f"{r.paper_id} depends on itself"})
            if dep not in ids:
                issues.append({"code": "missing_dependency", "message": f"{r.paper_id} depends on missing {dep}"})
            edges.append((dep, r.paper_id))

    # cycle detection (DFS)
    adj: Dict[str, List[str]] = {pid: [] for pid in ids}
    for u, v in edges:
        if u in adj and v in adj:
            adj[u].append(v)

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(u: str, stack: List[str]) -> None:
        if u in visited:
            return
        if u in visiting:
            # cycle found
            cycle = " -> ".join(stack + [u])
            issues.append({"code": "cycle_detected", "message": cycle})
            return
        visiting.add(u)
        for v in adj.get(u, []):
            dfs(v, stack + [u])
        visiting.remove(u)
        visited.add(u)

    for node in list(ids):
        if node not in visited:
            dfs(node, [])

    return issues


def taxonomy_coverage_stats(records: List[PaperRecordV2]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    total = 0
    for r in records:
        for tag in r.mechanism_tags or []:
            counts[tag] = counts.get(tag, 0) + 1
            total += 1
    other = counts.get("other", 0)
    return {
        "tag_counts": counts,
        "total_tags": total,
        "other_ratio": (other / total) if total else 0.0,
    }


def protocol_result_consistency_issues(rec: PaperRecordV2) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    proto = rec.protocol
    res = rec.results

    # Consider unknowns as "incomplete" rather than hard failures.
    unknowns = []
    for k in ("task_family_id", "dataset_id", "metric_id"):
        if getattr(proto, k) in ("", "unknown_task", "unknown_dataset", "unknown_metric"):
            unknowns.append(k)
    if unknowns:
        issues.append({"code": "protocol_incomplete", "message": f"Unknown fields: {', '.join(unknowns)}"})

    if res.primary_metric_rank <= 0:
        issues.append({"code": "rank_missing", "message": "primary_metric_rank should be >= 1"})

    if not isinstance(res.delta_over_baseline_bucket, int):
        issues.append({"code": "delta_bucket_bad_type", "message": "delta_over_baseline_bucket must be int"})

    return issues


def run_qa(
    *,
    paths: DatasetPaths,
    track: str = "both",
    tier: str = "extended",
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    targets = ["A", "B"] if track == "both" else [track]

    all_records: List[PaperRecordV2] = []
    internal_doi_by_pid: Dict[str, str] = {}

    def norm_doi(doi: str) -> str:
        s = str(doi or "").strip()
        if not s:
            return ""
        low = s.lower()
        for prefix in ("https://doi.org/", "http://doi.org/"):
            if low.startswith(prefix):
                s = s[len(prefix) :]
                break
        if s.lower().startswith("doi:"):
            s = s[4:]
        return s.strip().lower()

    for t in targets:
        p = paths.public_records_path(t, tier)
        if p.exists():
            all_records.extend(load_records_v2(p))
        ip = paths.private_records_path(t, tier)
        if ip.exists():
            for r in load_records_internal_v2(ip):
                pid = str(r.public.paper_id or "")
                doi = norm_doi(str(r.doi or ""))
                if pid and doi:
                    internal_doi_by_pid[pid] = doi

    pwc_hints: Dict[str, Dict[str, set]] = {}
    pwc_enabled = False
    pwc_dump_path = ""
    if cfg and isinstance(cfg, dict):
        pwc_cfg = ((cfg.get("sources") or {}).get("pwc_dump") or {}) if isinstance(cfg.get("sources"), dict) else {}
        pwc_enabled = bool(pwc_cfg.get("enable", False))
        pwc_dump_path = str(pwc_cfg.get("dump_path") or "")
        if pwc_enabled and pwc_dump_path:
            from provetok.sources.pwc_dump import load_pwc_dump, normalize_doi

            pwc_hints = load_pwc_dump(Path(pwc_dump_path))
            pwc_hints = {normalize_doi(k): v for k, v in pwc_hints.items() if k}

    qa_rows: List[Dict[str, Any]] = []
    schema_pass = 0
    consistency_pass = 0
    pwc_stats = {
        "enabled": bool(pwc_enabled and pwc_dump_path),
        "n_records_with_doi": 0,
        "n_records_with_pwc": 0,
        "n_task_hints": 0,
        "n_dataset_hints": 0,
        "n_metric_hints": 0,
        "n_task_mismatch": 0,
        "n_dataset_mismatch": 0,
        "n_metric_mismatch": 0,
    }

    def norm_id(s: str) -> str:
        s = str(s or "").strip().lower()
        s = re.sub(r"[\s\-]+", "_", s)
        s = re.sub(r"[^a-z0-9_]+", "", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    forbid_names = False
    name_allowlist: List[str] = []
    if cfg and isinstance(cfg, dict):
        rb = cfg.get("record_build") or {}
        if isinstance(rb, dict):
            forbid_names = bool(rb.get("forbid_names", False))
            raw_allow = rb.get("name_allowlist") or []
            if isinstance(raw_allow, list):
                name_allowlist = [str(x) for x in raw_allow if str(x).strip()]

    forbidden_patterns = list(FORBIDDEN_TEXT_PATTERNS) + (list(NAME_FINGERPRINT_PATTERNS) if forbid_names else [])

    for r in all_records:
        issues = []
        issues.extend(validate_record_schema(r, forbidden_patterns=forbidden_patterns, name_allowlist=name_allowlist))
        issues.extend(protocol_result_consistency_issues(r))

        # Optional: auxiliary cross-check with Papers-with-Code dump (by DOI, using private mapping).
        doi = internal_doi_by_pid.get(r.paper_id)
        if doi:
            pwc_stats["n_records_with_doi"] += 1
        hints = pwc_hints.get(doi or "")
        if hints:
            pwc_stats["n_records_with_pwc"] += 1
            proto = r.protocol

            tasks = {norm_id(x) for x in (hints.get("tasks") or set()) if norm_id(x)}
            datasets = {norm_id(x) for x in (hints.get("datasets") or set()) if norm_id(x)}
            metrics = {norm_id(x) for x in (hints.get("metrics") or set()) if norm_id(x)}

            if tasks:
                pwc_stats["n_task_hints"] += 1
            if datasets:
                pwc_stats["n_dataset_hints"] += 1
            if metrics:
                pwc_stats["n_metric_hints"] += 1

            task_id = norm_id(getattr(proto, "task_family_id", ""))
            dataset_id = norm_id(getattr(proto, "dataset_id", ""))
            metric_id = norm_id(getattr(proto, "metric_id", ""))

            def add_hint_or_mismatch(kind: str, field_val: str, hint_set: set[str]) -> None:
                if not hint_set:
                    return
                if field_val in ("unknown_task", "unknown_dataset", "unknown_metric", ""):
                    issues.append({"code": f"pwc_{kind}_hint_available", "message": "PWC hints available; protocol field is unknown"})
                elif field_val not in hint_set:
                    issues.append({"code": f"pwc_{kind}_mismatch", "message": "Protocol field differs from PWC hints"})

            add_hint_or_mismatch("task", task_id, tasks)
            add_hint_or_mismatch("dataset", dataset_id, datasets)
            add_hint_or_mismatch("metric", metric_id, metrics)

            pwc_stats["n_task_mismatch"] += sum(1 for i in issues if i["code"] == "pwc_task_mismatch")
            pwc_stats["n_dataset_mismatch"] += sum(1 for i in issues if i["code"] == "pwc_dataset_mismatch")
            pwc_stats["n_metric_mismatch"] += sum(1 for i in issues if i["code"] == "pwc_metric_mismatch")

        schema_ok = not any(i["code"].startswith(("missing_", "bad_", "background_too_long", "forbidden_")) for i in issues)
        consistency_ok = not any(i["code"] in ("rank_missing",) for i in issues)

        schema_pass += 1 if schema_ok else 0
        consistency_pass += 1 if consistency_ok else 0

        score = 100
        score -= 20 * sum(1 for i in issues if i["code"].startswith("missing_"))
        score -= 10 * sum(1 for i in issues if i["code"].startswith("bad_"))
        score -= 5 * sum(1 for i in issues if i["code"].startswith("forbidden_"))
        score = max(0, score)

        qa_rows.append(
            {
                "paper_id": r.paper_id,
                "track_id": r.track_id,
                "quality_score": score,
                "issues": issues,
            }
        )

    graph_issues = dependency_graph_issues(all_records) if all_records else []

    qa_path = paths.public_qa_report_path(tier)
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    with open(qa_path, "w", encoding="utf-8") as f:
        for row in qa_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "tier": tier,
        "n_records": len(all_records),
        "schema_pass_rate": (schema_pass / len(all_records)) if all_records else 0.0,
        "consistency_pass_rate": (consistency_pass / len(all_records)) if all_records else 0.0,
        "dependency_graph_issues": graph_issues,
        "taxonomy": taxonomy_coverage_stats(all_records) if all_records else {},
        "pwc": pwc_stats,
    }
    return summary
