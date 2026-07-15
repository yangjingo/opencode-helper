# OpenCode 内网模型接入方案

> ⚠️ 本文档中的 API 地址和 API Key 均为占位示例，使用前请替换为实际值。

---

## TL;DR

本文档是 **Claude Code 的内网替代方案**——用 OpenCode 对接内部模型服务，无需访问外网 API。

1. **配置 OpenCode 指向内网模型服务**（替代无法访问的公有云 API）
2. **自动清除上游代理**（防止 `HTTP_PROXY` 把内网请求错误转发，导致无法连接内网部署的模型）
3. **支持 Bash 和 PowerShell 两种终端**（打开即用，无需每次手动设置环境变量）

**如何使用本文档：** 你可以将本文档直接交给其他 AI Agent（如 Claude Code），让它按照文档内容帮你自动完成 OpenCode 的配置。配置完成后即可卸载 Claude Code，完全切换到 OpenCode。

---

## 1. 你面对的场景

```
┌──────────┐    直连内网    ┌──────────────────┐
│  OpenCode │ ──────────────→│ <内网API地址>:端口 │──→ 内部模型
│ (你的电脑) │ ←──────────────│  /v1 (兼容协议)   │
└─────┬────┘                └──────────────────┘
      │
      │ ❌ 如果 HTTP_PROXY 指向外网代理
      │    请求会经过外网绕一圈 → 超时 / 连不上
      ▼
  ┌──────────┐
  │ 外网代理  │  ← 不需要！API 在内网
  └──────────┘
```

- 团队在内网部署了模型服务，对外暴露兼容 API。
- 你的电脑可能设置了 `HTTP_PROXY` / `HTTPS_PROXY` 用于访问外网，但访问内网地址时这些代理需要绕开。
- `NO_PROXY=localhost,.rnd.huawei.com` 确保内网域名不走代理。但如果上游代理变量仍然存在，部分工具还是会尝试走代理。

---

## 2. 让 OpenCode 认识你的内部模型

**文件：** `~/.config/opencode/opencode.jsonc`

```jsonc
{
  "$schema": "https://opencode.ai/config.json",

  // 内网模型接入配置
  // baseURL 末尾的 /v1 是兼容 API 的标准路径后缀
  "provider": {
    "<your-provider>": {                // ⚠️ 改为你的 provider 名（如 openlab）
      "name": "<显示名称>",             // ⚠️ UI 中显示的友好名称
      "options": {
        "apiKey": "<your-api-key>",    // ⚠️ 替换为实际的认证 token
        "baseURL": "<http://IP:PORT/v1>" // ⚠️ 替换为实际的 API 端点
      },
      "models": {
        "<model-id>": {                // ⚠️ 替换为模型 ID，引用格式: provider名/model-id
          "name": "<模型显示名>",       // ⚠️ 显示名
          "reasoning": true,            // 是否开启推理链（thinking），视模型能力而定
          "thinking": true              // 是否展示思维过程，视模型能力而定
        }
      }
    }
  },

  "model": "<provider名>/<model-id>"    // ⚠️ 默认使用的模型
}
```

