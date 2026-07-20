"""Strategy-pattern validators for different provider API formats.

Each strategy knows how to test a specific API format:
- direct_post: Alibaba Coding Plan (POST to baseURL, no path append)
- openai_compatible: OpenAI / DeepSeek format (/v1/chat/completions)
- anthropic_compatible: Anthropic format (/v1/messages)

All public functions return ValidationResult objects with status, message,
detail, and actionable suggestions for failures.
"""
import subprocess
import os
import time
import shutil
import json
import re
from pathlib import Path
from typing import Callable, Optional
import requests

from core.validation_result import ValidationResult, Status
from core.detector import detect_opencode, detect_npm
from core.config_writer import _clean_jsonc, sanitize_model_id

# ── Strategy registry ─────────────────────────────────────────────────────────

TEST_STRATEGIES: dict[str, Callable] = {}


def _openai_chat_endpoint(url: str) -> str:
    """Return the Chat Completions route without rewriting valid version paths.

    Most OpenAI-compatible services use ``/v1``.  A few official Chinese
    services (for example Qianfan) use ``/v2``.  The former implementation
    always appended ``/v1`` unless the URL already ended in that exact string,
    turning ``.../v2`` into the invalid ``.../v2/v1/chat/completions``.
    """
    base = url.rstrip('/')
    if not re.search(r'/v\d+(?:\.\d+)?$', base, re.IGNORECASE):
        base = f'{base}/v1'
    return f'{base}/chat/completions'


def register_strategy(name: str):
    """Decorator to register a test strategy."""
    def decorator(func: Callable) -> Callable:
        TEST_STRATEGIES[name] = func
        return func
    return decorator


