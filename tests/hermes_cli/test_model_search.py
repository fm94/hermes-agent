"""Picker search aliases for brand-less wire model ids."""

from hermes_cli.curses_ui import _filter_indices
from hermes_cli.model_search import model_search_text


def test_model_search_text_keeps_ordinary_ids():
    assert model_search_text("kmx-k2.6") == "kmx-k2.6"
    assert model_search_text("glx-5.2") == "glx-5.2"


def test_filter_indices_surfaces_k3_for_kmx_query():
    models = ["kmx-k2.6", "kmx-k2.5", "k3", "kmx-for-coding"]
    haystacks = [model_search_text(m) for m in models]
    ranked = [models[i] for i in _filter_indices(haystacks, "kmx")]
    assert "k3" in ranked


def test_filter_indices_surfaces_ox_alpha_preview_slug():
    models = ["x-preview-f-free", "gpt-5.6-sol", "kmx-k3"]
    haystacks = [model_search_text(m) for m in models]
    for query in ("ox", "ox-alpha"):
        ranked = [models[i] for i in _filter_indices(haystacks, query)]
        assert "x-preview-f-free" in ranked, query
