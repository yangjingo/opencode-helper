import sys, os, shutil, subprocess
from pathlib import Path

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class MockPopen:
    def __init__(self, cmd, **kw):
        self.cmd = cmd
        self.returncode = 0
        self.stdout = ['+ opencode-ai@2.0.0\n', 'added 1 package\n']
    def __iter__(self):
        return iter(self.stdout)
    def wait(self):
        return self.returncode

class MockPopenFail:
    def __init__(self, cmd, **kw):
        self.cmd = cmd
        self.returncode = 1
        self.stdout = ['ERR!\n']
    def __iter__(self):
        return iter(self.stdout)
    def wait(self):
        return self.returncode

def test_install_npm_success(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer.subprocess, 'Popen', MockPopen)
    logs = []; result = installer.install_npm(progress_callback=lambda msg: logs.append(msg))
    assert result is True
    assert any('--verbose' in l for l in logs)

def test_install_npm_uses_mirror(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer.subprocess, 'Popen', MockPopen)
    logs = []; result = installer.install_npm(progress_callback=lambda msg: logs.append(msg))
    assert result is True
    assert any(installer.NPM_MIRROR in l for l in logs)

def test_upgrade_uses_powershell_and_latest_package(monkeypatch):
    from core import installer
    seen = []
    class CapturingPopen(MockPopen):
        def __init__(self, cmd, **kw):
            seen.extend(cmd)
            super().__init__(cmd, **kw)
    monkeypatch.setattr(installer, 'detect_npm', lambda: {'npm_path': r'C:\\Node\\npm.cmd'})
    monkeypatch.setattr(installer.subprocess, 'Popen', CapturingPopen)
    assert installer.upgrade_npm() is True
    assert seen[:5] == ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command']
    assert 'opencode-ai@latest' in seen[-1]
    assert installer.NPM_MIRROR in seen[-1]

def test_install_powershell_exposes_node_dir_to_postinstall(monkeypatch):
    from core import installer
    seen = []
    class CapturingPopen(MockPopen):
        def __init__(self, cmd, **kw):
            seen.extend(cmd)
            super().__init__(cmd, **kw)
    monkeypatch.setattr(installer, 'detect_npm', lambda: {'npm_path': r'C:\\Node\\npm.cmd'})
    monkeypatch.setattr(installer.subprocess, 'Popen', CapturingPopen)
    assert installer.install_npm() is True
    assert 'Split-Path -Parent $npm' in seen[-1]
    assert '$env:Path = "$nodeDir;$env:Path"' in seen[-1]
    assert 'VERIFY_PACKAGE_FAILED' in seen[-1]
    assert 'VERIFY_CLI_MISSING' in seen[-1]
    assert 'OpenCode installation chain passed' in seen[-1]

def test_diagnoses_missing_node_on_postinstall():
    from core.installer import diagnose_install_failure
    msg = diagnose_install_failure("npm error 'node' is not recognized as an internal command")
    assert 'postinstall' in msg
    assert '重试' in msg


@pytest.mark.skipif(os.name != 'nt' or not shutil.which('powershell'),
                    reason='Windows PowerShell is required for this integration test')
def test_real_powershell_chain_keeps_fnm_node_on_path_and_verifies_cli(tmp_path, monkeypatch):
    """Exercise PowerShell → npm.cmd → cmd → node.cmd with Node removed from PATH.

    The fake binaries make this a real child-process test without network access
    or mutation of the user's globally installed OpenCode package.
    """
    from core import installer

    runtime = tmp_path / 'fnm-runtime'
    runtime.mkdir()
    npm = runtime / 'npm.cmd'
    node = runtime / 'node.cmd'
    opencode = runtime / 'opencode.cmd'
    npm.write_text(
        '@echo off\n'
        'if /I "%1"=="config" exit /b 0\n'
        'if /I "%1"=="install" (cmd /d /s /c node --version & exit /b %ERRORLEVEL%)\n'
        'if /I "%1"=="list" (echo opencode-ai@fake & exit /b 0)\n'
        'if /I "%1"=="prefix" (echo %~dp0 & exit /b 0)\n'
        'exit /b 2\n', encoding='utf-8')
    node.write_text('@echo off\necho vfake-node\nexit /b 0\n', encoding='utf-8')
    opencode.write_text('@echo off\necho 9.9.9-test\nexit /b 0\n', encoding='utf-8')

    real_popen = subprocess.Popen
    powershell_dir = str(Path(shutil.which('powershell')).parent)
    system32 = str(Path(os.environ['SystemRoot']) / 'System32')

    class PopenWithoutNodeOnPath:
        def __init__(self, cmd, **kwargs):
            environment = os.environ.copy()
            environment['PATH'] = os.pathsep.join([powershell_dir, system32])
            self._process = real_popen(cmd, env=environment, **kwargs)
            self.stdout = self._process.stdout
            self.returncode = None

        def wait(self):
            self.returncode = self._process.wait()
            return self.returncode

    monkeypatch.setattr(installer, 'detect_npm', lambda: {'npm_path': str(npm)})
    monkeypatch.setattr(installer.subprocess, 'Popen', PopenWithoutNodeOnPath)
    logs = []
    assert installer.install_npm(progress_callback=logs.append) is True
    assert any('vfake-node' in line for line in logs)
    assert any('9.9.9-test' in line for line in logs)
    assert any('installation chain passed' in line for line in logs)

def test_install_npm_failure(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer.subprocess, 'Popen', MockPopenFail)
    logs = []; result = installer.install_npm(progress_callback=lambda msg: logs.append(msg))
    assert result is False

def test_check_npm_available_true(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer, 'detect_npm', lambda: {'npm_ok': True})
    assert installer.check_npm_available() is True

def test_check_npm_available_false(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer, 'detect_npm', lambda: {'npm_ok': False})
    assert installer.check_npm_available() is False
