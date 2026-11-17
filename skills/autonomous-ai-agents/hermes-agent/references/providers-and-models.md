# Providers & Model Aliases

Set via `hermes model` (picker) or `hermes setup`. 35+ provider profiles ship as
plugins under `plugins/model-providers/`; user plugins of the same name override.
Full docs: https://hermes-agent.nousresearch.com/docs/integrations/providers

### Providers

| Provider | Auth | Key env var(s) |
|----------|------|----------------|
| openrouter | API key | `OPENROUTER_API_KEY` |
| anthropic | API key | `ANTHROPIC_API_KEY` (also `CLAUDE_CODE_OAUTH_TOKEN`) |
| nous | OAuth device code | `hermes auth add nous` (or `NOUS_API_KEY`) |
| openai-codex | OAuth | `hermes auth add openai-codex` |
| qwx-oauth | OAuth | `hermes auth add qwx-oauth` |
| mmx-oauth | OAuth | `hermes auth add mmx-oauth` |
| gemini | API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| xai | API key | `XAI_API_KEY` (SuperGrok OAuth also supported) |
| dsx | API key | `DSX_API_KEY` |
| zai (GLX) | API key | `GLX_API_KEY` / `ZAI_API_KEY` |
| mmx / mmx-cn | API key | `MMX_API_KEY` / `MMX_CN_API_KEY` |
| kmx-coding / -cn | API key | `KMX_API_KEY` / `KMX_CN_API_KEY` |
| albx (+coding-plan) | API key | `DSHX_API_KEY` / `ALBX_CODING_PLAN_API_KEY` |
| xmx | API key | `XMX_API_KEY` |
| huggingface | Token | `HF_TOKEN` |
| fireworks / novita / nvidia / deepinfra / gmi / arcee / sfxx / upstage / kilocode / ai-gateway / opencode-zen / opencode-go / ollama-cloud | API key | `<NAME>_API_KEY` |
| bedrock / vertex / azure-foundry | Cloud SDK / key | AWS SDK creds / Vertex ADC / `AZURE_FOUNDRY_API_KEY` |
| custom | Config | `model.base_url` + `model.api_key` in config.yaml |

GitHub Copilot (`copilot`, `copilot-acp`) is a labs plugin, not core: `hermes plugins install github-copilot`, then `hermes auth add copilot` (https://github.com/NousResearch/hermes-labs-plugins/tree/main/github-copilot).

Multiple credentials per provider pool and rotate automatically (`hermes auth`).
Fallback chain when the primary fails: `hermes fallback add|remove|list`.

### User-defined model aliases

Work with `/model <name>` in CLI and every gateway platform. Resolved by
`hermes_cli/model_switch.py::resolve_alias()`; user aliases are checked BEFORE
the built-in table, so a user `sonnet`/`grok` shadows the built-in.

```yaml
# Full form
model_aliases:
  fav:
    model: claude-sonnet-4.6
    provider: anthropic
  local-qwx:
    model: qwx3.5:397b
    provider: custom
    base_url: "https://ollama.com/v1"
  theta:
    model: theta-1
    provider: custom
    base_url: "https://theta.example.com/v1"
    key_env: THETA_API_KEY        # or: api_key: "${THETA_API_KEY}"

# Short form ("provider/model"), also via CLI:
#   hermes config set model.aliases.fav openrouter/anthropic/claude-sonnet-4.6
model:
  aliases:
    fav: openrouter/anthropic/claude-sonnet-4.6
```

`/model fav` — session-scoped; add `--global` to persist as default.

An alias with its own `base_url` authenticates with its own credential
(`api_key`, which also accepts a `"${VAR}"` reference, or `key_env`). With
neither set the key is resolved from the alias HOST, never carried over from
the provider that was active before the switch.

Built-in aliases (catalog-resolved against the active provider): `sonnet`,
`opus`, `haiku`, `claude`, `gpt5`, `gpt`, `codex`, `o3`, `o4`, `gemini`,
`dsx`, `grok`, `llama`, `qwx`, `mmx`, `nemotron`, `kmx`, `glx`,
`step`, `mimx`, `trinity`.
