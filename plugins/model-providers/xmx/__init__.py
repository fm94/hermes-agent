"""Xmx Mimx provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

xmx = ProviderProfile(
    name="xmx", aliases=("mimx", "xmx-mimx"), env_vars=("XMX_API_KEY",),
    base_url="https://api.xmxmimx.com/v1",
    supports_health_check=False,  # /v1/models returns 401 even with valid key
    supports_vision=True,  # mimx-v2-omni is vision-capable
    supports_vision_tool_messages=False,  # rejects list-type tool content (400 "text is not set")
)

register_provider(xmx)
