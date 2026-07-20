import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from core import validator

class MockResponse:
    def __init__(self, status_code, json_data=None, text=''):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json

def test_test_endpoint_success(monkeypatch):
    def mock_post(url, headers, json, timeout):
        return MockResponse(200, {'id': 'msg_123'})
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    result = validator.test_endpoint('http://10.0.0.1/v1', 'sk-test')
    assert result['ok'] is True
    assert result['status_code'] == 200


def test_openai_compatible_preserves_official_v2_base_url(monkeypatch):
    """Qianfan's OpenAI-compatible API is versioned /v2, not /v1."""
    called = {}

    class Response:
        status_code = 401
        text = 'invalid key'

        def json(self):
            return {}

    def fake_post(url, **kwargs):
        called['url'] = url
        return Response()

    monkeypatch.setattr(validator.requests, 'post', fake_post)
    result = validator.test_endpoint(
        'https://qianfan.baidubce.com/v2', 'fake-key',
        {'test_strategy': 'openai_compatible', 'retry': {'times': 1}},
        'ernie-4.5-turbo-128k',
    )

    assert called['url'] == 'https://qianfan.baidubce.com/v2/chat/completions'
    assert result.metadata['status_code'] == 401
    assert result.ok is True
    assert result.metadata['reachable_via_auth_error'] is True

def test_endpoint_uses_selected_model_for_anthropic_gateway(monkeypatch):
    from core import validator
    captured = {}
    def mock_post(url, headers, json, timeout):
        captured['model'] = json['model']
        return MockResponse(200, {'content': [{'text': 'ok'}]})
    monkeypatch.setattr(validator.requests, 'post', mock_post)
    result = validator.test_endpoint(
        'https://gateway.example/v1', 'key',
        {'test_strategy': 'anthropic_compatible', 'retry': {'times': 1}, 'headers': {}},
        'glm-5.2')
    assert result.ok is True
    assert result.name == 'endpoint'
    assert captured['model'] == 'glm-5.2'

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

def test_run_all_returns_model_config_cli(monkeypatch, tmp_path):
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
    assert len(results) == 3  # model inference + config + CLI query
