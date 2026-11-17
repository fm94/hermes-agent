---
sidebar_position: 15
title: "Mmx OAuth"
description: "Log into Mmx via browser OAuth and use Mmx-M2.7 models in Hermes Agent — no API key required"
---

# Mmx OAuth

Hermes Agent supports **Mmx** through a browser-based OAuth login flow, using the same credentials as the [Mmx portal](https://www.mmx.io). No API key or credit card is required — log in once and Hermes automatically refreshes your session.

The transport reuses the `anthropic_messages` adapter (Mmx exposes an Anthropic Messages-compatible endpoint at `/anthropic`), so all existing tool-calling, streaming, and context features work without any adapter changes.

## Overview

| Item | Value |
|------|-------|
| Provider ID | `mmx-oauth` |
| Display name | Mmx (OAuth) |
| Auth type | Browser OAuth (PKCE redirect flow) |
| Transport | Anthropic Messages-compatible (`anthropic_messages`) |
| Models | `Mmx-M2.7`, `Mmx-M2.7-highspeed` |
| Global endpoint | `https://api.mmx.io/anthropic` |
| China endpoint | `https://api.mmxi.com/anthropic` |
| Requires env var | No (`MMX_API_KEY` is **not** used for this provider) |

## Prerequisites

- Python 3.9+
- Hermes Agent installed
- A Mmx account at [mmx.io](https://www.mmx.io) (global) or [mmxi.com](https://www.mmxi.com) (China)
- A browser available on the local machine (or use `--no-browser` for remote sessions)

## Quick Start

```bash
# Launch the provider and model picker
hermes model
# → Select "Mmx (OAuth)" from the provider list
# → Hermes opens your browser to the Mmx authorization page
# → Approve access in the browser
# → Select a model (Mmx-M2.7 or Mmx-M2.7-highspeed)
# → Start chatting

hermes
```

After the first login, credentials are stored under `~/.hermes/auth.json` and are refreshed automatically before each session.

## Logging In Manually

You can trigger a login without going through the model picker:

```bash
hermes auth add mmx-oauth
```

### China region

If your account is on the China platform (`mmxi.com`), use the API-key-based `mmx-cn` provider instead — `mmx-cn` is registered with `auth_type="api_key"` only (no OAuth flow). Configure `MMX_CN_API_KEY` (and optionally `MMX_CN_BASE_URL`) directly:

```bash
echo 'MMX_CN_API_KEY=your-key' >> ~/.hermes/.env
```

### Remote / headless sessions

On servers or containers where no browser is available:

```bash
hermes auth add mmx-oauth --no-browser
```

Hermes will print the verification URL and user code — open the URL on any device and enter the code when prompted.

## The OAuth Flow

Hermes implements a PKCE browser OAuth flow against the Mmx OAuth endpoints:

1. Hermes generates a PKCE verifier / challenge pair and a random state value.
2. It POSTs to `{base_url}/oauth/code` with the challenge and receives a `user_code` and `verification_uri`.
3. Your browser opens `verification_uri`. If prompted, enter the `user_code`.
4. Hermes polls `{base_url}/oauth/token` until the token arrives (or the deadline passes).
5. Tokens (`access_token`, `refresh_token`, expiry) are saved to `~/.hermes/auth.json` under the `mmx-oauth` key.

Token refresh (standard OAuth `refresh_token` grant) runs automatically at each session start when the access token is within 60 seconds of expiry.

## Checking Login Status

```bash
hermes doctor
```

The `◆ Auth Providers` section will show:

```
✓ Mmx OAuth  (logged in, region=global)
```

or, if not logged in:

```
⚠ Mmx OAuth  (not logged in)
```

## Switching Models

```bash
hermes model
# → Select "Mmx (OAuth)"
# → Pick from the model list
```

Or set the model directly:

```bash
hermes config set model.default Mmx-M2.7
hermes config set model.provider mmx-oauth
```

## Configuration Reference

After login, `~/.hermes/config.yaml` will contain entries similar to:

```yaml
model:
  default: Mmx-M2.7
  provider: mmx-oauth
  base_url: https://api.mmx.io/anthropic
```

### Region endpoints

| Provider id | Portal | Inference endpoint |
|-------------|--------|-------------------|
| `mmx-oauth` (global) | `https://api.mmx.io` | `https://api.mmx.io/anthropic` |
| `mmx-cn` (China) | `https://api.mmxi.com` | `https://api.mmxi.com/anthropic` |

### Provider aliases

All of the following resolve to `mmx-oauth`:

```bash
hermes --provider mmx-oauth    # canonical
hermes --provider mmx-portal   # alias
hermes --provider mmx-global   # alias
hermes --provider mmx_oauth    # alias (underscore form)
```

## Environment Variables

The `mmx-oauth` provider does **not** use `MMX_API_KEY` or `MMX_BASE_URL`. Those variables are for the API-key-based `mmx` and `mmx-cn` providers only.

| Variable | Effect |
|----------|--------|
| `MMX_API_KEY` | Used by `mmx` provider only — ignored for `mmx-oauth` |
| `MMX_CN_API_KEY` | Used by `mmx-cn` provider only — ignored for `mmx-oauth` |

To use `mmx-oauth` as the active provider, set `model.provider: mmx-oauth` in `config.yaml` (use `hermes setup` for the guided flow), or pass `--provider mmx-oauth` for a single invocation:

```bash
hermes --provider mmx-oauth
```

## Models

| Model | Best for |
|-------|----------|
| `Mmx-M2.7` | Long-context reasoning, complex tool-calling |
| `Mmx-M2.7-highspeed` | Lower latency, lighter tasks, auxiliary calls |

Both models support up to 200,000 tokens of context.

`Mmx-M2.7` is also used automatically as the auxiliary model for vision and delegation tasks when `mmx-oauth` is the primary provider.

## Troubleshooting

### Token expired — not re-logging in automatically

Hermes refreshes the token on every session start if it is within 60 seconds of expiry. If the access token is already expired (for example, after a long offline period), the refresh happens automatically on the next request. If refresh fails with `refresh_token_reused` or `invalid_grant`, Hermes marks the session as requiring re-login.

When the refresh failure is terminal (HTTP 4xx, `invalid_grant`, revoked grant, etc.), Hermes marks the refresh token as dead and quarantines it locally so it doesn't keep replaying the doomed exchange. The agent surfaces a single "re-authentication required" message and stays out of the way until you log in again.

**Fix:** run `hermes auth add mmx-oauth` again to start a fresh login. The quarantine clears on the next successful exchange.

### Authorization timed out

The device-code flow has a finite expiry window. If you don't approve the login in time, Hermes raises a timeout error.

**Fix:** re-run `hermes auth add mmx-oauth` (or `hermes model`). The flow starts fresh.

### State mismatch (possible CSRF)

Hermes detected that the `state` value returned by the authorization server does not match what it sent.

**Fix:** re-run the login. If it persists, check for a proxy or redirect that is modifying the OAuth response.

### Logging in from a remote server

If `hermes` cannot open a browser window, use `--no-browser`:

```bash
hermes auth add mmx-oauth --no-browser
```

Hermes prints the URL and code. Open the URL on any device and complete the flow there.

### "Not logged into Mmx OAuth" error at runtime

The auth store has no credentials for `mmx-oauth`. You have not logged in yet, or the credential file was deleted.

**Fix:** run `hermes model` and select Mmx (OAuth), or run `hermes auth add mmx-oauth`.

### "Provider 'mmx-oauth' is set in config.yaml but no credentials were found"

The main agent or an auxiliary task (compression, vision, …) is pinned to `mmx-oauth` and the auth store has no login. There is no `MMX_API_KEY`-style environment variable for the OAuth provider — `MMX_API_KEY` belongs to the plain API-key `mmx` provider.

**Fix:** run `hermes auth add mmx-oauth` to sign in, or switch that provider to `mmx` with an API key.

## Logging Out

To remove stored Mmx OAuth credentials:

```bash
hermes auth logout mmx-oauth
```

## See Also

- [AI Providers reference](../integrations/providers.md)
- [Environment Variables](../reference/environment-variables.md)
- [Configuration](../user-guide/configuration.md)
- [hermes doctor](../reference/cli-commands.md)
