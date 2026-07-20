"""Real OpenCode CLI regression for a migrated Claude Anthropic gateway."""
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def _localhost_intercepting_proxy_reason():
    """Return why opencode would route the local mock through a proxy, or None.

    opencode-ai honors both environment proxy variables and, on Windows, the
    WinINET system proxy. Either one intercepts the 127.0.0.1 mock and returns
    502 Bad Gateway, so the request never reaches our handler. These tests
    require direct localhost access; skip when that is impossible.
    """
    env_names = ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
                 'ALL_PROXY', 'all_proxy')
    present = [name for name in env_names if os.environ.get(name)]
    if present:
        return f'environment proxy variable(s) set: {", ".join(present)}'
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
                enabled, _ = winreg.QueryValueEx(key, 'ProxyEnable')
                if enabled:
                    try:
                        server, _ = winreg.QueryValueEx(key, 'ProxyServer')
                    except OSError:
                        server = '?'
                    return f'Windows system (WinINET) proxy enabled ({server})'
        except OSError:
            pass
    return None


@pytest.fixture(autouse=True)
def _skip_when_proxy_intercepts_localhost():
    reason = _localhost_intercepting_proxy_reason()
    if reason:
        pytest.skip(
            f'opencode-ai honors {reason} and routes the local mock through it '
            '(502 Bad Gateway). Disable the proxy to exercise this integration test.'
        )



class _AuthFailingAnthropicGateway(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        self.__class__.requests.append({
            'path': self.path,
            'x_api_key': self.headers.get('x-api-key'),
            'authorization': self.headers.get('authorization'),
            'body': json.loads(self.rfile.read(length).decode('utf-8')),
        })
        self.send_response(401)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'type': 'error',
            'error': {'type': 'authentication_error', 'message': 'mock invalid token'},
        }).encode())

    def log_message(self, *_args):
        pass


class _SuccessfulOpenAIGateway(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible endpoint supporting streaming and non-streaming."""
    requests = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length).decode('utf-8'))
        self.__class__.requests.append({'path': self.path, 'body': body})
        if body.get('stream'):
            self.send_response(200)
            self.send_header('content-type', 'text/event-stream')
            self.end_headers()
            for chunk in [
                {'id': 'mock-completion', 'object': 'chat.completion.chunk',
                 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': 'mock agent success'},
                              'finish_reason': None}]},
                {'id': 'mock-completion', 'object': 'chat.completion.chunk',
                 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]},
            ]:
                self.wfile.write(f'data: {json.dumps(chunk)}\n\n'.encode())
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        else:
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'id': 'mock-completion', 'object': 'chat.completion',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'mock agent success'},
                             'finish_reason': 'stop'}],
            }).encode())

    def log_message(self, *_args):
        pass


def test_opencode_uses_migrated_anthropic_provider_and_surfaces_auth_error(tmp_path):
    """No external service is contacted; OpenCode talks only to this local mock."""
    if not shutil.which('npx'):
        pytest.skip('npx is required for the OpenCode CLI integration test')

    from core.cc_migrator import extract_profile
    from core.config_writer import generate_config

    _AuthFailingAnthropicGateway.requests = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), _AuthFailingAnthropicGateway)
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

        (tmp_path / 'opencode.json').write_text(generate_config(State()), encoding='utf-8')
        # npm exposes npx as a .cmd shim on Windows; invoke it through cmd so
        # the test is portable across Python's Windows process launcher.
        command = ('npx --yes opencode-ai run --model '
                   'claude-migration/mock-claude-model hello')
        result = subprocess.run(
            [os.environ.get('ComSpec', 'cmd.exe'), '/d', '/s', '/c', command],
            cwd=tmp_path, text=True, capture_output=True, timeout=90,
        )
        output = f'{result.stdout}\n{result.stderr}'.lower()

        assert _AuthFailingAnthropicGateway.requests, output
        request = _AuthFailingAnthropicGateway.requests[0]
        assert request['path'] == '/v1/messages'
        assert request['x_api_key'] == 'mock-invalid-token'
        assert result.returncode != 0
        assert any(term in output for term in ('authentication', 'unauthorized', 'invalid token', '401')), output
        assert 'not found' not in output
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_opencode_uses_openai_compatible_v1_and_surfaces_auth_error(tmp_path):
    """Covers vLLM and any standard OpenAI-compatible /v1 gateway."""
    if not shutil.which('npx'):
        pytest.skip('npx is required for the OpenCode CLI integration test')

    from core.config_writer import generate_config

    _AuthFailingAnthropicGateway.requests = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), _AuthFailingAnthropicGateway)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f'http://127.0.0.1:{server.server_port}/v1'
        endpoint = base_url

        class State:
            provider_name = ''
            display_name = ''
            api_key = 'mock-invalid-token'
            base_url = endpoint
            api_style = ''
            model_id = 'mock-vllm-model'
            model_name = 'Mock vLLM model'
            reasoning = True
            thinking = True

        (tmp_path / 'opencode.json').write_text(generate_config(State()), encoding='utf-8')
        command = 'npx --yes opencode-ai run --model vllm/mock-vllm-model hello'
        result = subprocess.run(
            [os.environ.get('ComSpec', 'cmd.exe'), '/d', '/s', '/c', command],
            cwd=tmp_path, text=True, capture_output=True, timeout=90,
        )
        output = f'{result.stdout}\n{result.stderr}'.lower()

        assert _AuthFailingAnthropicGateway.requests, output
        request = _AuthFailingAnthropicGateway.requests[0]
        assert request['path'] == '/v1/chat/completions'
        assert request['authorization'] == 'Bearer mock-invalid-token'
        assert result.returncode != 0
        assert any(term in output for term in ('authentication', 'unauthorized', 'invalid token', '401')), output
        assert 'not found' not in output
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_opencode_runs_successfully_against_local_openai_compatible_mock(tmp_path):
    """A real OpenCode process reaches a local vLLM-style mock without any key."""
    if not shutil.which('npx'):
        pytest.skip('npx is required for the OpenCode CLI integration test')

    from core.config_writer import generate_config

    _SuccessfulOpenAIGateway.requests = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), _SuccessfulOpenAIGateway)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f'http://127.0.0.1:{server.server_port}/v1'

        class State:
            provider_name = ''
            display_name = ''
            api_key = 'mock-valid-token'
            base_url = endpoint
            api_style = ''
            model_id = 'mock-vllm-model'
            model_name = 'Mock vLLM model'
            reasoning = True
            thinking = True

        (tmp_path / 'opencode.json').write_text(generate_config(State()), encoding='utf-8')
        command = 'npx --yes opencode-ai run --model vllm/mock-vllm-model hello'
        result = subprocess.run(
            [os.environ.get('ComSpec', 'cmd.exe'), '/d', '/s', '/c', command],
            cwd=tmp_path, text=True, capture_output=True, timeout=90,
        )
        output = f'{result.stdout}\n{result.stderr}'.lower()

        assert result.returncode == 0, output
        assert _SuccessfulOpenAIGateway.requests
        assert _SuccessfulOpenAIGateway.requests[0]['path'] == '/v1/chat/completions'
        assert 'mock agent success' in output
    finally:
        server.shutdown()
        thread.join(timeout=2)
