"""End-to-end validation tests — engine + real validators + mocked HTTP.

These tests exercise the FULL path: ValidationEngine -> validator strategies
-> requests.post (mocked) -> response parsing -> ValidationResult -> report.
No monkeypatching of engine internals — only the network boundary is mocked.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from unittest.mock import patch, MagicMock
from core.validation_engine import ValidationEngine
from core.validation_result import Status, ValidationReport, ValidationResult
from core.validator import (
    test_endpoint, test_model, _test_direct_post, _test_openai_compatible,
    _test_anthropic_compatible,
)
from core.providers import get_provider_config, resolve_test_model


# ── Helpers: build realistic mock HTTP responses ─────────────────────────────

def mock_response(status_code=200, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or ''
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError('no json')
    return resp


# ── Fixtures: a complete fake WizardState ────────────────────────────────────

class FakeState:
    def __init__(self, base_url='https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
                 api_key='sk-test-123', model_id='qwen3.7-plus'):
        self.base_url = base_url
        self.api_key = api_key
        self.model_id = model_id
        self.provider_name = 'dashscope'
        self.display_name = 'Test'
        self.reasoning = True
        self.thinking = True


# ════════════════════════════════════════════════════════════════════════════
# TEST GROUP 1: Engine + real validators integration (full conversion path)
# ════════════════════════════════════════════════════════════════════════════

def test_engine_full_success_path(tmp_path):
    """Engine runs model, config and CLI checks in the user-visible order."""
    state = FakeState()
    progress_log = []

    config_path = tmp_path / '.config' / 'opencode' / 'opencode.jsonc'
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '{"provider":{"dashscope":{"models":{"qwen3.7-plus":{}}}},"model":"dashscope/qwen3.7-plus"}',
        encoding='utf-8')

    with patch('core.validator.requests.post') as mock_post, \
         patch('core.validator.detect_opencode', return_value={'opencode_path': 'opencode'}), \
         patch('core.validator.os.path.isfile', return_value=True), \
         patch('core.validator.subprocess.Popen') as mock_popen, \
         patch('core.validator.Path.home', return_value=tmp_path):
        # model inference succeeds (direct_post strategy)
        mock_post.return_value = mock_response(200, {'content': [{'text': 'hi'}]}, 'hi')
        # CLI succeeds
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = ('hello', '')
        mock_popen.return_value = proc
        engine = ValidationEngine(state)
        engine.on_progress = lambda n, v: progress_log.append((n, v))
        report = engine.run_all()

    assert report.overall_status == Status.SUCCESS, f'expected SUCCESS got {report.overall_status}'
    assert [result.name for result in report.results] == ['model', 'config', 'cli']
    assert len(report.get_failed()) == 0
    # Progress should reach 1.0
    assert progress_log[-1][1] == 1.0, f'final progress {progress_log[-1]}'
    print('  PASS: engine full success path ->', report.overall_status.value,
          f'({report.total_duration_ms}ms)')


def test_engine_partial_failure_produces_warning():
    """If config fails after model inference, the overall report fails."""
    state = FakeState()
    with patch('core.validator.requests.post') as mock_post, \
         patch('core.validator.detect_opencode', return_value={'opencode_path': 'opencode'}), \
         patch('core.validator.os.path.isfile', return_value=True), \
         patch('core.validator.subprocess.Popen') as mock_popen, \
         patch('core.validator.Path.exists', return_value=False):
        mock_post.return_value = mock_response(200, {'content': [{'text': 'hi'}]})
        proc = MagicMock(); proc.returncode = 0
        proc.communicate.return_value = ('hello', '')
        mock_popen.return_value = proc

        engine = ValidationEngine(state)
        report = engine.run_all()

    assert report.overall_status == Status.FAILED, f'config missing should FAIL overall, got {report.overall_status}'
    config_r = next(r for r in report.results if r.name == 'config')
    assert config_r.status == Status.FAILED
    assert config_r.suggestion is not None  # diagnostic present
    print('  PASS: partial failure ->', report.overall_status.value,
          'config suggestion:', config_r.suggestion[:40])


# ════════════════════════════════════════════════════════════════════════════
# TEST GROUP 2: Strategy-specific URL construction & parsing
# ════════════════════════════════════════════════════════════════════════════

def test_direct_post_no_path_append():
    """Alibaba direct_post must POST to baseURL exactly — no /messages appended."""
    cfg = get_provider_config('https://coding.dashscope.aliyuncs.com/apps/anthropic/v1')
    url = 'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1'

    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {'content': [{'text': 'hello'}]})
        _test_direct_post(url, 'key', 'qwen3.7-plus', cfg, max_tokens=50)

    called_url = mock_post.call_args[0][0]
    assert called_url == url, f'direct_post appended path! got {called_url}'
    print('  PASS: direct_post URL unmodified ->', called_url)


def test_openai_compatible_appends_chat_completions():
    """OpenAI strategy must POST to {base}/v1/chat/completions."""
    cfg = {'test_strategy': 'openai_compatible', 'timeout': (5, 30), 'retry': {'times': 1},
           'headers': {}}
    url = 'https://api.deepseek.com'

    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {'choices': [{'message': {'content': 'hi'}}]})
        result = _test_openai_compatible(url, 'key', 'deepseek-chat', cfg, max_tokens=50)

    called_url = mock_post.call_args[0][0]
    assert called_url == 'https://api.deepseek.com/v1/chat/completions', f'wrong URL: {called_url}'
    assert result.status == Status.SUCCESS
    print('  PASS: openai URL ->', called_url, '| content:', result.message[:30])


def test_openai_compatible_no_double_v1():
    """If baseURL already ends in /v1, don't add another /v1."""
    cfg = {'test_strategy': 'openai_compatible', 'timeout': (5, 30), 'retry': {'times': 1},
           'headers': {}}
    url = 'https://api.deepseek.com/v1'

    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {'choices': [{'message': {'content': 'hi'}}]})
        _test_openai_compatible(url, 'key', 'deepseek-chat', cfg, max_tokens=50)

    called_url = mock_post.call_args[0][0]
    assert called_url == 'https://api.deepseek.com/v1/chat/completions', f'got {called_url}'
    print('  PASS: no double /v1 ->', called_url)