**以 OpenLab GLM-5.2 为例（已脱敏）：**

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  // OpenLab GLM-5.2 · 内网代理
  "provider": {
    "openlab": {
      "name": "OpenLab",
      "options": {
        "apiKey": "<your-api-key>",
        "baseURL": "http://<IP:PORT>/v1"
      },
      "models": {
        "glm-5.2": {
          "name": "GLM 5.2",
          "reasoning": true,
          "thinking": true
        }
      }
    }
  },
  "model": "openlab/glm-5.2"
}
```

**配置逻辑解读（给 AI 看）：**

| 字段 | 作用 | 为什么这样设 |
|------|------|-------------|
| `provider.<name>` | 自定义 provider key | 体现实际来源；OpenCode 支持任意 provider 名 |
| `options.baseURL` | 替换默认的公有云 API 地址 | 指向内网代理；末尾 `/v1` 是兼容 API 的路径前缀 |
| `options.apiKey` | 认证令牌 | 内网代理用此 token 鉴权，不走公有云的 API Key 体系 |
| `models.<id>.reasoning` | 是否启用推理 | 支持 thinking 的模型可开启，以生成深度推理链 |
| `models.<id>.thinking` | 是否展示思维过程 | true 时模型输出 `<thinking>` 块，false 则仅返回最终回答 |
| `model` | 默认模型引用 | 格式 `provider名/model-id`，OpenCode 启动时自动选用 |
| `$schema` | JSON Schema 校验 | 非必须，删除可加速加载（省去一次远程 fetch） |

> **注意：** OpenCode 不支持顶层 `env` 键来自定义环境变量——环境变量必须通过 shell profile 来管理。

---

## 3. 让代理别捣乱

系统残留的 `HTTP_PROXY` / `HTTPS_PROXY` 会让 OpenCode 把内网请求转发到外网代理，导致无法连接内网部署的模型。有两种方式处理：

### 临时方式（不修改任何文件）

每次启动前手动执行一行：

```bash
# Git Bash
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy && opencode
```

```powershell
# PowerShell
Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY -ErrorAction SilentlyContinue; opencode
```

如果不想永久修改 shell 配置，这种方式最轻量。

### 永久方式（推荐）

### Git Bash — `~/.bashrc`

```bash
# OpenCode — 启动前清除上游代理
opencode() {
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
  command opencode "$@"
}
```

**逐行解释：**

| 行 | 做什么 | 为什么 |
|----|--------|--------|
| `opencode() { ... }` | 定义一个 shell 函数，名字和 CLI 同名 | 这样你输入 `opencode` 时，shell 执行函数而非直接调可执行文件 |
| `unset HTTP_PROXY ...` | 移除四个代理环境变量 | 大小写都覆盖（有的工具读大写，有的读小写），确保代理不干扰内网请求 |
| `command opencode "$@"` | 调用真正的 opencode 可执行文件 | `command` 内置命令跳过 shell 函数查找，直接执行 PATH 中的二进制，避免递归；`"$@"` 透传全部命令行参数 |

### PowerShell — `$PROFILE`

```powershell
# OpenCode — 启动前清除上游代理
function opencode {
    Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
    & "$env:APPDATA\npm\opencode.cmd" @args
}
```

**逐行解释：**

| 行 | 做什么 | 为什么 |
|----|--------|--------|
| `Remove-Item Env:...` | 从环境变量中删除四个代理变量 | PowerShell 里 `unset` 的等价操作；`Env:` 驱动器是 PS 访问环境变量的方式 |
| `-ErrorAction SilentlyContinue` | 变量不存在时不报错 | 第一次启动时可能压根没设代理，不报错体验更好 |
| `& "$env:APPDATA\npm\opencode.cmd" @args` | 用完整路径调用可执行文件 | **关键：不能写 `& opencode`**——那样 PowerShell 会再次匹配到同名 function，造成无限递归 → `CallDepthOverflow`；`$env:APPDATA` 展开为 `C:\Users\xxx\AppData\Roaming`；`@args` 是 PS 的 splatting 语法，等价于 bash 的 `"$@"` |

---

## 4. 涉及的文件

| 文件 | 路径 | 作用 |
|------|------|------|
| OpenCode 配置 | `~/.config/opencode/opencode.jsonc` | 定义 provider、模型、API 端点 |
| Bash 包装器 | `~/.bashrc` | 每次输 `opencode` 时自动清除代理 |
| PowerShell 包装器 | `$PROFILE` (`Documents\WindowsPowerShell\...`) | 同上，PowerShell 版 |

---

## 5. 验证一切正常

> ⚠️ 验证前先将 `<API地址>` 和 `<your-api-key>` 替换为实际值。

```bash
# ① 确认 API 端点可达 → 应返回模型列表 JSON
curl -s http://<API地址>/v1/models \
  -H "Authorization: Bearer <your-api-key>"

# ② 确认模型能推理 → 应返回 assistant 回复
curl -s http://<API地址>/v1/messages \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","max_tokens":50,"messages":[{"role":"user","content":"hello"}]}'

# ③ 确认 OpenCode 整条链路通 → 应输出模型回复
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy && opencode run "hello"
```

---

## 6. 踩过的坑

| 症状 | 根因 | 修复 |
|------|------|------|
| PowerShell 报 `CallDepthOverflow` | 函数名 `opencode` 与命令名冲突，`& opencode` 调了自己 | 改用完整路径 `$env:APPDATA\npm\opencode.cmd` |
| 启动报 `Unrecognized key: env` | 把 Claude Code 的 `env` 配置直接抄到了 OpenCode | OpenCode 不支持顶层 `env`，环境变量通过 shell profile 管理 |
| API 请求超时 / 连不上 | `HTTP_PROXY` 指向外网代理，内网请求被错误路由 | 启动前 `unset` / `Remove-Item` 清除上游代理 |
| 标题生成报 `model does not exist` | OpenCode 内置尝试调用一个不存在的模型名 | 换了自定义 provider 名后不再触发，可忽略 |
| `.json` 和 `.jsonc` 谁生效 | 两个都被加载并深度合并 | 删掉 `.json`，只保留 `.jsonc`（支持注释），维护更省心 |
