import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from core import env_fixer

def test_fix_npm_registry_success(monkeypatch):
    def mock_run(cmd, **kw):
        class R: returncode = 0; stdout = ''; stderr = ''
        return R()
    monkeypatch.setattr(env_fixer.subprocess, 'run', mock_run)
    result = env_fixer.fix_npm_registry()
    assert result is True

def test_fix_npm_registry_failure(monkeypatch):
    def mock_run(cmd, **kw):
        raise Exception('fail')
    monkeypatch.setattr(env_fixer.subprocess, 'run', mock_run)
    result = env_fixer.fix_npm_registry()
    assert result is False

def test_auto_fix_environment(monkeypatch):
    def mock_fix(cb=None): return True
    monkeypatch.setattr(env_fixer, 'fix_npm_registry', mock_fix)
    results = env_fixer.auto_fix_environment({'npm_ok': False, 'node_ok': True})
    assert results.get('npm_registry') is True
