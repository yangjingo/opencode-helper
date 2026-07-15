"""Environment detection — OS, Node.js, npm, OpenCode, proxy, disk, Claude Code config.

Optimized v2: full parallelism with ThreadPoolExecutor, short timeouts, and result caching.
"""
import json, os, sys, subprocess, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from functools import lru_cache

_SYSTEM = sys.platform
_S = 3  # default subprocess timeout (reduced from 5s for faster fail)

# ── Cache ──────────────────────────────────────────────────────────────────────

_cache: dict = {}

def clear_cache():
    """Clear all cached detection results (call before re-detect)."""
    _cache.clear()
    get_os_version.cache_clear()

# ── Helpers ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_os_version() -> str:
    try:
        result = subprocess.run(['cmd', '/c', 'ver'], capture_output=True, text=True, timeout=_S)
        return result.stdout.strip()
    except Exception:
        return 'Unknown'

def _try_cmd(cmd: list, timeout: int = _S) -> tuple[str, bool]:
    """Run a command through multiple shells. Never throws.

    Tries in order:
    1. Direct call — current process PATH
    2. cmd /c — system-wide PATH
    3. powershell -Command — loads user profile (nvm/fnm live here)
    4. powershell -NoProfile — clean PS (fastest, no profile overhead)
    """
    attempts = [
        cmd,
        ['cmd', '/c'] + cmd,
        ['powershell', '-Command'] + cmd,
        ['powershell', '-NoProfile', '-Command'] + cmd,
    ]
    for attempt in attempts:
        try:
            r = subprocess.run(attempt, capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip(), True
        except Exception:
            continue
    return '', False

def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return '***'
    return key[:6] + '••••••••' + key[-4:]

# ── Individual Detectors ──────────────────────────────────────────────────────

def detect_os() -> dict:
    ver = get_os_version()
    ok = _SYSTEM == 'win32'
    return {'os_name': 'Windows' if _SYSTEM == 'win32' else _SYSTEM, 'os_version': ver, 'os_ok': ok}

def detect_node() -> dict:
    out, ok = _try_cmd(['node', '--version'])
    node_path = shutil.which('node') or ''
    if ok and out:
        v = out.lstrip('v')
        major = int(v.split('.')[0]) if v else 0
        return {'node_installed': True, 'node_version': out, 'node_path': node_path, 'node_ok': major >= 18}
    return {'node_installed': False, 'node_version': '', 'node_path': node_path, 'node_ok': False}

def detect_npm() -> dict:
    out, ok = _try_cmd(['npm', '--version'])
    npm_path = shutil.which('npm') or ''
    if ok and out:
        major = int(out.split('.')[0]) if out else 0
        return {'npm_installed': True, 'npm_version': out, 'npm_path': npm_path, 'npm_ok': major >= 9}
    return {'npm_installed': False, 'npm_version': '', 'npm_path': npm_path, 'npm_ok': False}

def detect_opencode() -> dict:
    exe_path = shutil.which('opencode') or ''
    if exe_path:
        # Try to get version
        ver_out, ver_ok = _try_cmd(['opencode', '--version'], timeout=5)
        return {'opencode_installed': True, 'opencode_version': ver_out if ver_ok else '', 'opencode_path': exe_path}
    # Check npm global
    out, ok = _try_cmd(['npm', 'list', '-g', 'opencode-ai', '--depth=0'], timeout=3)
    if ok and 'opencode-ai@' in out:
        version = out.split('opencode-ai@')[1].split()[0]
        return {'opencode_installed': True, 'opencode_version': version, 'opencode_path': 'npm global'}
    return {'opencode_installed': False, 'opencode_version': '', 'opencode_path': ''}

def detect_disk() -> dict:
    try:
        usage = shutil.disk_usage(str(Path.home()))
        free_gb = usage.free / (1024 ** 3)
        return {'disk_free_gb': round(free_gb, 1), 'disk_ok': free_gb >= 0.5}
    except Exception:
        return {'disk_free_gb': 0, 'disk_ok': False}

def _detect_system_proxy_registry() -> dict:
    """Read Windows system proxy from registry (Internet Options -> LAN Settings).
    Returns registry-level proxy config or empty dict on failure.
    """
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')
        proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
        proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
        proxy_override, _ = winreg.QueryValueEx(key, 'ProxyOverride')
        winreg.CloseKey(key)

        enabled = bool(proxy_enable)
        return {
            'system_proxy_enabled': enabled,
            'system_proxy_server': proxy_server if enabled else '',
            'system_proxy_bypass': proxy_override if enabled else '',
            'source': 'registry',
        }
    except Exception:
        return {
            'system_proxy_enabled': False,
            'system_proxy_server': '',
            'system_proxy_bypass': '',
            'source': 'registry',
        }

def _detect_winhttp_proxy() -> dict:
    """Detect WinHTTP system proxy via netsh command."""
    try:
        r = subprocess.run(['netsh', 'winhttp', 'show', 'proxy'],
                          capture_output=True, text=True, timeout=5)
        output = r.stdout
        direct = '直接访问' in output or 'Direct access' in output.lower()
        proxy_line = ''
        bypass_line = ''
        for line in output.split('\n'):
            stripped = line.strip()
            if '代理服务器' in stripped or 'Proxy Server' in stripped:
                proxy_line = stripped.split(':', 1)[-1].strip() if ':' in stripped else ''
            if '绕过' in stripped or 'Bypass' in stripped:
                bypass_line = stripped.split(':', 1)[-1].strip() if ':' in stripped else ''
        return {
            'winhttp_direct': direct,
            'winhttp_proxy': '' if direct else proxy_line,
            'winhttp_bypass': bypass_line,
        }
    except Exception:
        return {'winhttp_direct': True, 'winhttp_proxy': '', 'winhttp_bypass': ''}

def _detect_env_proxy() -> dict:
    """Detect proxy from environment variables (HTTP_PROXY, HTTPS_PROXY, etc.)."""
    all_vars = {}
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
                'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy']:
        val = os.environ.get(var, '')
        if val:
            all_vars[var] = val
    return all_vars

