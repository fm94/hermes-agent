"""Unit tests for the Dsx provider profile's thinking-mode wiring.

Dsx V4 expects every request to carry an explicit ``extra_body.thinking``
parameter.  Omitting it makes the server default to thinking-mode ON, which
then enforces the ``reasoning_content``-must-be-echoed-back contract on
subsequent turns and breaks the conversation with HTTP 400 (#15700, #17212,
#17825).

These tests pin the profile's wire-shape contract so Dsx requests stay
correctly shaped without going live.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def dsx_profile():
    """Resolve the registered Dsx profile.

    Going through ``providers.get_provider_profile`` keeps the test honest —
    if someone later replaces the registered class with a plain
    ``ProviderProfile``, every assertion below collapses.
    """
    # ``model_tools`` triggers plugin discovery on import, which is what
    # registers the Dsx profile in the global provider registry.
    import model_tools
    import providers

    profile = providers.get_provider_profile("dsx")
    assert profile is not None, "dsx provider profile must be registered"
    return profile


class TestDsxThinkingWireShape:
    """``build_api_kwargs_extras`` produces Dsx's exact wire format."""

    def test_v4_pro_default_enables_thinking_without_effort(self, dsx_profile):
        """No reasoning_config → thinking enabled, server picks default effort."""
        extra_body, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config=None, model="dsx-v4-pro"
        )
        assert extra_body == {"thinking": {"type": "enabled"}}
        assert top_level == {}


    @pytest.mark.parametrize("effort", ["low", "medium", "high"])
    def test_standard_efforts_pass_through(self, dsx_profile, effort):
        _, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="dsx-v4-pro",
        )
        assert top_level == {"reasoning_effort": effort}

    @pytest.mark.parametrize("effort", ["xhigh", "max", "MAX", "  Max  "])
    def test_xhigh_and_max_normalize_to_max(self, dsx_profile, effort):
        _, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="dsx-v4-pro",
        )
        assert top_level == {"reasoning_effort": "max"}

    def test_explicitly_disabled_sends_disabled_marker(self, dsx_profile):
        """``reasoning_config.enabled=False`` → ``thinking.type=disabled``.

        The crucial bit is that the parameter is *sent* at all — Dsx
        defaults to thinking-on when ``thinking`` is absent.
        """
        extra_body, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False}, model="dsx-v4-pro"
        )
        assert extra_body == {"thinking": {"type": "disabled"}}
        # No effort when disabled — Dsx rejects it.
        assert top_level == {}

    @pytest.mark.parametrize(
        "reasoning_config",
        [
            {"effort": "none"},
            {"effort": "false"},
            {"effort": "disabled"},
            {"effort": "NONE"},
            {"enabled": True, "effort": "none"},
        ],
    )
    def test_effort_none_without_enabled_false_sends_disabled(
        self, dsx_profile, reasoning_config
    ):
        """UI/CLI ``none`` can arrive as ``{effort: "none"}`` without ``enabled: False``.

        ``_session_info`` / ``_cfg_get_reasoning`` already report that as Off, but
        the plugin used to fall through to ``thinking: enabled`` (#107238).
        """
        extra_body, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config=reasoning_config,
            model="dsx-v4.1-flash-expires-on-0910",
        )
        assert extra_body == {"thinking": {"type": "disabled"}}
        assert top_level == {}
        assert "reasoning_effort" not in top_level

    def test_disabled_ignores_effort_field(self, dsx_profile):
        """Effort silently dropped when thinking is off."""
        _, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False, "effort": "high"},
            model="dsx-v4-pro",
        )
        assert top_level == {}

    def test_unknown_effort_omits_top_level(self, dsx_profile):
        """Garbage effort → omit reasoning_effort so Dsx applies its default."""
        _, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "garbage"},
            model="dsx-v4-pro",
        )
        assert top_level == {}

    def test_empty_effort_omits_top_level(self, dsx_profile):
        _, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": ""},
            model="dsx-v4-pro",
        )
        assert top_level == {}


