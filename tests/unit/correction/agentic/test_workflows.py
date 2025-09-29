import pytest

from lyrics_transcriber.correction.agentic.workflows.correction_graph import build_correction_graph


def test_build_correction_graph_safe_without_langgraph_installed(monkeypatch):
    # If langgraph not installed, the function should return None safely
    g = build_correction_graph()
    # Either None (no dependency) or a compiled graph object
    assert g is None or hasattr(g, "invoke")


