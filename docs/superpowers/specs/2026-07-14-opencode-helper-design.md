# OpenCode Helper — 一键安装 & 配置工具 PRD

> **状态**: v2.0 修订  
> **日期**: 2026-07-14  
> **版本**: v2.0  
> **目标用户**: 内网环境下需要快速部署 OpenCode 并配置内部模型的开发者

---

## 1. 产品概述

### 1.1 核心洞察

**OpenCode 桌面端 (.exe) 和 CLI 共享同一份配置文件** `~/.config/opencode/opencode.jsonc`。桌面 exe 启动时自动读取该目录配置。

因此我们的策略是：**先通过 CLI (npm) 完成环境部署和配置，最后引导用户下载桌面 exe**。

```
用户 ──[opencode-helper]──→ ① npm install opencode-ai (CLI 就绪)
                        → ② 写入 ~/.config/opencode/opencode.jsonc (桌面共享)
                        → ③ shell profile 代理包装器
                        → ④ 弹出桌面 exe 下载链接
                        
         CLI `opencode` ✓    桌面 exe 下载安装后 ✓ (配置自动生效)
```

### 1.2 一句话描述

像素风格 Windows GUI 工具，一键完成 OpenCode CLI 安装 + 模型配置 + 代理处理 + Claude Code 迁移，最后引导下载桌面 exe。

### 1.3 解决的痛点

| 痛点 | 方案 |
|------|------|
| 配置复杂 | GUI 表单 + 预设模板 |
| 代理干扰 | 自动检测 + shell profile 包装函数 |
| 环境缺失 | 后台线程检测 + 授权后自动修复（国内镜像） |
| CC 迁移 | 自动扫描，显示实际配置值，勾选迁移 |
| 桌面端配置重复 | CLI 配置写完桌面 exe 直接读，无需二次配置 |

---

## 2. 用户流程

### 2.1 简化页面流程（8 步）

```
[① 欢迎] → [② Claude 配置迁移] → [③ 环境检测] → [④ 环境修复(按需)]
     → [⑤ CLI 安装] → [⑥ 模型配置] → [⑦ 验证测试] → [⑧ 完成 + 桌面exe引导]
```

> 相比 v1.0 去掉：安装方式选择页、安装路径选择页、exe 下载安装逻辑。因为桌面 exe 由用户自行下载安装，配置自动共享。

### 2.2 各页面详情

#### ① 欢迎页
- 像素风格 ASCII art Logo
- 一句话说明："一键配置 OpenCode，CLI + 桌面端共享配置"
- `[ 开始安装 → ]` 按钮
- 底部：版本号 + `by whyj`

#### ② Claude 配置迁移页
- **触发条件**: 检测到 `~/.claude/` 存在
- **未检测到则跳过**
- 卡片式展示每项可迁移配置，显示**实际内容预览**：

```
🔑 API Key           sk-ant••••••••XXXX     📁 ~/.claude/settings.json
🤖 Default Model     claude-sonnet-5        📁 ~/.claude/settings.json
📋 Instructions      # My Instructions...   📁 ~/.claude/CLAUDE.md
🛠 Skill             my-tool.md             📁 ~/.claude/skills/
```

- 每项可勾选/取消
- `[ 上一步 ]` `[ 跳过迁移 ]` `[ 一键迁移选中的 → ]`

#### ③ 环境检测页
- 后台异步检测，UI 不卡死
- 显示 `⏳ 检测中...` 加载动画
- 三大区块：

```
💻 System
  ✓ OS:    Windows 10.0.22631
  ✓ Disk:  50.0 GB free

📦 Runtime  
  ✓ Node.js:  v20.11.0
  ✓ npm:      v10.2.4
  ✓ OpenCode: 未安装

🤖 Claude / LLM Environment Variables
  ANTHROPIC_API_KEY  = sk-ant••••••••XXXX
  ANTHROPIC_BASE_URL = http://10.0.0.1:8080/v1
  ANTHROPIC_MODEL    = claude-sonnet-5

🌐 Proxy & Environment Variables
  HTTP_PROXY  = http://proxy.company.com:8080
  NO_PROXY    = localhost,127.0.0.1
```

