"""Tests for formula graph extraction from arXiv-like sources."""

import io
import tarfile
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from provetok.dataset.formula_graph import extract_formula_graph_from_source_paths


def test_extract_formula_graph_from_tar_source():
    tex = r"""
    % comment line
    We define $x + y = z$ and also:
    \begin{equation}
      \frac{a}{b} = c
    \end{equation}
    """

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "1234.56789.source"

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            info = tarfile.TarInfo(name="main.tex")
            blob = tex.encode("utf-8")
            info.size = len(blob)
            tf.addfile(info, io.BytesIO(blob))

        out.write_bytes(buf.getvalue())

        graph, status, reason = extract_formula_graph_from_source_paths([str(out)])
        assert status == "ok", (status, reason)
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0
        assert any(op in graph.ops for op in ("+", "=", "frac"))

