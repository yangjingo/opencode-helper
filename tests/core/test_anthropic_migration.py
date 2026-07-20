"""Regression tests for Claude Code Anthropic endpoint migration."""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class _MockAnthropicHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        payload = self.rfile.read(length).decode('utf-8')
        self.__class__.requests.append({
            'path': self.path,
            'x_api_key': self.headers.get('x-api-key'),
            'authorization': self.headers.get('Authorization'),
            'body': json.loads(payload),
        })
        self.send_response(401)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'type': 'error',
            'error': {'type': 'authentication_error', 'message': 'mock invalid token'},
        }).encode('utf-8'))

    def log_message(self, *_args):
        pass


def test_claude_anthropic_env_migrates_to_valid_opencode_provider_and_reports_bad_token():
    """A plain /v1 Claude gateway must not be mistaken for OpenAI-compatible."""
    from core.cc_migrator import extract_profile
    from core.config_writer import generate_config
    from core.validator import test_model
    from core.validation_result import Status

    _MockAnthropicHandler.requests = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), _MockAnthropicHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f'http://127.0.0.1:{server.server_port}/v1'
        profile = extract_profile(runtime_env={
            'ANTHROPIC_API_KEY': 'mock-invalid-token',
            'ANTHROPIC_BASE_URL': base_url,
            'ANTHROPIC_DEFAULT_SONNET_MODEL': 'mock-claude-model',
        })

        class State:
            provider_name = 'claude-migration'
            display_name = 'Claude migration gateway'
            api_key = profile['api_key']
            base_url = profile['base_url']
            api_style = profile['api_style']
            model_id = profile['model_id']
            model_name = profile['model_id']
            reasoning = True
            thinking = True

        config = json.loads(generate_config(State()))
        provider = config['provider']['claude-migration']
        assert provider['npm'] == '@ai-sdk/anthropic'
        assert provider['options']['baseURL'] == base_url
        assert config['model'] == 'claude-migration/mock-claude-model'

        result = test_model(base_url, profile['api_key'], profile['model_id'], {
            'test_strategy': 'anthropic_compatible',
            'timeout': (1, 2), 'retry': {'times': 1}, 'headers': {},
        })
        assert _MockAnthropicHandler.requests[0]['path'] == '/v1/messages'
        assert _MockAnthropicHandler.requests[0]['x_api_key'] == 'mock-invalid-token'
        assert result.status == Status.FAILED
        assert result.metadata['status_code'] == 401
        assert '认证失败' in result.message
        assert '地址' not in result.message
    finally:
        server.shutdown()
        thread.join(timeout=2)
