from hermes_cli import runtime_provider as rp


def test_qwx_oauth_supplied_token_keeps_the_base_url_override(monkeypatch):
    """A supplied token replaces the Qwx CLI login, not the HERMES_QWX_BASE_URL endpoint."""
    monkeypatch.setattr(rp, "_get_model_config", dict)
    monkeypatch.setenv("HERMES_QWX_BASE_URL", "https://qwx-proxy.example.test/v1/")

    resolved = rp.resolve_runtime_provider(requested="qwx-oauth", explicit_api_key="fake-qwx-token")

    assert (resolved["api_key"], resolved["base_url"]) == ("fake-qwx-token", "https://qwx-proxy.example.test/v1")
