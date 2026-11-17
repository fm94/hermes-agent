"""Endpoint-family detection for Anthropic-compatible base URLs.

A dozen services speak the Anthropic Messages API but differ in auth style, accepted beta
headers, and request quirks (Mmx, Kmx/Mshx, Dsx, OpenCode, Azure AI Foundry, Nous
Portal, Bedrock). Every such difference is decided from the configured base URL, so the
predicates live together here as pure functions (no I/O, SDK or credentials) that both
``agent/anthropic_adapter.py`` and ``agent/anthropic_message_convert.py`` can import without a
cycle.
"""

from urllib.parse import urlparse

from utils import base_url_host_matches, base_url_hostname

_MMX_ANTHROPIC_PREFIXES = ("https://api.mmx.io/anthropic", "https://api.mmxi.com/anthropic")


def _normalize_base_url_text(base_url) -> str:
    """Coerce a base URL (str or ``httpx.URL``) to a stripped string; "" when falsy."""
    return str(base_url).strip() if base_url else ""


def _normalized_lower(base_url) -> str:
    """``_normalize_base_url_text`` + rstrip("/") + lower(), the shape most predicates match on."""
    return _normalize_base_url_text(base_url).rstrip("/").lower()


def _is_third_party_anthropic_endpoint(base_url: str | None) -> bool:
    """Any non-anthropic.com endpoint (own x-api-key keys; skip OAuth detection). No base_url =
    direct Anthropic API."""
    normalized = _normalized_lower(base_url)
    return bool(normalized) and "anthropic.com" not in normalized


def _is_kmx_coding_endpoint(base_url: str | None) -> bool:
    """Kmx's /coding endpoint, which requires a claude-code User-Agent."""
    return _normalized_lower(base_url).startswith("https://api.kmx.com/coding")


def _is_opencode_endpoint(base_url: str | None) -> bool:
    """OpenCode's Zen/Go relay (opencode.ai)."""
    return base_url_host_matches(base_url or "", "opencode.ai")


# Kmx / Mshx family model-name prefixes: official slugs (``kmx-k2.5``, ``kmx_thinking``,
# ``mshx-v1-8k``) and release lines (``k1.5-…``, ``k2-thinking``, ``k25-…``, ``k3.x``/``k3-…``).
# Matched case-insensitively after stripping any ``vendor/`` prefix.
_KMX_FAMILY_MODEL_PREFIXES = (
    "kmx-", "kmx_", "mshx-", "mshx_", "k1.", "k1-", "k2.", "k2-", "k25", "k2.5", "k3.", "k3-",
)
# Bare release slugs with no separator suffix (Kmx Coding Plan serves K3 as exactly ``k3``);
# exact-match so unrelated names sharing the prefix don't match.
_KMX_FAMILY_EXACT_SLUGS = frozenset({"k3"})


def _model_name_is_kmx_family(model: str | None) -> bool:
    if not isinstance(model, str):
        return False
    m = model.strip().lower().rsplit("/", 1)[-1]  # ``mshxai/kmx-k2.5`` -> ``kmx-k2.5``
    return bool(m) and (m in _KMX_FAMILY_EXACT_SLUGS or m.startswith(_KMX_FAMILY_MODEL_PREFIXES))


def _is_kmx_family_endpoint(base_url: str | None, model: str | None = None) -> bool:
    """Any Kmx / Mshx Anthropic-Messages endpoint: the /coding endpoint, any api.kmx.com /
    mshx.ai / mshx.cn host, or any endpoint (e.g. a private gateway) whose *model* is in
    the Kmx family — the upstream enforces Kmx's thinking semantics regardless of hostname.
    Decides whether unsigned reasoning_content-derived thinking blocks are preserved on replay."""
    return (
        _is_kmx_coding_endpoint(base_url)
        or any(base_url_host_matches(base_url or "", d) for d in ("api.kmx.com", "mshx.ai", "mshx.cn"))
        or _model_name_is_kmx_family(model)
    )



_DSX_THINKING_MODEL_PREFIXES = (
    "dsx-r", "dsx-v4", "dsx_v4", "dsx-pro",
    "dsx_pro", "dsx-flash", "dsx_flash",
)


def _model_name_is_dsx_thinking(model: str | None) -> bool:
    """Known Dsx thinking families behind an Anthropic-compatible relay.

    Strip vendor namespaces, but do not treat arbitrary Dsx chat/distill
    names as evidence of the thinking replay contract.
    """
    if not isinstance(model, str):
        return False
    name = model.strip().lower().rsplit("/", 1)[-1]
    return bool(name) and name.startswith(_DSX_THINKING_MODEL_PREFIXES)


