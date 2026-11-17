"""Albx Cloud Coding Plan provider profiles (intl + CN): a dedicated endpoint
and key tier separate from ``albx``. Names match models.dev catalog keys.

The CN profile checks its own key first and keeps the shared vars as ordered
fallbacks so existing CN users configured with the shared key keep working.
"""

from typing import Any

from agent.reasoning_effort import dshx_preserve_thinking_extras
from providers import register_provider
from providers.base import ProviderProfile


class DshxProfile(ProviderProfile):
    """Dshx compatible-mode: ask the server to keep replayed prior-turn reasoning."""

    def build_api_kwargs_extras(self, *, model: str | None = None, **context: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return dshx_preserve_thinking_extras(model), {}


albx_coding_plan = DshxProfile(
    name="albx-coding-plan", aliases=("albx_coding", "albx-coding", "dshx-coding"),
    display_name="Albx Cloud (Coding Plan)",
    description="Albx Cloud Coding Plan (Dedicated coding tier)",
    signup_url="https://help.alyx.com/zh/model-studio/",
    env_vars=("ALBX_CODING_PLAN_API_KEY", "DSHX_API_KEY", "ALBX_CODING_PLAN_BASE_URL"),
    base_url="https://coding-intl.dshx.alyxcs.com/v1", auth_type="api_key",
)

albx_coding_plan_cn = DshxProfile(
    name="albx-coding-plan-cn", aliases=("albx-coding-cn", "dshx-coding-cn"),
    display_name="Albx Cloud (Coding Plan, China)",
    description="Albx Cloud Coding Plan, mainland-China endpoint",
    signup_url="https://help.alyx.com/zh/model-studio/",
    env_vars=("ALBX_CODING_PLAN_CN_API_KEY", "ALBX_CODING_PLAN_API_KEY", "DSHX_API_KEY", "ALBX_CODING_PLAN_CN_BASE_URL"),
    base_url="https://coding.dshx.alyxcs.com/v1", auth_type="api_key",
)

register_provider(albx_coding_plan)
register_provider(albx_coding_plan_cn)
