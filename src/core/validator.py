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
from pathlib import Path
from typing import Callable, Optional
import requests

from core.validation_result import ValidationResult, Status

# ── Strategy registry ─────────────────────────────────────────────────────────

TEST_STRATEGIES: dict[str, Callable] = {}


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
                # Don't retry client errors (4xx) — they won't fix themselves
                status_code = last_result.metadata.get('status_code', 0) \
                    if isinstance(last_result.metadata, dict) else 0
                if 400 <= status_code < 500:
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
            message=f'连接超时: {url}', detail=f'Timeout after {timeout[1]}s',
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
    base = url.rstrip('/')
    if not base.endswith('/v1'):
        base = f'{base}/v1'
    endpoint = f'{base}/chat/completions'
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
            message=f'连接超时: {endpoint}', detail=f'Timeout after {timeout[1]}s',
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
    """Anthropic compatible format: POST /v1/messages."""
    base = url.rstrip('/')
    if not base.endswith('/v1'):
        base = f'{base}/v1'
    endpoint = f'{base}/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
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
            message=f'连接超时: {endpoint}', detail=f'Timeout after {timeout[1]}s',
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
        return data.get('choices', [{}])[0].get('message', {}).get('content', '')
    if strategy == 'anthropic_compatible':
        return data.get('content', [{}])[0].get('text', '')
    return ''


def _get_strategy_func(config: dict) -> Callable:
    """Resolve the strategy function from config."""
    strategy = config.get('test_strategy', 'anthropic_compatible')
    return TEST_STRATEGIES.get(strategy, _test_anthropic_compatible)


# ── Public API ────────────────────────────────────────────────────────────────

def test_endpoint(base_url: str, api_key: str, config: dict = None) -> ValidationResult:
    """Test API endpoint connectivity using the provider's strategy.

    Args:
        base_url: The API base URL.
        api_key: The API key.
        config: Provider config (auto-detected if None).

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
    return wrapped(base_url, api_key, 'connectivity-test', config)


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
    commands = [
        ['opencode', 'run', test_prompt],
        ['opencode', 'run', '--print-logs', test_prompt],
    ]
    start = time.perf_counter()

    if not shutil.which('opencode'):
        return ValidationResult(
            name='cli', status=Status.FAILED,
            duration_ms=int((time.perf_counter() - start) * 1000),
            message='OpenCode CLI 未在 PATH 中找到', detail=None,
            suggestion='OpenCode 未安装 — 请返回上一步先安装 OpenCode',
            metadata={'available': False})

    last_error = ''
    for cmd in commands:
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env={**os.environ, 'NO_COLOR': '1', 'CI': '1', 'FORCE_COLOR': '0'},
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
                ok = proc.returncode == 0
                return ValidationResult(
                    name='cli',
                    status=Status.SUCCESS if ok else Status.FAILED,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    message=f'CLI 退出码 {proc.returncode} {"✓" if ok else "✗"}',
                    detail=combined[-1000:],
                    suggestion=(None if ok else
                                "CLI 失败 — 运行 'opencode doctor' 检查配置"),
                    metadata={'command': ' '.join(cmd), 'exit_code': proc.returncode})
        except Exception as e:
            last_error = str(e)
            continue

    return ValidationResult(
        name='cli', status=Status.FAILED,
        duration_ms=int((time.perf_counter() - start) * 1000),
        message='OpenCode CLI 查询失败', detail=last_error,
        suggestion="CLI 错误 — 用 'npm list -g opencode-ai' 检查安装",
        metadata={'error': last_error})


def test_config_written() -> ValidationResult:
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

    return ValidationResult(
        name='config', status=Status.SUCCESS,
        duration_ms=int((time.perf_counter() - start) * 1000),
        message=f'配置文件已写入: {config_path}',
        detail=content[:500] if len(content) > 500 else content,
        suggestion=None,
        metadata={'path': str(config_path), 'size': len(content)})


def read_config_file() -> str:
    """Read the generated opencode.jsonc content (empty string if missing)."""
    config_path = Path.home() / '.config' / 'opencode' / 'opencode.jsonc'
    if config_path.exists():
        try:
            return config_path.read_text(encoding='utf-8')
        except Exception:
            pass
    return ''
