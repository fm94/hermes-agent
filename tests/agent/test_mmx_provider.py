"""Tests for Mmx provider hardening — context lengths, thinking, catalog, beta headers, transport."""

from unittest.mock import patch




class TestMmxM3StaleCacheGuard:
    """Pre-catalog builds resolved M3 via the generic 'mmx' catch-all
    (204,800) and persisted it before the 'mmx-m3' (1M) catalog entry
    existed.  The step-1 cache guard must drop that stale value and re-resolve
    to 1M, while leaving correct M2.x entries (204,800) untouched.
    """




    def test_m2_cache_not_clobbered(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        import importlib
        import agent.model_metadata as mm
        importlib.reload(mm)
        base = "https://api.mmxi.com/anthropic"
        # 204,800 is the CORRECT value for M2.x — guard must not touch it.
        for slug in ("Mmx-M2.7", "Mmx-M2.5", "Mmx-M2.1"):
            mm.save_context_length(slug, base, 204_800)
            ctx = mm.get_model_context_length(
                slug, base_url=base, api_key="", provider="mmx-cn"
            )
            assert ctx == 204_800, f"{slug} should stay 204800, got {ctx}"



class TestMmxThinkingSupport:
    """Verify that Mmx gets manual thinking (not adaptive).

    Mmx's Anthropic-compat endpoint officially supports the thinking
    parameter (https://platform.mmx.io/docs/api-reference/text-anthropic-api).
    It should get manual thinking (type=enabled + budget_tokens), NOT adaptive
    thinking (which is Claude 4.6-only).
    """

    def test_mmx_m27_gets_manual_thinking(self):
        from agent.anthropic_adapter import build_anthropic_kwargs
        kwargs = build_anthropic_kwargs(
            model="Mmx-M2.7",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            max_tokens=4096,
            reasoning_config={"enabled": True, "effort": "medium"},
        )
        assert "thinking" in kwargs
        assert kwargs["thinking"]["type"] == "enabled"
        assert "budget_tokens" in kwargs["thinking"]
        # Mmx should NOT get adaptive thinking or output_config
        assert "output_config" not in kwargs






class TestMmxBetaHeaders:
    """Mmx Anthropic-compat endpoints reject fine-grained-tool-streaming beta.

    Verify that build_anthropic_client omits the tool-streaming beta for Mmx
    (both global and China domains) while keeping it for native Anthropic and
    other third-party endpoints.  Covers the fix for #6510 / #6555.
    """

    _TOOL_BETA = "fine-grained-tool-streaming-2025-05-14"
    _THINKING_BETA = "interleaved-thinking-2025-05-14"

    # -- helper ----------------------------------------------------------

    def _build_and_get_betas(self, api_key, base_url=None):
        """Build client, return the anthropic-beta header string."""
        from agent.anthropic_adapter import build_anthropic_client
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client(api_key, base_url=base_url)
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs.get("default_headers", {})
            return headers.get("anthropic-beta", "")

    # -- Mmx global --------------------------------------------------

    def test_mmx_global_omits_tool_streaming(self):
        betas = self._build_and_get_betas(
            "mm-key-123", base_url="https://api.mmx.io/anthropic"
        )
        assert self._TOOL_BETA not in betas
        assert self._THINKING_BETA in betas


    # -- Mmx China ---------------------------------------------------



    # -- Non-Mmx keeps full betas ------------------------------------




    # -- _common_betas_for_base_url unit tests ---------------------------







class TestMmxApiMode:
    """Verify determine_api_mode returns anthropic_messages for Mmx providers.

    The Mmx /anthropic endpoint speaks Anthropic Messages wire format,
    not OpenAI chat completions.  The overlay transport must reflect this
    so that code paths calling determine_api_mode() without a base_url
    (e.g. /model switch) get the correct api_mode.
    """

    def test_mmx_returns_anthropic_messages(self):
        from hermes_cli.providers import determine_api_mode
        assert determine_api_mode("mmx") == "anthropic_messages"








class TestMmxPreserveDots:
    """Verify that Mmx model names preserve dots through the Anthropic adapter.

    Mmx model IDs like 'Mmx-M2.7' must NOT have dots converted to
    hyphens — the endpoint expects the exact name with dots.
    """

    def test_mmx_provider_preserves_dots(self):
        from types import SimpleNamespace
        agent = SimpleNamespace(provider="mmx", base_url="")
        from run_agent import AIAgent
        assert AIAgent._anthropic_preserve_dots(agent) is True









    def test_normalize_preserves_m25_free_dot(self):
        from agent.anthropic_message_convert import normalize_model_name
        assert normalize_model_name("mmx-m2.5-free", preserve_dots=True) == "mmx-m2.5-free"





class TestMmxSwitchModelCredentialGuard:
    """Verify switch_model() does not leak Anthropic credentials to Mmx.

    The __init__ path correctly guards against this (line 761), but switch_model()
    must mirror that guard. Without it, /model switch to mmx with no explicit
    api_key would fall back to resolve_anthropic_token() and send Anthropic creds
    to the Mmx endpoint.
    """

    def test_switch_to_mmx_does_not_resolve_anthropic_token(self):
        """switch_model() should NOT call resolve_anthropic_token() for Mmx."""
        from unittest.mock import patch, MagicMock

        with patch("run_agent.AIAgent.__init__", return_value=None):
            from run_agent import AIAgent
            agent = AIAgent.__new__(AIAgent)
            agent.provider = "anthropic"
            agent.model = "claude-sonnet-4"
            agent.api_key = "sk-ant-fake"
            agent.base_url = "https://api.anthropic.com"
            agent.api_mode = "anthropic_messages"
            agent._anthropic_base_url = "https://api.anthropic.com"
            agent._anthropic_api_key = "sk-ant-fake"
            agent._is_anthropic_oauth = False
            agent._client_kwargs = {}
            agent.client = None
            agent._anthropic_client = MagicMock()
            agent._fallback_chain = []

        with patch("agent.anthropic_adapter.build_anthropic_client") as mock_build, \
             patch("agent.anthropic_credentials.resolve_anthropic_token", return_value="sk-ant-leaked") as mock_resolve, \
             patch("agent.anthropic_credentials._is_oauth_token", return_value=False):

            agent.switch_model(
                new_model="Mmx-M2.7",
                new_provider="mmx",
                api_mode="anthropic_messages",
                api_key="mm-key-123",
                base_url="https://api.mmx.io/anthropic",
            )
            # resolve_anthropic_token should NOT be called for non-Anthropic providers
            mock_resolve.assert_not_called()
            # The key passed to build_anthropic_client should be the Mmx key
            build_args = mock_build.call_args
            assert build_args[0][0] == "mm-key-123"
