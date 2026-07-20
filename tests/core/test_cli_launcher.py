import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_windows_launch_opens_visible_powershell(monkeypatch):
    from core import cli_launcher
    captured = {}

    def fake_popen(args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        return 'process'

    monkeypatch.setattr(cli_launcher.sys, 'platform', 'win32')
    monkeypatch.setattr(cli_launcher.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(cli_launcher, 'resolve_opencode_executable', lambda _path='': r'C:\tools\opencode.cmd')
    assert cli_launcher.launch_opencode_cli() == 'process'
    assert captured['args'][:-1] == ['powershell.exe', '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command']
    assert captured['args'][-1] == "& 'C:\\tools\\opencode.cmd'"
    assert 'creationflags' in captured['kwargs']


def test_windows_direct_launch_clears_proxy_before_opencode(monkeypatch):
    from core import cli_launcher
    captured = {}

    def fake_popen(args, **kwargs):
        captured['args'] = args
        return 'process'

    monkeypatch.setattr(cli_launcher.sys, 'platform', 'win32')
    monkeypatch.setattr(cli_launcher.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(cli_launcher, 'resolve_opencode_executable', lambda _path='': r'C:\tools\opencode.cmd')
    cli_launcher.launch_opencode_cli(direct=True)
    command = captured['args'][-1]
    assert 'Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY -ErrorAction SilentlyContinue' in command
    assert command.endswith("; & 'C:\\tools\\opencode.cmd'")


def test_resolve_prefers_cmd_shim_over_powershell_script(monkeypatch):
    from core import cli_launcher

    paths = {'opencode.cmd': r'C:\fnm\opencode.cmd', 'opencode.exe': None, 'opencode': r'C:\fnm\opencode'}
    monkeypatch.setattr(cli_launcher.shutil, 'which', lambda name: paths[name])
    assert cli_launcher.resolve_opencode_executable() == r'C:\fnm\opencode.cmd'
