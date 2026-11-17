"""Unit tests for the Z.AI / GLX provider profile's reasoning wiring.

Z.AI's GLX-4.5-and-later chat models default to thinking-mode ON when the
request omits ``thinking``.  Before the profile emitted the parameter,
``reasoning_config = {"enabled": False}`` was a silent no-op on the direct
Z.AI route — users who turned thinking off kept burning thinking tokens on
every turn (the desktop "thinking reverts to medium" report).

GLX-5.2 additionally exposes a native ``reasoning_effort`` knob with two
enabled levels (high / max) on the OpenAI-compatible ``/api/paas/v4``
endpoint; the Hermes effort scale is collapsed onto those.

These tests pin the profile's wire-shape contract so Z.AI requests stay
correctly shaped without going live.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def zai_profile():
    """Resolve the registered Z.AI profile through the real discovery path."""
    # ``model_tools`` triggers plugin discovery on import, which is what
    # registers the Z.AI profile in the global provider registry.
    import model_tools
    import providers

    profile = providers.get_provider_profile("zai")
    assert profile is not None, "zai provider profile must be registered"
    return profile


class TestZaiThinkingWireShape:
    """``build_api_kwargs_extras`` produces Z.AI's exact wire format."""

    def test_no_preference_omits_thinking(self, zai_profile):
        """No reasoning_config → omit ``thinking`` so the server default
        applies (matches prior behavior for users with no preference)."""
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config=None, model="glx-5"
        )
        assert extra_body == {}
        assert top_level == {}

    def test_enabled_sends_enabled_marker(self, zai_profile):
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "medium"}, model="glx-5"
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {}

    def test_explicitly_disabled_sends_disabled_marker(self, zai_profile):
        """``reasoning_config.enabled=False`` → ``thinking.type=disabled``.

        The crucial bit is that the parameter is *sent* at all — GLX defaults
        to thinking-on when ``thinking`` is absent, so an unsent disable
        burns thinking tokens forever.
        """
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False}, model="glx-5"
        )
        assert extra_body == {"thinking": {"type": "disabled"}}
        assert top_level == {}


class TestZaiGLX52ReasoningEffort:
    """GLX-5.2's native ``reasoning_effort`` knob (two enabled levels)."""

    def test_high_maps_to_high(self, zai_profile):
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "high"},
            model="glx-5.2",
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {"reasoning_effort": "high"}

    @pytest.mark.parametrize("effort", ["low", "medium", "minimal"])
    def test_lower_efforts_clamp_up_to_high(self, zai_profile, effort):
        """GLX-5.2's minimum thinking level is high — lower Hermes levels
        clamp onto it."""
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="glx-5.2",
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {"reasoning_effort": "high"}

    @pytest.mark.parametrize("effort", ["xhigh", "max"])
    def test_strong_efforts_map_to_max(self, zai_profile, effort):
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="glx-5.2",
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {"reasoning_effort": "max"}

    def test_disabled_sends_no_effort(self, zai_profile):
        """Disabled reasoning still sends the thinking-off marker but never
        an effort level."""
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False, "effort": "high"},
            model="glx-5.2",
        )
        assert extra_body == {"thinking": {"type": "disabled"}}
        assert top_level == {}

    @pytest.mark.parametrize(
        "model",
        [
            "z-ai/glx-5.2",
            "glx-5-2",
            "glx-5p2",
            "accounts/fireworks/models/glx-5p2",
            "zai-org-glx-5-2",
        ],
    )
    def test_alias_spellings_recognized(self, zai_profile, model):
        _, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "max"},
            model=model,
        )
        assert top_level == {"reasoning_effort": "max"}

    @pytest.mark.parametrize(
        "model",
        ["glx-5.1", "glx-5", "glx-4.7", "glx-4-9b", "", None],
    )
    def test_non_glx_5_2_models_get_no_effort(self, zai_profile, model):
        _, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "high"},
            model=model,
        )
        assert top_level == {}


