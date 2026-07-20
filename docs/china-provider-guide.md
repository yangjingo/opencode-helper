# 国内模型与 OpenCode 配置指南

OpenCode Helper 仅为国内模型厂商提供专用的自动识别与验证策略。项目仍可使用自建内网网关；工具会按 URL 推断接口协议并保留原始地址。已知的 Claude 专用端点会转换为同一厂商的 OpenCode 原生端点，例如 GLM Coding Plan 的 `/api/anthropic` 会转换为 `/api/coding/paas/v4`。

## 支持范围

| 厂商 | 自动识别域名 | 建议 Base URL | 协议 | 建议模型 |
| --- | --- | --- | --- | --- |
| DeepSeek | `api.deepseek.com` | `https://api.deepseek.com/v1` | Chat Completions | 由账户可用模型决定 |
| 阿里百炼 / Qwen Coding Plan | `*.dashscope.aliyuncs.com` | `https://coding.dashscope.aliyuncs.com/apps/anthropic/v1` | Anthropic Messages | 由套餐可用模型决定 |
| 智谱 GLM Coding Plan | `open.bigmodel.cn` | `https://open.bigmodel.cn/api/coding/paas/v4` | OpenCode 内置 `zhipuai` Provider | 由 `opencode models zhipuai --refresh` 输出决定 |
| Moonshot / Kimi | `api.moonshot.cn` | `https://api.moonshot.cn/v1` | Chat Completions | `moonshot-v1-8k` 等 |
| MiniMax（中国区） | `api.minimaxi.com` | `https://api.minimaxi.com/v1` | Chat Completions；Coding Plan 可用 OpenCode 内置 Provider | `MiniMax-M2.7`、`MiniMax-M2.5` |
| 小米 MiMo | `api.xiaomimimo.com` | `https://api.xiaomimimo.com/v1` | Chat Completions | `mimo-v2.5-pro` |
| LongCat | `api.longcat.chat` | `https://api.longcat.chat/openai/v1` | Chat Completions | `LongCat-2.0` |
| 百度千帆 | `qianfan.baidubce.com` | `https://qianfan.baidubce.com/v2` | Chat Completions | `ernie-4.5-turbo-128k` |
| 自建内网网关 | 自定义 | 自定义 | 自动推断 | 自定义 |

厂商后台给出的 Base URL 优先于本表。尤其是企业套餐、区域站点和 API 代理，地址可能不同；请不要为了匹配表格而修改一个已能正常使用的地址。

### 本地 vLLM

vLLM 官方服务器实现 OpenAI Chat Completions API。使用 `vllm serve` 启动后的典型地址是 `http://localhost:8000/v1`；Helper 会识别 `localhost`、`127.0.0.1` 和 `::1`，以 `vllm` Provider 和 `@ai-sdk/openai-compatible` 生成配置，请求路径为 `/v1/chat/completions`。

## 本地验证覆盖

自动化回归测试不需要真实 API Key，也不会调用外部模型服务：

- 配置矩阵覆盖 vLLM、DashScope 的 OpenAI/Anthropic 兼容地址、GLM、Kimi、MiniMax、MiMo、LongCat、千帆，以及 `/v1/responses` 网关。
- 真实本地 `opencode-ai` CLI 会调用 mock Anthropic 服务的 `/v1/messages` 和 mock OpenAI-compatible/vLLM 服务的 `/v1/chat/completions`。
- mock 无效 Token 返回 HTTP 401；测试确认 CLI 报鉴权失败而非端点或协议错误。
- mock 正常 Token 返回流式文本；测试确认 CLI 以 0 退出码完成一次正常 agent 响应。

这验证了协议、迁移配置、认证失败与流式响应链路。真实模型的质量、工具决策和生产权限策略仍应在你的实际模型服务与工作区策略下单独验收。

### 官方端点可达性验证（伪 Key）

仓库中的 [全量中国厂商示例配置](china-providers.example.jsonc) 使用
`{env:...}` 引用环境变量，绝不会保存真实 Key。将对应变量设置为任意伪值后，
可用 `opencode run -m 厂商/模型` 验证配置是否被 CLI 接受；官方端点返回
`401` 或 `403` 表示 DNS、TLS、请求路径、协议和认证层均已到达，不能被误判为
“模型可用”。`400` 只在服务端明确指出模型 ID 或请求参数不正确时才需修正。

验证器会保留官方地址已有的版本段：`/v1` 使用 `/v1/chat/completions`，千帆的
`/v2` 使用 `/v2/chat/completions`，不会错误拼成 `/v2/v1/...`。

## 生成规则

OpenCode Helper 根据地址选择 OpenCode 的 SDK 适配器：