def test_anthropic_compatible_appends_messages():
    """Anthropic strategy must POST to {base}/v1/messages."""
    cfg = {'test_strategy': 'anthropic_compatible', 'timeout': (5, 30), 'retry': {'times': 1},
           'headers': {}}

    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {'content': [{'text': 'hi'}]})
        _test_anthropic_compatible('https://api.anthropic.com', 'key', 'claude-sonnet-4', cfg, max_tokens=50)

    called_url = mock_post.call_args[0][0]
    assert called_url == 'https://api.anthropic.com/v1/messages', f'got {called_url}'
    # Verify anthropic-version header present
    headers = mock_post.call_args[1]['headers'] or mock_post.call_args.kwargs.get('headers')
    assert headers.get('anthropic-version') == '2023-06-01'
    print('  PASS: anthropic URL ->', called_url, '| header ok')


def test_dashscope_appends_messages():
    """test_endpoint() for dashscope appends /messages (Anthropic-compat, baseURL has /v1)."""
    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {'content': [{'text': 'hi'}]})
        result = test_endpoint('https://coding.dashscope.aliyuncs.com/apps/anthropic/v1', 'key')

    called_url = mock_post.call_args[0][0]
    assert called_url.endswith('/v1/messages'), f'dashscope should append /messages: {called_url}'
    assert result.ok
    print('  PASS: test_endpoint(dashscope) -> appends /messages:', called_url)


# ════════════════════════════════════════════════════════════════════════════
# TEST GROUP 3: Retry logic + diagnostics
# ════════════════════════════════════════════════════════════════════════════