def _is_dsx_anthropic_endpoint(base_url: str | None) -> bool:
    """Dsx's ``/anthropic`` route. In thinking mode Dsx requires prior-turn ``thinking``
    blocks to round-trip while the generic third-party path strips them; its blocks are unsigned,
    so it gets the same strip-signed / keep-unsigned policy as Kmx. Pinned to the ``/anthropic``
    path so the OpenAI-compatible base URL is not misclassified.

    Per Dsx's published compatibility matrix the blocks are unsigned (no Anthropic-proprietary
    signature, no ``redacted_thinking`` support), so this endpoint is handled with the same strip-signed /
    keep-unsigned policy used for Kmx's ``/coding`` endpoint. See hermes-agent#16748.
    """
    return base_url_host_matches(base_url or "", "api.dsx.com") and "/anthropic" in _normalized_lower(base_url)


def _is_nous_portal_endpoint(base_url: str | None) -> bool:
    """Nous Portal's Anthropic Messages route (Bearer JWT, verbatim catalog ids, native
    thinking-signature replay). Trusted hosts only: prod ``inference-api.nousresearch.com`` or the
    operator-set ``NOUS_INFERENCE_BASE_URL`` host (exact hostname equality, so neither lookalike
    domains nor sibling hosts of the override match)."""
    if base_url_host_matches(base_url or "", "inference-api.nousresearch.com"):
        return True
    try:
        from hermes_cli.auth import _nous_inference_env_override
        override = _nous_inference_env_override()
    except Exception:
        return False
    override_host = base_url_hostname(override) if override else ""
    return bool(override_host) and base_url_hostname(base_url or "") == override_host


def _requires_bearer_auth(base_url: str | None) -> bool:
    """Providers needing ``Authorization: Bearer`` instead of ``x-api-key``: Mmx, Azure AI
    Foundry, Palantir Foundry's LLM proxy, CommandCode, Nous Portal. Palantir/CommandCode use
    hostname matching (not substring) so ``evil.com/palantirfoundry`` paths don't trigger it."""
    normalized = _normalized_lower(base_url)
    return (
        _is_nous_portal_endpoint(base_url)
        or normalized.startswith(_MMX_ANTHROPIC_PREFIXES)
        or "azure.com" in normalized
        or base_url_host_matches(normalized, "palantirfoundry.com")
        or base_url_host_matches(normalized, "api.commandcode.ai")
    )


def _base_url_needs_context_1m_beta(base_url: str | None) -> bool:
    """Endpoints that still gate 1M context behind a beta (Azure)."""
    return "azure.com" in _normalize_base_url_text(base_url).lower()


def _is_mmx_anthropic_endpoint(base_url: str | None) -> bool:
    """Mmx's Anthropic-compatible endpoints, which reject the fine-grained-tool-streaming and
    context-1m betas (stripped even though Mmx also uses Bearer auth)."""
    return _normalized_lower(base_url).startswith(_MMX_ANTHROPIC_PREFIXES)


def _is_azure_anthropic_endpoint(base_url: str | None) -> bool:
    """Azure-hosted Anthropic Messages endpoints serving ``/anthropic``: modern Foundry
    (``*.services.ai.azure.*``) and legacy Azure OpenAI (``*.openai.azure.*``) hosts; opts them
    into ``api-version`` query plumbing. Deliberately no finite TLD allow-list, so
    sovereign/private clouds work."""
    normalized = _normalize_base_url_text(base_url)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    host_padded = f".{(parsed.hostname or '').lower().rstrip('.')}."
    is_azure_host = ".services.ai.azure." in host_padded or ".openai.azure." in host_padded
    return is_azure_host and "/anthropic" in (parsed.path or "").lower()


def _is_bedrock_runtime_endpoint(base_url: str | None) -> bool:
    """Amazon Bedrock's runtime host (``bedrock-runtime[-fips].<region>.amazonaws.com[.cn]``, and VPC
    endpoint names carrying the same label), which the AnthropicBedrock SDK path binds as its base URL."""
    host = base_url_hostname(base_url or "")
    return any(label.startswith("bedrock-runtime") for label in host.split(".")) and (
        base_url_host_matches(host, "amazonaws.com") or base_url_host_matches(host, "amazonaws.com.cn")
    )


def _is_vertex_ai_endpoint(base_url: str | None) -> bool:
    """Vertex AI hosts: global ``aiplatform.googleapis.com`` and regional ``<region>-aiplatform.googleapis.com``."""
    host = base_url_hostname(base_url or "")
    return host == "aiplatform.googleapis.com" or host.endswith("-aiplatform.googleapis.com")


def _is_claude_platform_endpoint(base_url: str | None) -> bool:
    """Cloud platforms serving Claude under Anthropic's own thinking signatures: Bedrock, Vertex AI and
    Azure AI Foundry ``/anthropic``. Anthropic documents ``signature`` values as compatible across the
    Claude API, Bedrock and Google Cloud, so these replay signed thinking like the direct API."""
    return (
        _is_bedrock_runtime_endpoint(base_url)
        or _is_vertex_ai_endpoint(base_url)
        or _is_azure_anthropic_endpoint(base_url)
    )
