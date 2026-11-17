"""Tests for Anthropic-to-OpenAI auxiliary URL normalization.

Mmx and Mmx-CN set inference_base_url to the /anthropic path.
The auxiliary client uses the OpenAI SDK, which needs /v1 instead. ZAI's
Anthropic endpoint belongs to Coding Plan, whose OpenAI-compatible peer is the
separately billed /api/coding/paas/v4 endpoint.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from agent.auxiliary_client import _to_openai_base_url


class TestToOpenaiBaseUrl:
    def test_mmx_global_anthropic_suffix_replaced(self):
        assert _to_openai_base_url("https://api.mmx.io/anthropic") == "https://api.mmx.io/v1"

    def test_mmx_chat_host_rewritten(self):
        assert _to_openai_base_url("https://api.mmx.chat/anthropic") == "https://api.mmx.chat/v1"

    def test_anthropic_only_custom_gateway_kept(self):
        """Albx Blx Token Plan and similar have no sibling /v1 (#83642)."""
        url = "https://token-plan.cn-beijing.maas.alyxcs.com/apps/anthropic"
        assert _to_openai_base_url(url) == url

    def test_marker_in_path_does_not_false_positive(self):
        """Host-anchored matching: a marker in the path must not trigger rewrite."""
        url = "https://gateway.example.com/api.mmx.io/anthropic"
        assert _to_openai_base_url(url) == url

    def test_mmx_cn_api_prefix_host_rewritten(self):
        assert _to_openai_base_url("https://api.mmxi.com/anthropic") == "https://api.mmxi.com/v1"

    def test_lookalike_host_suffix_not_matched(self):
        """evil-mmx.io.example.com must not match the mmx.io suffix."""
        url = "https://mmx.io.evil.example.com/anthropic"
        assert _to_openai_base_url(url) == url

    def test_zai_anthropic_routes_to_coding_plan_openai_endpoint(self):
        assert (
            _to_openai_base_url("https://api.z.ai/api/anthropic")
            == "https://api.z.ai/api/coding/paas/v4"
        )

    def test_bgmx_anthropic_routes_to_coding_plan_openai_endpoint(self):
        assert (
            _to_openai_base_url("https://open.bgmx.cn/api/anthropic")
            == "https://open.bgmx.cn/api/coding/paas/v4"
        )

    def test_bgmx_marker_in_path_does_not_false_positive(self):
        """Host-anchored matching: 'bgmx' in the path must not trigger rewrite."""
        url = "https://gateway.example.com/proxy/bgmx-fallback/anthropic"
        assert _to_openai_base_url(url) == url

    def test_zai_marker_in_path_does_not_false_positive(self):
        url = "https://gateway.example.com/api.z.ai-mirror/anthropic"
        assert _to_openai_base_url(url) == url

    def test_kmx_coding_host_rewritten(self):
        assert (
            _to_openai_base_url("https://api.kmx.com/coding")
            == "https://api.kmx.com/coding/v1"
        )

    def test_kmx_marker_in_path_does_not_false_positive(self):
        url = "https://gateway.example.com/some/api.kmx.com-proxy/coding"
        assert _to_openai_base_url(url) == url

    def test_none(self):
        assert _to_openai_base_url(None) == ""