def with_retry(config: dict):
    """Decorator adding retry with exponential backoff.

    Retries on network errors and 5xx server errors, but NOT on 4xx client
    errors (auth/bad-request) since those won't succeed on retry.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> ValidationResult:
            retry_config = config.get('retry', {'times': 1, 'backoff': 1.0})
            max_attempts = retry_config.get('times', 1)
            backoff = retry_config.get('backoff', 1.0)

            last_result = None
            for attempt in range(max_attempts):
                last_result = func(*args, **kwargs)
                if last_result.ok:
                    return last_result
                # Most client errors will not fix themselves. HTTP 429 is a
                # transient rate limit and must use the configured backoff.
                status_code = last_result.metadata.get('status_code', 0) \
                    if isinstance(last_result.metadata, dict) else 0
                if 400 <= status_code < 500 and status_code != 429:
                    return last_result
                if attempt < max_attempts - 1:
                    time.sleep(backoff * (2 ** attempt))
            return last_result
        return wrapper
    return decorator


# ── Strategy implementations ──────────────────────────────────────────────────

@register_strategy('direct_post')
def _test_direct_post(url: str, api_key: str, model_id: str, config: dict,
                      max_tokens: int = 1) -> ValidationResult:
    """POST directly to baseURL — used by Alibaba Coding Plan (no path append)."""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        **config.get('headers', {}),
    }
    body = {
        'model': model_id,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': 'hi' if max_tokens <= 1
                      else 'Say hello in one word.'}],
    }
    timeout = config.get('timeout', (5, 15))
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    except requests.Timeout:
        return ValidationResult(
            name='direct_post', status=Status.FAILED, duration_ms=0,
            message=f'连接超时 (timeout): {url}', detail=f'Timeout after {timeout[1]}s',
            suggestion='网络超时 — 检查网络连接或代理设置（阿里需关闭 VPN/代理）',
            metadata={'error': 'timeout'})
    except requests.ConnectionError as e:
        return ValidationResult(
            name='direct_post', status=Status.FAILED, duration_ms=0,
            message=f'无法连接: {url}', detail=str(e),
            suggestion='连接被拒绝 — 检查 Endpoint 地址是否正确',
            metadata={'error': 'connection'})
    except Exception as e:
        return ValidationResult(
            name='direct_post', status=Status.FAILED, duration_ms=0,
            message=f'请求异常: {e}', detail=str(e),
            suggestion='未知错误 — 查看日志详情',
            metadata={'error': str(e)})

    return _build_http_result(resp, url, model_id, 'direct_post')


@register_strategy('openai_compatible')
def _test_openai_compatible(url: str, api_key: str, model_id: str, config: dict,
                            max_tokens: int = 1) -> ValidationResult:
    """OpenAI compatible format: POST /v1/chat/completions."""
    endpoint = _openai_chat_endpoint(url)
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        **config.get('headers', {}),
    }
    body = {
        'model': model_id,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': 'hi' if max_tokens <= 1
                      else 'Say hello in one word.'}],
    }
    timeout = config.get('timeout', (5, 30))
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
    except requests.Timeout:
        return ValidationResult(
            name='openai', status=Status.FAILED, duration_ms=0,
            message=f'连接超时 (timeout): {endpoint}', detail=f'Timeout after {timeout[1]}s',
            suggestion='网络超时 — 检查网络连接或代理设置',
            metadata={'error': 'timeout'})
    except requests.ConnectionError as e:
        return ValidationResult(
            name='openai', status=Status.FAILED, duration_ms=0,
            message=f'无法连接: {endpoint}', detail=str(e),
            suggestion='连接被拒绝 — 检查 Base URL 是否正确',
            metadata={'error': 'connection'})
    except Exception as e:
        return ValidationResult(
            name='openai', status=Status.FAILED, duration_ms=0,
            message=f'请求异常: {e}', detail=str(e),
            suggestion='未知错误 — 查看日志详情',
            metadata={'error': str(e)})

    return _build_http_result(resp, endpoint, model_id, 'openai_compatible')


@register_strategy('anthropic_compatible')
def _test_anthropic_compatible(url: str, api_key: str, model_id: str, config: dict,
                               max_tokens: int = 1) -> ValidationResult:
    """Anthropic compatible format: POST /v1/messages.

    Sends both `Authorization: Bearer` and `x-api-key` — the standard Anthropic
    API accepts either, and major Anthropic-compatible providers (阿里百炼 /
    智谱 GLM / DeepSeek) document `x-api-key` as their preferred auth header.
    Sending both maximizes compatibility.
    """
    base = url.rstrip('/')
    if not base.endswith('/v1'):
        base = f'{base}/v1'
    endpoint = f'{base}/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
        **config.get('headers', {}),
    }
    body = {
        'model': model_id,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': 'hi' if max_tokens <= 1
                      else 'Say hello in one word.'}],
    }
    timeout = config.get('timeout', (5, 30))
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
    except requests.Timeout:
        return ValidationResult(
            name='anthropic', status=Status.FAILED, duration_ms=0,
            message=f'连接超时 (timeout): {endpoint}', detail=f'Timeout after {timeout[1]}s',
            suggestion='网络超时 — 检查网络连接或代理设置',
            metadata={'error': 'timeout'})
    except requests.ConnectionError as e:
        return ValidationResult(
            name='anthropic', status=Status.FAILED, duration_ms=0,
            message=f'无法连接: {endpoint}', detail=str(e),
            suggestion='连接被拒绝 — 检查 Base URL 是否正确',
            metadata={'error': 'connection'})
    except Exception as e:
        return ValidationResult(
            name='anthropic', status=Status.FAILED, duration_ms=0,
            message=f'请求异常: {e}', detail=str(e),
            suggestion='未知错误 — 查看日志详情',
            metadata={'error': str(e)})

    return _build_http_result(resp, endpoint, model_id, 'anthropic_compatible')


def _build_http_result(resp, url: str, model_id: str, strategy: str) -> ValidationResult:
    """Build a ValidationResult from an HTTP response with smart suggestions."""
    code = resp.status_code
    name_prefix = strategy.split('_')[0]

    # 5xx server error
    if code >= 500:
        return ValidationResult(
            name=name_prefix, status=Status.FAILED, duration_ms=0,
            message=f'服务器错误 (HTTP {code})', detail=resp.text[:500],
            suggestion='服务端错误 — 检查 Provider 状态页或稍后重试',
            metadata={'status_code': code, 'url': url})

    # 4xx client error
    if code == 401 or code == 403:
        return ValidationResult(
            name=name_prefix, status=Status.FAILED, duration_ms=0,
            message=f'认证失败 (HTTP {code})', detail=resp.text[:500],
            suggestion='API Key 无效或权限不足 — 检查 opencode.jsonc 中的 apiKey',
            metadata={'status_code': code})
    if code == 404:
        return ValidationResult(
            name=name_prefix, status=Status.FAILED, duration_ms=0,
            message=f'地址不存在 (HTTP 404)', detail=resp.text[:500],
            suggestion='Endpoint 地址错误 — 阿里 Coding Plan 应使用 '
                       'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
            metadata={'status_code': code})
    if code == 429:
        return ValidationResult(
            name=name_prefix, status=Status.FAILED, duration_ms=0,
            message='请求过于频繁 (HTTP 429)', detail=resp.text[:500],
            suggestion='模型服务暂时限流，验证器会自动退避重试；仍失败时请稍后再试。',
            metadata={'status_code': code, 'url': url})
    if 400 <= code < 500:
        return ValidationResult(
            name=name_prefix, status=Status.FAILED, duration_ms=0,
            message=f'请求错误 (HTTP {code})', detail=resp.text[:500],
            suggestion=f'请求被拒 (HTTP {code}) — 检查模型 ID「{model_id}」是否正确',
            metadata={'status_code': code})

    # 2xx success
    content = _extract_content(resp, strategy)
    if content:
        return ValidationResult(
            name=name_prefix, status=Status.SUCCESS, duration_ms=0,
            message=f'响应成功: {content[:80]}', detail=None, suggestion=None,
            metadata={'status_code': code, 'response': content})

    # 2xx but empty — still reachable (connectivity test passed)
    return ValidationResult(
        name=name_prefix,
        status=Status.SUCCESS if code == 200 else Status.WARNING,
        duration_ms=0, message=f'可达 (HTTP {code})',
        detail=f'URL: {url}', suggestion=None,
        metadata={'status_code': code, 'url': url})


def _extract_content(resp, strategy: str) -> str:
    """Extract response text based on strategy format."""
    try:
        data = resp.json()
    except Exception:
        return ''
    if strategy == 'openai_compatible':
        message = data.get('choices', [{}])[0].get('message', {})
        return message.get('content', '') or message.get('reasoning_content', '')
    if strategy == 'anthropic_compatible':
        return data.get('content', [{}])[0].get('text', '')
    return ''


def _get_strategy_func(config: dict) -> Callable:
    """Resolve the strategy function from config."""
    strategy = config.get('test_strategy', 'anthropic_compatible')
    return TEST_STRATEGIES.get(strategy, _test_anthropic_compatible)


# ── Public API ────────────────────────────────────────────────────────────────

def test_endpoint(base_url: str, api_key: str, config: dict = None,
                  model_id: str = '') -> ValidationResult:
    """Test API endpoint connectivity using the provider's strategy.

    Args:
        base_url: The API base URL.
        api_key: The API key.
        config: Provider config (auto-detected if None).
        model_id: Actual selected model. Endpoint requests are model-aware for
            Anthropic-compatible gateways, which reject placeholder IDs.

    Returns:
        ValidationResult with connectivity status and suggestions.
    """
    if config is None:
        from core.providers import get_provider_config
        config = get_provider_config(base_url)

    strategy_func = _get_strategy_func(config)
    # Endpoint test: minimal payload, just check reachability
    wrapped = with_retry(config)(
        lambda url, key, model, cfg: strategy_func(url, key, model, cfg, max_tokens=1)
    )
    effective_model = sanitize_model_id(model_id) or config.get('default_test_model', '') or 'connectivity-test'
    result = wrapped(base_url, api_key, effective_model, config)
    # A deliberately fake key is a valid reachability result: the request has
    # reached the official API gateway, passed DNS/TLS/routing and was rejected
    # by its authentication layer.  Keep model inference strict, but present
    # this endpoint-only probe as a successful connectivity check.
    code = result.metadata.get('status_code') if isinstance(result.metadata, dict) else None
    if code in (401, 403):
        return ValidationResult(
            name='endpoint', status=Status.SUCCESS, duration_ms=result.duration_ms,
            message=f'端点可达，认证层已响应 (HTTP {code})', detail=result.detail,
            suggestion='端点和协议正常；填入有效 API Key 后再执行模型推理测试。',
            metadata={**result.metadata, 'model': effective_model,
                      'reachable_via_auth_error': True})
    return ValidationResult(
        name='endpoint', status=result.status, duration_ms=result.duration_ms,
        message=result.message, detail=result.detail, suggestion=result.suggestion,
        metadata={**result.metadata, 'model': effective_model})


def test_model(base_url: str, api_key: str, model_id: str,
               config: dict = None) -> ValidationResult:
    """Test model inference using the provider's strategy.

    Args:
        base_url: The API base URL.
        api_key: The API key.
        model_id: The model ID to test.
        config: Provider config (auto-detected if None).

    Returns:
        ValidationResult with model inference status and suggestions.
    """
    if config is None:
        from core.providers import get_provider_config
        config = get_provider_config(base_url)

    strategy_func = _get_strategy_func(config)
    # Model test: ask for a short reply to verify the model responds
    wrapped = with_retry(config)(
        lambda url, key, model, cfg: strategy_func(url, key, model, cfg, max_tokens=50)
    )
    result = wrapped(base_url, api_key, model_id, config)
    # Rename to 'model' for the report regardless of strategy
    return ValidationResult(
        name='model', status=result.status, duration_ms=result.duration_ms,
        message=result.message, detail=result.detail, suggestion=result.suggestion,
        metadata=result.metadata)


def test_opencode_cli(model_id: str = '', timeout: int = 60) -> ValidationResult:
    """Test OpenCode CLI by running a real non-interactive query.

    Args:
        model_id: Optional model hint (unused in query but for diagnostics).
        timeout: Command timeout in seconds.

    Returns:
        ValidationResult with CLI status, raw output, and suggestions.
    """
    test_prompt = 'Reply with exactly one word: hello'
    cli_info = detect_opencode()
    cli_path = cli_info.get('opencode_path', '')
    if not cli_path or cli_path == 'npm global' or not os.path.isfile(cli_path):
        npm_path = detect_npm().get('npm_path', '')
        candidate = os.path.join(os.path.dirname(npm_path), 'opencode.cmd') if npm_path else ''
        cli_path = candidate if os.path.isfile(candidate) else ''
    start = time.perf_counter()

    if not cli_path:
        return ValidationResult(
            name='cli', status=Status.FAILED,
            duration_ms=int((time.perf_counter() - start) * 1000),
            message='OpenCode CLI 未在 PATH 中找到', detail=None,
            suggestion='OpenCode 未安装或不在 PATH。请点击“一键安装 OpenCode”；人工兜底：npm list -g opencode-ai --depth=0。',
            metadata={'available': False})

    def make_command(args: list[str]) -> list[str]:
        if os.name == 'nt' and cli_path.lower().endswith(('.cmd', '.bat')):
            shell_line = 'call ' + subprocess.list2cmdline([cli_path] + args)
            return [os.environ.get('ComSpec', 'cmd.exe'), '/d', '/s', '/c', shell_line]
        return [cli_path] + args

    run_args = ['run', '--format', 'json']
    if model_id:
        run_args.extend(['--model', model_id])
    run_args.append(test_prompt)
    commands = [
        make_command(run_args),
        make_command(['run', '--print-logs', *run_args[1:]]),
    ]

    last_error = ''
    for cmd in commands:
        try:
            # The validation page owns all output.  On Windows, launching a
            # .cmd shim through cmd.exe without this flag briefly creates a
            # visible console window for every connection test.
            popen_kwargs = {}
            if os.name == 'nt':
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env={**os.environ, 'NO_COLOR': '1', 'CI': '1', 'FORCE_COLOR': '0'},
                **popen_kwargs,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return ValidationResult(
                    name='cli', status=Status.FAILED,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    message='CLI 命令超时', detail=f'Command: {" ".join(cmd)}',
                    suggestion='CLI 超时 — 可能模型未响应，检查网络或模型配置',
                    metadata={'timeout': timeout})

            parts = []
            if stderr.strip():
                parts.append(stderr.strip())
            if stdout.strip():
                parts.append(stdout.strip())
            combined = '\n'.join(parts)

            if combined:
                # A zero exit code with only ``> build · model`` is not a
                # model response. Require at least one non-status text line.
                clean_output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', combined)
                json_events = []
                for line in clean_output.splitlines():
                    try:
                        json_events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                visible_lines = [
                    line.strip() for line in clean_output.splitlines()
                    if line.strip() and not line.lstrip().startswith(('>', 'timestamp=', 'level='))
                ]
                if json_events:
                    # JSON mode is the authoritative CLI protocol. A complete
                    # turn must contain generated output tokens; a bare
                    # ``step_finish`` with output=0 is explicitly a failure.
                    generated_tokens = sum(
                        int(event.get('part', {}).get('tokens', {}).get('output', 0) or 0)
                        for event in json_events if isinstance(event, dict)
                    )
                    has_model_text = generated_tokens > 0
                else:
                    # Retain compatibility with older CLI shims used in tests.
                    has_model_text = bool(visible_lines)
                ok = proc.returncode == 0 and has_model_text
                return ValidationResult(
                    name='cli',
                    status=Status.SUCCESS if ok else Status.FAILED,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    message=('CLI 已收到模型文本 ✓' if ok else
                             f'CLI 未收到模型文本（退出码 {proc.returncode}）'),
                    detail=combined[-1000:],
                    suggestion=(None if ok else
                                "CLI 未返回模型文本，不能视为验证成功。运行 opencode run --print-logs \"hello\" 检查模型、密钥与接口。"),
                    metadata={'command': ' '.join(cmd), 'exit_code': proc.returncode,
                              'cli_path': cli_path, 'has_model_text': has_model_text})
        except Exception as e:
            last_error = str(e)
            continue

    return ValidationResult(
        name='cli', status=Status.FAILED,
        duration_ms=int((time.perf_counter() - start) * 1000),
        message='OpenCode CLI 查询失败', detail=last_error,
        suggestion="CLI 无法启动。人工兜底：npm list -g opencode-ai --depth=0；确认后执行 opencode --version。",
        metadata={'error': last_error})


def test_config_written(expected_model_ref: str = '') -> ValidationResult:
    """Check if opencode.jsonc config file exists and is readable."""
    start = time.perf_counter()
    config_path = Path.home() / '.config' / 'opencode' / 'opencode.jsonc'

    if not config_path.exists():
        return ValidationResult(
            name='config', status=Status.FAILED,
            duration_ms=int((time.perf_counter() - start) * 1000),
            message='配置文件未找到', detail=f'期望路径: {config_path}',
            suggestion='配置未写入 — 请返回重新生成配置',
            metadata={'exists': False, 'expected_path': str(config_path)})

    try:
        content = config_path.read_text(encoding='utf-8')
    except Exception as e:
        return ValidationResult(
            name='config', status=Status.WARNING,
            duration_ms=int((time.perf_counter() - start) * 1000),
            message=f'配置文件无法读取: {e}', detail=str(e),
            suggestion='配置文件权限问题 — 检查文件权限',
            metadata={'path': str(config_path)})

    try:
        config = json.loads(_clean_jsonc(content))
        providers = config.get('provider', {})
        model_ref = str(config.get('model', ''))
        if not isinstance(providers, dict) or not providers or '/' not in model_ref:
            raise ValueError('缺少 provider 或 model')
        provider_id, model_id = model_ref.split('/', 1)
        if provider_id not in providers or not model_id or sanitize_model_id(model_id) != model_id:
            raise ValueError('模型 ID 无效或包含终端格式字符')
        models = providers[provider_id].get('models', {})
        if model_id not in models:
            raise ValueError('默认模型未在 provider.models 中声明')
        if expected_model_ref and model_ref != expected_model_ref:
            raise ValueError(f'当前配置模型为 {model_ref}，预期为 {expected_model_ref}')
    except (ValueError, json.JSONDecodeError) as exc:
        return ValidationResult(
            name='config', status=Status.FAILED,
            duration_ms=int((time.perf_counter() - start) * 1000),
            message=f'配置语义校验失败: {exc}', detail=f'路径: {config_path}',
            suggestion='请返回模型配置页重新保存。人工兜底：检查 model 与 provider.models 的模型 ID 必须完全一致。',
            metadata={'path': str(config_path), 'valid': False})

    return ValidationResult(
        name='config', status=Status.SUCCESS,
        duration_ms=int((time.perf_counter() - start) * 1000),
        message=f'配置文件已写入: {config_path}',
        detail=f'provider={provider_id}; model={model_ref}',
        suggestion=None,
        metadata={'path': str(config_path), 'size': len(content), 'provider': provider_id,
                  'model': model_ref, 'valid': True})


def read_config_file() -> str:
    """Read the generated opencode.jsonc content (empty string if missing)."""
    config_path = Path.home() / '.config' / 'opencode' / 'opencode.jsonc'
    if config_path.exists():
        try:
            return config_path.read_text(encoding='utf-8')
        except Exception:
            pass
    return ''


def run_all(base_url: str, api_key: str, model_id: str) -> list:
    """Backward-compatible sequential validation entry point.

    The UI uses :class:`ValidationEngine` for sequential, typed reporting. This
    helper keeps scripts written for the original public API working.
    """
    return [test_model(base_url, api_key, model_id), test_config_written(),
            test_opencode_cli(model_id)]


# These are runtime API functions, not pytest test cases.  Some e2e scripts
# import them directly, which otherwise makes pytest try to inject fixtures.
test_endpoint.__test__ = False
test_model.__test__ = False
test_opencode_cli.__test__ = False
