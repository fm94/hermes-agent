"""Targeted tests for ``utils.base_url_hostname`` and ``base_url_host_matches``.

These helpers are used across provider routing, auxiliary client, setup
wizards, billing routes, and the trajectory compressor to avoid the
substring-match false-positive class documented in
tests/agent/test_direct_provider_url_detection.py.
"""

from __future__ import annotations

from utils import base_url_hostname, base_url_host_matches


# ─── base_url_hostname ────────────────────────────────────────────────────


def test_empty_returns_empty_string():
    assert base_url_hostname("") == ""
    assert base_url_hostname(None) == ""  # type: ignore[arg-type]


def test_plain_host_without_scheme():
    assert base_url_hostname("api.openai.com") == "api.openai.com"
    assert base_url_hostname("api.openai.com/v1") == "api.openai.com"






def test_trailing_dot_stripped():
    assert base_url_hostname("https://api.openai.com./v1") == "api.openai.com"




def test_host_suffix_is_not_the_provider():
    assert base_url_hostname("https://api.openai.com.example/v1") == "api.openai.com.example"
    assert base_url_hostname("https://api.x.ai.example/v1") == "api.x.ai.example"


def test_port_is_ignored():
    assert base_url_hostname("https://api.openai.com:443/v1") == "api.openai.com"




# ─── base_url_host_matches ────────────────────────────────────────────────


class TestBaseUrlHostMatchesExact:
    def test_exact_domain_matches(self):
        assert base_url_host_matches("https://openrouter.ai/api/v1", "openrouter.ai") is True
        assert base_url_host_matches("https://mshx.ai", "mshx.ai") is True

    def test_subdomain_matches(self):
        # A subdomain of the registered domain should match — needed for
        # api.mshx.ai / api.kmx.com / portal.qwx.ai lookups that
        # accept both the bare registrable domain and any subdomain under it.
        assert base_url_host_matches("https://api.mshx.ai/v1", "mshx.ai") is True
        assert base_url_host_matches("https://api.kmx.com/v1", "api.kmx.com") is True
        assert base_url_host_matches("https://portal.qwx.ai/v1", "portal.qwx.ai") is True


class TestBaseUrlHostMatchesNegatives:
    """The reason this helper exists — defend against substring collisions."""

    def test_path_segment_containing_domain_does_not_match(self):
        assert base_url_host_matches("https://evil.test/mshx.ai/v1", "mshx.ai") is False
        assert base_url_host_matches("https://proxy.example.test/openrouter.ai/v1", "openrouter.ai") is False
        assert base_url_host_matches("https://proxy/api.kmx.com/v1", "api.kmx.com") is False

    def test_host_suffix_does_not_match(self):
        # Attacker-controlled hosts that end with the domain string are not
        # the domain.
        assert base_url_host_matches("https://mshx.ai.evil/v1", "mshx.ai") is False
        assert base_url_host_matches("https://openrouter.ai.example/v1", "openrouter.ai") is False

    def test_host_prefix_does_not_match(self):
        # "fake-openrouter.ai" is not a subdomain of openrouter.ai.
        assert base_url_host_matches("https://fake-openrouter.ai/v1", "openrouter.ai") is False


class TestBaseUrlHostMatchesEdgeCases:
    def test_empty_base_url_returns_false(self):
        assert base_url_host_matches("", "openrouter.ai") is False
        assert base_url_host_matches(None, "openrouter.ai") is False  # type: ignore[arg-type]





class TestOllamaUrlHostCheck:
    """GHSA-76xc-57q6-vm5m — ollama.com was using a raw substring match for
    credential selection (same bug class as GHSA-xf8p-v2cg-h7h5 for OpenRouter).
    These tests lock in that the base_url_host_matches fix correctly rejects
    the same attack vectors for Ollama.
    """

    def test_ollama_com_path_injection_rejected(self):
        """http://evil.test/ollama.com/v1 — ollama.com appears in the path,
        not the host. Must not be treated as Ollama Cloud."""
        assert base_url_host_matches(
            "http://127.0.0.1:9000/ollama.com/v1", "ollama.com"
        ) is False

    def test_ollama_com_subdomain_lookalike_rejected(self):
        """ollama.com.attacker.test is a separate host, not ollama.com."""
        assert base_url_host_matches(
            "http://ollama.com.attacker.test:9000/v1", "ollama.com"
        ) is False




    def test_genuine_ollama_com_matches(self):
        assert base_url_host_matches(
            "https://ollama.com/api/generate", "ollama.com"
        ) is True