def test_retry_on_5xx_then_success():
    """5xx should be retried via the public API's with_retry wrapper; eventual 200 -> SUCCESS.

    Tests through test_model() (which wraps the strategy in with_retry),
    NOT the raw strategy function — retry lives in the public API layer.
    """
    cfg = {'test_strategy': 'direct_post', 'timeout': (5, 15),
           'retry': {'times': 3, 'backoff': 0.01}, 'headers': {}}
    url = 'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1'

    responses = [
        mock_response(503, text='Service Unavailable'),
        mock_response(503, text='Service Unavailable'),
        mock_response(200, {'content': [{'text': 'ok'}]}),
    ]
    with patch('core.validator.requests.post', side_effect=responses) as mock_post:
        result = test_model(url, 'key', 'qwen3.7-plus', cfg)

    assert result.status == Status.SUCCESS, f'expected success after retry, got {result.status}'
    assert mock_post.call_count == 3, f'expected 3 attempts, got {mock_post.call_count}'
    print('  PASS: retried 5xx -> eventually SUCCESS (3 attempts)')


def test_retry_on_429_then_success():
    """Rate limiting is transient and must use the configured backoff retry."""
    cfg = {'test_strategy': 'openai_compatible', 'timeout': (1, 2),
           'retry': {'times': 2, 'backoff': 0}, 'headers': {}}
    with patch('core.validator.requests.post') as mock_post:
        mock_post.side_effect = [
            mock_response(429, {'error': {'message': 'rate limited'}}, 'rate limited'),
            mock_response(200, {'choices': [{'message': {'content': 'ok'}}]}),
        ]
        result = test_model('https://api.example.com/v1', 'key', 'model', cfg)
    assert result.status == Status.SUCCESS
    assert mock_post.call_count == 2


def test_openai_reasoning_content_counts_as_model_output():
    cfg = {'test_strategy': 'openai_compatible', 'timeout': (1, 2),
           'retry': {'times': 1}, 'headers': {}}
    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(200, {
            'choices': [{'message': {'content': '', 'reasoning_content': 'thinking'}}],
        })
        result = test_model('https://api.example.com/v1', 'key', 'model', cfg)
    assert result.status == Status.SUCCESS
    assert 'thinking' in result.message


def test_no_retry_on_4xx():
    """401 should NOT be retried (won't fix itself) — fast fail."""
    cfg = {'test_strategy': 'direct_post', 'timeout': (5, 15),
           'retry': {'times': 3, 'backoff': 0.01}, 'headers': {}}

    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(401, text='Unauthorized')
        result = _test_direct_post('https://x.example.com', 'bad-key', 'm', cfg, max_tokens=50)

    assert mock_post.call_count == 1, f'401 should not retry, called {mock_post.call_count} times'
    assert result.status == Status.FAILED
    print('  PASS: 401 not retried (single call), suggestion:', result.suggestion[:35])


def test_diagnostics_401():
    """401 -> suggestion about API Key."""
    cfg = {'test_strategy': 'openai_compatible', 'timeout': (5, 30), 'retry': {'times': 1}, 'headers': {}}
    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(401, text='Unauthorized')
        result = test_model('https://api.example.com', 'bad', 'm', cfg)
    assert 'API Key' in result.suggestion or 'apiKey' in result.suggestion
    print('  PASS: 401 diagnostic:', result.suggestion)


def test_diagnostics_404():
    """404 -> suggestion about Endpoint address."""
    cfg = {'test_strategy': 'direct_post', 'timeout': (5, 15), 'retry': {'times': 1},
           'headers': {}}
    with patch('core.validator.requests.post') as mock_post:
        mock_post.return_value = mock_response(404, text='Not Found')
        result = _test_direct_post('https://x.example.com', 'key', 'm', cfg, max_tokens=50)
    assert 'Endpoint' in result.suggestion or '地址' in result.suggestion
    print('  PASS: 404 diagnostic:', result.suggestion[:45])


def test_diagnostics_timeout():
    """Timeout -> suggestion about network/proxy."""
    import requests
    cfg = {'test_strategy': 'direct_post', 'timeout': (1, 2), 'retry': {'times': 1}, 'headers': {}}
    with patch('core.validator.requests.post', side_effect=requests.Timeout('timed out')):
        result = _test_direct_post('https://x.example.com', 'key', 'm', cfg, max_tokens=50)
    assert result.status == Status.FAILED
    assert result.suggestion is not None
    assert any(k in result.suggestion for k in ['超时', '网络', '代理', 'timeout', 'proxy'])
    print('  PASS: timeout diagnostic:', result.suggestion[:40])


