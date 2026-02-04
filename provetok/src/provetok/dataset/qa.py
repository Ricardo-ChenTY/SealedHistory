"""Dataset QA checks (plan.md §8)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import PaperRecordV2, load_records_v2
from provetok.dataset.paths import DatasetPaths


FORBIDDEN_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("url", r"https?://"),
    ("doi", r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b"),
    ("arxiv", r"\barxiv\b|\b\d{4}\.\d{4,5}(v\d+)?\b"),
    ("year", r"\b(19|20)\d{2}\b"),
    ("venue", r"\b(NeurIPS|ICML|ICLR|CVPR|ICCV|ECCV|ACL|EMNLP|NAACL|COLING)\b"),
]


def _find_forbidden(text: str) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    for code, pat in FORBIDDEN_TEXT_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            issues.append({"code": f"forbidden_{code}", "message": f"Matched pattern: {pat}"})
    return issues


def validate_record_schema(rec: PaperRecordV2) -> List[Dict[str, str]]:
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
    issues.extend(_find_forbidden(rec.background))

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
) -> Dict[str, Any]:
    targets = ["A", "B"] if track == "both" else [track]

    all_records: List[PaperRecordV2] = []
    for t in targets:
        p = paths.public_records_path(t, tier)
        if p.exists():
            all_records.extend(load_records_v2(p))

    qa_rows: List[Dict[str, Any]] = []
    schema_pass = 0
    consistency_pass = 0

    for r in all_records:
        issues = []
        issues.extend(validate_record_schema(r))
        issues.extend(protocol_result_consistency_issues(r))

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
    }
    return summary