class TestZaiGLX53ReasoningEffort:
    """GLX-5.3's graded low/medium/high/max effort scale (issue #91789).

    Verified live on api.z.ai/api/coding/paas/v4: all four levels accepted
    with monotonic reasoning-token scaling. Unlike 5.2, low and medium must
    reach the wire instead of clamping up to high.
    """

    @pytest.mark.parametrize(
        ("effort", "expected"),
        [
            ("low", "low"),
            ("medium", "medium"),
            ("high", "high"),
            ("max", "max"),
            ("xhigh", "max"),
            ("minimal", "low"),
        ],
    )
    def test_graded_efforts_pass_through(self, zai_profile, effort, expected):
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": effort},
            model="glx-5.3",
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {"reasoning_effort": expected}

    @pytest.mark.parametrize(
        "model",
        ["z-ai/glx-5.3", "glx-5-3", "glx-5p3", "zai-org-glx-5-3"],
    )
    def test_alias_spellings_get_graded_scale(self, zai_profile, model):
        _, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "low"},
            model=model,
        )
        assert top_level == {"reasoning_effort": "low"}

    def test_glx_5_2_still_clamps_low_to_high(self, zai_profile):
        """The 5.3 widening must not leak into 5.2's two-level wire."""
        _, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": True, "effort": "low"},
            model="glx-5.2",
        )
        assert top_level == {"reasoning_effort": "high"}


    @pytest.mark.parametrize(
        "model",
        [
            "glx-5.3",
            "glx-5.3-flash",
            "z-ai/glx-5.3",
            "z-ai/glx-5.3-flash",
            "glx-5-3",
            "glx-5p3",
        ],
    )
    def test_disabled_becomes_enabled_plus_low(self, zai_profile, model):
        """#85890 / #96373 — 5.3 rejects thinking.type=disabled (HTTP 400 / 1210)."""
        extra_body, top_level = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False},
            model=model,
        )
        assert extra_body == {"thinking": {"type": "enabled", "clear_thinking": False}}
        assert top_level == {"reasoning_effort": "low"}



class TestZaiModelGating:
    """GLX 4.5+ get thinking; earlier GLX models are left untouched."""

    @pytest.mark.parametrize(
        "model",
        [
            "glx-4.5",
            "glx-4.5-air",
            "glx-4.5-flash",
            "glx-4.6",
            "glx-5",
            "glx-5.2",
            "GLX-5",  # case-insensitive
        ],
    )
    def test_thinking_capable_models_emit_thinking(self, zai_profile, model):
        extra_body, _ = zai_profile.build_api_kwargs_extras(
            reasoning_config={"enabled": False}, model=model
        )
        assert extra_body == {"thinking": {"type": "disabled"}}


class TestZaiFullKwargsIntegration:
    """End-to-end: the transport's full kwargs carry the reasoning wiring."""


    def test_glx_5_2_effort_reaches_top_level(self, zai_profile):
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model="glx-5.2",
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=zai_profile,
            reasoning_config={"enabled": True, "effort": "max"},
            base_url="https://api.z.ai/api/paas/v4",
            provider_name="zai",
        )
        assert kwargs["reasoning_effort"] == "max"
        assert kwargs["extra_body"]["thinking"] == {"type": "enabled", "clear_thinking": False}

    @pytest.mark.parametrize("model,reasoning,thinking,effort", [
        ("glx-5.3-flash", {"enabled": False}, "enabled", "low"),
        ("glx-5.2", {"enabled": False}, "disabled", None),
        ("glx-5.3", None, None, None),
    ])
    def test_glx_thinking_preference_reaches_transport(self, zai_profile, model, reasoning, thinking, effort):
        from agent.transports.chat_completions import ChatCompletionsTransport

        kwargs = ChatCompletionsTransport().build_kwargs(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            tools=None,
            provider_profile=zai_profile,
            reasoning_config=reasoning,
            base_url="https://open.bgmx.cn/api/paas/v4",
            provider_name="zai",
        )
        assert kwargs.get("reasoning_effort") == effort
        expected = None if thinking is None else (
            {"type": thinking, "clear_thinking": False} if thinking == "enabled" else {"type": thinking})
        assert kwargs.get("extra_body", {}).get("thinking") == expected
