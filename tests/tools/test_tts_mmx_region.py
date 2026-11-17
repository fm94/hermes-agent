"""Mmx TTS region, endpoint, and credential selection tests."""

from unittest.mock import MagicMock, patch

import pytest

from tools.tts_tool import (
    _generate_mmx_tts,
    _resolve_mmx_tts_runtime,
    check_tts_requirements,
)
from tools.tts_tool_providers import DEFAULT_MMX_BASE_URL, DEFAULT_MMX_CN_BASE_URL


GLOBAL_CREDENTIAL_SENTINEL = "FAKE_GLOBAL_CREDENTIAL"
CN_CREDENTIAL_SENTINEL = "FAKE_CN_CREDENTIAL"


@pytest.fixture(autouse=True)
def _fake_mmx_credentials(monkeypatch):
    values = {}
    monkeypatch.setattr(
        "hermes_cli.config.get_env_value",
        lambda name, default=None: values.get(name, default),
    )
    return values


@pytest.mark.parametrize(
    ("config", "credentials", "expected"),
    [
        pytest.param(
            {},
            {"MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL},
            (
                "global",
                DEFAULT_MMX_BASE_URL,
                "MMX_API_KEY",
                GLOBAL_CREDENTIAL_SENTINEL,
            ),
            id="global-only",
        ),
        pytest.param(
            {},
            {"MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL},
            (
                "cn",
                DEFAULT_MMX_CN_BASE_URL,
                "MMX_CN_API_KEY",
                CN_CREDENTIAL_SENTINEL,
            ),
            id="china-only",
        ),
        pytest.param(
            {},
            {
                "MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL,
                "MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL,
            },
            (
                "global",
                DEFAULT_MMX_BASE_URL,
                "MMX_API_KEY",
                GLOBAL_CREDENTIAL_SENTINEL,
            ),
            id="both-default-to-global",
        ),
        pytest.param(
            {"mmx": {"region": "global"}},
            {
                "MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL,
                "MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL,
            },
            (
                "global",
                DEFAULT_MMX_BASE_URL,
                "MMX_API_KEY",
                GLOBAL_CREDENTIAL_SENTINEL,
            ),
            id="explicit-global",
        ),
        pytest.param(
            {"mmx": {"region": "cn"}},
            {
                "MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL,
                "MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL,
            },
            (
                "cn",
                DEFAULT_MMX_CN_BASE_URL,
                "MMX_CN_API_KEY",
                CN_CREDENTIAL_SENTINEL,
            ),
            id="explicit-china",
        ),
    ],
)
def test_runtime_selection_matrix(
    _fake_mmx_credentials,
    config,
    credentials,
    expected,
):
    _fake_mmx_credentials.update(credentials)

    runtime = _resolve_mmx_tts_runtime(config)

    assert (
        runtime.region,
        runtime.endpoint,
        runtime.credential_source,
        runtime.api_key,
    ) == expected


@pytest.mark.parametrize(
    ("region", "credentials", "missing_source"),
    [
        pytest.param(
            "global",
            {"MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL},
            "MMX_API_KEY",
            id="global-does-not-borrow-china-key",
        ),
        pytest.param(
            "cn",
            {"MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL},
            "MMX_CN_API_KEY",
            id="china-does-not-borrow-global-key",
        ),
    ],
)
def test_explicit_region_requires_matching_credential(
    _fake_mmx_credentials,
    region,
    credentials,
    missing_source,
):
    _fake_mmx_credentials.update(credentials)

    with pytest.raises(ValueError, match=missing_source):
        _resolve_mmx_tts_runtime({"mmx": {"region": region}})


@pytest.mark.parametrize(
    ("config", "credentials", "expected"),
    [
        pytest.param(
            {"provider": "mmx"},
            {"MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL},
            True,
            id="china-only-available",
        ),
        pytest.param(
            {"provider": "mmx", "mmx": {"region": "cn"}},
            {"MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL},
            False,
            id="selected-region-missing",
        ),
        pytest.param(
            {"provider": "mmx", "mmx": {"region": "invalid"}},
            {
                "MMX_API_KEY": GLOBAL_CREDENTIAL_SENTINEL,
                "MMX_CN_API_KEY": CN_CREDENTIAL_SENTINEL,
            },
            False,
            id="invalid-region",
        ),
    ],
)
def test_availability_uses_atomic_runtime(
    monkeypatch,
    _fake_mmx_credentials,
    config,
    credentials,
    expected,
):
    _fake_mmx_credentials.update(credentials)
    monkeypatch.setattr("tools.tts_tool._load_tts_config", lambda: config)

    assert check_tts_requirements() is expected


def test_runtime_repr_excludes_raw_credential(_fake_mmx_credentials):
    _fake_mmx_credentials["MMX_API_KEY"] = GLOBAL_CREDENTIAL_SENTINEL

    runtime = _resolve_mmx_tts_runtime({})

    assert GLOBAL_CREDENTIAL_SENTINEL not in repr(runtime)
