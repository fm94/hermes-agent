"""Regression tests for OpenCode Zen model picker limits."""

import os
from unittest.mock import patch

import hermes_cli.providers as providers_mod
from hermes_cli.model_switch import list_authenticated_providers


def test_opencode_zen_lists_all_models_while_other_providers_remain_capped(monkeypatch):
    """OpenCode Zen is an aggregator product, so the picker must expose its full catalog."""
    zen_models = [f"zen-model-{i}" for i in range(57)]
    dsx_models = [f"dsx-model-{i}" for i in range(57)]

    monkeypatch.setattr(
        "agent.models_dev.PROVIDER_TO_MODELS_DEV",
        {
            "opencode-zen": "opencode",
            "dsx": "dsx",
        },
    )
    monkeypatch.setattr(
        "agent.models_dev.fetch_models_dev",
        lambda: {"opencode": {}, "dsx": {}},
    )
    monkeypatch.setattr(providers_mod, "HERMES_OVERLAYS", {})
    monkeypatch.setattr(
        "hermes_cli.models.cached_provider_model_ids",
        lambda provider, **_: {
            "opencode-zen": zen_models,
            "dsx": dsx_models,
        }.get(provider, []),
    )

    with patch.dict(
        os.environ,
        {
            "OPENCODE_ZEN_API_KEY": "test-zen-key",
            "DSX_API_KEY": "test-dsx-key",
        },
        clear=False,
    ):
        providers = list_authenticated_providers(max_models=50)

    opencode_zen = next(p for p in providers if p["slug"] == "opencode-zen")
    dsx = next(p for p in providers if p["slug"] == "dsx")

    assert opencode_zen["models"] == zen_models
    assert opencode_zen["total_models"] == len(zen_models)
    assert dsx["models"] == dsx_models[:50]
    assert dsx["total_models"] == len(dsx_models)
