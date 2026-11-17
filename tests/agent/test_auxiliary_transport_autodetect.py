"""Tests for transport auto-detection in agent.auxiliary_client.

Auxiliary clients must pick the correct wire protocol (OpenAI
chat.completions vs native Anthropic Messages) based on the endpoint,
regardless of which resolve_provider_client branch built them.

Regression target (April 2026): Kmx Coding Plan's ``api.kmx.com/coding``
endpoint only speaks Anthropic Messages — sending ``kmx-for-coding`` over
chat.completions returns 404 "resource_not_found_error".  The named
``kmx-coding`` provider branch in resolve_provider_client used to build a
plain OpenAI client, so title generation / vision / compression /
web_extract all failed on Kmx Coding Plan users.
"""

from __future__ import annotations


import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "OPENAI_API_KEY", "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN",
        "KMX_API_KEY", "KMX_CODING_API_KEY", "KMX_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# URL detection helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected,label", [
    ("https://api.kmx.com/coding/v1", True, "Kmx Coding Plan /v1"),
    ("https://api.kmx.com/coding", True, "Kmx Coding Plan no /v1"),
    ("https://api.mshx.ai/v1", False, "Mshx legacy"),
    ("https://api.mmx.io/anthropic", True, "Mmx /anthropic"),
    ("https://litellm.example.com/v1/anthropic", True, "/anthropic suffix"),
    ("https://litellm.example.com/anthropic/v1", True, "/anthropic/v1 base"),
    ("https://litellm.example.com/anthropic/v1/models", False, "/anthropic/v1 subpath"),
    ("https://api.anthropic.com", True, "native Anthropic"),
    ("https://api.anthropic.com/v1", True, "native Anthropic /v1"),
    ("https://openrouter.ai/api/v1", False, "OpenRouter"),
    ("https://api.openai.com/v1", False, "OpenAI"),
    ("https://inference-api.nousresearch.com/v1", False, "Nous"),
    ("", False, "empty"),
    (None, False, "None"),
])
def test_endpoint_speaks_anthropic_messages(url, expected, label):
    from agent.auxiliary_client import _endpoint_speaks_anthropic_messages
    assert _endpoint_speaks_anthropic_messages(url) is expected, (
        f"{label}: {url!r} should be {expected}"
    )


# ---------------------------------------------------------------------------
# _maybe_wrap_anthropic decision table
# ---------------------------------------------------------------------------

















# ---------------------------------------------------------------------------
# Integration: resolve_provider_client for named kmx-coding provider
# ---------------------------------------------------------------------------

def test_resolve_provider_client_kmx_coding_wraps_anthropic(monkeypatch, tmp_path):
    """End-to-end: resolve_provider_client('kmx-coding', 'kmx-for-coding')
    must return AnthropicAuxiliaryClient because /coding speaks Anthropic.

    This is the primary regression guard: the bug that caused title
    generation 404s on every Kmx Coding Plan user after the "main model
    for every user" aux design shipped.
    """
    from agent.auxiliary_client import (
        resolve_provider_client,
        AnthropicAuxiliaryClient,
    )

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    # sk-kmx- prefix triggers /coding endpoint auto-detection
    monkeypatch.setenv("KMX_API_KEY", "sk-kmx-faketesttoken123")

    client, _model = resolve_provider_client("kmx-coding", "kmx-for-coding")
    assert client is not None, "Should resolve a client"
    assert isinstance(client, AnthropicAuxiliaryClient), (
        "Kmx Coding Plan endpoint (api.kmx.com/coding) speaks Anthropic "
        "Messages — aux client MUST be AnthropicAuxiliaryClient, got "
        f"{type(client).__name__}"
    )
    assert "kmx.com/coding" in str(client.base_url)
