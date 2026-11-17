"""Kmx / Mshx thinking behavior on the Anthropic-Messages wire.

Contract (changed from the original #13848 mitigation):

- Kmx-family endpoints receive ``thinking`` in **adaptive** form
  (``thinking.type="adaptive"`` + ``output_config.effort``) — never manual
  ``budget_tokens``.  Their Anthropic-compatible endpoints
  (``api.mshx.cn/anthropic``, ``api.kmx.com/coding``) accept the
  field set, and the replay-validation 400s that originally motivated
  dropping the parameter (#13848) no longer occur.

- ``convert_messages_to_anthropic`` still preserves unsigned
  reasoning_content-derived thinking blocks on replay for this family, so
  multi-turn tool-call history round-trips.

Kmx on the chat_completions route handles ``thinking`` via ``extra_body``
in ``ChatCompletionsTransport`` (#13503).
"""

from __future__ import annotations

import pytest


class TestKmxCodingAnthropicThinking:
    """Kmx-family thinking on the Anthropic wire (incl. /coding)."""

    def test_kmx_coding_with_explicit_disabled_omits_thinking(self) -> None:
        from agent.anthropic_adapter import build_anthropic_kwargs

        kwargs = build_anthropic_kwargs(
            model="kmx-k2.5",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            max_tokens=4096,
            reasoning_config={"enabled": False},
            base_url="https://api.kmx.com/coding",
        )
        assert "thinking" not in kwargs

    def test_non_kmx_third_party_still_gets_thinking(self) -> None:
        """Mmx and other third-party Anthropic endpoints must retain thinking."""
        from agent.anthropic_adapter import build_anthropic_kwargs

        kwargs = build_anthropic_kwargs(
            model="Mmx-M2.7",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            max_tokens=4096,
            reasoning_config={"enabled": True, "effort": "medium"},
            base_url="https://api.mmx.io/anthropic",
        )
        assert "thinking" in kwargs
        assert kwargs["thinking"]["type"] == "enabled"

    def test_native_anthropic_still_gets_thinking(self) -> None:
        from agent.anthropic_adapter import build_anthropic_kwargs

        kwargs = build_anthropic_kwargs(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            max_tokens=4096,
            reasoning_config={"enabled": True, "effort": "medium"},
            base_url=None,
        )
        assert "thinking" in kwargs


class TestKmxFamilyGetsAdaptiveThinking:
    """Kmx-family endpoints get adaptive thinking + output_config.effort."""

    @pytest.mark.parametrize(
        "base_url,model",
        [
            # Official Kmx / Mshx hosts (all URL shapes)
            ("https://api.kmx.com/coding", "kmx-k2.5"),
            ("https://api.kmx.com/coding/v1", "kmx-k2.5"),
            ("https://api.kmx.com/coding/anthropic", "kmx-k2.5"),
            ("https://api.kmx.com/v1", "kmx-k2.5"),
            ("https://api.mshx.ai/anthropic", "mshx-v1-32k"),
            ("https://api.mshx.cn/anthropic", "mshx-v1-32k"),
            ("https://api.mshx.cn/anthropic/v1", "kmx-0714-preview"),
            # Custom / proxied hosts with a Kmx-family model (#17057)
            ("http://my-kmx-proxy.internal", "kmx-2.6"),
            ("https://llm.example.com/anthropic", "mshxai/kmx-k2.5"),
        ],
    )
    def test_kmx_family_endpoint_gets_adaptive_thinking(
        self, base_url: str, model: str
    ) -> None:
        from agent.anthropic_adapter import build_anthropic_kwargs

        kwargs = build_anthropic_kwargs(
            model=model,
            messages=[{"role": "user", "content": "hello"}],
            tools=None,
            max_tokens=4096,
            reasoning_config={"enabled": True, "effort": "high"},
            base_url=base_url,
        )
        assert kwargs.get("thinking", {}).get("type") == "adaptive", (
            f"Kmx-family endpoint ({base_url}, {model}) must receive "
            f"adaptive thinking, got {kwargs.get('thinking')!r}"
        )
        assert "budget_tokens" not in kwargs["thinking"]
        assert kwargs["output_config"] == {"effort": "high"}
        # Adaptive mode must not force temperature or inflate max_tokens
        # (those are manual-budget-mode side effects).
        assert "temperature" not in kwargs
        assert kwargs["max_tokens"] == 4096




    def test_kmx_family_replay_preserves_unsigned_thinking(self) -> None:
        """On a custom Kmx endpoint, unsigned reasoning_content thinking
        blocks must survive the third-party signature-stripping pass so
        the upstream's message-history validation passes.
        """
        from agent.anthropic_message_convert import convert_messages_to_anthropic

        messages = [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "reasoning_content": "planning the tool call",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "skill_view", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
        ]
        _, converted = convert_messages_to_anthropic(
            messages,
            base_url="http://my-kmx-proxy.internal",
            model="kmx-2.6",
        )
        # The assistant message still carries the unsigned thinking block
        # synthesised from reasoning_content (required by Kmx's history
        # validation).  A plain third-party endpoint would have stripped it.
        assistant_msg = next(m for m in converted if m["role"] == "assistant")
        assistant_blocks = assistant_msg["content"]
        thinking_blocks = [
            b for b in assistant_blocks
            if isinstance(b, dict) and b.get("type") == "thinking"
        ]
        assert len(thinking_blocks) == 1
        assert thinking_blocks[0]["thinking"] == "planning the tool call"
