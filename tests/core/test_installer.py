import sys, os
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

def test_install_npm_failure(monkeypatch):
    from core import installer
    monkeypatch.setattr(installer.subprocess, 'Popen', MockPopenFail)
    logs = []; result = installer.install_npm(progress_callback=lambda msg: logs.append(msg))
    assert result is False

def test_check_npm_available_true(monkeypatch):
    from core import installer
    def mock_run(cmd, **kw):
        class R: returncode = 0
        return R()
    monkeypatch.setattr(installer.subprocess, 'run', mock_run)
    assert installer.check_npm_available() is True

def test_check_npm_available_false(monkeypatch):
    from core import installer
    def mock_run(cmd, **kw):
        raise FileNotFoundError()
    monkeypatch.setattr(installer.subprocess, 'run', mock_run)
    assert installer.check_npm_available() is False
