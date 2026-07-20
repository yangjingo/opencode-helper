"""OpenCode install/upgrade through PowerShell with a domestic npm mirror."""
import subprocess
from core.detector import detect_npm, hidden_process_kwargs

OPENCODE_NPM_PACKAGE = 'opencode-ai'
NPM_MIRROR = 'https://registry.npmmirror.com'

def _powershell_quote(value: str) -> str:
    return value.replace("'", "''")


def diagnose_install_failure(output: str) -> str:
    """Return an actionable, user-facing diagnosis for common npm failures."""
    text = (output or '').lower()
    if "'node' is not recognized" in text or 'node is not recognized' in text:
        return '诊断：npm 的 postinstall 找不到 node。请点击“重试”；工具会把检测到的 Node 目录临时加入 PATH。'
    if 'verify_package_failed' in text:
        return '诊断：npm 返回成功但全局包清单中没有 opencode-ai。请点击“重试”；人工兜底：npm list -g opencode-ai --depth=0。'
    if 'verify_cli_missing' in text:
        return '诊断：已找到 npm 包，但未找到 opencode.cmd。请重开终端后执行 npm prefix -g，确认该目录是否在 PATH。'
    if 'verify_cli_failed' in text:
        return '诊断：已安装 OpenCode，但 CLI 无法输出版本。请复制终端命令手动执行，并将完整输出反馈。'
    if 'eacces' in text or 'eperm' in text or 'access is denied' in text:
        return '诊断：全局安装目录没有写入权限。请以管理员身份运行本工具后重试。'
    if 'econnreset' in text or 'etimedout' in text or 'enotfound' in text:
        return '诊断：网络或镜像连接失败。请检查网络后点击“重试”。'
    return '安装失败。请点击“重试”；如仍失败，请复制终端日志反馈。'


def install_or_upgrade_npm(progress_callback=None, upgrade: bool = False) -> bool:
    """Install or upgrade OpenCode via PowerShell, using npmmirror throughout."""

    def log(msg):
        if progress_callback:
            progress_callback(msg)

    npm_path = detect_npm().get('npm_path', '')
    npm_command = _powershell_quote(npm_path) if npm_path else 'npm'
    operation = 'upgrade' if upgrade else 'install'
    script = f'''$ErrorActionPreference = 'Stop'
$npm = '{npm_command}'
if (Test-Path $npm) {{
    # npm postinstall launches `cmd /c node ...`; Explorer-launched GUIs do not
    # inherit fnm's shell PATH, so expose the paired Node executable explicitly.
    $nodeDir = Split-Path -Parent $npm
    $env:Path = "$nodeDir;$env:Path"
    Write-Output "[npm] Added Node runtime to this install session: $nodeDir"
}}
Write-Output '[npm] Configuring domestic registry: {NPM_MIRROR}'
& $npm config set registry '{NPM_MIRROR}'
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
Write-Output '[npm] {operation}: {OPENCODE_NPM_PACKAGE}@latest'
& $npm install -g '{OPENCODE_NPM_PACKAGE}@latest' --verbose --registry '{NPM_MIRROR}'
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}

# Verification is deliberately in this same PowerShell session: fnm's Node
# directory remains on PATH while npm postinstall and opencode.cmd are tested.
Write-Output '[verify] Step 1/3: checking global package'
& $npm list -g '{OPENCODE_NPM_PACKAGE}' --depth=0
if ($LASTEXITCODE -ne 0) {{ Write-Output 'VERIFY_PACKAGE_FAILED'; exit 41 }}

Write-Output '[verify] Step 2/3: locating OpenCode CLI'
$prefixLines = @(& $npm prefix -g)
if ($LASTEXITCODE -ne 0 -or -not $prefixLines) {{ Write-Output 'VERIFY_CLI_MISSING'; exit 42 }}
$prefix = $prefixLines[-1].Trim()
$opencode = Join-Path $prefix 'opencode.cmd'
if (-not (Test-Path $opencode)) {{ Write-Output "VERIFY_CLI_MISSING: $opencode"; exit 42 }}

Write-Output "[verify] Step 3/3: $opencode --version"
& $opencode --version
if ($LASTEXITCODE -ne 0) {{ Write-Output 'VERIFY_CLI_FAILED'; exit 43 }}
Write-Output '[verify] OpenCode installation chain passed'
exit 0
'''
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script]
    log('[PowerShell] $ PowerShell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"npm config set registry {NPM_MIRROR}; npm install -g {OPENCODE_NPM_PACKAGE}@latest --verbose --registry {NPM_MIRROR}; npm list -g {OPENCODE_NPM_PACKAGE} --depth=0; opencode --version"')
    log(f'[npm] mirror: {NPM_MIRROR}')
    if npm_path:
        log(f'[npm] executable: {npm_path}')

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, **hidden_process_kwargs(),
        )
        output_lines = []
        for line in proc.stdout:
            stripped = line.rstrip()
            if stripped:
                output_lines.append(stripped)
                log(stripped)
        proc.wait()
        if proc.returncode == 0:
            log(f'[npm] ✓ OpenCode {"upgrade" if upgrade else "installation"} complete and CLI verified')
            return True
        else:
            log(f'[npm] ✗ Installation failed (exit code {proc.returncode})')
            log(f'[npm] {diagnose_install_failure("\\n".join(output_lines))}')
            return False
    except FileNotFoundError:
        log('[PowerShell] ✗ PowerShell not found — cannot run installation')
        return False
    except Exception as e:
        log(f'[npm] ✗ Unexpected error: {e}')
        return False


def install_npm(progress_callback=None) -> bool:
    """Backward-compatible OpenCode installation entry point."""
    return install_or_upgrade_npm(progress_callback, upgrade=False)


def upgrade_npm(progress_callback=None) -> bool:
    """Upgrade OpenCode to the latest version through the domestic mirror."""
    return install_or_upgrade_npm(progress_callback, upgrade=True)

def check_npm_available() -> bool:
    """Quick check using the same fnm/nvm-aware discovery as the UI."""
    return bool(detect_npm().get('npm_ok'))
