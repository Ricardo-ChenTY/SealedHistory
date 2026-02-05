"""Best-effort formula graph extraction from arXiv TeX sources.

This module is intentionally lightweight and dependency-free. It aims to
populate `PaperRecordV2.formula_graph` for arXiv-source papers while keeping
failure modes explicit and auditable (manual queue).
"""

from __future__ import annotations

import logging
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from provetok.data.schema_v2 import FormulaGraph

logger = logging.getLogger(__name__)


_MATH_ENVS = (
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
)

_ENV_RE = re.compile(
    r"\\\\begin\\{(" + "|".join(re.escape(e) for e in _MATH_ENVS) + r")\\}(.*?)\\\\end\\{\\1\\}",
    flags=re.DOTALL,
)

_BRACKET_RE = re.compile(r"\\\\\\[(.*?)\\\\\\]", flags=re.DOTALL)
_PAREN_RE = re.compile(r"\\\\\\((.*?)\\\\\\)", flags=re.DOTALL)
_DOLLAR_BLOCK_RE = re.compile(r"\\$\\$(.*?)\\$\\$", flags=re.DOTALL)


_OP_CMDS = {
    "sum",
    "prod",
    "int",
    "log",
    "ln",
    "exp",
    "max",
    "min",
    "argmax",
    "argmin",
    "softmax",
    "cdot",
    "times",
    "frac",
    "sqrt",
}

_GREEK = {
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "pi",
    "rho",
    "sigma",
    "tau",
    "upsilon",
    "phi",
    "chi",
    "psi",
    "omega",
}

_IGNORE_CMDS = {
    "left",
    "right",
    "mathbf",
    "mathrm",
    "mathbb",
    "mathcal",
    "mathsf",
    "mathtt",
    "text",
    "operatorname",
    "label",
    "ref",
    "cite",
    "tag",
    "nonumber",
    "quad",
    "qquad",
    "displaystyle",
    "textstyle",
    "scriptstyle",
    "scriptscriptstyle",
}


def _strip_comments(tex: str) -> str:
    out_lines: List[str] = []
    for line in tex.splitlines():
        i = 0
        while True:
            idx = line.find("%", i)
            if idx < 0:
                out_lines.append(line)
                break
            # Escaped percent \% should be kept.
            if idx > 0 and line[idx - 1] == "\\":
                i = idx + 1
                continue
            out_lines.append(line[:idx])
            break
    return "\n".join(out_lines)


def _iter_tex_blobs_from_tar(tf: tarfile.TarFile) -> Iterable[Tuple[str, bytes]]:
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = str(m.name or "")
        if not name.lower().endswith(".tex"):
            continue
        f = tf.extractfile(m)
        if f is None:
            continue
        with f:
            yield name, f.read()


def _iter_tex_blobs_from_zip(zf: zipfile.ZipFile) -> Iterable[Tuple[str, bytes]]:
    for name in zf.namelist():
        if not str(name).lower().endswith(".tex"):
            continue
        yield name, zf.read(name)


def _read_tex_sources(
    source_path: Path,
    *,
    max_tex_files: int = 50,
    max_tex_bytes_total: int = 2_000_000,
) -> Tuple[List[str], str]:
    """Return (tex_texts, reason)."""
    # Prefer archive detection helpers to keep control flow explicit.
    if tarfile.is_tarfile(source_path):
        texts: List[str] = []
        total = 0
        with tarfile.open(source_path, mode="r:*") as tf:
            for _, blob in _iter_tex_blobs_from_tar(tf):
                if len(texts) >= max_tex_files:
                    break
                if total + len(blob) > max_tex_bytes_total:
                    break
                total += len(blob)
                texts.append(blob.decode("utf-8", errors="replace"))
        if texts:
            return texts, "tar_tex"

    if zipfile.is_zipfile(source_path):
        texts = []
        total = 0
        with zipfile.ZipFile(source_path) as zf:
            for _, blob in _iter_tex_blobs_from_zip(zf):
                if len(texts) >= max_tex_files:
                    break
                if total + len(blob) > max_tex_bytes_total:
                    break
                total += len(blob)
                texts.append(blob.decode("utf-8", errors="replace"))
        if texts:
            return texts, "zip_tex"

    # Fallback: treat as plain text.
    text = source_path.read_text(encoding="utf-8", errors="replace")
    if text.strip():
        return [text], "plain_text"

    return [], "no_tex"


def _extract_inline_dollar_math(tex: str, *, max_expr: int) -> List[str]:
    """Very lightweight $...$ extractor that avoids $$...$$ blocks."""
    out: List[str] = []
    s = tex
    i = 0
    n = len(s)
    while i < n and len(out) < max_expr:
        if s[i] != "$":
            i += 1
            continue
        # Skip $$...$$ (handled elsewhere)
        if i + 1 < n and s[i + 1] == "$":
            i += 2
            continue
        j = s.find("$", i + 1)
        if j < 0:
            break
        expr = s[i + 1 : j]
        if expr.strip():
            out.append(expr)
        i = j + 1
    return out


