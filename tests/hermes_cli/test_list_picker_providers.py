"""Tests for ``list_picker_providers`` — the /model picker filter.

``list_picker_providers`` wraps ``list_authenticated_providers`` and
post-processes the result for interactive pickers (Telegram, Discord):

- OpenRouter's ``models`` are replaced with the live-filtered output of
  ``fetch_openrouter_models``, so IDs the live catalog no longer carries
  drop out.
- Provider rows with an empty ``models`` list are dropped, except custom
  endpoints (``is_user_defined=True`` with an ``api_url``) where the user
  may supply their own model set through config.

These tests exercise the filter in isolation by mocking
``list_authenticated_providers`` and ``fetch_openrouter_models`` so no
network or auth state is required.
"""

import pytest
from hermes_cli import model_switch
import hermes_cli.models as models_mod
import hermes_cli.model_switch_providers as hermes_cli_model_switch_providers
from hermes_cli import model_switch_providers


@pytest.fixture(autouse=True)
def _disable_live_custom_provider_model_probe(monkeypatch):
    """Keep custom-provider picker fixtures independent of local model servers."""
    monkeypatch.setattr("hermes_cli.models.fetch_api_models", lambda *_a, **_kw: None)


def _make_provider(slug, name=None, models=None, *, is_current=False,
                   is_user_defined=False, source="built-in", api_url=None):
    """Build a dict shaped like ``list_authenticated_providers`` output."""
    entry = {
        "slug": slug,
        "name": name or slug.title(),
        "is_current": is_current,
        "is_user_defined": is_user_defined,
        "models": list(models or []),
        "total_models": len(models or []),
        "source": source,
    }
    if api_url is not None:
        entry["api_url"] = api_url
    return entry


















def test_passthrough_kwargs_to_base(monkeypatch):
    """All kwargs must be forwarded to ``list_authenticated_providers`` unchanged.

    The gateway /model picker passes ``current_base_url`` and ``current_model``
    so custom endpoint grouping can mark the current row. Dropping those kwargs
    regressed Telegram/Discord into the text-list fallback.
    """
    captured = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(model_switch, "list_authenticated_providers", _capture)
    monkeypatch.setattr(hermes_cli_model_switch_providers, "list_authenticated_providers", _capture)
    monkeypatch.setattr("hermes_cli.models.fetch_openrouter_models",
                        lambda *a, **kw: [])

    model_switch_providers.list_picker_providers(
        current_provider="openrouter",
        current_base_url="http://x",
        current_model="openai/gpt-5.4",
        user_providers={"foo": {"api": "http://x"}},
        custom_providers=[{"name": "bar", "base_url": "http://y"}],
        max_models=12,
    )

    assert captured["current_provider"] == "openrouter"
    assert captured["current_base_url"] == "http://x"
    assert captured["current_model"] == "openai/gpt-5.4"
    assert captured["user_providers"] == {"foo": {"api": "http://x"}}
    assert captured["custom_providers"] == [{"name": "bar", "base_url": "http://y"}]
    assert captured["max_models"] == 12



def test_current_custom_endpoint_passthrough_marks_current_row(monkeypatch):
    """Interactive picker should preserve current custom endpoint semantics."""
    monkeypatch.setattr("agent.models_dev.fetch_models_dev", dict)
    monkeypatch.setattr("agent.models_dev.PROVIDER_TO_MODELS_DEV", {})
    monkeypatch.setattr("hermes_cli.providers.HERMES_OVERLAYS", {})
    monkeypatch.setattr("hermes_cli.models.fetch_openrouter_models",
                        lambda *a, **kw: [])

    result = model_switch_providers.list_picker_providers(
        current_provider="custom:ollama",
        current_base_url="http://localhost:11434/v1",
        current_model="glx-5.1",
        user_providers={},
        custom_providers=[
            {
                "name": "Ollama — GLX 5.1",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "model": "glx-5.1",
                "discover_models": False,
            },
            {
                "name": "Ollama — Qwx3",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
                "model": "qwx3",
                "discover_models": False,
            },
        ],
        max_models=50,
    )

    custom_rows = [p for p in result if p.get("is_user_defined")]
    assert len(custom_rows) == 1
    row = custom_rows[0]
    assert row["slug"] == "custom:ollama"
    assert row["is_current"] is True
    assert row["models"] == ["glx-5.1", "qwx3"]



