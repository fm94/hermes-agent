"""Test that kmx-coding and kmx-coding-cn both appear in the /model picker.

Both providers share the same models.dev ID (kmx-for-coding) but are distinct
profiles with different API keys, base URLs, and endpoints.  The /model picker
must show both so users can pick the right endpoint for their key type.

Regression: the original ``seen_mdev_ids`` dedup by mdev_id alone would skip
kmx-coding-cn after kmx-coding was emitted because both map to
``kmx-for-coding`` (#10526).  The fix deduplicates by
``(mdev_id, canonical_profile_name)`` instead, allowing distinct profiles
through.
"""

import os
from unittest.mock import patch

from hermes_cli.model_switch import (
    list_authenticated_providers,
    switch_model,
)
from hermes_cli.providers import resolve_provider_full


# -- Only KMX_CN_API_KEY set ------------------------------------------------


@patch.dict(os.environ, {"KMX_CN_API_KEY": "sk-cn-fake"}, clear=False)
def test_kmx_cn_appears_when_only_cn_key_set():
    """kmx-coding-cn should appear when only KMX_CN_API_KEY is set."""
    providers = list_authenticated_providers(current_provider="kmx-coding-cn")

    # kmx-coding-cn must be listed (it has credentials)
    cn = next((p for p in providers if p["slug"] == "kmx-coding-cn"), None)
    assert cn is not None, (
        "kmx-coding-cn should appear when KMX_CN_API_KEY is set"
    )
    assert cn["is_current"] is True
    assert cn["total_models"] > 0

    # kmx-coding must NOT appear (no KMX_API_KEY)
    intl = next((p for p in providers if p["slug"] == "kmx-coding"), None)
    assert intl is None, (
        "kmx-coding should NOT appear when only KMX_CN_API_KEY is set"
    )


# -- Only KMX_API_KEY set ---------------------------------------------------


# -- Both keys set -----------------------------------------------------------



# -- Both aliases deduped correctly ------------------------------------------



@patch.dict(os.environ, {
    "KMX_API_KEY": "sk-intl-fake",
    "KMX_CN_API_KEY": "sk-cn-fake",
}, clear=False)
def test_resolve_provider_full_preserves_kmx_cn_provider_identity():
    """Explicit kmx-coding-cn must not collapse to shared models.dev alias.

    Regression: resolve_provider_full('kmx-coding-cn') used normalize_provider(),
    which mapped both kmx-coding and kmx-coding-cn to the models.dev alias
    'kmx-for-coding'. That silently rewired CN users to the international
    endpoint and KMX_API_KEY.
    """
    pdef = resolve_provider_full("kmx-coding-cn", None, None)
    assert pdef is not None
    assert pdef.id == "kmx-coding-cn"
    assert pdef.base_url == "https://api.mshx.cn/v1"
    assert pdef.api_key_env_vars == ("KMX_CN_API_KEY",)