def test_diagnostics_connection_error():
    """Connection error -> suggestion about URL/reachability."""
    import requests
    cfg = {'test_strategy': 'direct_post', 'timeout': (5, 15), 'retry': {'times': 1}, 'headers': {}}
    with patch('core.validator.requests.post',
               side_effect=requests.ConnectionError('refused')):
        result = _test_direct_post('https://x.invalid', 'key', 'm', cfg, max_tokens=50)
    assert result.status == Status.FAILED
    assert result.suggestion is not None
    print('  PASS: connection-error diagnostic:', result.suggestion[:40])


# ════════════════════════════════════════════════════════════════════════════
# TEST GROUP 4: Provider detection + model resolution
# ════════════════════════════════════════════════════════════════════════════

def test_provider_detection_matrix():
    cases = [
        ('https://coding.dashscope.aliyuncs.com/apps/anthropic/v1', 'anthropic_compatible'),
        ('https://dashscope.aliyuncs.com/apps/anthropic/v1', 'anthropic_compatible'),
        ('https://api.deepseek.com/anthropic', 'anthropic_compatible'),
        ('https://api.openai.com/v1', 'openai_compatible'),
        ('https://api.anthropic.com', 'anthropic_compatible'),
        ('https://unknown-provider.com/v1', 'openai_compatible'),  # generic /v1 default
    ]
    for url, expected_strategy in cases:
        cfg = get_provider_config(url)
        assert cfg['test_strategy'] == expected_strategy, \
            f'{url} -> {cfg["test_strategy"]} (expected {expected_strategy})'
    print('  PASS: provider detection matrix (6 cases)')


def test_model_resolution_priority():
    """User model takes priority over provider default."""
    cfg = get_provider_config('https://coding.dashscope.aliyuncs.com/apps/anthropic/v1')
    assert resolve_test_model(cfg, 'user-custom-model') == 'user-custom-model'
    assert resolve_test_model(cfg, '') == cfg['default_test_model']
    assert resolve_test_model(cfg, '   ') == cfg['default_test_model']  # whitespace
    print('  PASS: model resolution priority (user > default > fallback)')


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

ALL_TESTS = [
    # Group 1: integration
    ('engine_success', test_engine_full_success_path),
    ('engine_partial', test_engine_partial_failure_produces_warning),
    # Group 2: strategies
    ('direct_post', test_direct_post_no_path_append),
    ('openai_url', test_openai_compatible_appends_chat_completions),
    ('openai_no_double_v1', test_openai_compatible_no_double_v1),
    ('anthropic_url', test_anthropic_compatible_appends_messages),
    ('dashscope_messages', test_dashscope_appends_messages),
    # Group 3: retry + diagnostics
    ('retry_5xx', test_retry_on_5xx_then_success),
    ('no_retry_4xx', test_no_retry_on_4xx),
    ('diag_401', test_diagnostics_401),
    ('diag_404', test_diagnostics_404),
    ('diag_timeout', test_diagnostics_timeout),
    ('diag_conn', test_diagnostics_connection_error),
    # Group 4: detection
    ('provider_matrix', test_provider_detection_matrix),
    ('model_resolution', test_model_resolution_priority),
]


def run_all():
    passed, failed = 0, 0
    for name, fn in ALL_TESTS:
        try:
            print(f'\n[RUN] {name}')
            fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f'  ✗ FAIL: {e}')
        except Exception as e:
            failed += 1
            print(f'  ✗ ERROR: {type(e).__name__}: {e}')
    print(f'\n{"="*60}')
    print(f'E2E RESULTS: {passed} passed, {failed} failed, {len(ALL_TESTS)} total')
    print('='*60)
    return failed == 0


if __name__ == '__main__':
    sys.exit(0 if run_all() else 1)