# ---------------------------------------------------------------------------
# list_authenticated_providers: alias/canonical de-dup for Kmx (#49439)
# ---------------------------------------------------------------------------
#
# A single Kmx credential used to surface TWO picker rows: the alias slug
# "kmx" (emitted by the PROVIDER_TO_MODELS_DEV pass) plus its canonical
# "kmx-coding" (re-emitted by the CANONICAL_PROVIDERS cross-check pass),
# both backed by the same kmx-for-coding models.dev provider. The picker
# must list each authenticated credential exactly once, under the CANONICAL
# slug ("kmx-coding") — matching list_authenticated_providers' other alias
# rows and the overlay slug-resolution contract (see
# test_overlay_slug_resolution.py).


def _stub_kmx_discovery(monkeypatch, *, canonical):
    """Isolate list_authenticated_providers to the Kmx alias family.

    Restricts the models.dev map / catalog / overlays / canonical list to
    just the Kmx entries and stubs the model-id fetch so discovery stays
    offline and deterministic. ``canonical`` is the CANONICAL_PROVIDERS list
    the 2b cross-check pass should iterate.
    """
    import agent.models_dev as md
    import hermes_cli.models as hm
    import hermes_cli.models_catalog_static as hermes_cli_models_catalog_static
    from hermes_cli import models_catalog_static

    kmx_map = {
        "kmx": "kmx-for-coding",
        "kmx-coding": "kmx-for-coding",
        "mshx": "kmx-for-coding",
        "kmx-coding-cn": "kmx-for-coding",
    }
    monkeypatch.setattr(md, "PROVIDER_TO_MODELS_DEV", kmx_map)
    monkeypatch.setattr(
        md, "fetch_models_dev",
        lambda *a, **k: {
            "kmx-for-coding": {"name": "Kmx For Coding", "env": ["KMX_API_KEY"]},
        },
    )

    class _PInfo:
        name = "Kmx For Coding"

    monkeypatch.setattr(md, "get_provider_info", lambda _pid: _PInfo())
    monkeypatch.setattr("hermes_cli.providers.HERMES_OVERLAYS", {})
    monkeypatch.setattr(hm, "CANONICAL_PROVIDERS", canonical)
    monkeypatch.setattr(hermes_cli_models_catalog_static, "CANONICAL_PROVIDERS", canonical)
    monkeypatch.setattr(hm, "cached_provider_model_ids",
                        lambda *a, **k: ["kmx-k2.6", "kmx-k2.5"])
    monkeypatch.setattr(hm, "clear_provider_models_cache", lambda *a, **k: None)


def test_single_kmx_credential_yields_one_canonical_row(monkeypatch):
    """One Kmx key yields a single row under the canonical 'kmx-coding' slug."""
    import hermes_cli.models as hm
    from hermes_cli import models_catalog_static

    _stub_kmx_discovery(
        monkeypatch,
        canonical=[models_catalog_static.ProviderEntry("kmx-coding", "Kmx / Kmx Coding Plan", "desc")],
    )
    monkeypatch.setenv("KMX_API_KEY", "sk-test-kmx")

    rows = model_switch.list_authenticated_providers(max_models=10)
    slugs = [r["slug"] for r in rows]

    # Exactly one Kmx / kmx-for-coding-backed row, under the canonical slug —
    # not both the alias ("kmx") and its canonical ("kmx-coding").
    kmx_rows = [s for s in slugs if s in {"kmx", "kmx-coding"}]
    assert kmx_rows == ["kmx-coding"], (
        f"expected a single canonical Kmx row, got: {slugs}"
    )
    assert slugs.count("kmx-coding") == 1
    assert "kmx" not in slugs