def detect_proxy() -> dict:
    """Comprehensive proxy detection: env vars + Windows registry + WinHTTP."""
    # 1. Environment variables
    env_vars = _detect_env_proxy()
    http = env_vars.get('HTTP_PROXY', '') or env_vars.get('http_proxy', '')
    https = env_vars.get('HTTPS_PROXY', '') or env_vars.get('https_proxy', '')
    no_proxy = env_vars.get('NO_PROXY', '') or env_vars.get('no_proxy', '')
    all_proxy = env_vars.get('ALL_PROXY', '') or env_vars.get('all_proxy', '')

    # 2. Windows system proxy (registry)
    sys_proxy = _detect_system_proxy_registry()

    # 3. WinHTTP proxy
    winhttp = _detect_winhttp_proxy()

    # Aggregate: any proxy detected from any source?
    detected = bool(http or https or all_proxy
                    or sys_proxy.get('system_proxy_enabled')
                    or (not winhttp.get('winhttp_direct', True)))

    return {
        'proxy_detected': detected,
        # Env
        'proxy_http': http,
        'proxy_https': https,
        'no_proxy': no_proxy,
        'all_proxy': all_proxy,
        'env_vars': env_vars,
        # System
        'system_proxy_enabled': sys_proxy.get('system_proxy_enabled', False),
        'system_proxy_server': sys_proxy.get('system_proxy_server', ''),
        'system_proxy_bypass': sys_proxy.get('system_proxy_bypass', ''),
        # WinHTTP
        'winhttp_direct': winhttp.get('winhttp_direct', True),
        'winhttp_proxy': winhttp.get('winhttp_proxy', ''),
        'winhttp_bypass': winhttp.get('winhttp_bypass', ''),
    }

