import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from core import proxy_manager

def test_detect_all_proxies_no_proxy(monkeypatch):
    monkeypatch.delenv('HTTP_PROXY', raising=False)
    monkeypatch.delenv('HTTPS_PROXY', raising=False)
    monkeypatch.setattr(proxy_manager, '_wininet_system_proxy', lambda: {})
    result = proxy_manager.detect_all_proxies()
    assert result['has_proxy'] is False
    assert result['wininet'] == {}

def test_detect_all_proxies_with_proxy(monkeypatch):
    monkeypatch.setenv('HTTP_PROXY', 'http://proxy:8080')
    monkeypatch.setattr(proxy_manager, '_wininet_system_proxy', lambda: {})
    result = proxy_manager.detect_all_proxies()
    assert result['has_proxy'] is True
    assert result['http'] == 'http://proxy:8080'

def test_detect_all_proxies_reports_wininet_system_proxy(monkeypatch):
    monkeypatch.delenv('HTTP_PROXY', raising=False)
    monkeypatch.delenv('HTTPS_PROXY', raising=False)
    monkeypatch.setattr(proxy_manager, '_wininet_system_proxy',
                        lambda: {'enabled': True, 'server': '127.0.0.1:7897'})
    result = proxy_manager.detect_all_proxies()
    # No env proxy, yet has_proxy is True because the WinINET system proxy is on.
    assert result['has_proxy'] is True
    assert result['http'] == ''
    assert result['wininet'] == {'enabled': True, 'server': '127.0.0.1:7897'}

def test_wininet_system_proxy_off_windows(monkeypatch):
    monkeypatch.setattr(proxy_manager.os, 'name', 'posix')
    assert proxy_manager._wininet_system_proxy() == {}

def test_generate_bat_launcher(tmp_path):
    exe_dir = tmp_path / 'OpenCode'
    exe_dir.mkdir()
    (exe_dir / 'opencode.exe').write_text('')
    paths = proxy_manager.generate_launcher_scripts(str(exe_dir), 'exe')
    bat_path = os.path.join(str(exe_dir), 'opencode.bat')
    assert os.path.exists(bat_path)
    content = open(bat_path).read()
    assert 'set HTTP_PROXY=' in content
    assert 'opencode.exe' in content

def test_generate_ps1_launcher(tmp_path):
    exe_dir = tmp_path / 'OpenCode'
    exe_dir.mkdir()
    (exe_dir / 'opencode.exe').write_text('')
    paths = proxy_manager.generate_launcher_scripts(str(exe_dir), 'exe')
    ps1_path = os.path.join(str(exe_dir), 'opencode.ps1')
    assert os.path.exists(ps1_path)
    content = open(ps1_path).read()
    assert 'Remove-Item Env:HTTP_PROXY' in content

def test_npm_mode_skips_exe_launcher(tmp_path):
    paths = proxy_manager.generate_launcher_scripts(str(tmp_path), 'npm')
    assert len([p for p in paths if p.endswith('.bat')]) == 0

def test_direct_connection_commands_cover_permanent_and_temporary_powershell_proxy_variables():
    commands = proxy_manager.direct_connection_commands()
    assert 'Add-Content -Path $PROFILE' in commands['powershell_profile']
    assert 'function opencode' in commands['powershell_profile']
    assert 'Get-Command opencode -CommandType Application' in commands['powershell_profile']
    assert commands['powershell_once'] == (
        'Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY -ErrorAction SilentlyContinue; opencode'
    )
    assert commands['powershell_once'].endswith('; opencode')

def test_is_internal_address():
    assert proxy_manager.is_internal_address('192.168.1.1') is True
    assert proxy_manager.is_internal_address('10.0.0.1') is True
    assert proxy_manager.is_internal_address('8.8.8.8') is False