def _extract_math_expressions(tex: str, *, max_expr: int = 200) -> List[str]:
    tex = _strip_comments(tex)

    exprs: List[str] = []
    for m in _ENV_RE.finditer(tex):
        exprs.append(m.group(2))
        if len(exprs) >= max_expr:
            return exprs[:max_expr]

    for pat in (_BRACKET_RE, _PAREN_RE, _DOLLAR_BLOCK_RE):
        for m in pat.finditer(tex):
            exprs.append(m.group(1))
            if len(exprs) >= max_expr:
                return exprs[:max_expr]

    exprs.extend(_extract_inline_dollar_math(tex, max_expr=max(0, max_expr - len(exprs))))
    return exprs[:max_expr]


def _tokenize_math(expr: str, *, max_tokens: int = 200) -> List[Tuple[str, str]]:
    tokens: List[Tuple[str, str]] = []
    s = str(expr or "")
    i = 0
    n = len(s)

    def add(typ: str, val: str) -> None:
        if not val:
            return
        tokens.append((typ, val))

    while i < n and len(tokens) < max_tokens:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue

        if ch == "\\":
            m = re.match(r"\\\\[A-Za-z]+", s[i:])
            if m:
                cmd = m.group(0)[1:].lower()
                if cmd in _IGNORE_CMDS:
                    i += len(m.group(0))
                    continue
                if cmd in _OP_CMDS:
                    add("op", cmd)
                elif cmd in _GREEK:
                    add("symbol", cmd)
                # else: ignore unknown LaTeX commands (formatting)
                i += len(m.group(0))
                continue

        if ch.isalpha():
            m = re.match(r"[A-Za-z][A-Za-z0-9]*", s[i:])
            if m:
                add("symbol", m.group(0).lower())
                i += len(m.group(0))
                continue

        if ch.isdigit():
            # Keep small numeric constants as symbols (publish-safe).
            m = re.match(r"\\d+(?:\\.\\d+)?", s[i:])
            if m:
                add("symbol", m.group(0))
                i += len(m.group(0))
                continue

        if ch in "+-*/=<>^_":
            add("op", ch)
            i += 1
            continue

        i += 1

    return tokens


def extract_formula_graph_from_source_paths(
    source_paths: List[str],
    *,
    max_tex_files: int = 50,
    max_tex_bytes_total: int = 2_000_000,
    max_math_expressions: int = 200,
    max_nodes: int = 200,
    max_edges: int = 500,
) -> Tuple[FormulaGraph, str, str]:
    """Build a best-effort `FormulaGraph` from arXiv source paths.

    Returns:
        (graph, status, reason)

    Status is one of: ok | empty | missing_source | error.
    """
    src_candidates: List[Path] = []
    for p in source_paths or []:
        sp = Path(str(p))
        low = sp.name.lower()
        if low.endswith(".source") or low.endswith(".tar") or low.endswith(".tgz") or low.endswith(".tar.gz") or low.endswith(".zip") or low.endswith(".gz"):
            src_candidates.append(sp)
    src = src_candidates[0] if src_candidates else None

    if src is None or not src.exists():
        return FormulaGraph(), "missing_source", "no_source_archive"

    tex_texts, tex_reason = _read_tex_sources(
        src,
        max_tex_files=max_tex_files,
        max_tex_bytes_total=max_tex_bytes_total,
    )

    if not tex_texts:
        return FormulaGraph(), "empty", f"no_tex:{tex_reason}"

    node_by_id: Dict[str, Dict[str, Any]] = {}
    edge_counts: Dict[Tuple[str, str], int] = {}
    ops_seen: set[str] = set()

    n_expr_total = 0
    for tex in tex_texts:
        exprs = _extract_math_expressions(tex, max_expr=max_math_expressions)
        for expr in exprs:
            n_expr_total += 1
            toks = _tokenize_math(expr, max_tokens=200)
            if not toks:
                continue

            ids: List[str] = []
            for typ, val in toks:
                node_id = f"{typ}:{val}"
                if node_id not in node_by_id:
                    if len(node_by_id) >= max_nodes:
                        continue
                    node_by_id[node_id] = {"id": node_id, "type": typ, "value": val}
                ids.append(node_id)
                if typ == "op":
                    ops_seen.add(val)

            for a, b in zip(ids, ids[1:]):
                if len(edge_counts) >= max_edges and (a, b) not in edge_counts:
                    continue
                edge_counts[(a, b)] = edge_counts.get((a, b), 0) + 1

    edges = [{"src": a, "dst": b, "count": c} for (a, b), c in edge_counts.items()]
    graph = FormulaGraph(nodes=list(node_by_id.values()), edges=edges, ops=sorted(ops_seen))

    if not graph.nodes:
        return graph, "empty", "no_tokens"

    return graph, "ok", f"expressions={n_expr_total}"

