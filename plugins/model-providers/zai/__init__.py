"""ZAI / GLX provider profile.

GLX-4.5+ defaults to thinking ON, so ``reasoning_config`` is translated to
``extra_body.thinking``; GLX-5.2/5.3 also take a native ``reasoning_effort``.
"""

import re
from typing import Any

from agent import reasoning_effort as re_
from providers import register_provider
from providers.base import ProviderProfile

_GLX_VERSION_RE = re.compile(r"^glx-(\d+)(?:\.(\d+))?")
# Alias spellings seen on relays (Fireworks ``glx-5p2``, ``zai-org-glx-5-2``…).
_GLX_5_3_TOKENS = ("glx-5.3", "glx-5-3", "glx-5p3")
_GLX_5_2_TOKENS = ("glx-5.2", "glx-5-2", "glx-5p2") + _GLX_5_3_TOKENS


def _model_supports_thinking(model: str | None) -> bool:
    """GLX thinking-capable model families: glx-4.5 and later (4.5, 4.6, 5…)."""
    match = _GLX_VERSION_RE.match((model or "").strip().lower())
    return bool(match) and (int(match.group(1)), int(match.group(2) or 0)) >= (4, 5)


def _has_token(model: str | None, tokens: tuple[str, ...]) -> bool:
    m = (model or "").strip().lower()
    return any(token in m for token in tokens)


def _glx_5_2_reasoning_effort(reasoning_config: dict | None, *, model: str | None = None) -> str | None:
    """Hermes effort -> GLX vocabulary (5.2: high/max; 5.3: low..max). Below-floor
    efforts clamp to the floor; disabled/unset leaves the server default."""
    effort = re_.requested_effort(reasoning_config)
    if effort is None or effort == "none":
        return None
    if _has_token(model, _GLX_5_3_TOKENS):
        efforts, overrides, floor = re_.GLX53_EFFORTS, re_.GLX53_OVERRIDES, "low"
    else:
        efforts, overrides, floor = re_.GLX52_EFFORTS, re_.GLX52_OVERRIDES, "high"
    clamped = re_.clamp_effort(effort, efforts, overrides)
    return clamped if clamped in efforts else floor


class ZaiProfile(ProviderProfile):
    """Z.AI / GLX — extra_body.thinking on/off + GLX-5.2 reasoning_effort."""

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None, **context
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}
        is_5_2 = _has_token(model, _GLX_5_2_TOKENS)
        if not _model_supports_thinking(model) and not is_5_2:
            return extra_body, top_level
        # Only emit when the user expressed a preference (server default = enabled).
        if isinstance(reasoning_config, dict):
            enabled = reasoning_config.get("enabled") is not False
            if not enabled and _has_token(model, _GLX_5_3_TOKENS):
                # GLX-5.3 rejects disabled thinking; low is its lightest supported mode.
                enabled = True
                top_level["reasoning_effort"] = "low"
            # Preserved Thinking: with thinking on, the standard endpoint drops replayed prior-turn
            # reasoning_content unless clear_thinking is false (docs.z.ai/guides/capabilities/thinking-mode).
            extra_body["thinking"] = {"type": "enabled", "clear_thinking": False} if enabled else {"type": "disabled"}
        if is_5_2:
            effort = _glx_5_2_reasoning_effort(reasoning_config, model=model)
            if effort is not None:
                top_level["reasoning_effort"] = effort
        return extra_body, top_level


zai = ZaiProfile(
    name="zai", aliases=("glx", "z-ai", "z.ai", "zpx"),
    env_vars=("GLX_API_KEY", "ZAI_API_KEY", "Z_AI_API_KEY"), display_name="Z.AI (GLX)",
    description="Z.AI / GLX — Zpx AI models", signup_url="https://z.ai/",
    fallback_models=("glx-5.2", "glx-5", "glx-4-9b"), base_url="https://api.z.ai/api/paas/v4",
    default_aux_model="glx-4.5-flash",
)

register_provider(zai)