def test_distinct_kmx_china_credential_still_listed(monkeypatch):
    """A separate China (kmx-coding-cn) credential remains its own row.

    Negative-control guard: the de-dup must collapse only the alias/canonical
    pair that share a credential, not legitimately distinct providers.
    """
    import hermes_cli.models as hm
    from hermes_cli import models_catalog_static

    _stub_kmx_discovery(
        monkeypatch,
        canonical=[
            models_catalog_static.ProviderEntry("kmx-coding", "Kmx / Kmx Coding Plan", "desc"),
            models_catalog_static.ProviderEntry("kmx-coding-cn", "Kmx / Mshx (China)", "desc"),
        ],
    )
    monkeypatch.setenv("KMX_API_KEY", "sk-test-kmx")
    monkeypatch.setenv("KMX_CN_API_KEY", "sk-test-kmx-cn")

    rows = model_switch.list_authenticated_providers(max_models=10)
    slugs = [r["slug"] for r in rows]

    assert "kmx-coding" in slugs       # canonical global row
    assert slugs.count("kmx-coding") == 1
    assert "kmx" not in slugs          # alias collapsed into the canonical row
    assert "kmx-coding-cn" in slugs    # distinct China endpoint preserved


def test_non_blocking_listing_opens_no_socket(monkeypatch, tmp_path):
    """#74003: ``non_blocking_catalogs=True`` must not run a single live catalog probe in the calling
    thread — not the per-provider ``/models`` prefetch and not OpenRouter's curated-catalog GET —
    even with several credentialed providers and an empty on-disk cache."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(models_mod, "_openrouter_catalog_cache", None)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DSX_API_KEY", "GROQ_API_KEY",
                "MISTRAL_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.setenv(key, "dummy")
    (tmp_path / "provider_models_cache.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda *a, **k: {})

    live: list[str] = []

    def _live_probe(*args, **kwargs):
        live.append((args, kwargs))
        return []

    monkeypatch.setattr(models_mod, "provider_model_ids", _live_probe)
    monkeypatch.setattr(models_mod, "fetch_api_models", _live_probe)
    monkeypatch.setattr(models_mod, "_fetch_live_catalog_index", _live_probe)
    monkeypatch.setattr(models_mod, "_spawn_swr_refresh", lambda *a, **k: None)  # background warm is not "live"

    rows = model_switch_providers.list_picker_providers(
        max_models=50, include_moa=True, current_provider="openrouter", user_providers={},
        custom_providers=[], excluded_providers=[], non_blocking_catalogs=True)

    assert live == [], f"cache-only listing ran live probes in the request path: {live}"
    assert any(r.get("slug") == "openrouter" and r.get("models") for r in rows), "OpenRouter row lost its curated snapshot"


def test_curated_openrouter_row_keeps_free_tail_past_max_models(monkeypatch):
    """The OpenRouter row is already curated; its bottom "Free tier" block must survive the picker cap
    while an ordinary provider row stays capped."""
    curated = [(f"vendor/model-{i}", "") for i in range(55)] + [("stealth/free-model", "free, stealth model")]
    other = [f"other-{i}" for i in range(60)]
    monkeypatch.setattr(model_switch, "list_authenticated_providers", lambda **_: [
        _make_provider("openrouter", models=[mid for mid, _ in curated][:50]),
        _make_provider("dsx", models=other[:50]) | {"total_models": len(other)},
    ])
    monkeypatch.setattr(models_mod, "fetch_openrouter_models", lambda **_: curated)

    rows = {r["slug"]: r for r in model_switch_providers.list_picker_providers(max_models=50)}

    assert rows["openrouter"]["models"] == [mid for mid, _ in curated]
    assert len(rows["dsx"]["models"]) == 50
