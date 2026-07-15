import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from core import detector

def test_detect_os(monkeypatch):
    monkeypatch.setattr(detector, '_SYSTEM', 'win32')
    monkeypatch.setattr(detector, 'get_os_version', lambda: '10.0.22631')
    info = detector.detect_os()
    assert info['os_name'] == 'Windows'
    assert info['os_ok'] is True

def test_detect_node_installed(monkeypatch):
    def mock_run(cmd, **kw):
        class R: stdout = 'v20.11.0'; stderr = ''; returncode = 0
        return R()
    monkeypatch.setattr(detector.subprocess, 'run', mock_run)
    info = detector.detect_node()
    assert info['node_installed'] is True
    assert info['node_version'] == 'v20.11.0'
    assert info['node_ok'] is True

def test_detect_node_not_installed(monkeypatch):
    def mock_run(cmd, **kw):
        raise FileNotFoundError()
    monkeypatch.setattr(detector.subprocess, 'run', mock_run)
    info = detector.detect_node()
    assert info['node_installed'] is False
    assert info['node_ok'] is False

def test_detect_proxy(monkeypatch):
    monkeypatch.setenv('HTTP_PROXY', 'http://proxy.company.com:8080')
    monkeypatch.setenv('HTTPS_PROXY', '')
    monkeypatch.setattr(detector, '_detect_system_proxy_registry',
        lambda: {'system_proxy_enabled': False, 'system_proxy_server': '', 'system_proxy_bypass': '', 'source': 'registry'})
    monkeypatch.setattr(detector, '_detect_winhttp_proxy',
        lambda: {'winhttp_direct': True, 'winhttp_proxy': '', 'winhttp_bypass': ''})
    info = detector.detect_proxy()
    assert info['proxy_detected'] is True
    assert info['proxy_http'] == 'http://proxy.company.com:8080'
    assert 'HTTP_PROXY' in info['env_vars']

def test_detect_proxy_none(monkeypatch):
    monkeypatch.delenv('HTTP_PROXY', raising=False)
    monkeypatch.delenv('HTTPS_PROXY', raising=False)
    monkeypatch.delenv('http_proxy', raising=False)
    monkeypatch.delenv('https_proxy', raising=False)
    monkeypatch.delenv('NO_PROXY', raising=False)
    monkeypatch.delenv('no_proxy', raising=False)
    monkeypatch.setattr(detector, '_detect_system_proxy_registry',
        lambda: {'system_proxy_enabled': False, 'system_proxy_server': '', 'system_proxy_bypass': '', 'source': 'registry'})
    monkeypatch.setattr(detector, '_detect_winhttp_proxy',
        lambda: {'winhttp_direct': True, 'winhttp_proxy': '', 'winhttp_bypass': ''})
    info = detector.detect_proxy()
    assert info['proxy_detected'] is False
    assert info['env_vars'] == {}

def test_detect_proxy_shows_no_proxy(monkeypatch):
    monkeypatch.setenv('HTTP_PROXY', 'http://proxy:8080')
    monkeypatch.setenv('NO_PROXY', 'localhost,.internal.com')
    monkeypatch.setattr(detector, '_detect_system_proxy_registry',
        lambda: {'system_proxy_enabled': False, 'system_proxy_server': '', 'system_proxy_bypass': '', 'source': 'registry'})
    monkeypatch.setattr(detector, '_detect_winhttp_proxy',
        lambda: {'winhttp_direct': True, 'winhttp_proxy': '', 'winhttp_bypass': ''})
    info = detector.detect_proxy()
    assert info['no_proxy'] == 'localhost,.internal.com'
    assert 'NO_PROXY' in info['env_vars']

def test_detect_claude_config_found(monkeypatch, tmp_path):
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    (claude_dir / 'settings.json').write_text('{"model": "claude-sonnet-5", "apiKey": "sk-ant-test"}')
    monkeypatch.setattr(detector.Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(detector.Path, 'cwd', lambda: tmp_path)
    info = detector.detect_claude_config()
    assert info['claude_config_found'] is True
    assert info['claude_settings'] == {'model': 'claude-sonnet-5', 'apiKey': 'sk-ant-test'}

def test_detect_claude_config_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(detector.Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(detector.Path, 'cwd', lambda: tmp_path)
    info = detector.detect_claude_config()
    assert info['claude_config_found'] is False
    assert info['claude_settings'] == {}

def test_detect_all_keys(monkeypatch):
    monkeypatch.setattr(detector, '_SYSTEM', 'win32')
    monkeypatch.setattr(detector, 'get_os_version', lambda: '10.0.22631')
    monkeypatch.setattr(detector, 'detect_node', lambda: {'node_installed': True, 'node_version': 'v20.11.0', 'node_ok': True})
    monkeypatch.setattr(detector, 'detect_npm', lambda: {'npm_installed': True, 'npm_version': '10.2.4', 'npm_ok': True})
    monkeypatch.setattr(detector, 'detect_opencode', lambda: {'opencode_installed': False, 'opencode_version': '', 'opencode_path': ''})
    monkeypatch.setattr(detector, 'detect_disk', lambda: {'disk_free_gb': 50.0, 'disk_ok': True})
    monkeypatch.setattr(detector, 'detect_proxy', lambda: {'proxy_detected': False, 'proxy_http': '', 'proxy_https': '', 'no_proxy': '', 'env_vars': {}})
    monkeypatch.setattr(detector, 'detect_claude_env_vars', lambda: {'claude_env_vars': {}})
    monkeypatch.setattr(detector, 'detect_claude_config', lambda: {'claude_config_found': False, 'claude_settings_path': '', 'claude_skills_path': '', 'project_claude_path': '', 'claude_settings': {}, 'project_settings': {}})
    report = detector.detect_all()
    required = ['os_name', 'os_version', 'os_ok', 'node_installed', 'node_version', 'node_ok',
                'npm_installed', 'npm_version', 'npm_ok', 'opencode_installed', 'disk_free_gb',
                'disk_ok', 'proxy_detected', 'claude_config_found', 'claude_env_vars']
    for key in required:
        assert key in report, f"Missing key: {key}"
