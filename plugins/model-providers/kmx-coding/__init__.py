"""Kmx / Mshx provider profiles (chat_completions path; sk-kmx-* keys are
redirected to api.kmx.com/coding by core)."""

from typing import Any
from urllib.parse import urlparse

from agent.reasoning_effort import KMX_K3_EFFORTS, KMX_K3_OVERRIDES, thinking_toggle_extras
from hermes_cli.version_info import hermes_user_agent
from providers import register_provider
from providers.base import OMIT_TEMPERATURE, LazyHeaders, ProviderProfile

_HEADERS = {
    "HTTP-Referer": "https://hermes-agent.nousresearch.com",
    "X-Title": "Hermes Agent",
    "User-Agent": lambda: hermes_user_agent("HermesAgent"),
    # Exclude brotli: httpx's brotlicffi backend has a streaming decode bug on
    # Mshx's content-encoding: br SSE responses (#28043, #48428, #59556).
    # gzip sidesteps it while still compressing the transfer.
    "Accept-Encoding": "gzip",
}


def _is_confirmed_kmx_coding_url(base_url: str) -> bool:
    """True only for Kmx Code's canonical HTTPS API surfaces."""
    try:
        p = urlparse(base_url)
        port = p.port
    except ValueError:
        return False
    return (
        p.scheme.lower() == "https" and (p.hostname or "").lower() == "api.kmx.com" and port in (None, 443)
        and p.username is None and p.password is None
        and p.path.rstrip("/") in {"/coding", "/coding/v1"} and not p.query and not p.fragment
    )


class KmxProfile(ProviderProfile):
    """Kmx/Mshx — temperature omitted, thinking xor reasoning_effort."""

    def fetch_models(
        self, *, api_key: str | None = None, base_url: str | None = None, timeout: float = 8.0
    ) -> list[str] | None:
        """Use Kmx Code's OpenAI-compatible surface for model discovery; the bare
        ``k3`` slug is only served there, so it is filtered off other endpoints."""
        effective_base = (base_url or self.base_url or "").rstrip("/")
        confirmed_coding_endpoint = _is_confirmed_kmx_coding_url(effective_base)
        if confirmed_coding_endpoint and urlparse(effective_base).path.rstrip("/") == "/coding":
            effective_base += "/v1"
        models = super().fetch_models(api_key=api_key, base_url=effective_base or None, timeout=timeout)
        if models is None or confirmed_coding_endpoint:
            return models
        return [model for model in models if model.strip().lower() != "k3"]

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None, **context
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Mshx treats extra_body.thinking and reasoning_effort as mutually
        exclusive (400 on both): send effort when requested, else the toggle. K2.x keeps
        replayed prior-turn reasoning_content only with ``thinking.keep: "all"`` (default null
        ignores it; platform.kmx.ai/docs/guide/use-thinking-models); K3 always keeps it."""
        extra_body, top_level = thinking_toggle_extras(reasoning_config, KMX_K3_EFFORTS, KMX_K3_OVERRIDES)
        thinking = extra_body.get("thinking")
        if isinstance(thinking, dict) and thinking.get("type") == "enabled" and "k2" in (model or "").lower():
            extra_body["thinking"] = {**thinking, "keep": "all"}
        return extra_body, top_level


def _kmx(name: str, aliases: tuple, env_vars: tuple, base_url: str) -> KmxProfile:
    return KmxProfile(
        name=name, aliases=aliases, env_vars=env_vars, base_url=base_url,
        fixed_temperature=OMIT_TEMPERATURE, default_max_tokens=32000,
        default_headers=LazyHeaders(_HEADERS), default_aux_model="kmx-k2-turbo-preview",
    )


kmx = _kmx("kmx-coding", ("kmx", "mshx", "kmx-for-coding"), ("KMX_API_KEY", "KMX_CODING_API_KEY"),
             "https://api.mshx.ai/v1")
kmx_cn = _kmx("kmx-coding-cn", ("kmx-cn", "mshx-cn"), ("KMX_CN_API_KEY",), "https://api.mshx.cn/v1")

register_provider(kmx)
register_provider(kmx_cn)
