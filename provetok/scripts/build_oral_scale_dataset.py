"""Build a scale (non-toy) micro-history dataset for oral vNext.

This script converts v2 internal records (PaperRecordInternalV2 JSONL) into the
legacy micro-history `PaperRecord` JSONL format used by the benchmark/oral
scripts, then seals them with SDG (full + L1-only variants).

Outputs (under --out_dir):
- track_A_raw.jsonl
- track_B_raw.jsonl
- track_A_sealed.jsonl + track_A_sealed.codebook.json
- track_B_sealed.jsonl + track_B_sealed.codebook.json
- track_A_sealed_l1only.jsonl + track_A_sealed_l1only.codebook.json
- track_B_sealed_l1only.jsonl + track_B_sealed_l1only.codebook.json
- dataset_manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import ExperimentResult, PaperRecord, save_records
from provetok.data.schema_v2 import PaperRecordInternalV2, load_records_internal_v2
from provetok.sdg.sealer import SDGPipeline


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _parse_index(paper_id: str) -> int:
    s = str(paper_id or "")
    parts = s.split("_", 1)
    if len(parts) != 2:
        return 0
    tail = parts[1]
    return int(tail) if tail.isdigit() else 0


def _phase_by_quantiles(indices: List[int]) -> Tuple[int, int]:
    xs = sorted(int(x) for x in indices if isinstance(x, int))
    if not xs:
        return 0, 0
    q1 = xs[int(0.33 * (len(xs) - 1))]
    q2 = xs[int(0.66 * (len(xs) - 1))]
    return q1, q2


def _phase_for_idx(idx: int, q1: int, q2: int) -> str:
    if idx <= q1:
        return "early"
    if idx <= q2:
        return "mid"
    return "late"


def _results_from_v2(
    *,
    primary_rank: int,
    delta_bucket: int,
    max_rank: int,
) -> ExperimentResult:
    # Normalize rank so larger is worse; map to [0,1] with 1=best.
    denom = max(1, int(max_rank) - 1)
    metric_main = 1.0 - (max(1, int(primary_rank)) - 1) / denom

    # Convert delta bucket [-3..3] to [0..1] so claim_validity isn't dominated by sign flips.
    delta_vs_prev = (max(-3, min(3, int(delta_bucket))) + 3) / 6.0

    return ExperimentResult(
        metric_main=round(float(metric_main), 6),
        delta_vs_prev=round(float(delta_vs_prev), 6),
        extra={
            "delta_bucket": float(delta_bucket),
        },
    )


def _mechanism_text(pub: dict) -> str:
    tags = pub.get("mechanism_tags") or []
    fg = pub.get("formula_graph") or {}
    ops = fg.get("ops") or []
    nodes = fg.get("nodes") or []
    edges = fg.get("edges") or []
    return (
        "Mechanism tags: {tags}. Formula graph: {n_nodes} nodes, {n_edges} edges. Ops: {ops}.".format(
            tags=", ".join(str(t) for t in tags[:12]),
            n_nodes=len(nodes),
            n_edges=len(edges),
            ops=", ".join(str(o) for o in ops[:12]),
        )
    )


def _experiment_text(pub: dict) -> str:
    proto = pub.get("protocol") or {}
    res = pub.get("results") or {}
    return (
        "Protocol: task={task}, dataset={ds}, metric={m}, compute={c}, regime={r}. "
        "Results: primary_metric_rank={rank}, delta_bucket={db}, significance={sig}.".format(
            task=str(proto.get("task_family_id") or "unknown_task"),
            ds=str(proto.get("dataset_id") or "unknown_dataset"),
            m=str(proto.get("metric_id") or "unknown_metric"),
            c=str(proto.get("compute_class") or "unknown_compute"),
            r=str(proto.get("train_regime_class") or "unknown_regime"),
            rank=int(res.get("primary_metric_rank") or 0),
            db=int(res.get("delta_over_baseline_bucket") or 0),
            sig=str(res.get("significance_flag")),
        )
    )


def _convert_internal_to_paperrecord(
    rec: PaperRecordInternalV2,
    *,
    phase: str,
    max_rank: int,
) -> PaperRecord:
    pub = rec.public.to_dict()
    res = pub.get("results") or {}
    r = PaperRecord(
        paper_id=str(pub.get("paper_id") or ""),
        title=str(rec.title or pub.get("paper_id") or ""),
        phase=str(phase),
        background=str(pub.get("background") or ""),
        mechanism=_mechanism_text(pub),
        experiment=_experiment_text(pub),
        results=_results_from_v2(
            primary_rank=int(res.get("primary_metric_rank") or 0),
            delta_bucket=int(res.get("delta_over_baseline_bucket") or 0),
            max_rank=int(max_rank),
        ),
        dependencies=[str(x) for x in (pub.get("dependencies") or []) if str(x).strip()],
        keywords=[str(x) for x in (rec.keywords or []) if str(x).strip()],
        year=int(rec.year) if rec.year is not None else None,
        venue=str(rec.venue) if rec.venue is not None else None,
        authors=[str(x) for x in (rec.authors or [])] if rec.authors else None,
    )
    return r


def _read_internal(path: Path) -> List[PaperRecordInternalV2]:
    return load_records_internal_v2(path)


def _git_head() -> str:
    p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return str(p.stdout or "").strip()


def _git_dirty() -> bool:
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False)
    return bool(str(p.stdout or "").strip())


def _build_track(
    records_internal: List[PaperRecordInternalV2],
    *,
    out_dir: Path,
    track_id: str,
    seal_seed: int,
    numeric_bins: int,
    write_l1only: bool,
) -> Dict[str, dict]:
    # Stable order by paper_id index.
    indices = [_parse_index(r.public.paper_id) for r in records_internal]
    q1, q2 = _phase_by_quantiles(indices)

    max_rank = 1
    for r in records_internal:
        res = r.public.results
        max_rank = max(max_rank, int(getattr(res, "primary_metric_rank", 0) or 0))

    raw: List[PaperRecord] = []
    for r in sorted(records_internal, key=lambda x: (_parse_index(x.public.paper_id), x.public.paper_id)):
        idx = _parse_index(r.public.paper_id)
        phase = _phase_for_idx(idx, q1, q2)
        raw.append(_convert_internal_to_paperrecord(r, phase=phase, max_rank=max_rank))

    raw_path = out_dir / f"track_{track_id}_raw.jsonl"
    save_records(raw, raw_path)

    # Full sealing (L1+L2+L3)
    pipe_full = SDGPipeline(seed=seal_seed, enable_l1=True, enable_l2=True, enable_l3=True, numeric_bins=numeric_bins)
    sealed = pipe_full.seal_records(raw)
    sealed_path = out_dir / f"track_{track_id}_sealed.jsonl"
    save_records(sealed, sealed_path)
    cb_path = out_dir / f"track_{track_id}_sealed.codebook.json"
    pipe_full.codebook.save(cb_path)

    out = {
        "raw": {"path": str(raw_path), "n_records": len(raw)},
        "sealed": {"path": str(sealed_path), "n_records": len(sealed), "codebook": str(cb_path)},
    }

    if write_l1only:
        pipe_l1 = SDGPipeline(
            seed=seal_seed, enable_l1=True, enable_l2=False, enable_l3=False, numeric_bins=numeric_bins
        )
        sealed_l1 = pipe_l1.seal_records(raw)
        sealed_l1_path = out_dir / f"track_{track_id}_sealed_l1only.jsonl"
        save_records(sealed_l1, sealed_l1_path)
        cb_l1_path = out_dir / f"track_{track_id}_sealed_l1only.codebook.json"
        pipe_l1.codebook.save(cb_l1_path)
        out["sealed_l1only"] = {
            "path": str(sealed_l1_path),
            "n_records": len(sealed_l1),
            "codebook": str(cb_l1_path),
        }

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build oral scale micro-history dataset from v2 internal exports.")
    parser.add_argument("--in_internal_a", required=True)
    parser.add_argument("--in_internal_b", required=True)
    parser.add_argument("--out_dir", default="runs/EXP-021/dataset")
    parser.add_argument("--seal_seed", type=int, default=42)
    parser.add_argument("--numeric_bins", type=int, default=10)
    parser.add_argument("--write_l1only", action="store_true", help="Also write L1-only sealed variant.")
    args = parser.parse_args()

    t0 = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    in_a = Path(args.in_internal_a)
    in_b = Path(args.in_internal_b)
    recs_a = _read_internal(in_a)
    recs_b = _read_internal(in_b)

    tracks: Dict[str, dict] = {}
    tracks["A"] = _build_track(
        recs_a,
        out_dir=out_dir,
        track_id="A",
        seal_seed=int(args.seal_seed),
        numeric_bins=int(args.numeric_bins),
        write_l1only=bool(args.write_l1only),
    )
    tracks["B"] = _build_track(
        recs_b,
        out_dir=out_dir,
        track_id="B",
        seal_seed=int(args.seal_seed),
        numeric_bins=int(args.numeric_bins),
        write_l1only=bool(args.write_l1only),
    )

    files = []
    for _, spec in tracks.items():
        for k, v in spec.items():
            p = Path(v["path"])
            files.append(
                {
                    "name": k,
                    "path": str(p),
                    "bytes": p.stat().st_size,
                    "sha256": _sha256_file(p),
                    "n_records": int(v.get("n_records") or 0),
                    "codebook": v.get("codebook"),
                }
            )
            cb = v.get("codebook")
            if cb:
                cbp = Path(cb)
                files.append(
                    {
                        "name": f"{k}_codebook",
                        "path": str(cbp),
                        "bytes": cbp.stat().st_size,
                        "sha256": _sha256_file(cbp),
                    }
                )

    elapsed = time.time() - t0
    manifest = {
        "dataset_name": "oral_scale_microhistory_from_v2_internal",
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "in_internal_a": str(in_a),
            "in_internal_b": str(in_b),
        },
        "tracks": {k: {kk: vv for kk, vv in spec.items()} for k, spec in tracks.items()},
        "sealer": {
            "seal_seed": int(args.seal_seed),
            "numeric_bins": int(args.numeric_bins),
            "variants": ["sealed_full", "sealed_l1only"] if args.write_l1only else ["sealed_full"],
        },
        "runtime": {
            "elapsed_sec": round(float(elapsed), 3),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": {
            "commit": _git_head(),
            "dirty": bool(_git_dirty()),
        },
        "files": files,
    }

    (out_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Saved dataset manifest to {out_dir / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()

