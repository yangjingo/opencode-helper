import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_config_validation_rejects_terminal_markup_in_model(tmp_path, monkeypatch):
    from core import validator
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    path = tmp_path / '.config' / 'opencode' / 'opencode.jsonc'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        'provider': {'zhipu': {'models': {'glm-5.2[1m]': {}}}},
        'model': 'zhipu/glm-5.2[1m]',
    }), encoding='utf-8')
    result = validator.test_config_written()
    assert result.status.value == 'failed'
    assert '模型 ID' in result.message
    assert 'apiKey' not in (result.detail or '')


@pytest.mark.skipif(os.name != 'nt', reason='Windows cmd shim behavior')
def test_cli_validation_runs_cmd_shim_by_absolute_path(tmp_path, monkeypatch):
    from core import validator
    shim = tmp_path / 'opencode.cmd'
    shim.write_text('@echo off\necho mock-cli-ok\nexit /b 0\n', encoding='utf-8')
    monkeypatch.setattr(validator, 'detect_opencode', lambda: {
        'opencode_path': str(shim), 'opencode_installed': True,
    })
    monkeypatch.setattr(validator, 'detect_npm', lambda: {'npm_path': ''})
    result = validator.test_opencode_cli(timeout=10)
    assert result.status.value == 'success'
    assert 'mock-cli-ok' in (result.detail or '')
    assert result.metadata['cli_path'] == str(shim)


@pytest.mark.skipif(os.name != 'nt', reason='Windows cmd shim behavior')
def test_cli_validation_rejects_zero_token_json_turn(tmp_path, monkeypatch):
    """A completed OpenCode session with output=0 is not a model response."""
    from core import validator

    shim = tmp_path / 'opencode.cmd'
    shim.write_text('@echo off\nexit /b 0\n', encoding='utf-8')
    monkeypatch.setattr(validator, 'detect_opencode', lambda: {
        'opencode_path': str(shim), 'opencode_installed': True,
    })
    monkeypatch.setattr(validator, 'detect_npm', lambda: {'npm_path': ''})

    class Process:
        returncode = 0

        def communicate(self, timeout=None):
            return ('{"type":"step_finish","part":{"tokens":{"output":0}}}', '')

        def kill(self):
            pass

    monkeypatch.setattr(validator.subprocess, 'Popen', lambda *args, **kwargs: Process())
    result = validator.test_opencode_cli('zhipu/glm-5.2', timeout=10)
    assert result.status.value == 'failed'
    assert result.metadata['has_model_text'] is False
    assert '未收到模型文本' in result.message
