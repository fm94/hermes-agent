import pytest
from unittest.mock import MagicMock
from agent.agent_runtime_helpers import create_openai_client


def _fake_openai_factory(captured_kwargs):
    def fake_openai(**kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock()
    return fake_openai


def test_create_openai_client_normalizes_kmx_coding_base_url(monkeypatch):
    """#102247: OpenAI-wire client creation must normalize api.kmx.com/coding to /v1
    to avoid HTTP 404 when appending /chat/completions."""
    mock_agent = MagicMock()
    mock_agent.provider = "kmx-coding"
    mock_agent._build_keepalive_http_client.return_value = None
    mock_agent._client_log_context.return_value = "test_context"

    captured_kwargs = {}
    monkeypatch.setattr("agent.process_bootstrap.OpenAI", _fake_openai_factory(captured_kwargs))

    client_kwargs = {
        "api_key": "sk-kmx-test12345",
        "base_url": "https://api.kmx.com/coding",
    }

    client = create_openai_client(mock_agent, client_kwargs, reason="test", shared=False)
    assert client is not None
    assert captured_kwargs.get("base_url") == "https://api.kmx.com/coding/v1"


def test_create_openai_client_preserves_already_suffixed_kmx_url(monkeypatch):
    """Already-suffixed /v1 should remain unchanged."""
    mock_agent = MagicMock()
    mock_agent.provider = "kmx-coding"
    mock_agent._build_keepalive_http_client.return_value = None
    mock_agent._client_log_context.return_value = "test_context"

    captured_kwargs = {}
    monkeypatch.setattr("agent.process_bootstrap.OpenAI", _fake_openai_factory(captured_kwargs))

    client_kwargs = {
        "api_key": "sk-kmx-test12345",
        "base_url": "https://api.kmx.com/coding/v1",
    }

    create_openai_client(mock_agent, client_kwargs, reason="test", shared=False)
    assert captured_kwargs.get("base_url") == "https://api.kmx.com/coding/v1"
