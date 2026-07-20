# OpenCode Helper v2.0 发布说明

发布日期：2026-07-20  
产物：`opencode-helper.exe`

## 这是什么

OpenCode Helper 用于在 Windows 上完成 OpenCode CLI 的环境检测、安装或升级、模型配置、Claude Code 配置迁移与连通性验证。

## 本版能力

- 检测 Node.js、npm、OpenCode、代理与 Claude Code 配置。
- 缺失环境时可一键修复；安装或升级 OpenCode 使用国内 npm 镜像。
- 配置中国模型服务，以及 OpenAI 风格 `/v1`、本地 vLLM 等兼容接口。
- 支持 DeepSeek、智谱 GLM、通义、MiniMax、小米、LongCat 等服务的配置识别。
- 可从 Claude Code 迁移可复用配置与 Skills，并显示 Skill 名称和绝对路径。
- 使用真实 HTTP 请求验证端点；无效 token 会返回相应的鉴权状态，避免把“可达”误判为“可用”。
- 所有后台安装命令会在界面终端中显示，并可复制排查。
- 完成页会显示可复制的 PowerShell 启动命令，并可一键打开终端、清除 HTTP/HTTPS 代理后启动 OpenCode。

## 使用方式

1. 双击 `opencode-helper.exe`。
2. 按向导完成环境检测、安装、模型配置与验证。
3. 验证失败时，复制界面命令或错误信息进行排查。

## 打包内容

- `opencode-helper.exe`：Windows 单文件程序。
- `RELEASE.md`：本发布说明。完整开发文档不随发行包复制。

## 已知事项

- 当前发行文件未使用商业代码签名证书；Windows SmartScreen 可能提示“未知发布者”。
- 若 npm 的 postinstall 提示找不到 `node`，请使用程序的环境修复或一键安装按钮；它会将实际 Node 目录加入安装进程的 PATH。
- 本工具不会提供或存储第三方服务的 API Key；请使用自己的密钥，并按服务商要求保管。

## 反馈信息

提交问题时请附上：系统版本、Node/npm/OpenCode 版本、模型接口类型、界面终端的完整错误输出（请先隐藏 API Key）。