- 展示环境变量的**实际值**（API Key 脱敏）
- 阻塞项 ✗ 时 next 按钮变灰
- `[ 上一步 ]` `[ 重新检测 ]` `[ 下一步 → ]`

#### ④ 环境修复页（按需出现）
- 用户授权后自动修复
- 国内镜像加速：npm registry → `npmmirror.com`
- `[ 上一步 ]` `[ 跳过 ]` `[ 下一步 → ]`

#### ⑤ CLI 安装页
- npm 全局安装 `opencode-ai`
- 像素进度条 + 终端风格日志
- 后台线程执行，UI 不卡死
- 完成后自动跳下一步

#### ⑥ 模型配置页
- 预设模板下拉（OpenLab GLM-5.2 等）
- Provider / API Key / Base URL / Model ID 表单
- API Key 支持 `👁` 切换明文/密文
- reasoning / thinking 开关
- `[ 上一步 ]` `[ 测试连接 → ]` `[ 下一步 → ]`

#### ⑦ 验证测试页
- 自动测试 3 项：API 端点 / 模型推理 / 配置文件
- 终端风格输出
- `[ 上一步 ]` `[ 下一步 → ]`

#### ⑧ 完成页
- 像素撒花动画
- 摘要信息
- **核心：桌面 exe 下载引导**

```
╔══════════════════════════════════════════╗
║  🎉 配置完成！                           ║
║  ─────────────────────────────────────  ║
║  OpenCode CLI   ✓ 已安装                ║
║  模型            openlab/glm-5.2         ║
║  代理处理        已自动配置              ║
║  配置迁移         3 项已迁移             ║
║  ─────────────────────────────────────  ║
║                                         ║
║  📥 下载桌面版 OpenCode                  ║
║  ┌──────────────────────────────────┐  ║
║  │ 桌面 exe 会自动读取 CLI 配置      │  ║
║  │ 无需重复配置，安装即用            │  ║
║  └──────────────────────────────────┘  ║
║  🔗 https://opencode.ai/zht/download   ║
║     /stable/windows-x64-nsis            ║
║                                         ║
║  [ 🚀 启动 OpenCode CLI ]               ║
║  [ 📥 打开下载页面 ]                    ║
║  [ 📂 打开配置目录 ]                    ║
║  [ 🏠 关闭 ]                            ║
╚══════════════════════════════════════════╝
```

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────┐
│               opencode-helper.exe                 │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │            GUI 层 (Tkinter 像素风)            │ │
│  │  ①欢迎 → ②迁移 → ③环境 → ④修复 → ⑤安装    │ │
│  │       → ⑥配置 → ⑦验证 → ⑧完成              │ │
│  └─────────────────────┬───────────────────────┘ │
│                        │                         │
│  ┌─────────────────────▼───────────────────────┐ │
│  │              Core 核心引擎                    │ │
│  │  detector │ env_fixer │ installer(npm only)  │ │
│  │  config_writer │ proxy_manager │ cc_migrator│ │
│  │  validator │ updater                         │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 3.2 组件职责

| 组件 | 职责 |
|------|------|
| `detector.py` | 环境检测（OS/Node/npm/OC/磁盘/代理/Claude env vars），后台并行 |
| `env_fixer.py` | 自动修复（npm registry 切换国内镜像） |
| `installer.py` | npm 全局安装 opencode-ai |
| `config_writer.py` | 生成 `opencode.jsonc` + 预设模板管理 |
| `proxy_manager.py` | 代理检测 + 写入 shell profile 包装函数 |
| `cc_migrator.py` | Claude Code 配置扫描 + 迁移 |
| `validator.py` | API 端点 / 模型推理 / 配置文件 验证 |
| `updater.py` | opencode-helper 自更新检查 |

---

## 4. 代理处理方案（简化版）

> 只保留 CLI 模式。桌面 exe 通过已设置的系统环境变量 `NO_PROXY` 自动处理。

### Shell Profile 包装器

**Git Bash** → `~/.bashrc`：
```bash
opencode() {
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
  command opencode "$@"
}
```

**PowerShell** → `$PROFILE`：
```powershell
function opencode {
    Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
    & opencode @args
}
```

