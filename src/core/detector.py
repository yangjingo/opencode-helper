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


def hidden_process_kwargs() -> dict:
    """Prevent console windows from flashing while the GUI probes commands."""
    if os.name == 'nt':
        return {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    return {}

def clear_cache():
    """Clear all cached detection results (call before re-detect)."""
    _cache.clear()
    get_os_version.cache_clear()

# ── Helpers ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_os_version() -> str:
    try:
        result = subprocess.run(['cmd', '/c', 'ver'], capture_output=True, text=True,
                                errors='replace', timeout=_S, **hidden_process_kwargs())
        return result.stdout.strip()
    except Exception:
        return 'Unknown'

def _try_cmd(cmd: list, timeout: int = _S) -> tuple[str, bool]:
    """Run a command through multiple shells. Never throws.

    Tries in order:
    1. Direct call — current process PATH
    2. cmd /c — system-wide PATH
    3. clean PowerShell — never loads the user's profile or opens a window

    fnm/nvm are discovered from their on-disk version stores, so loading a
    PowerShell profile is both unnecessary and a source of console popups.
    """
    attempts = [
        cmd,
        ['cmd', '/c'] + cmd,
        ['powershell', '-NoProfile', '-Command', subprocess.list2cmdline(cmd)],
    ]
    for attempt in attempts:
        try:
            # Windows tools can emit a codepage different from Python's active
            # console codec.  Replacement keeps background detection reliable.
            r = subprocess.run(attempt, capture_output=True, text=True,
                               errors='replace', timeout=timeout, **hidden_process_kwargs())
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip(), True
        except Exception:
            continue
    return '', False


def _paths_from_where(command: str) -> list[str]:
    """Return executable paths known to ``where.exe`` without raising.

    A desktop application is commonly launched by Explorer, whose PATH does
    not contain the shell-only PATH changes made by fnm/nvm.  ``where`` is a
    useful extra source, but it is deliberately not our only source.
    """
    try:
        result = subprocess.run(['where.exe', command], capture_output=True, text=True,
                                errors='replace', timeout=_S, **hidden_process_kwargs())
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def _node_candidates() -> list[str]:
    """Find Node installations including fnm/nvm/Scoop installations.

    This must not rely solely on PATH: fnm puts the active Node version in a
    per-shell ``fnm_multishells`` directory, which is absent when the helper
    EXE is started from the Windows desktop.
    """
    candidates = [shutil.which('node') or ''] + _paths_from_where('node')
    home = Path.home()
    local_app_data = Path(os.environ.get('LOCALAPPDATA', home / 'AppData' / 'Local'))
    app_data = Path(os.environ.get('APPDATA', home / 'AppData' / 'Roaming'))
    program_files = [Path(value) for value in (
        os.environ.get('ProgramFiles', ''), os.environ.get('ProgramFiles(x86)', '')
    ) if value]

    # Standard installer, nvm-windows, Scoop, and fnm's durable version store.
    candidates.extend(str(base / 'nodejs' / 'node.exe') for base in program_files)
    candidates.extend([
        str(home / 'scoop' / 'apps' / 'nodejs' / 'current' / 'node.exe'),
        str(home / 'scoop' / 'apps' / 'nodejs-lts' / 'current' / 'node.exe'),
    ])
    scan_patterns = [
        # fnm_multishells is intentionally excluded: it can contain thousands
        # of stale junctions.  The durable fnm node-versions store below is
        # where those links point, and is safe to scan.
        (home / 'scoop' / 'persist' / 'fnm' / 'node-versions', '*/installation/node.exe'),
        (app_data / 'fnm' / 'node-versions', '*/installation/node.exe'),
        (app_data / 'nvm', '*/node.exe'),
    ]
    for root, pattern in scan_patterns:
        try:
            if root.exists():
                candidates.extend(str(path) for path in root.glob(pattern))
        except OSError:
            continue

    # Preserve order (PATH's active version first), while ignoring stale paths.
    unique, seen = [], set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate)) if candidate else ''
        # A fnm per-shell directory disappears after its creating shell exits.
        # Never report it to the GUI as a durable runtime, even if it happens
        # to exist while detection is running.
        is_ephemeral_fnm = 'fnm_multishells' in normalized
        if normalized and not is_ephemeral_fnm and normalized not in seen and Path(candidate).is_file():
            unique.append(candidate)
            seen.add(normalized)
    return unique