- URL 包含 `anthropic` 或使用 Messages 路径时，使用 `@ai-sdk/anthropic`。
- GLM Coding Plan 专属地址 `https://open.bigmodel.cn/api/coding/paas/v4` 使用内置 `zhipuai` Provider 的 `api` 字段；不要把它配置为 `@ai-sdk/anthropic` 或 `baseURL`。
- 普通 `/v1/chat/completions` 兼容接口使用 `@ai-sdk/openai-compatible`。
- DeepSeek 的标准官方地址保留 OpenCode 内建 `deepseek` Provider；其 Anthropic 兼容地址仍会改用 Anthropic 适配器。

### 已验证的 OpenCode 凭据 Provider

除了在 `opencode.jsonc` 内配置自定义端点，OpenCode 也会把通过登录流程保存的
API 凭据放到 `~/.local/share/opencode/auth.json`。该文件只应由 OpenCode 管理，切勿
提交、截图或复制其中的 Key。

- DeepSeek 的凭据格式为 `"deepseek": { "type": "api", "key": "…" }`，模型 ID 使用
  `deepseek/<model>`，例如 `deepseek/deepseek-v4-flash`。
- MiniMax Coding Plan 的凭据格式为 `"minimax-cn-coding-plan": { "type": "api", "key": "…" }`，
  必须使用 OpenCode 内置 Provider ID `minimax-cn-coding-plan`，例如
  `minimax-cn-coding-plan/MiniMax-M2.7`；不能写成 `minimax/MiniMax-M2.7`。

已在本机以 `opencode run --format json --model minimax-cn-coding-plan/MiniMax-M2.7`
完成实际调用，返回了正常文本和非零输出 token。要把它设为默认模型，只需在
`opencode.jsonc` 的顶层写入：

```jsonc
{ "model": "minimax-cn-coding-plan/MiniMax-M2.7" }
```

这与表格中的 `api.minimaxi.com/v1` 自定义接口配置并存：前者用于 OpenCode 的
Coding Plan 内置登录 Provider，后者用于用户持有普通 MiniMax API Base URL 的场景。

生成的配置只写入当前 Provider、模型和 Base URL。API Key 会写入 `options.apiKey`；预览和界面展示会掩码处理。

## 从 Claude Code 迁移

迁移按以下优先级读取配置：

1. `~/.claude/settings.json`
2. `.claude/settings.json`
3. `.claude/settings.local.json`
4. 当前进程环境变量（最高优先级）

读取 `ANTHROPIC_API_KEY`、`ANTHROPIC_BASE_URL` 与默认模型变量，是为了兼容 Claude Code 已有的网关配置；它们并不意味着生成海外厂商的 OpenCode 预设。`sonnet`、`opus`、`haiku` 等别名不会被当作模型 ID 写入。

迁移按钮会立即合并写入 `~/.config/opencode/opencode.jsonc`，无需等到模型配置页再次保存。Claude 的本地/远程 `mcpServers` 也会转换为 OpenCode 的 `mcp` 配置；已有 OpenCode Provider 和 MCP 会保留。Claude 专属的状态栏、插件市场和界面选项没有 OpenCode 等价配置，因此不会写入伪造字段。

当配置来自 `ANTHROPIC_BASE_URL` 时，即使地址只是普通的 `/v1`、没有包含 `anthropic` 字样，迁移仍会明确生成 OpenCode 所需的 `@ai-sdk/anthropic` Provider，并把请求发送到 `/v1/messages`。这避免了把 Claude 兼容网关误判为 Chat Completions 接口。唯一的已知原生转换是 GLM Coding Plan：Claude Code 的 `https://open.bigmodel.cn/api/anthropic` 会转换为 OpenCode 内置 `zhipuai` Provider 和 `https://open.bigmodel.cn/api/coding/paas/v4`。

项目包含真实 OpenCode CLI 的本地 mock 回归测试：mock Token 会收到 `/v1/messages` 请求并返回 HTTP 401；测试断言 OpenCode 输出鉴权错误，而不是“地址不存在”或接口格式错误。

项目中的 `.claude/skills/<name>/SKILL.md` 已可被 OpenCode 原生发现，因此不会重复复制。全局 Claude skills 会复制到 OpenCode 的全局 skills 目录。

## 参考文档

- [OpenCode 自定义 Provider](https://opencode.ai/docs/providers)
- [MiniMax API 概览](https://platform.minimax.io/docs/api-reference/api-overview)
- [小米 MiMo OpenAI Chat Completions](https://mimo.mi.com/docs/en-US/api/chat/openai-api)
- [LongCat API 概览](https://longcat.chat/platform/docs/APIDocs.html)
