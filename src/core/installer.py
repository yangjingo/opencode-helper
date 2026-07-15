"""OpenCode installation — npm global install with domestic mirror and live streaming output."""
import subprocess, threading

OPENCODE_NPM_PACKAGE = 'opencode-ai'
NPM_MIRROR = 'https://registry.npmmirror.com'

def install_npm(progress_callback=None) -> bool:
    """Install OpenCode via npm with live streaming output. Uses Popen for real-time lines."""

    def log(msg):
        if progress_callback:
            progress_callback(msg)

    cmd = f'npm install -g {OPENCODE_NPM_PACKAGE} --verbose --registry {NPM_MIRROR}'
    log(f'[npm] $ {cmd}')
    log(f'[npm] mirror: {NPM_MIRROR}')

    try:
        proc = subprocess.Popen(
            ['cmd', '/c', cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            stripped = line.rstrip()
            if stripped:
                log(stripped)
        proc.wait()
        if proc.returncode == 0:
            log('[npm] ✓ Installation complete')
            return True
        else:
            log(f'[npm] ✗ Installation failed (exit code {proc.returncode})')
            return False
    except FileNotFoundError:
        log('[npm] ✗ cmd not found — cannot run installation')
        return False
    except Exception as e:
        log(f'[npm] ✗ Unexpected error: {e}')
        return False

def check_npm_available() -> bool:
    """Quick check if npm is available on PATH."""
    try:
        r = subprocess.run(['cmd', '/c', 'npm --version'], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False
