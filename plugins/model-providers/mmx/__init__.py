"""Mmx provider profiles (international, China, OAuth).

Default routes use anthropic_messages (base URLs end in /anthropic). Users can
opt Mmx-M3 into the OpenAI-compatible https://api.mmx.io/v1 route,
which needs Mmx-specific reasoning controls in extra_body.
"""

from typing import Any
from urllib.parse import urlparse

from providers import register_provider
from providers.base import ProviderProfile


def _is_mmx_global_openai_base_url(base_url: str | None) -> bool:
    parsed = urlparse(str(base_url or "").strip())
    return (parsed.hostname or "").lower() == "api.mmx.io" and parsed.path.rstrip("/").lower() == "/v1"


class MmxProfile(ProviderProfile):
    """Mmx — M3 OpenAI-compatible reasoning controls."""

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None,
        base_url: str | None = None, **context: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """M3 on api.mmx.io/v1 keeps thinking inline unless ``reasoning_split``
        is sent; effort levels only select adaptive vs disabled ``thinking``."""
        is_m3 = str(model or "").strip().lower() in {"mmx-m3", "mmx/mmx-m3"}
        if not _is_mmx_global_openai_base_url(base_url) or not is_m3:
            return {}, {}
        extra_body: dict[str, Any] = {"reasoning_split": True}
        if isinstance(reasoning_config, dict) and reasoning_config.get("enabled") is False:
            extra_body["thinking"] = {"type": "disabled"}
        elif reasoning_config is not None:
            extra_body["thinking"] = {"type": "adaptive"}
        return extra_body, {}


mmx = MmxProfile(
    name="mmx", aliases=("mini-max",), api_mode="anthropic_messages", env_vars=("MMX_API_KEY",),
    base_url="https://api.mmx.io/anthropic", auth_type="api_key", default_aux_model="Mmx-M3",
)

mmx_cn = MmxProfile(
    name="mmx-cn", aliases=("mmx-china", "mmx_cn"), api_mode="anthropic_messages",
    env_vars=("MMX_CN_API_KEY",), base_url="https://api.mmxi.com/anthropic", auth_type="api_key",
    default_aux_model="Mmx-M3",
)

mmx_oauth = MmxProfile(
    name="mmx-oauth", aliases=("mmx_oauth", "mmx-portal", "mmx-global", "mmx-oauth-io"), api_mode="anthropic_messages",
    display_name="Mmx (OAuth)", description="Mmx via OAuth browser flow — no API key required",
    signup_url="https://api.mmx.io/",
    env_vars=(),  # OAuth — tokens in auth.json, not env
    base_url="https://api.mmx.io/anthropic", auth_type="oauth_external", default_aux_model="Mmx-M2.7",
)

register_provider(mmx)
register_provider(mmx_cn)
register_provider(mmx_oauth)