**用户级 NO_PROXY**：
```powershell
[Environment]::SetEnvironmentVariable("NO_PROXY", "localhost,127.0.0.1,::1", "User")
```

---

## 5. 像素风格设计系统

同 v1.0（配色 #0a0e27 / #00ff88 / #ff6b6b / #ffd93d / Consolas 等宽字体）

---

## 6. 性能优化

| 优化点 | 方案 |
|--------|------|
| 环境检测 | 后台 `ThreadPoolExecutor` 并行 subprocess，超时 2s |
| UI 响应 | 检测/安装均在线程中执行，`after()` 轮询结果 |
| 加载指示 | `⏳ 检测中...` 带动画点 |

---

## 7. 错误处理矩阵

| 场景 | 级别 | 处理 |
|------|------|------|
| Node.js 未安装 | ✗ 阻塞 | 用户授权后自动下载安装 |
| npm registry 不可达 | ✗ 阻塞 | 自动切换 npmmirror |
| 磁盘不足 | ✗ 阻塞 | 提示释放空间 |
| HTTP 代理已设置 | ⚠ 警告 | 自动写 shell profile 包装器 |
| API Key 无效 | ✗ 阻塞 | 返回修改 |
| BaseURL 不通 | ⚠ 警告 | 允许跳过 |

---

## 8. 文件结构（简化）

```
opencode-helper/
├── main.py                    # 入口（根目录，PyInstaller 友好）
├── src/
│   ├── app.py                 # 主窗口 + WizardState + 页面路由
│   ├── core/
│   │   ├── detector.py        # 环境检测（并行优化）
│   │   ├── env_fixer.py       # 环境修复
│   │   ├── installer.py       # npm 安装（仅 CLI）
│   │   ├── config_writer.py   # opencode.jsonc 生成
│   │   ├── proxy_manager.py   # shell profile 包装器
│   │   ├── cc_migrator.py     # Claude Code 迁移
│   │   ├── validator.py       # API 验证
│   │   └── updater.py         # 自更新
│   ├── ui/
│   │   ├── theme.py / widgets.py / animations.py
│   │   └── pages/
│   │       ├── welcome.py
│   │       ├── migration.py
│   │       ├── environment.py
│   │       ├── env_fix.py
│   │       ├── install.py          # CLI install only
│   │       ├── config_model.py
│   │       ├── verify.py
│   │       └── finish.py           # 含桌面 exe 引导
│   └── i18n/
│       ├── zh_CN.json / en_US.json
├── tests/                     # 66 个测试
├── requirements.txt
└── build.py
```

---

## 9. 桌面 exe 引导策略

完成页展示：
1. **说明**："桌面 exe 和 CLI 共享配置，下载安装即用，无需重新配置"
2. **下载链接**：`https://opencode.ai/zht/download/stable/windows-x64-nsis`
3. **按钮**：`[ 📥 打开下载页面 ]` 调用 `webbrowser.open(url)` 
4. **按钮**：`[ 📂 打开配置目录 ]` 打开 `~/.config/opencode/`

用户下载安装桌面 exe 后，它会自动读取 `~/.config/opencode/opencode.jsonc`，模型和 provider 配置即刻生效。

---

## 10. 里程碑

### Phase 1 — 核心链路 ✓
- [x] 项目骨架 + i18n
- [x] 像素主题 + 组件库
- [x] 环境检测（并行优化）
- [x] npm CLI 安装
- [x] 模型配置 + 写入
- [x] 代理处理（shell profile）

### Phase 2 — 增强功能 ✓
- [x] Claude Code 迁移（显示实际配置值）
- [x] 环境自动修复
- [x] API 验证测试
- [x] 预设模板

### Phase 3 — 体验打磨（当前）
- [x] 性能优化（后台线程检测）
- [x] 回退按钮全覆盖
- [ ] 环境检测显示 Cluade/LLM 环境变量实际值
- [ ] 完成页桌面 exe 下载引导

### Phase 4 — 发布
- [x] PyInstaller 打包
- [ ] 内部分发测试

---

> **v2.0 核心变更**: 去掉安装方式选择、exe 下载安装逻辑；CLI+桌面共享配置，完成页引导下载桌面 exe。