def _npm_candidates(node_path: str = '') -> list[str]:
    """Find npm.cmd, preferring the npm paired with the detected Node binary."""
    candidates = [shutil.which('npm') or ''] + _paths_from_where('npm')
    if node_path:
        node_dir = Path(node_path).parent
        candidates.extend([str(node_dir / 'npm.cmd'), str(node_dir / 'npm')])
    for node in _node_candidates():
        node_dir = Path(node).parent
        candidates.extend([str(node_dir / 'npm.cmd'), str(node_dir / 'npm')])

    unique, seen = [], set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate)) if candidate else ''
        is_ephemeral_fnm = 'fnm_multishells' in normalized
        if normalized and not is_ephemeral_fnm and normalized not in seen and Path(candidate).is_file():
            unique.append(candidate)
            seen.add(normalized)
    return unique


def _try_executables(executables: list[str], args: list[str], timeout: int = _S) -> tuple[str, bool, str]:
    """Run known executable files, returning its output and successful path."""
    for executable in executables:
        try:
            result = subprocess.run([executable] + args, capture_output=True, text=True,
                                    errors='replace', timeout=timeout, **hidden_process_kwargs())
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip(), True, executable
        except Exception:
            continue
    return '', False, ''

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
    out, ok, node_path = _try_executables(_node_candidates(), ['--version'])
    if not ok:
        out, ok = _try_cmd(['node', '--version'])
        node_path = shutil.which('node') or ''
    if ok and out:
        v = out.lstrip('v')
        major = int(v.split('.')[0]) if v else 0
        return {'node_installed': True, 'node_version': out, 'node_path': node_path, 'node_ok': major >= 18}
    return {'node_installed': False, 'node_version': '', 'node_path': node_path, 'node_ok': False}

def detect_npm() -> dict:
    node_path = detect_node().get('node_path', '')
    out, ok, npm_path = _try_executables(_npm_candidates(node_path), ['--version'])
    if not ok:
        out, ok = _try_cmd(['npm', '--version'])
        npm_path = shutil.which('npm') or ''
    if ok and out:
        major = int(out.split('.')[0]) if out else 0
        return {'npm_installed': True, 'npm_version': out, 'npm_path': npm_path, 'npm_ok': major >= 9}
    return {'npm_installed': False, 'npm_version': '', 'npm_path': npm_path, 'npm_ok': False}

def detect_opencode() -> dict:
    # Prefer the shim paired with the verified npm runtime.  ``shutil.which``
    # can otherwise return fnm_multishells\...\opencode.cmd, a stale shell
    # junction that is unusable from the desktop GUI.
    npm_path = detect_npm().get('npm_path', '')
    paired_cli = str(Path(npm_path).parent / 'opencode.cmd') if npm_path else ''
    path_cli = shutil.which('opencode') or ''
    candidates = [paired_cli, path_cli]
    for exe_path in candidates:
        normalized = os.path.normcase(os.path.abspath(exe_path)) if exe_path else ''
        if not exe_path or 'fnm_multishells' in normalized or not Path(exe_path).is_file():
            continue
        ver_out, ver_ok, verified_path = _try_executables([exe_path], ['--version'], timeout=5)
        if ver_ok:
            return {'opencode_installed': True, 'opencode_version': ver_out, 'opencode_path': verified_path}
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
                          capture_output=True, text=True, errors='replace', timeout=5,
                          **hidden_process_kwargs())
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
    # Keep the legacy UI shape, but discover every documented Claude settings
    # scope (user, project and settings.local.json) via the migration engine.
    from core.cc_migrator import settings_sources
    home, cwd = Path.home(), Path.cwd()
    sources = settings_sources(home, cwd)
    user, project, local = sources
    settings_path = user['path']
    project_claude = cwd / '.claude'
    skills_path = home / '.claude' / 'skills'
    project_files = []
    if project_claude.exists():
        for f in project_claude.iterdir():
            if f.is_file() and f.suffix in ('.json', '.md', '.yml', '.yaml'):
                project_files.append({'name': f.name, 'path': str(f)})

    return {
        'claude_config_found': any(source['exists'] for source in sources) or skills_path.exists() or project_claude.exists(),
        'claude_settings_path': str(settings_path) if settings_path.exists() else '',
        'claude_skills_path': str(skills_path) if skills_path.exists() else '',
        'project_claude_path': str(project_claude) if project_claude.exists() else '',
        'claude_settings': user['settings'],
        'claude_settings_raw': user['raw'],
        'claude_settings_readable': user['readable'],
        'project_settings': project['settings'],
        'project_settings_raw': project['raw'],
        'project_settings_readable': project['readable'],
        'local_settings_path': str(local['path']) if local['exists'] else '',
        'local_settings': local['settings'],
        'local_settings_raw': local['raw'],
        'local_settings_readable': local['readable'],
        'settings_sources': [{'scope': source['scope'], 'path': str(source['path']),
                              'exists': source['exists'], 'readable': source['readable']} for source in sources],
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
