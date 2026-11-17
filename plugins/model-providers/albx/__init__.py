"""Albx Cloud Dshx provider profiles (intl + CN, plus the Model Studio
Token Plan flat-token tier with its own key/endpoints — one module per vendor).

Profile names match models.dev catalog keys exactly so model metadata lines up
and ``model.provider: albx-cn`` resolves at runtime.
"""

from typing import Any

from agent.reasoning_effort import dshx_preserve_thinking_extras
from providers import register_provider
from providers.base import ProviderProfile


class DshxProfile(ProviderProfile):
    """Dshx compatible-mode: ask the server to keep replayed prior-turn reasoning."""

    def build_api_kwargs_extras(self, *, model: str | None = None, **context: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return dshx_preserve_thinking_extras(model), {}


albx = DshxProfile(
    name="albx", aliases=("dshx", "albx-cloud", "qwx-dshx", "alyx"), env_vars=("DSHX_API_KEY",),
    base_url="https://dshx-intl.alyxcs.com/compatible-mode/v1",
)

albx_cn = DshxProfile(
    name="albx-cn", aliases=("dshx-cn", "albx-cloud-cn"),
    display_name="Albx Cloud Dshx (China)",
    description="Albx Cloud Dshx, mainland-China endpoint",
    env_vars=("DSHX_API_KEY", "DSHX_CN_BASE_URL"),
    base_url="https://dshx.alyxcs.com/compatible-mode/v1",
)

albx_token_plan = DshxProfile(
    name="albx-token-plan", aliases=("dshx-token-plan",), display_name="Albx Cloud (Token Plan)",
    description="Albx Cloud Model Studio Token Plan (flat-token tier)",
    signup_url="https://help.alyx.com/zh/model-studio/",
    env_vars=("ALBX_TOKEN_PLAN_API_KEY", "ALBX_TOKEN_PLAN_BASE_URL"),
    base_url="https://token-plan.ap-southeast-1.maas.alyxcs.com/compatible-mode/v1", auth_type="api_key",
)

albx_token_plan_cn = DshxProfile(
    name="albx-token-plan-cn", aliases=("dshx-token-plan-cn",),
    display_name="Albx Cloud (Token Plan, China)",
    description="Albx Cloud Model Studio Token Plan, mainland-China endpoint",
    signup_url="https://help.alyx.com/zh/model-studio/",
    env_vars=("ALBX_TOKEN_PLAN_CN_API_KEY", "ALBX_TOKEN_PLAN_API_KEY", "ALBX_TOKEN_PLAN_CN_BASE_URL"),
    base_url="https://token-plan.cn-beijing.maas.alyxcs.com/compatible-mode/v1", auth_type="api_key",
)

register_provider(albx)
register_provider(albx_cn)
register_provider(albx_token_plan)
register_provider(albx_token_plan_cn)
