"""albx-coding-plan and albx-coding-plan-cn must not both appear in the
/model picker off a single shared key (#101122).

The CN profile now has its own ALBX_CODING_PLAN_CN_API_KEY (checked first),
keeping the shared ALBX_CODING_PLAN_API_KEY / DSHX_API_KEY as ordered
fallbacks so existing CN users are not broken.  The picker hides a ``-cn`` row
whose only lit vars are shared with a lit non-CN sibling row.
"""

import os
from unittest.mock import patch

from hermes_cli.model_switch import list_authenticated_providers

_CLEAR = {k: "" for k in ("ALBX_CODING_PLAN_API_KEY", "ALBX_CODING_PLAN_CN_API_KEY", "DSHX_API_KEY")}


def _albx_slugs(current_provider=""):
    return [p["slug"] for p in list_authenticated_providers(current_provider=current_provider) if "coding-plan" in p["slug"]]


@patch.dict(os.environ, {**_CLEAR, "ALBX_CODING_PLAN_CN_API_KEY": "sk-cn-fake"}, clear=False)
def test_albx_cn_appears_when_only_cn_key_set():
    assert _albx_slugs() == ["albx-coding-plan-cn"]


@patch.dict(os.environ, {**_CLEAR, "ALBX_CODING_PLAN_API_KEY": "sk-intl-fake"}, clear=False)
def test_albx_cn_does_not_appear_when_only_intl_key_set():
    """#101122: the shared intl key alone must light only the intl row."""
    assert _albx_slugs() == ["albx-coding-plan"]