def detect_claude_env_vars() -> dict:
    relevant = [
        'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_AUTH_TOKEN',
        'ANTHROPIC_MODEL', 'ANTHROPIC_SMALL_FAST_MODEL',
        'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL',
        'ANTHROPIC_DEFAULT_HAIKU_MODEL',
        'CLAUDE_CODE_API_KEY', 'CLAUDE_CODE_SUBAGENT_MODEL',
        'CLAUDE_CODE_EFFORT_LEVEL', 'CLAUDE_CODE_ATTRIBUTION_HEADER',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', 'CLAUDE_CODE_AUTO_COMPACT_WINDOW',
        'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL',
    ]
    env_vars = {}
    for var in relevant:
        val = os.environ.get(var, '')
        if val:
            env_vars[var] = val
    return {'claude_env_vars': env_vars}

def detect_claude_config() -> dict:
    home = Path.home()
    settings_path = home / '.claude' / 'settings.json'
    skills_path = home / '.claude' / 'skills'
    project_claude = Path.cwd() / '.claude'

    # Read user-level settings
    settings_content = {}
    settings_raw = ''
    settings_readable = False
    if settings_path.exists():
        try:
            settings_raw = settings_path.read_text(encoding='utf-8')
            settings_content = json.loads(settings_raw)
            settings_readable = True
        except json.JSONDecodeError:
            settings_readable = False
        except Exception:
            settings_readable = False

    # Read project-level settings
    project_settings_path = project_claude / 'settings.json'
    project_content = {}
    project_raw = ''
    project_readable = False
    if project_settings_path.exists():
        try:
            project_raw = project_settings_path.read_text(encoding='utf-8')
            project_content = json.loads(project_raw)
            project_readable = True
        except json.JSONDecodeError:
            project_readable = False
        except Exception:
            pass

    # Scan project .claude for more config files
    project_files = []
    if project_claude.exists():
        for f in project_claude.iterdir():
            if f.is_file() and f.suffix in ('.json', '.md', '.yml', '.yaml'):
                project_files.append({'name': f.name, 'path': str(f)})

    return {
        'claude_config_found': settings_path.exists() or skills_path.exists() or project_claude.exists(),
        'claude_settings_path': str(settings_path) if settings_path.exists() else '',
        'claude_skills_path': str(skills_path) if skills_path.exists() else '',
        'project_claude_path': str(project_claude) if project_claude.exists() else '',
        'claude_settings': settings_content,
        'claude_settings_raw': settings_raw,
        'claude_settings_readable': settings_readable,
        'project_settings': project_content,
        'project_settings_raw': project_raw,
        'project_settings_readable': project_readable,
        'project_files': project_files,
    }

# ── Full Detection (fully parallel) ───────────────────────────────────────────

_ALL_CHECKS = {
    'os':             detect_os,
    'disk':           detect_disk,
    'node':           detect_node,
    'npm':            detect_npm,
    'opencode':       detect_opencode,
    'proxy':          detect_proxy,
    'claude_env':     detect_claude_env_vars,
    'claude_config':  detect_claude_config,
}

def detect_all(progress_callback=None) -> dict:
    """Run ALL detections in parallel via ThreadPoolExecutor.

    Args:
        progress_callback: Optional callable(step_name: str) called as each check completes.
    """
    global _cache
    if _cache:
        return dict(_cache)

    report = {}

    def _run(name, fn):
        try:
            result = fn()
        except Exception:
            result = {}
        if progress_callback:
            try:
                progress_callback(name)
            except Exception:
                pass
        return name, result

    with ThreadPoolExecutor(max_workers=min(8, len(_ALL_CHECKS))) as pool:
        futures = {pool.submit(_run, name, fn): name for name, fn in _ALL_CHECKS.items()}
        for future in as_completed(futures):
            try:
                name, result = future.result()
                report.update(result)
            except Exception:
                pass

    _cache = dict(report)
    return report
