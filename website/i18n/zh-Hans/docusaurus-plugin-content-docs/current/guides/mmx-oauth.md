---
sidebar_position: 15
title: "Mmx OAuth"
description: "通过浏览器 OAuth 登录 Mmx，在 Hermes Agent 中使用 Mmx-M2.7 模型——无需 API 密钥"
---

# Mmx OAuth

Hermes Agent 通过基于浏览器的 OAuth 登录流程支持 **Mmx**，使用与 [Mmx 门户](https://www.mmx.io) 相同的凭据。无需 API 密钥或信用卡——登录一次，Hermes 即可自动刷新您的会话。

该传输层复用了 `anthropic_messages` 适配器（Mmx 在 `/anthropic` 路径暴露了一个兼容 Anthropic Messages 的端点），因此所有现有的工具调用、流式传输和上下文功能无需任何适配器改动即可正常使用。

## 概览

| 项目 | 值 |
|------|-------|
| Provider ID | `mmx-oauth` |
| 显示名称 | Mmx (OAuth) |
| 认证类型 | 浏览器 OAuth（PKCE 设备码流程） |
| 传输层 | 兼容 Anthropic Messages（`anthropic_messages`） |
| 模型 | `Mmx-M2.7`、`Mmx-M2.7-highspeed` |
| 全球端点 | `https://api.mmx.io/anthropic` |
| 中国端点 | `https://api.mmxi.com/anthropic` |
| 需要环境变量 | 否（`MMX_API_KEY` **不**用于此 provider） |

## 前提条件

- Python 3.9+
- 已安装 Hermes Agent
- 在 [mmx.io](https://www.mmx.io)（全球）或 [mmxi.com](https://www.mmxi.com)（中国）注册的 Mmx 账户
- 本地机器上可用的浏览器（远程会话请使用 `--no-browser`）

## 快速开始

```bash
# 启动 provider 和模型选择器
hermes model
# → 从 provider 列表中选择 "Mmx (OAuth)"
# → Hermes 在浏览器中打开 Mmx 授权页面
# → 在浏览器中批准访问
# → 选择模型（Mmx-M2.7 或 Mmx-M2.7-highspeed）
# → 开始对话

hermes
```

首次登录后，凭据将存储在 `~/.hermes/auth.json` 下，并在每次会话前自动刷新。

## 手动登录

您可以在不经过模型选择器的情况下触发登录：

```bash
hermes auth add mmx-oauth
```

### 中国区域

如果您的账户在中国平台（`mmxi.com`），请改用中国区域 OAuth provider id `mmx-cn`，或跳过 OAuth 直接配置 `MMX_CN_API_KEY` / `MMX_CN_BASE_URL`。旧版文档中描述的 `--region cn` 标志**未**接入 CLI 的参数解析器；请改用 `mmx-cn` provider：

```bash
hermes auth add mmx-cn --type oauth   # 如果您的中国账户支持 OAuth
# 或更简单的方式：
echo 'MMX_CN_API_KEY=your-key' >> ~/.hermes/.env
```

### 远程/无头会话

在没有浏览器的服务器或容器上：

```bash
hermes auth add mmx-oauth --no-browser
```

Hermes 将打印验证 URL 和用户码——在任意设备上打开该 URL，并在提示时输入用户码。

## OAuth 流程

Hermes 针对 Mmx OAuth 端点实现了 PKCE 设备码流程：

1. Hermes 生成 PKCE verifier/challenge 对和一个随机 state 值。
2. 携带 challenge 向 `{base_url}/oauth/code` 发送 POST 请求，获取 `user_code` 和 `verification_uri`。
3. 浏览器打开 `verification_uri`。如有提示，输入 `user_code`。
4. Hermes 轮询 `{base_url}/oauth/token`，直到令牌到达（或超过截止时间）。
5. 令牌（`access_token`、`refresh_token`、过期时间）以 `mmx-oauth` 为键保存到 `~/.hermes/auth.json`。

令牌刷新（标准 OAuth `refresh_token` 授权）在每次会话启动时自动执行，当 access token 距过期不足 60 秒时触发。

## 检查登录状态

```bash
hermes doctor
```

`◆ Auth Providers` 部分将显示：

```
✓ Mmx OAuth  (logged in, region=global)
```

或者，如果未登录：

```
⚠ Mmx OAuth  (not logged in)
```

## 切换模型

```bash
hermes model
# → 选择 "Mmx (OAuth)"
# → 从模型列表中选择
```

或直接设置模型：

```bash
hermes config set model Mmx-M2.7
hermes config set provider mmx-oauth
```

## 配置参考

登录后，`~/.hermes/config.yaml` 将包含类似如下的条目：

```yaml
model:
  default: Mmx-M2.7
  provider: mmx-oauth
  base_url: https://api.mmx.io/anthropic
```

### 区域端点

| Provider id | 门户 | 推理端点 |
|-------------|--------|-------------------|
| `mmx-oauth`（全球） | `https://api.mmx.io` | `https://api.mmx.io/anthropic` |
| `mmx-cn`（中国） | `https://api.mmxi.com` | `https://api.mmxi.com/anthropic` |

### Provider 别名

以下所有别名均解析为 `mmx-oauth`：

```bash
hermes --provider mmx-oauth    # 规范名称
hermes --provider mmx-portal   # 别名
hermes --provider mmx-global   # 别名
hermes --provider mmx_oauth    # 别名（下划线形式）
```

## 环境变量

`mmx-oauth` provider **不**使用 `MMX_API_KEY` 或 `MMX_BASE_URL`。这些变量仅用于基于 API 密钥的 `mmx` 和 `mmx-cn` provider。

| 变量 | 作用 |
|----------|--------|
| `MMX_API_KEY` | 仅用于 `mmx` provider——对 `mmx-oauth` 无效 |
| `MMX_CN_API_KEY` | 仅用于 `mmx-cn` provider——对 `mmx-oauth` 无效 |

要将 `mmx-oauth` 设为活跃 provider，请在 `config.yaml` 中设置 `model.provider: mmx-oauth`（使用 `hermes setup` 进行引导式配置），或在单次调用时传入 `--provider mmx-oauth`：

```bash
hermes --provider mmx-oauth
```

## 模型

| 模型 | 最适合 |
|-------|----------|
| `Mmx-M2.7` | 长上下文推理、复杂工具调用 |
| `Mmx-M2.7-highspeed` | 低延迟、轻量任务、辅助调用 |

两个模型均支持最多 200,000 个 token 的上下文。

当 `mmx-oauth` 为主 provider 时，`Mmx-M2.7-highspeed` 也会自动用作视觉和委托任务的辅助模型。

## 故障排查

### 令牌已过期——未自动重新登录

Hermes 在每次会话启动时，若 access token 距过期不足 60 秒则刷新令牌。如果 access token 已经过期（例如长时间离线后），刷新将在下一次请求时自动触发。如果刷新失败并返回 `refresh_token_reused` 或 `invalid_grant`，Hermes 会将会话标记为需要重新登录。

当刷新失败为终态（HTTP 4xx、`invalid_grant`、授权已撤销等）时，Hermes 将 refresh token 标记为失效并在本地隔离，避免持续重放注定失败的交换。Agent 会显示一条"需要重新认证"的消息，并在您再次登录之前保持等待。

**解决方法：** 再次运行 `hermes auth add mmx-oauth` 以开始全新登录。下一次成功交换后隔离状态将自动清除。

### 授权超时

设备码流程有有限的过期窗口。如果您未在规定时间内批准登录，Hermes 将抛出超时错误。

**解决方法：** 重新运行 `hermes auth add mmx-oauth`（或 `hermes model`）。流程将重新开始。

### State 不匹配（可能的 CSRF）

Hermes 检测到授权服务器返回的 `state` 值与其发送的值不匹配。

**解决方法：** 重新运行登录。如果问题持续，请检查是否有代理或重定向正在修改 OAuth 响应。

### 从远程服务器登录

如果 `hermes` 无法打开浏览器窗口，请使用 `--no-browser`：

```bash
hermes auth add mmx-oauth --no-browser
```

Hermes 将打印 URL 和用户码。在任意设备上打开该 URL 并在那里完成流程。

### 运行时出现"未登录 Mmx OAuth"错误

auth 存储中没有 `mmx-oauth` 的凭据。您尚未登录，或凭据文件已被删除。

**解决方法：** 运行 `hermes model` 并选择 Mmx (OAuth)，或运行 `hermes auth add mmx-oauth`。

## 退出登录

要移除已存储的 Mmx OAuth 凭据：

```bash
hermes auth logout mmx-oauth
```

## 另请参阅

- [AI Providers 参考](../integrations/providers.md)
- [环境变量](../reference/environment-variables.md)
- [配置](../user-guide/configuration.md)
- [hermes doctor](../reference/cli-commands.md)