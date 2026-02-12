"""Run an LLM-backed attacker calibration for the oral paper/story.

Goal (Checklist-3)
------------------
Address the reviewer concern that "heuristic leakage proxies" may not reflect a
real attacker by running an LLM-backed term-recovery attack and reporting:
  - hit@1 / hit@3 for recovering the real term behind a pseudotoken
  - comparable heuristic proxy numbers (from existing adaptive-attack artifacts)

This script requires a real LLM API key. It intentionally does not contain any
`try/except/finally` (forbidden under `provetok/`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.data.schema import PaperRecord, load_records
from provetok.utils.llm_client import LLMClient, LLMConfig


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _norm_term(s: str) -> str:
    t = str(s or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def _parse_guess_list(text: str, *, top_k: int = 3) -> List[str]:
    t = str(text or "").strip()

    # If a bracketed list exists, focus on it.
    if "[" in t and "]" in t:
        i = t.find("[")
        j = t.rfind("]")
        if 0 <= i < j:
            t = t[i : j + 1]

    out = [s.strip() for s in re.findall(r"\"([^\"]+)\"", t) if str(s or "").strip()]
    if not out:
        out = [s.strip() for s in re.findall(r"'([^']+)'", t) if str(s or "").strip()]
    if out:
        return out[:top_k]

    parts = re.split(r"[,\n]+", t)
    cleaned: List[str] = []
    for p in parts:
        s = str(p or "").strip()
        s = re.sub(r"^(?:\\d+\\.|-)\\s*", "", s)
        if s:
            cleaned.append(s)
    return cleaned[:top_k]


def _load_codebook_reverse(codebook_json: Path) -> Dict[str, str]:
    obj = json.loads(codebook_json.read_text(encoding="utf-8"))
    forward = obj.get("forward") or {}
    # forward: real -> pseudo ; we need pseudo -> real
    reverse = {str(v).strip().lower(): str(k).strip().lower() for k, v in forward.items()}
    return reverse


def _build_trials(
    sealed: List[PaperRecord],
    pseudo_to_real: Dict[str, str],
    *,
    seed: int,
    n_samples: int,
) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    trials: List[Dict[str, Any]] = []

    for rec in sealed:
        ctx = " ".join(
            [
                str(rec.title or ""),
                str(rec.background or "")[:400],
                str(rec.mechanism or "")[:400],
                str(rec.experiment or "")[:300],
            ]
        ).strip()
        for pseudo in rec.keywords or []:
            p = str(pseudo or "").strip().lower()
            real = pseudo_to_real.get(p)
            if not real:
                continue
            trials.append(
                {
                    "paper_id": str(rec.paper_id or ""),
                    "pseudo": p,
                    "real": str(real),
                    "context_preview": ctx[:220],
                }
            )

    rng.shuffle(trials)
    return trials[:n_samples]


def _term_recovery_run(
    *,
    llm: LLMClient,
    trials: List[Dict[str, Any]],
    top_k: int,
) -> Dict[str, Any]:
    prompt_template = (
        "You are an attacker seeing a sealed (anonymised) research record. "
        "A pseudotoken '{pseudo}' appears in the record.\n\n"
        "Context:\n{context}\n\n"
        "Guess the original real-world term behind '{pseudo}'. "
        "Return your top-{k} guesses as a JSON list of strings.\n"
        "Output ONLY the JSON list."
    )

    hits_at_1 = 0
    hits_at_k = 0
    details: List[Dict[str, Any]] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for t in trials:
        prompt = prompt_template.format(pseudo=t["pseudo"], context=t["context_preview"], k=int(top_k))
        resp = llm.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=220)
        for kk in usage_total:
            usage_total[kk] += int((resp.usage or {}).get(kk) or 0)

        guesses = _parse_guess_list(resp.content, top_k=top_k)
        gold = _norm_term(t["real"])
        norm_guesses = [_norm_term(g) for g in guesses]
        hit1 = bool(norm_guesses and norm_guesses[0] == gold)
        hitk = bool(gold in norm_guesses)
        hits_at_1 += 1 if hit1 else 0
        hits_at_k += 1 if hitk else 0

        details.append(
            {
                "paper_id": t["paper_id"],
                "pseudo": t["pseudo"],
                "gold_real": t["real"],
                "guesses": guesses,
                "hit@1": hit1,
                f"hit@{top_k}": hitk,
            }
        )

    n = len(trials)
    out = {
        "n_trials": n,
        "hit@1": round(hits_at_1 / n, 4) if n else 0.0,
        f"hit@{top_k}": round(hits_at_k / n, 4) if n else 0.0,
        "usage_total": usage_total,
        "details": details,
    }
    return out


def _load_heuristic_attack(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_api_key() -> str:
    # Prefer OPENAI_* envs (matches repo .env); fallback to LLM_* envs.
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    key = os.environ.get("LLM_API_KEY", "").strip()
    if key:
        return key
    raise RuntimeError("Missing LLM API key: set OPENAI_API_KEY (preferred) or LLM_API_KEY")


def _normalize_api_base(api_base: str) -> str:
    # `openai` client expects a base URL that includes the `/v1` prefix for
    # OpenAI-compatible endpoints. Many self-hosted providers expose the root
    # without `/v1`, so we normalize here.
    s = str(api_base or "").strip().rstrip("/")
    if s.endswith("/v1"):
        return s
    return s + "/v1"


def main() -> None:
    p = argparse.ArgumentParser(description="Run LLM-backed attacker calibration (term recovery) for oral readiness.")
    p.add_argument("--out_dir", default="runs/EXP-032")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n_samples", type=int, default=30)
    p.add_argument("--top_k", type=int, default=3)

    # micro fixtures (public, synthetic)
    p.add_argument("--micro_raw_a", default="provetok/data/raw/micro_history_a.jsonl")
    p.add_argument("--micro_sealed_a", default="provetok/data/sealed/micro_history_a.sealed.jsonl")
    p.add_argument("--micro_codebook_a", default="provetok/data/sealed/micro_history_a.sealed.codebook.json")
    p.add_argument("--micro_raw_b", default="provetok/data/raw/micro_history_b.jsonl")
    p.add_argument("--micro_sealed_b", default="provetok/data/sealed/micro_history_b.sealed.jsonl")
    p.add_argument("--micro_codebook_b", default="provetok/data/sealed/micro_history_b.sealed.codebook.json")

    # scale dataset (optional; requires private codebooks, so not publicly reproducible by default)
    p.add_argument("--scale_dataset_dir", default="")

    # LLM config (default to OPENAI_* envs to match repo .env)
    p.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "deepseek-chat"))
    p.add_argument("--api_base", default=os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1"))
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    if out_dir.exists() and args.overwrite:
        # Shallow clear: only remove known outputs, keep directory.
        for name in ["summary.json", "summary.md", "run_meta.json", "run.log", "micro_A.json", "micro_B.json", "scale_A.json", "scale_B.json"]:
            pth = out_dir / name
            if pth.exists():
                pth.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = _require_api_key()
    api_base = _normalize_api_base(str(args.api_base))
    llm = LLMClient(
        LLMConfig(
            model=str(args.model),
            api_base=api_base,
            api_key=api_key,
            temperature=0.0,
            max_tokens=512,
        )
    )
    if not llm.is_configured():
        raise RuntimeError("LLM client not configured; ensure `openai` is installed and the API key/base URL are valid")

    t0 = time.time()
    seed = int(args.seed)
    n_samples = int(args.n_samples)
    top_k = int(args.top_k)

    # Micro A/B
    micro = {}
    for track in ["A", "B"]:
        sealed_path = Path(getattr(args, f"micro_sealed_{track.lower()}"))
        codebook_path = Path(getattr(args, f"micro_codebook_{track.lower()}"))
        raw_path = Path(getattr(args, f"micro_raw_{track.lower()}"))

        sealed = load_records(sealed_path)
        _ = load_records(raw_path)  # loaded to keep the pairing explicit in metadata
        pseudo_to_real = _load_codebook_reverse(codebook_path)
        trials = _build_trials(sealed, pseudo_to_real, seed=seed, n_samples=n_samples)

        res = _term_recovery_run(llm=llm, trials=trials, top_k=top_k)
        micro[track] = {
            "inputs": {
                "sealed": str(sealed_path),
                "raw": str(raw_path),
                "codebook": str(codebook_path),
                "codebook_sha256": _sha256_file(codebook_path),
            },
            "term_recovery": res,
        }
        (out_dir / f"micro_{track}.json").write_text(json.dumps(micro[track], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Optional scale (uses private codebooks; record explicitly as such).
    scale = {}
    if str(args.scale_dataset_dir or "").strip():
        ds = Path(str(args.scale_dataset_dir))
        for track in ["A", "B"]:
            sealed_path = ds / f"track_{track}_sealed.jsonl"
            codebook_path = ds / f"track_{track}_sealed.codebook.json"
            raw_path = ds / f"track_{track}_raw.jsonl"
            sealed = load_records(sealed_path)
            _ = load_records(raw_path)
            pseudo_to_real = _load_codebook_reverse(codebook_path)
            trials = _build_trials(sealed, pseudo_to_real, seed=seed, n_samples=n_samples)
            res = _term_recovery_run(llm=llm, trials=trials, top_k=top_k)
            scale[track] = {
                "inputs": {
                    "sealed": str(sealed_path),
                    "raw": str(raw_path),
                    "codebook": str(codebook_path),
                    "codebook_sha256": _sha256_file(codebook_path),
                    "note": "Scale codebooks are private; this section is not publicly reproducible unless codebooks are released.",
                },
                "term_recovery": res,
            }
            (out_dir / f"scale_{track}.json").write_text(json.dumps(scale[track], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Heuristic proxies (existing artifacts).
    heuristic = {
        "micro": {
            "A": _load_heuristic_attack(Path("runs/EXP-011/attacks/A_sealed.json")),
            "B": _load_heuristic_attack(Path("runs/EXP-011/attacks/B_sealed.json")),
        },
        "scale": {
            "A": _load_heuristic_attack(Path("runs/EXP-022/attacks/A_sealed.json")),
            "B": _load_heuristic_attack(Path("runs/EXP-022/attacks/B_sealed.json")),
        },
    }

    elapsed = time.time() - t0
    meta = {
        "created_ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "seed": seed,
        "n_samples": n_samples,
        "top_k": top_k,
        "llm": {
            "model": str(args.model),
            "api_base": str(api_base),
            "api_key_env_used": "OPENAI_API_KEY" if os.environ.get("OPENAI_API_KEY", "").strip() else "LLM_API_KEY",
        },
        "runtime": {"elapsed_sec": round(float(elapsed), 3)},
    }
    summary = {
        "meta": meta,
        "micro": {
            "A": {"hit@1": micro["A"]["term_recovery"]["hit@1"], f"hit@{top_k}": micro["A"]["term_recovery"][f"hit@{top_k}"]},
            "B": {"hit@1": micro["B"]["term_recovery"]["hit@1"], f"hit@{top_k}": micro["B"]["term_recovery"][f"hit@{top_k}"]},
        },
        "scale": {
            "A": {"hit@1": scale.get("A", {}).get("term_recovery", {}).get("hit@1"), f"hit@{top_k}": scale.get("A", {}).get("term_recovery", {}).get(f"hit@{top_k}")},
            "B": {"hit@1": scale.get("B", {}).get("term_recovery", {}).get("hit@1"), f"hit@{top_k}": scale.get("B", {}).get("term_recovery", {}).get(f"hit@{top_k}")},
        },
        "heuristic_proxy": {
            "micro": {
                "A_black_box_composite": heuristic["micro"]["A"]["black_box"]["composite_leakage"],
                "B_black_box_composite": heuristic["micro"]["B"]["black_box"]["composite_leakage"],
            },
            "scale": {
                "A_black_box_composite": heuristic["scale"]["A"]["black_box"]["composite_leakage"],
                "B_black_box_composite": heuristic["scale"]["B"]["black_box"]["composite_leakage"],
            },
        },
    }

    (out_dir / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# LLM Attacker Calibration (Term Recovery)\n")
    md.append(f"- n_samples: `{n_samples}` per track\n")
    md.append(f"- hit@1 / hit@{top_k}: micro(A,B)=`{summary['micro']['A']['hit@1']}`,`{summary['micro']['B']['hit@1']}` / `{summary['micro']['A'][f'hit@{top_k}']}`,`{summary['micro']['B'][f'hit@{top_k}']}`\n")
    if scale:
        md.append(f"- scale hit@1 / hit@{top_k}: A,B=`{summary['scale']['A']['hit@1']}`,`{summary['scale']['B']['hit@1']}` / `{summary['scale']['A'][f'hit@{top_k}']}`,`{summary['scale']['B'][f'hit@{top_k}']}`\n")
    md.append("\n## Heuristic Proxy (Existing Composite Leakage)\n")
    md.append(f"- micro black-box composite: A=`{summary['heuristic_proxy']['micro']['A_black_box_composite']}`, B=`{summary['heuristic_proxy']['micro']['B_black_box_composite']}`\n")
    md.append(f"- scale black-box composite: A=`{summary['heuristic_proxy']['scale']['A_black_box_composite']}`, B=`{summary['heuristic_proxy']['scale']['B_black_box_composite']}`\n")
    md.append("\nArtifacts:\n")
    md.append(f"- `runs/EXP-032/summary.json`\n")
    md.append(f"- `runs/EXP-032/micro_A.json`, `runs/EXP-032/micro_B.json`\n")
    if scale:
        md.append(f"- `runs/EXP-032/scale_A.json`, `runs/EXP-032/scale_B.json` (private-codebook dependent)\n")
    (out_dir / "summary.md").write_text("".join(md), encoding="utf-8")

    (out_dir / "run.log").write_text("OK\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
