"""Proxy detection, launcher script generation, and shell profile management."""
import os, re, subprocess
from pathlib import Path

BAT_TEMPLATE = '''@echo off
REM OpenCode Launcher — auto-clears upstream proxy for internal model access
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=localhost,127.0.0.1,::1{extra_no_proxy}
"{exe_path}" %*
'''

PS1_TEMPLATE = '''# OpenCode Launcher — auto-clears upstream proxy
Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
$env:NO_PROXY = "localhost,127.0.0.1,::1{extra_no_proxy}"
& "{exe_path}" @args
'''

BASH_WRAPPER = '''
# OpenCode — auto-clears upstream proxy
opencode() {
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
  command opencode "$@"
}
'''

PS_WRAPPER = '''
# OpenCode — auto-clears upstream proxy
function opencode {
    Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy, Env:ALL_PROXY, Env:all_proxy -ErrorAction SilentlyContinue
    $opencodeCommand = Get-Command opencode -CommandType Application -ErrorAction Stop
    & $opencodeCommand.Source @args
}
'''

# Human-facing commands rendered by the Direct Connection page. Keep the
# command text here so UI, documentation, and tests cannot drift apart.
DIRECT_POWERSHELL_PROFILE_COMMAND = '''$profileDirectory = Split-Path -Parent $PROFILE
New-Item -ItemType Directory -Force -Path $profileDirectory | Out-Null
@'
# OpenCode: always connect directly (bypass HTTP/HTTPS/SOCKS proxies)
function opencode {
    Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy, Env:ALL_PROXY, Env:all_proxy -ErrorAction SilentlyContinue
    $opencodeCommand = Get-Command opencode -CommandType Application -ErrorAction Stop
    & $opencodeCommand.Source @args
}
'@ | Add-Content -Path $PROFILE
. $PROFILE'''

DIRECT_POWERSHELL_COMMAND = (
    'Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY -ErrorAction SilentlyContinue; opencode'
)


def direct_connection_commands() -> dict[str, str]:
    """Return copy-ready PowerShell commands for permanent and one-shot use."""
    return {
        'powershell_profile': DIRECT_POWERSHELL_PROFILE_COMMAND,
        'powershell_once': DIRECT_POWERSHELL_COMMAND,
    }

def _wininet_system_proxy() -> dict:
    """Read the Windows WinINET (system-wide) proxy setting.

    opencode-ai honors this proxy in addition to environment variables. The
    helper app deliberately never *modifies* system proxy settings, but it must
    still detect them so users learn their endpoint may be intercepted. Returns
    an empty dict off-Windows or when the value cannot be read.
    """
    if os.name != 'nt':
        return {}
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
        try:
            enabled, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            try:
                server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            except OSError:
                server = ''
        finally:
            winreg.CloseKey(key)
    except OSError:
        return {}
    return {'enabled': bool(enabled), 'server': server}


def detect_all_proxies() -> dict:
    http = os.environ.get('HTTP_PROXY', '') or os.environ.get('http_proxy', '')
    https = os.environ.get('HTTPS_PROXY', '') or os.environ.get('https_proxy', '')
    wininet = _wininet_system_proxy()
    has_proxy = bool(http or https or wininet.get('enabled'))
    return {'has_proxy': has_proxy, 'http': http, 'https': https, 'wininet': wininet}

def is_internal_address(address: str) -> bool:
    host = address
    if '://' in host:
        host = host.split('://')[1]
    host = host.split('/')[0].split(':')[0]
    for pat in [r'^10\.\d+\.\d+\.\d+$', r'^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$', r'^192\.168\.\d+\.\d+$', r'^127\.\d+\.\d+\.\d+$']:
        if re.match(pat, host):
            return True
    return False

def generate_launcher_scripts(install_dir: str, install_method: str, extra_no_proxy: str = '') -> list[str]:
    paths = []
    if install_method == 'exe':
        exe_path = os.path.join(install_dir, 'opencode.exe')
        extra = ',' + extra_no_proxy if extra_no_proxy else ''
        bat_path = os.path.join(install_dir, 'opencode.bat')
        with open(bat_path, 'w') as f:
            f.write(BAT_TEMPLATE.format(exe_path=exe_path, extra_no_proxy=extra))
        paths.append(bat_path)
        ps1_path = os.path.join(install_dir, 'opencode.ps1')
        with open(ps1_path, 'w') as f:
            f.write(PS1_TEMPLATE.format(exe_path=exe_path, extra_no_proxy=extra))
        paths.append(ps1_path)
    return paths

def write_shell_profile_wrapper(method: str) -> list[str]:
    modified = []
    marker = '# OpenCode — auto-clears upstream proxy'
    # The desktop helper targets Windows. Do not unexpectedly edit .bashrc on
    # Windows; use its native PowerShell profile. Keep Bash behavior only for
    # development on Unix-like systems.
    if os.name != 'nt':
        bashrc = Path.home() / '.bashrc'
        content = ''
        if bashrc.exists():
            content = bashrc.read_text()
        if marker not in content:
            if content and not content.endswith('\n'):
                content += '\n'
            content += BASH_WRAPPER
            bashrc.write_text(content)
            modified.append(str(bashrc))
    try:
        result = subprocess.run(['powershell', '-NoProfile', '-Command', 'echo $PROFILE'],
                                capture_output=True, text=True, timeout=5)
        ps_profile = Path(result.stdout.strip())
        if not ps_profile.parent.exists():
            ps_profile.parent.mkdir(parents=True, exist_ok=True)
        content = ''
        if ps_profile.exists():
            content = ps_profile.read_text()
        if marker not in content:
            if content and not content.endswith('\n'):
                content += '\n'
            content += PS_WRAPPER
            ps_profile.write_text(content)
            modified.append(str(ps_profile))
    except Exception:
        pass
    return modified

def set_user_no_proxy(domains: list[str]) -> bool:
    try:
        no_proxy = ','.join(domains)
        subprocess.run(['setx', 'NO_PROXY', no_proxy], capture_output=True, timeout=5)
        os.environ['NO_PROXY'] = no_proxy
        return True
    except Exception:
        return False
