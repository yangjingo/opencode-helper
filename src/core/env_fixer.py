"""Auto-fix environment issues — domestic mirrors + PowerShell repair."""
import subprocess
from core.detector import detect_node, detect_npm, hidden_process_kwargs

NPM_MIRROR = 'https://registry.npmmirror.com'
NODE_VERSION = 'v22.18.0'
NODE_MIRROR_URL = f'https://npmmirror.com/mirrors/node/{NODE_VERSION}/node-{NODE_VERSION}-x64.msi'


def _log_output(output: str, log) -> None:
    for line in (output or '').strip().splitlines():
        if line.strip():
            log(f'  {line.strip()}')


def fix_npm_registry(progress_callback=None) -> bool:
    def log(msg):
        if progress_callback: progress_callback(msg)

    npm_path = detect_npm().get('npm_path', '')
    commands = []
    if npm_path:
        commands.append([npm_path, 'config', 'set', 'registry', NPM_MIRROR])
    commands.extend([
        ['npm', 'config', 'set', 'registry', NPM_MIRROR],
        ['cmd', '/c', 'npm config set registry ' + NPM_MIRROR],
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
         'npm config set registry ' + NPM_MIRROR],
    ])
    for cmd in commands:
        log(f'$ {" ".join(cmd)}')
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, **hidden_process_kwargs())
            _log_output(r.stdout, log)
            _log_output(r.stderr, lambda line: log(f'  [stderr] {line.strip()}'))
            if r.returncode == 0:
                log(f'[npm] ✓ Registry set to {NPM_MIRROR}')
                return True
            else:
                log(f'[npm] ✗ exit code {r.returncode}')
        except Exception as e:
            log(f'[npm] ✗ {e}')

    log(f'[npm] All attempts failed. Run manually: npm config set registry {NPM_MIRROR}')
    return False


def fix_node_install(progress_callback=None) -> bool:
    def log(msg):
        if progress_callback: progress_callback(msg)

    # Re-use the same robust discovery as the environment page.  This avoids
    # installing a second Node when fnm/nvm has one outside Explorer's PATH.
    node_path = detect_node().get('node_path', '')
    if node_path:
        log('$ node --version')
        log(f'  {node_path}')
        log('[node] ✓ Node.js already installed — no fix needed')
        return True

    # PowerShell downloads the MSI from npmmirror and invokes msiexec with an
    # elevation prompt.  No GitHub/npmjs/winget download path is used.
    script = f'''$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$url = '{NODE_MIRROR_URL}'
$installer = Join-Path $env:TEMP 'node-{NODE_VERSION}-x64.msi'
Write-Output "[node] Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
Write-Output "[node] Installing Node.js LTS (Windows may request administrator approval)..."
$proc = Start-Process -FilePath 'msiexec.exe' -Verb RunAs -ArgumentList @('/i', $installer, '/qn', '/norestart') -Wait -PassThru
if ($proc.ExitCode -notin 0, 3010) {{ throw "msiexec failed with exit code $($proc.ExitCode)" }}
Write-Output "[node] Node.js LTS installed successfully. Restart this app or click Re-check."
'''
    ps_cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script]
    log('$ PowerShell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest {NODE_MIRROR_URL}; Start-Process msiexec.exe /i node-{NODE_VERSION}-x64.msi"')
    try:
        r = subprocess.run(ps_cmd, capture_output=True, text=True, errors='replace', timeout=900,
                           **hidden_process_kwargs())
        _log_output(r.stdout, log)
        _log_output(r.stderr, lambda line: log(f'  [stderr] {line.strip()}'))
        if r.returncode == 0:
            log('[node] ✓ PowerShell repair completed')
            return True
        log(f'[node] ✗ PowerShell exited with code {r.returncode}')
    except Exception as e:
        log(f'[node] ✗ {e}')
    return False


def auto_fix_environment(env_report: dict, progress_callback=None) -> dict:
    results = {}
    if not env_report.get('node_ok', True):
        results['nodejs'] = fix_node_install(progress_callback)
    # Set the registry after Node repair so a newly installed npm is configured
    # immediately.  The repair always prefers the domestic npmmirror registry.
    if not env_report.get('npm_ok', True) or results.get('nodejs'):
        results['npm_registry'] = fix_npm_registry(progress_callback)
    return results
