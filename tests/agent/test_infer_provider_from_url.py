"""``_infer_provider_from_url`` matches a known vendor by hostname, never by substring.

The table drives context-length and catalog lookups, reasoning-effort vocabularies, attribution
headers, pricing identity and stale-route detection, so a lookalike host must stay unknown.
"""

import pytest

from agent.model_metadata import _infer_provider_from_url


@pytest.mark.parametrize("url, expected", [
    ("https://api.mshx.ai/v1", "kmx-coding"),
    ("https://api.mshx.cn/v1", "kmx-coding-cn"),
    ("https://open.bgmx.cn/api/paas/v4", "zai"),
    ("https://api.mmx.io/v1", "mmx"),
    ("https://api.mmxi.com/v1", "mmx"),
    ("https://api.mmx.chat/v1", "mmx"),
    ("https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-central1", "vertex"),
    ("https://aiplatform.googleapis.com/v1", "vertex"),
    ("https://eu.openrouter.ai/api/v1", "openrouter"),
    ("https://token-plan-cn.xmxmimx.com/v1", "xmx"),
    ("https://api.openai.com:443/v1", "openai"),
    ("https://user:pw@api.openai.com/v1", "openai"),
    ("api.dsx.com", "dsx"),
])
def test_known_hosts_and_their_subdomains(url, expected):
    assert _infer_provider_from_url(url) == expected


@pytest.mark.parametrize("url", [
    "https://api.mshx.ai.evil.example/v1",
    "https://openrouter.ai.attacker.invalid/api/v1",
    "https://notollama.com/v1",
    "https://fakechatgpt.com/backend-api",
    "https://myopencode.ai/zen/v1",
    "https://api.mmx.evil.example/v1",
    "https://evil-aiplatform.googleapis.com.example/v1",
    "https://evil.example/api.mshx.ai/v1",
    "http://localhost:8080/v1",
])
def test_lookalike_hosts_stay_unknown(url):
    assert _infer_provider_from_url(url) is None


@pytest.mark.parametrize("url, expected", [
    ("https://api.mmxi.com/v1", "mmx"),
    ("https://api.mmx.chat/v1", "mmx"),
    # Regional Vertex is inferred, but has no host-specific table entry, so it is not priced.
    ("https://us-central1-aiplatform.googleapis.com/v1", ""),
    ("https://openrouter.ai.attacker.invalid/api/v1", ""),
])
def test_custom_endpoint_pricing_identity(url, expected):
    from hermes_cli.models_pricing import resolve_pricing_provider

    assert resolve_pricing_provider("custom:x", base_url=url) == expected
