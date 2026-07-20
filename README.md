# 🎮 OpenCode Helper

> 一键安装 · 模型配置 · Claude Code 迁移 · 真实验证

一个桌面助手，让你 5 分钟内完成 OpenCode 的安装、模型配置、代理绕行和 Claude Code 配置迁移。零门槛，零手动编辑。

![Platform](https://img.shields.io/badge/platform-Windows%2010%2B-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Size](https://img.shields.io/badge/size-8.9MB-lightgrey)

---

## 一张图看懂

![OpenCode Helper：海报、流程演示与真实 EXE 录屏](docs/assets/opencode-helper-showcase.gif)

> 左侧为功能海报；右上为流程演示；右下为真实打包 EXE 的运行录屏。

**OpenCode Helper 帮你解决什么问题？**

- Node、npm、OpenCode 或国内镜像配置缺失：自动检测，并提供一键安装/修复。
- Claude Code 已能用但 OpenCode 不可用：迁移 Key、Base URL、模型与 Skills，保留原始地址。
- 模型配置容易填错：识别 GLM、Qwen、DeepSeek、Kimi、MiniMax、MiMo、LongCat、千帆及本地 vLLM 的接口协议。
- 不知道接口到底通不通：真实访问官方端点；伪 Key 返回 `401/403` 也会明确标记为“端点可达”。

## 功能

- 🔍 **环境检测** — 自动扫描 OS、Node.js、npm、磁盘、代理、Claude Code 配置
- 🔧 **自动修复** — Node.js 缺失？npm 源慢？一键自动修复（国内镜像加速）
- 📦 **双模式安装** — npm 全局安装 / .exe 独立安装包
- ⚙ **模型配置** — 表单填写 + 预设模板，零出错
- 🛡 **代理处理** — 自动检测上游代理，生成 launcher 脚本，内网直连
- 🔄 **Claude Code 迁移** — 按用户 / 项目 / 本地配置优先级识别 API Key、Base URL、真实模型、Instructions、Skills
- ✅ **验证测试** — 安装后自动测试 API 端点和模型推理
- 🎨 **清晰引导** — 进度、命令与验证结果始终可见
- 🌐 **中英双语** — 默认中文，自动检测系统语言

---

## 快速开始

### 方式 1：直接下载 .exe（推荐）

从 [Releases](../../releases) 下载 `opencode-helper.exe`，双击运行。

### 方式 2：从源码运行

```bash
# 安装 uv（如果没有）
pip install uv

# 创建环境 & 安装依赖
uv venv
uv pip install -r requirements.txt

# 运行
.venv/Scripts/python src/main.py
```

### 打包为 .exe

```bash
uv venv
uv pip install pyinstaller Pillow requests
.venv/Scripts/python build.py
# 输出: dist/opencode-helper.exe
```

---

## 使用流程

```
① 欢迎页  →  ② CC配置迁移  →  ③ 环境检测  →  ④ 自动修复
→ ⑤ 安装方式  →  ⑥ 安装路径  →  ⑦ 下载安装
→ ⑧ 模型配置  →  ⑨ 验证测试  →  ⑩ 完成!
```

每一步都有清晰指引，阻塞项自动拦截并提示修复。

---

## 项目结构

```
opencode-helper/
├── src/
│   ├── main.py                  # 入口
│   ├── app.py                   # 主窗口 + 页面路由
│   ├── core/                    # 核心引擎
│   │   ├── detector.py          # 环境检测
│   │   ├── env_fixer.py         # 自动修复 (国内镜像)
│   │   ├── installer.py         # OpenCode 安装
│   │   ├── config_writer.py     # 配置生成
│   │   ├── proxy_manager.py     # 代理管理
│   │   ├── cc_migrator.py       # Claude Code 迁移
│   │   ├── validator.py         # API 验证
│   │   └── updater.py           # 更新检查
│   ├── ui/                      # GUI 层
│   │   ├── theme.py             # 像素主题
│   │   ├── widgets.py           # 自定义组件
│   │   ├── animations.py        # 动画效果
│   │   └── pages/               # 10 个步骤页面
│   └── i18n/                    # 中/英 双语
├── tests/                       # 66 个测试用例
├── docs/superpowers/            # PRD + 实施计划
├── build.py                     # 打包脚本
└── requirements.txt
```

---

## 预设模型模板

内置 `OpenLab GLM-5.2` 预设，用户可在 `~/.config/opencode-helper/presets.json` 中自定义：

```json
{
  "presets": [{
    "name": "OpenLab GLM-5.2",
    "provider": "openlab",
    "baseURL": "http://<IP:PORT>/v1",
    "modelId": "glm-5.2",
    "reasoning": true,
    "thinking": true
  }]
}
```

---

## Claude Code 与厂商配置迁移

完整的国内厂商端点、协议和迁移规则见 [国内模型与 OpenCode 配置指南](docs/china-provider-guide.md)。

迁移会读取 Claude Code 官方支持的 `~/.claude/settings.json`、项目
`.claude/settings.json` 和 `.claude/settings.local.json`，后者优先级最高；运行时环境变量优先于文件配置。`sonnet`、`opus` 等 Claude 别名不会被误当成模型 ID。

生成 OpenCode 配置时会保留原始 Base URL，并按接口协议选择适配器：国内厂商的 Anthropic Messages 兼容接口使用 `@ai-sdk/anthropic`，Chat Completions 兼容接口使用 `@ai-sdk/openai-compatible`。内置识别并支持 DeepSeek、阿里百炼 / Qwen、智谱 GLM、Moonshot / Kimi、MiniMax、小米 MiMo、LongCat、百度千帆和自建内网网关；不再提供海外模型厂商的专用预设或自动识别。

| 厂商 | 建议 Base URL | 接口类型 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | Chat Completions |
| 阿里百炼 / Qwen Coding Plan | `https://coding.dashscope.aliyuncs.com/apps/anthropic/v1` | Anthropic Messages |
| 智谱 GLM | `https://open.bigmodel.cn/api/anthropic/v1` | Anthropic Messages |
| Moonshot / Kimi | `https://api.moonshot.cn/v1` | Chat Completions |
| MiniMax（中国区） | `https://api.minimaxi.com/v1` | Chat Completions |
| 小米 MiMo | `https://api.xiaomimimo.com/v1` | Chat Completions |
| LongCat | `https://api.longcat.chat/openai/v1` | Chat Completions |

如厂商后台提供的地址不同，以后台实际地址为准；工具会保留你填写或从 Claude Code 检测到的地址，而不再强制替换。

项目内 `.claude/skills/<name>/SKILL.md` 已被 OpenCode 原生发现，不会重复复制；全局 Claude skills 会复制到 OpenCode 的全局 skills 目录。

---

## 开发

```bash
# 运行测试
uv run pytest tests/ -v

# 当前: 64 passed, 2 skipped (Tcl环境)
```

---

## 作者

**whyj**

---

## License

MIT

---

> 🤖 由 [Claude Code](https://claude.ai/code) 驱动开发
