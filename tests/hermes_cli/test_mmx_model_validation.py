"""Tests for Mmx model validation via static catalog (issues #12611, #12460, #12399, #12547).

Mmx and Mmx-CN providers don't expose /v1/models, so validate_requested_model()
must validate against the static catalog instead of probing the live API.
"""

from unittest.mock import patch

import pytest

from hermes_cli.models_validate import validate_requested_model


class TestMmxModelValidation:
    """Test that validate_requested_model handles Mmx providers correctly."""

    @pytest.fixture(autouse=True)
    def _isolate_mmx(self):
        """Ensure Mmx catalog is used even if a live /v1/models endpoint exists."""
        # Simulate fetch_api_models returning None (i.e., /v1/models is unreachable),
        # proving that the catalog path is taken.
        probe_payload = {
            "models": None,
            "probed_url": "https://api.mmx.io/v1/models",
            "resolved_base_url": "https://api.mmx.io/v1",
            "suggested_base_url": None,
            "used_fallback": False,
        }
        with patch("hermes_cli.models.fetch_api_models", return_value=None), \
             patch("hermes_cli.models.probe_api_models", return_value=probe_payload):
            yield

    # -------------------------------------------------------------------------
    # Test 1: A known Mmx model is accepted with recognized=True
    # -------------------------------------------------------------------------
    def test_valid_mmx_model_accepted(self):
        result = validate_requested_model("Mmx-M2.7", "mmx")
        assert result["accepted"] is True
        assert result["persist"] is True
        assert result["recognized"] is True
        assert result["message"] is None

    # -------------------------------------------------------------------------
    # Test 1b: Case-insensitive lookup matches catalog entries
    # -------------------------------------------------------------------------

    def test_valid_mmx_model_uppercase(self):
        result = validate_requested_model("MMX-M2.7", "mmx")
        assert result["accepted"] is True
        assert result["recognized"] is True

    # -------------------------------------------------------------------------
    # Test 2: A near-match model on mmx-cn triggers a suggestion (not auto-correct)
    # -------------------------------------------------------------------------
    def test_near_match_mmx_cn_suggests_similar(self):
        # "Mmx-M2.7-highspeed" is somewhat similar to "Mmx-M2.7" (ratio ~0.71)
        # but below the 0.9 auto-correct cutoff. It should be accepted with a
        # recognized=False and a similar-models suggestion (ratio > 0.5).
        result = validate_requested_model("Mmx-M2.7-highspeed", "mmx-cn")
        assert result["accepted"] is True
        assert result["persist"] is True
        assert result["recognized"] is False
        # Should NOT auto-correct (ratio 0.71 < 0.9)
        assert "corrected_model" not in result
        # But should suggest similar models (ratio 0.71 > 0.5)
        assert "Mmx-M2.7" in result["message"]

    # -------------------------------------------------------------------------
    # Test 3: A completely unknown model is accepted (not rejected) with a warning
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Test 4: Verify catalog path is used (probe_api_models returns None)
    # -------------------------------------------------------------------------


