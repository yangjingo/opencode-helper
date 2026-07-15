import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class MockResponse:
    def __init__(self, status_code, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json

def test_test_endpoint_success(monkeypatch):
    from core import validator
    def mock_post(url, headers, json, timeout):
        return MockResponse(200, {'id': 'msg_123'})
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    result = validator.test_endpoint('http://10.0.0.1/v1', 'sk-test')
    assert result['ok'] is True
    assert result['status_code'] == 200

def test_test_endpoint_reachable_with_401(monkeypatch):
    from core import validator
    def mock_post(url, headers, json, timeout):
        return MockResponse(401, {}, 'Unauthorized')
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    result = validator.test_endpoint('http://10.0.0.1/v1', 'bad-key')
    assert result['ok'] is True  # server IS reachable, just auth failed
    assert result['status_code'] == 401

def test_test_endpoint_timeout(monkeypatch):
    from core import validator
    import requests as req
    def mock_post(url, headers, json, timeout):
        raise req.Timeout()
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    result = validator.test_endpoint('http://10.0.0.1/v1', 'sk-test')
    assert result['ok'] is False
    assert 'timeout' in result['message'].lower()

def test_run_all_returns_four(monkeypatch, tmp_path):
    from core import validator
    from pathlib import Path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    (tmp_path / '.config' / 'opencode').mkdir(parents=True, exist_ok=True)
    (tmp_path / '.config' / 'opencode' / 'opencode.jsonc').write_text('{}')
    def mock_get(url, headers, timeout):
        return MockResponse(200)
    def mock_post(url, headers, json, timeout):
        return MockResponse(200, {'choices': [{'message': {'content': 'Hello'}}]})
    def mock_cli(model_id='', timeout=30):
        return {'ok': True, 'command': 'opencode -p test --json',
                'raw_output': '{"response":"hello"}',
                'formatted': '{"response": "hello"}',
                'message': 'OpenCode CLI responded successfully'}
    monkeypatch.setattr(validator.requests, 'get', mock_get)
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    monkeypatch.setattr(validator, 'test_opencode_cli', mock_cli)
    results = validator.run_all('http://10.0.0.1/v1', 'sk-test', 'glm-5.2')
    assert len(results) == 4  # endpoint + model + cli query + config