class TestDsxModelGating:
    """V4 family gets thinking; V3 / unknown stay untouched."""

    @pytest.mark.parametrize(
        "model",
        [
            "dsx-v4-pro",
            "dsx-v4-flash",
            "dsx-v4-future-variant",
            "DSX-V4-PRO",  # case-insensitive
            # Version-less canonical ids (2026-09 Flash refresh) carry the
            # same thinking-mode contract but no v<N> marker.
            "dsx-flash",
            "DSX-FLASH",  # case-insensitive
        ],
    )
    def test_thinking_capable_models_emit_thinking(self, dsx_profile, model):
        extra_body, _ = dsx_profile.build_api_kwargs_extras(
            reasoning_config=None, model=model
        )
        assert extra_body == {"thinking": {"type": "enabled"}}

    @pytest.mark.parametrize(
        "model",
        [
            "dsx-v3-0324",      # explicit V3
            "dsx-v3.1",         # V3 minor revisions
            "",                       # bare/unknown
            None,                     # missing
            "dsx-unknown",      # unrecognized
        ],
    )
    def test_non_thinking_models_emit_nothing(self, dsx_profile, model):
        extra_body, top_level = dsx_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "high"}, model=model
        )
        assert extra_body == {}
        assert top_level == {}


class TestDsxFullKwargsIntegration:
    """End-to-end: the transport's full kwargs match Dsx's live wire format.

    The live test harness in ``tests/agent/test_dsx_v4_thinking_live.py``
    sends ``{"reasoning_effort": "high", "extra_body": {"thinking": {"type":
    "enabled"}}}``.  Confirm the transport produces that exact shape when wired
    through the registered Dsx profile.
    """

    def test_full_kwargs_match_live_wire_shape(self, dsx_profile):
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="dsx-v4-pro",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=dsx_profile,
            reasoning_config={"enabled": True, "effort": "high"},
            base_url="https://api.dsx.com/v1",
            provider_name="dsx",
        )
        assert kwargs["model"] == "dsx-v4-pro"
        assert kwargs["reasoning_effort"] == "high"
        assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}

    def test_v3_full_kwargs_omit_thinking(self, dsx_profile):
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="dsx-v3-0324",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=dsx_profile,
            reasoning_config={"enabled": True, "effort": "high"},
            base_url="https://api.dsx.com/v1",
            provider_name="dsx",
        )
        assert "reasoning_effort" not in kwargs
        assert "extra_body" not in kwargs or "thinking" not in kwargs.get("extra_body", {})

    def test_unset_full_kwargs_still_enable_thinking(self, dsx_profile):
        """CONTROL: rc=None on V4 must keep thinking=enabled (echo-trap / #106648)."""
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="dsx-v4.1-flash-expires-on-0910",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=dsx_profile,
            reasoning_config=None,
            base_url="https://api.dsx.com/v1",
            provider_name="dsx",
        )
        assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}
        assert "reasoning_effort" not in kwargs

    def test_effort_none_full_kwargs_disable_thinking(self, dsx_profile):
        """CLI/UI ``none`` as ``{effort: "none"}`` (no enabled:False) must disable."""
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="dsx-v4.1-flash-expires-on-0910",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=dsx_profile,
            reasoning_config={"effort": "none"},
            base_url="https://api.dsx.com/v1",
            provider_name="dsx",
        )
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
        assert "reasoning_effort" not in kwargs

    def test_cli_parse_none_full_kwargs_disable_thinking(self, dsx_profile):
        """``--reasoning none`` / ``parse_reasoning_effort('none')`` → disabled on the wire."""
        from agent.transports.chat_completions import ChatCompletionsTransport
        from hermes_constants import parse_reasoning_effort

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="dsx-v4-pro",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=dsx_profile,
            reasoning_config=parse_reasoning_effort("none"),
            base_url="https://api.dsx.com/v1",
            provider_name="dsx",
        )
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
        assert "reasoning_effort" not in kwargs


class TestDsxAuxModel:
    """Dsx aux model is set on the profile so users stop seeing the
    bogus 'No auxiliary LLM provider configured' warning (#26924).

    Pinned at the profile layer rather than the legacy
    `_API_KEY_PROVIDER_AUX_MODELS_FALLBACK` dict — new providers are
    expected to set `default_aux_model` on `ProviderProfile`, and the
    fallback dict only exists for providers that predate the profiles
    system.
    """


    def test_fallback_models_are_current_ids(self, dsx_profile):
        from hermes_cli.model_normalize import _normalize_for_dsx
        # Every advertised id must survive normalization unchanged (no retired alias in the picker).
        assert all(_normalize_for_dsx(m) == m for m in dsx_profile.fallback_models)

    def test_consumer_api_matches_profile_aux_model(self, dsx_profile):
        from agent.auxiliary_client import _get_aux_model_for_provider
        assert dsx_profile.default_aux_model
        assert _get_aux_model_for_provider("dsx") == dsx_profile.default_aux_model

