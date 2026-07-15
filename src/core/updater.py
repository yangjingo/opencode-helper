"""Self-update and OpenCode update checking."""
import requests

VERSION = '1.0.0'
UPDATE_URL = 'https://github.com/your-org/opencode-helper/releases/latest/download/version.json'

def check_self_update() -> dict | None:
    try:
        resp = requests.get(UPDATE_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('version', '') > VERSION:
                return {'version': data['version'], 'url': data.get('url', ''), 'changelog': data.get('changelog', '')}
    except Exception:
        pass
    return None

def check_opencode_update(install_method: str) -> str:
    if install_method == 'npm':
        try:
            import subprocess
            result = subprocess.run(['npm', 'outdated', '-g', 'opencode-ai'],
                                    capture_output=True, text=True, timeout=15)
            if 'opencode-ai' in result.stdout:
                return result.stdout.strip().split('\n')[-1].split()[-1]
        except Exception:
            pass
    return ''
