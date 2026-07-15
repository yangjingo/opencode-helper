# 🎮 OpenCode Helper

> 像素风格 · 一键安装 · 内网模型配置 · Claude Code 迁移

一个 **Windows GUI 桌面工具**，让你 5 分钟内完成 OpenCode 的安装、内网模型配置、代理绕行和 Claude Code 配置迁移。零门槛，零手动编辑。

![Platform](https://img.shields.io/badge/platform-Windows%2010%2B-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Size](https://img.shields.io/badge/size-8.9MB-lightgrey)

---

## 截图

```
╔══════════════════════════════════════════════════╗
║  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ║
║  ▓  ╔══════════════════════════════════════╗  ▓  ║
║  ▓  ║    🎮 OpenCode Helper v1.0          ║  ▓  ║
║  ▓  ║    ─────────────────────────────    ║  ▓  ║
║  ▓  ║  一键安装 OpenCode                  ║  ▓  ║
║  ▓  ║  配置内网模型，5 分钟搞定           ║  ▓  ║
║  ▓  ║                                    ║  ▓  ║
║  ▓  ║     [ 开始安装 → ]                 ║  ▓  ║
║  ▓  ╚══════════════════════════════════════╝  ▓  ║
║  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ▓  ║
╚══════════════════════════════════════════════════╝
```

---

## 功能

- 🔍 **环境检测** — 自动扫描 OS、Node.js、npm、磁盘、代理、Claude Code 配置
- 🔧 **自动修复** — Node.js 缺失？npm 源慢？一键自动修复（国内镜像加速）
- 📦 **双模式安装** — npm 全局安装 / .exe 独立安装包
- ⚙ **模型配置** — 表单填写 + 预设模板，零出错
- 🛡 **代理处理** — 自动检测上游代理，生成 launcher 脚本，内网直连
- 🔄 **Claude Code 迁移** — API Key、Instructions、Skills 一键迁移
- ✅ **验证测试** — 安装后自动测试 API 端点和模型推理
- 🎨 **像素风格** — 霓虹绿黑配色，像素进度条，庆祝撒花动画
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
