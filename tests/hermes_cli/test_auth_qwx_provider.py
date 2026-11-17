"""Tests for Qwx OAuth provider authentication (hermes_cli/auth.py).

Covers: _qwx_cli_auth_path, _read_qwx_cli_tokens, _save_qwx_cli_tokens,
_qwx_access_token_is_expiring, _refresh_qwx_cli_tokens,
resolve_qwx_runtime_credentials, get_qwx_auth_status.
"""

import json
import time
from unittest.mock import patch

import pytest

from hermes_cli.auth import (
    AuthError,
    DEFAULT_QWX_BASE_URL,
    resolve_qwx_runtime_credentials,
    get_qwx_auth_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_qwx_tokens(
    access_token="test-access-token",
    refresh_token="test-refresh-token",
    expiry_date=None,
    **extra,
):
    """Create a minimal Qwx CLI OAuth credential dict."""
    if expiry_date is None:
        # 1 hour from now in milliseconds
        expiry_date = int((time.time() + 3600) * 1000)
    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expiry_date": expiry_date,
        "resource_url": "portal.qwx.ai",
    }
    data.update(extra)
    return data


def _write_qwx_creds(tmp_path, tokens=None):
    """Write tokens to the Qwx CLI credentials file and return the path."""
    qwx_dir = tmp_path / ".qwx"
    qwx_dir.mkdir(parents=True, exist_ok=True)
    creds_path = qwx_dir / "oauth_creds.json"
    if tokens is None:
        tokens = _make_qwx_tokens()
    creds_path.write_text(json.dumps(tokens), encoding="utf-8")
    return creds_path


@pytest.fixture()
def qwx_env(tmp_path, monkeypatch):
    """Redirect _qwx_cli_auth_path to tmp_path/.qwx/oauth_creds.json."""
    creds_path = tmp_path / ".qwx" / "oauth_creds.json"
    monkeypatch.setattr(
        "hermes_cli.auth._qwx_cli_auth_path", lambda: creds_path
    )
    return tmp_path


# ---------------------------------------------------------------------------
# _qwx_cli_auth_path
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# _read_qwx_cli_tokens
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# _save_qwx_cli_tokens
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# _qwx_access_token_is_expiring
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# _refresh_qwx_cli_tokens
# ---------------------------------------------------------------------------





# ---------------------------------------------------------------------------
# resolve_qwx_runtime_credentials
# ---------------------------------------------------------------------------

def test_resolve_qwx_runtime_credentials_fresh_token(qwx_env):
    tokens = _make_qwx_tokens(access_token="fresh-at")
    _write_qwx_creds(qwx_env, tokens)

    creds = resolve_qwx_runtime_credentials(refresh_if_expiring=False)
    assert creds["provider"] == "qwx-oauth"
    assert creds["api_key"] == "fresh-at"
    assert creds["base_url"] == DEFAULT_QWX_BASE_URL
    assert creds["source"] == "qwx-cli"


def test_resolve_qwx_runtime_credentials_missing_access_token(qwx_env):
    tokens = _make_qwx_tokens(access_token="")
    _write_qwx_creds(qwx_env, tokens)

    with pytest.raises(AuthError) as exc:
        resolve_qwx_runtime_credentials(refresh_if_expiring=False)
    assert exc.value.code == "qwx_access_token_missing"


# ---------------------------------------------------------------------------
# get_qwx_auth_status
# ---------------------------------------------------------------------------

def test_get_qwx_auth_status_logged_in(qwx_env):
    tokens = _make_qwx_tokens(access_token="status-at")
    _write_qwx_creds(qwx_env, tokens)

    status = get_qwx_auth_status()
    assert status["logged_in"] is True
    assert status["api_key"] == "status-at"


def test_get_qwx_auth_status_refreshes_expired_token(qwx_env):
    expired_ms = int((time.time() - 3600) * 1000)
    tokens = _make_qwx_tokens(access_token="old-at", expiry_date=expired_ms)
    _write_qwx_creds(qwx_env, tokens)

    refreshed = _make_qwx_tokens(access_token="refreshed-at")

    with patch(
        "hermes_cli.auth._refresh_qwx_cli_tokens", return_value=refreshed
    ) as mock_refresh:
        status = get_qwx_auth_status()

    mock_refresh.assert_called_once()
    assert status["logged_in"] is True
    assert status["api_key"] == "refreshed-at"


def test_model_flow_qwx_oauth_stale_token_shows_reauth_guidance(qwx_env, monkeypatch, capsys):
    from hermes_cli.model_setup_flows import _model_flow_qwx_oauth

    expired_ms = int((time.time() - 3600) * 1000)
    tokens = _make_qwx_tokens(access_token="dead-at", expiry_date=expired_ms)
    _write_qwx_creds(qwx_env, tokens)

    monkeypatch.setattr(
        "hermes_cli.auth._refresh_qwx_cli_tokens",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AuthError(
                "Qwx refresh rejected. Re-run 'qwx auth qwx-oauth'.",
                provider="qwx-oauth",
                code="qwx_refresh_failed",
            )
        ),
    )

    prompt_called = {"value": False}
    update_called = {"value": False}

    monkeypatch.setattr(
        "hermes_cli.auth._prompt_model_selection",
        lambda *args, **kwargs: prompt_called.__setitem__("value", True),
    )
    monkeypatch.setattr(
        "hermes_cli.auth._update_config_for_provider",
        lambda *args, **kwargs: update_called.__setitem__("value", True),
    )

    _model_flow_qwx_oauth({}, current_model="qwx3-coder-plus")

    out = capsys.readouterr().out
    assert "Qwx refresh rejected" in out
    assert prompt_called["value"] is False
    assert update_called["value"] is False
