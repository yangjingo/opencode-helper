"""Auto-fix environment issues — domestic mirrors + npm/node repair."""
import os, subprocess, webbrowser, shutil

NPM_MIRROR = 'https://registry.npmmirror.com'
NODE_MIRROR_URL = 'https://npmmirror.com/mirrors/node/v22.18.0/node-v22.18.0-x64.msi'


def fix_npm_registry(progress_callback=None) -> bool:
    def log(msg):
        if progress_callback: progress_callback(msg)

    for cmd in [
        ['npm', 'config', 'set', 'registry', NPM_MIRROR],
        ['cmd', '/c', 'npm config set registry ' + NPM_MIRROR],
        ['powershell', '-Command', 'npm config set registry ' + NPM_MIRROR],
        ['powershell', '-NoProfile', '-Command', 'npm config set registry ' + NPM_MIRROR],
    ]:
        log(f'$ {" ".join(cmd)}')
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            for line in r.stdout.strip().split('\n'):
                if line.strip():
                    log(f'  {line.strip()}')
            if r.stderr.strip():
                for line in r.stderr.strip().split('\n'):
                    if line.strip():
                        log(f'  [stderr] {line.strip()}')
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

    # Check if Node already installed
    node_path = shutil.which('node')
    if node_path:
        log(f'$ where node')
        log(f'  {node_path}')
        log('[node] ✓ Node.js already installed — no fix needed')
        return True

    # Try winget
    winget_cmd = ['winget', 'install', 'OpenJS.NodeJS.LTS', '--silent', '--accept-package-agreements']
    log(f'$ {" ".join(winget_cmd)}')
    try:
        r = subprocess.run(winget_cmd, capture_output=True, text=True, timeout=60)
        for line in r.stdout.strip().split('\n'):
            if line.strip():
                log(f'  {line.strip()}')
        if r.returncode == 0:
            log('[node] ✓ winget install started')
            return True
        else:
            log(f'[node] ✗ exit code {r.returncode}')
    except FileNotFoundError:
        log('[node] winget not available')
    except Exception as e:
        log(f'[node] ✗ {e}')

    # Fallback: browser download
    log(f'[node] Opening browser → {NODE_MIRROR_URL}')
    try:
        webbrowser.open(NODE_MIRROR_URL)
        log('[node] ✓ Download page opened. Install Node.js, then Re-check.')
        return True
    except Exception as e:
        log(f'[node] ✗ {e}')
        return False


def auto_fix_environment(env_report: dict, progress_callback=None) -> dict:
    results = {}
    if not env_report.get('npm_ok', True):
        results['npm_registry'] = fix_npm_registry(progress_callback)
    if not env_report.get('node_ok', True):
        results['nodejs'] = fix_node_install(progress_callback)
    return results
