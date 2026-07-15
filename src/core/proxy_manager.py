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
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
  command opencode "$@"
}
'''

PS_WRAPPER = '''
# OpenCode — auto-clears upstream proxy
function opencode {
    Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy -ErrorAction SilentlyContinue
    & opencode @args
}
'''

def detect_all_proxies() -> dict:
    http = os.environ.get('HTTP_PROXY', '') or os.environ.get('http_proxy', '')
    https = os.environ.get('HTTPS_PROXY', '') or os.environ.get('https_proxy', '')
    return {'has_proxy': bool(http or https), 'http': http, 'https': https}

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
