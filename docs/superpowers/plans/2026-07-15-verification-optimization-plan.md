# Verification Flow Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement parallel validation with retry logic, provider-specific strategies, granular progress UI, and diagnostic suggestions.

**Architecture:** Abstract validation into a provider-aware engine with strategy pattern for different API formats, parallel execution via ThreadPoolExecutor, unified result structures, and enhanced UI with real-time progress and actionable error messages.

**Tech Stack:** Python 3.10, tkinter (8-bit pixel style), requests, concurrent.futures, dataclasses

## Global Constraints

- Python 3.10+ with type hints
- Preserve existing 8-bit pixel UI theme (COLORS, FONTS from ui.theme)
- Thread-safe: validation runs in background threads, UI updates via `after()`
- Backward compatible: `run_all()` function signature preserved
- All provider configs must include: test_strategy, timeout, retry, default_test_model
- Progress callback: `on_progress(name: str, value: float)` where value is 0.0-1.0

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/core/providers.py` | Provider configurations (DashScope, DeepSeek, OpenAI, Anthropic) with test strategies, timeouts, retry policies, and available models |
| `src/core/validation_result.py` | Unified result structures: Status enum, ValidationResult dataclass, ValidationReport dataclass |
| `src/core/validation_engine.py` | Parallel execution engine with ThreadPoolExecutor, progress callbacks, and task orchestration |
| `src/core/validator.py` | Strategy-pattern validation functions for different API formats (direct_post, openai_compatible, anthropic_compatible) |
| `src/ui/pages/verify.py` | Enhanced verification page with progress bar, status labels, diagnostic suggestion boxes |

---

### Task 1: Create Provider Configurations

**Files:**
- Create: `src/core/providers.py`
- Test: `tests/core/test_providers.py`

**Interfaces:**
- Produces: `PROVIDER_CONFIG: dict[str, dict]`, `get_provider_config(base_url: str) -> dict`, `resolve_test_model(config: dict, user_model: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_providers.py
def test_get_provider_config_dashscope():
    config = get_provider_config('https://coding.dashscope.aliyuncs.com/apps/anthropic/v1')
    assert config['test_strategy'] == 'direct_post'
    assert config['timeout'] == (5, 15)
    assert config['default_test_model'] == 'qwen3.7-plus'
    assert 'qwen3.7-plus' in config['available_models']

def test_resolve_test_model_prefers_user():
    config = {'default_test_model': 'qwen3.7-plus'}
    assert resolve_test_model(config, 'user-model') == 'user-model'

def test_resolve_test_model_fallback():
    config = {'default_test_model': 'qwen3.7-plus'}
    assert resolve_test_model(config, '') == 'qwen3.7-plus'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_providers.py -v`
Expected: FAIL with "get_provider_config not defined"

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/providers.py
"""Provider configurations for validation engine."""

PROVIDER_CONFIG = {
    'dashscope': {
        'name': 'Alibaba Coding Plan',
        'test_strategy': 'direct_post',
        'timeout': (5, 15),
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {'anthropic-version': '2023-06-01'},
        'default_test_model': 'qwen3.7-plus',
        'available_models': [
            'qwen3.7-plus', 'qwen3.6-plus', 'qwen3.5-plus',
            'qwen3-max-2026-01-23', 'qwen3-coder-next', 'qwen3-coder-plus',
            'MiniMax-M2.5', 'glm-5', 'glm-4.7', 'kimi-k2.5'
        ],
    },
    'deepseek': {
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'deepseek-chat',
        'available_models': ['deepseek-chat', 'deepseek-reasoner'],
    },
    'openai': {
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'default_test_model': 'gpt-4o',
        'available_models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    },
    'anthropic': {
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'default_test_model': 'claude-sonnet-4',
        'available_models': ['claude-opus-4', 'claude-sonnet-4', 'claude-haiku-4'],
    },
    'default': {
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'default_test_model': 'claude-sonnet-4',
    }
}

def _detect_provider(base_url: str) -> str:
    """Detect provider from base URL."""
    url_lower = base_url.lower()
    if 'dashscope' in url_lower or 'aliyun' in url_lower:
        return 'dashscope'
    if 'deepseek' in url_lower:
        return 'deepseek'
    if 'openai.com' in url_lower:
        return 'openai'
    if 'anthropic' in url_lower:
        return 'anthropic'
    return 'default'

def get_provider_config(base_url: str) -> dict:
    """Get provider config based on base URL."""
    provider = _detect_provider(base_url)
    return PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG['default'])

def resolve_test_model(provider_config: dict, user_model_id: str) -> str:
    """Resolve test model: prefer user config, fallback to provider default."""
    if user_model_id and user_model_id.strip():
        return user_model_id.strip()
    return provider_config.get('default_test_model', 'unknown')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_providers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_providers.py src/core/providers.py
git commit -m "feat: add provider configurations with strategies and retry policies"
```

---

### Task 2: Create Validation Result Structures

**Files:**
- Create: `src/core/validation_result.py`
- Test: `tests/core/test_validation_result.py`

**Interfaces:**
- Produces: `Status(Enum)`, `ValidationResult`, `ValidationReport`, `format_duration(ms: int) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_validation_result.py
from src.core.validation_result import Status, ValidationResult, ValidationReport

def test_status_enum():
    assert Status.SUCCESS.value == 'success'
    assert Status.FAILED.value == 'failed'

def test_validation_result_ok():
    r = ValidationResult(name='test', status=Status.SUCCESS, duration_ms=100,
                         message='ok', detail=None, suggestion=None, metadata={})
    assert r.ok is True
    
    r2 = ValidationResult(name='test', status=Status.FAILED, duration_ms=100,
                          message='fail', detail=None, suggestion=None, metadata={})
    assert r2.ok is False

def test_validation_report_get_failed():
    results = [
        ValidationResult('a', Status.SUCCESS, 0, '', None, None, {}),
        ValidationResult('b', Status.FAILED, 0, '', None, None, {}),
    ]
    report = ValidationReport(results, 100, Status.WARNING)
    failed = report.get_failed()
    assert len(failed) == 1
    assert failed[0].name == 'b'

def test_format_duration():
    from src.core.validation_result import format_duration
    assert format_duration(1500) == '1.5s'
    assert format_duration(100) == '100ms'
    assert format_duration(60000) == '60.0s'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_validation_result.py -v`
Expected: FAIL with import errors

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/validation_result.py
"""Unified validation result structures."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class Status(Enum):
    """Validation status enumeration."""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    WARNING = 'warning'

@dataclass
class ValidationResult:
    """Result of a single validation test."""
    name: str
    status: Status
    duration_ms: int
    message: str
    detail: Optional[str]
    suggestion: Optional[str]
    metadata: Dict[str, Any]
    
    @property
    def ok(self) -> bool:
        """True if status is SUCCESS or WARNING."""
        return self.status in (Status.SUCCESS, Status.WARNING)

@dataclass
class ValidationReport:
    """Complete validation report containing all test results."""
    results: list[ValidationResult]
    total_duration_ms: int
    overall_status: Status
    
    def get_failed(self) -> list[ValidationResult]:
        """Return all failed results."""
        return [r for r in self.results if r.status == Status.FAILED]
    
    def get_suggestions(self) -> list[str]:
        """Return all non-empty suggestions from failed tests."""
        suggestions = []
        for r in self.results:
            if r.status == Status.FAILED and r.suggestion:
                suggestions.append(r.suggestion)
        return suggestions

def format_duration(ms: int) -> str:
    """Format milliseconds to human readable string."""
    if ms < 1000:
        return f'{ms}ms'
    return f'{ms/1000:.1f}s'
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_validation_result.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_validation_result.py src/core/validation_result.py
git commit -m "feat: add unified validation result structures"
```

---

### Task 3: Create Validation Engine

**Files:**
- Create: `src/core/validation_engine.py`
- Modify: `src/app.py` (add imports for type hints if needed)
- Test: `tests/core/test_validation_engine.py` (mock tests)

**Interfaces:**
- Consumes: `ValidationResult`, `Status`, `get_provider_config`, `resolve_test_model`
- Produces: `ValidationEngine` class with `run_all() -> ValidationReport`, `on_progress: Callable[[str, float], None]`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_validation_engine.py
from unittest.mock import Mock, patch
from src.core.validation_engine import ValidationEngine
from src.core.validation_result import Status

def test_engine_initializes_with_state():
    state = Mock()
    state.base_url = 'https://api.example.com'
    state.api_key = 'test-key'
    state.model_id = 'test-model'
    
    engine = ValidationEngine(state)
    assert engine.state == state

def test_run_all_returns_report():
    state = Mock()
    state.base_url = 'https://api.example.com'
    state.api_key = 'test-key'
    state.model_id = 'test-model'
    state.provider_name = 'test'
    state.display_name = 'Test'
    state.reasoning = True
    state.thinking = True
    
    # Mock the actual test functions to avoid network calls
    with patch('src.core.validation_engine.test_endpoint') as mock_endpoint, \
         patch('src.core.validation_engine.test_model') as mock_model, \
         patch('src.core.validation_engine.test_opencode_cli') as mock_cli, \
         patch('src.core.validation_engine.test_config_written') as mock_config:
        
        from src.core.validation_result import ValidationResult
        mock_endpoint.return_value = ValidationResult(
            'endpoint', Status.SUCCESS, 100, 'ok', None, None, {}
        )
        mock_model.return_value = ValidationResult(
            'model', Status.SUCCESS, 200, 'ok', None, None, {}
        )
        mock_cli.return_value = ValidationResult(
            'cli', Status.SUCCESS, 300, 'ok', None, None, {}
        )
        mock_config.return_value = ValidationResult(
            'config', Status.SUCCESS, 50, 'ok', None, None, {}
        )
        
        engine = ValidationEngine(state)
        report = engine.run_all()
        
        assert len(report.results) == 4
        assert report.overall_status == Status.SUCCESS

def test_progress_callback_invoked():
    state = Mock()
    state.base_url = 'https://api.example.com'
    state.api_key = 'test-key'
    state.model_id = 'test-model'
    state.provider_name = 'test'
    state.display_name = 'Test'
    state.reasoning = True
    state.thinking = True
    
    progress_calls = []
    def on_progress(name, value):
        progress_calls.append((name, value))
    
    with patch('src.core.validation_engine.test_endpoint'), \
         patch('src.core.validation_engine.test_model'), \
         patch('src.core.validation_engine.test_opencode_cli'), \
         patch('src.core.validation_engine.test_config_written'):
        
        from src.core.validation_result import ValidationResult
        with patch('src.core.validation_engine.test_endpoint') as mock_ep:
            mock_ep.return_value = ValidationResult('ep', Status.SUCCESS, 0, '', None, None, {})
            with patch('src.core.validation_engine.test_model') as mock_m:
                mock_m.return_value = ValidationResult('m', Status.SUCCESS, 0, '', None, None, {})
                with patch('src.core.validation_engine.test_opencode_cli') as mock_c:
                    mock_c.return_value = ValidationResult('c', Status.SUCCESS, 0, '', None, None, {})
                    with patch('src.core.validation_engine.test_config_written') as mock_cfg:
                        mock_cfg.return_value = ValidationResult('cfg', Status.SUCCESS, 0, '', None, None, {})
                        
                        engine = ValidationEngine(state)
                        engine.on_progress = on_progress
                        engine.run_all()
                        
                        assert len(progress_calls) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_validation_engine.py -v`
Expected: FAIL with import errors

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/validation_engine.py
"""Parallel validation engine with progress callbacks."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from dataclasses import dataclass

from core.providers import get_provider_config, resolve_test_model
from core.validation_result import ValidationResult, ValidationReport, Status

# Import validators (will be refactored in Task 4)
from core.validator import test_endpoint, test_model, test_opencode_cli, test_config_written


@dataclass
class WizardState:
    """Minimal interface for state - actual import from app.py."""
    base_url: str
    api_key: str
    model_id: str
    provider_name: str = ''
    display_name: str = ''
    reasoning: bool = True
    thinking: bool = True


class ValidationEngine:
    """Parallel validation engine with provider-aware strategies.
    
    Usage:
        engine = ValidationEngine(state)
        engine.on_progress = lambda name, val: ui.update_progress(name, val)
        report = engine.run_all()
    """
    
    def __init__(self, state: WizardState):
        self.state = state
        self.provider_config = get_provider_config(state.base_url)
        self.on_progress: Optional[Callable[[str, float], None]] = None
    
    def _notify_progress(self, name: str, value: float):
        """Safely invoke progress callback."""
        if self.on_progress:
            try:
                self.on_progress(name, value)
            except Exception:
                pass
    
    def _run_with_timing(self, name: str, func, *args, **kwargs) -> ValidationResult:
        """Run a test function and measure duration."""
        start = time.time()
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict):
                # Convert old dict format to ValidationResult
                return ValidationResult(
                    name=name,
                    status=Status.SUCCESS if result.get('ok') else Status.FAILED,
                    duration_ms=int((time.time() - start) * 1000),
                    message=result.get('message', ''),
                    detail=result.get('detail'),
                    suggestion=result.get('suggestion'),
                    metadata={k: v for k, v in result.items() 
                             if k not in ('ok', 'message', 'detail', 'suggestion')}
                )
            return result
        except Exception as e:
            return ValidationResult(
                name=name,
                status=Status.FAILED,
                duration_ms=int((time.time() - start) * 1000),
                message=str(e)[:200],
                detail=str(e),
                suggestion=f"Check {name} configuration and network connectivity",
                metadata={}
            )
    
    def run_all(self) -> ValidationReport:
        """Run all validations in parallel with progress updates."""
        start_time = time.time()
        
        # Define tasks with their weights for progress calculation
        tasks = [
            ('endpoint', self._test_endpoint_wrapper, 0.25),
            ('model', self._test_model_wrapper, 0.25),
            ('cli', self._test_cli_wrapper, 0.25),
            ('config', self._test_config_wrapper, 0.25),
        ]
        
        results = []
        completed = 0
        
        # Notify start
        self._notify_progress('init', 0.0)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(func): (name, weight)
                for name, func, weight in tasks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                name, weight = future_to_task[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = ValidationResult(
                        name=name,
                        status=Status.FAILED,
                        duration_ms=0,
                        message=f'Task failed: {e}',
                        detail=str(e),
                        suggestion=f"{name} validation crashed - check logs",
                        metadata={}
                    )
                
                results.append(result)
                completed += 1
                progress = sum(t[2] for t in tasks[:completed])
                self._notify_progress(name, progress)
        
        # Sort results by task order for consistent display
        result_order = ['endpoint', 'model', 'cli', 'config']
        results.sort(key=lambda r: result_order.index(r.name) if r.name in result_order else 99)
        
        # Determine overall status
        failed_count = sum(1 for r in results if r.status == Status.FAILED)
        if failed_count == 0:
            overall = Status.SUCCESS
        elif failed_count == len(results):
            overall = Status.FAILED
        else:
            overall = Status.WARNING
        
        total_duration = int((time.time() - start_time) * 1000)
        
        self._notify_progress('complete', 1.0)
        
        return ValidationReport(results, total_duration, overall)
    
    def _test_endpoint_wrapper(self):
        """Wrapper for endpoint test with provider config."""
        return test_endpoint(
            self.state.base_url,
            self.state.api_key,
            self.provider_config
        )
    
    def _test_model_wrapper(self):
        """Wrapper for model test with resolved model ID."""
        model_id = resolve_test_model(self.provider_config, self.state.model_id)
        return test_model(
            self.state.base_url,
            self.state.api_key,
            model_id,
            self.provider_config
        )
    
    def _test_cli_wrapper(self):
        """Wrapper for CLI test."""
        return test_opencode_cli(self.state.model_id)
    
    def _test_config_wrapper(self):
        """Wrapper for config test."""
        return test_config_written()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_validation_engine.py -v`
Expected: PASS (may need to adjust imports)

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_validation_engine.py src/core/validation_engine.py
git commit -m "feat: add parallel validation engine with progress callbacks"
```

---

### Task 4: Refactor Validator with Strategy Pattern

**Files:**
- Modify: `src/core/validator.py` (complete rewrite)
- Test: `tests/core/test_validator.py`

**Interfaces:**
- Consumes: `Status`, `ValidationResult`, `PROVIDER_CONFIG` values
- Produces: `test_endpoint(base_url, api_key, config) -> ValidationResult`, `test_model(base_url, api_key, model_id, config) -> ValidationResult`, `test_opencode_cli(model_id) -> ValidationResult`, `test_config_written() -> ValidationResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_validator.py
from unittest.mock import Mock, patch
import pytest
from src.core.validator import test_endpoint, test_model, test_opencode_cli, test_config_written
from src.core.validation_result import ValidationResult, Status

def test_test_endpoint_success():
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        config = {'timeout': (5, 15), 'retry': {'times': 1}, 'headers': {}}
        result = test_endpoint('https://api.example.com', 'key', config)
        
        assert isinstance(result, (ValidationResult, dict))
        if isinstance(result, ValidationResult):
            assert result.status == Status.SUCCESS
        else:
            assert result['ok'] is True

def test_test_model_with_provider_config():
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Hello'}}]
        }
        mock_post.return_value = mock_response
        
        config = {'timeout': (5, 15), 'retry': {'times': 1}, 'headers': {}}
        result = test_model('https://api.example.com', 'key', 'model-id', config)
        
        assert isinstance(result, (ValidationResult, dict))

def test_test_config_written_returns_ok_when_exists(tmp_path, monkeypatch):
    # Mock the config path
    from pathlib import Path
    mock_config = tmp_path / '.config' / 'opencode' / 'opencode.jsonc'
    mock_config.parent.mkdir(parents=True)
    mock_config.write_text('{}')
    
    def mock_home():
        return tmp_path
    
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: tmp_path))
    
    result = test_config_written()
    assert result['ok'] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/core/test_validator.py -v`
Expected: FAIL - the validator doesn't have the new signature yet

- [ ] **Step 3: Write implementation with strategy pattern**

```python
# src/core/validator.py
"""Strategy-pattern validators for different provider API formats."""
import json
import subprocess
import os
import time
import shutil
from pathlib import Path
from typing import Callable
import requests

from core.validation_result import ValidationResult, Status

# Strategy registry
TEST_STRATEGIES: dict[str, Callable] = {}


def register_strategy(name: str):
    """Decorator to register a test strategy."""
    def decorator(func: Callable) -> Callable:
        TEST_STRATEGIES[name] = func
        return func
    return decorator


def with_retry(config: dict):
    """Decorator to add retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> ValidationResult:
            retry_config = config.get('retry', {'times': 1, 'backoff': 1.0})
            max_attempts = retry_config.get('times', 1)
            backoff = retry_config.get('backoff', 1.0)
            
            last_result = None
            for attempt in range(max_attempts):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    last_result = result
                    if result.ok:
                        return result
                    # Don't retry on 4xx client errors
                    if isinstance(result.metadata, dict):
                        status_code = result.metadata.get('status_code', 0)
                        if 400 <= status_code < 500:
                            return result
                except Exception as e:
                    duration_ms = int((time.time() - start) * 1000)
                    last_result = ValidationResult(
                        name=func.__name__,
                        status=Status.FAILED,
                        duration_ms=duration_ms,
                        message=str(e)[:200],
                        detail=str(e),
                        suggestion=f"Network or configuration error - will retry ({attempt + 1}/{max_attempts})" if attempt < max_attempts - 1 else "Check API endpoint and key",
                        metadata={'attempt': attempt + 1}
                    )
                
                if attempt < max_attempts - 1:
                    time.sleep(backoff * (2 ** attempt))
            
            return last_result
        return wrapper
    return decorator


@register_strategy('direct_post')
def _test_direct_post(url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """Direct POST to base URL - used by Alibaba Coding Plan."""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        **config.get('headers', {})
    }
    body = {
        'model': model_id,
        'max_tokens': 1,
        'messages': [{'role': 'user', 'content': 'hi'}]
    }
    
    timeout = config.get('timeout', (5, 15))
    
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        
        if resp.status_code < 500:
            return ValidationResult(
                name='endpoint',
                status=Status.SUCCESS if resp.status_code == 200 else Status.WARNING,
                duration_ms=0,  # Will be set by wrapper
                message=f'API reachable: {url} (HTTP {resp.status_code})',
                detail=f'Response: {resp.text[:500]}' if resp.status_code != 200 else None,
                suggestion=None if resp.status_code == 200 else f"HTTP {resp.status_code} - check API key if 401",
                metadata={'status_code': resp.status_code, 'url': url}
            )
        else:
            return ValidationResult(
                name='endpoint',
                status=Status.FAILED,
                duration_ms=0,
                message=f'Server error at {url} (HTTP {resp.status_code})',
                detail=resp.text[:500],
                suggestion="Server error - check provider status page",
                metadata={'status_code': resp.status_code}
            )
    except requests.Timeout:
        return ValidationResult(
            name='endpoint',
            status=Status.FAILED,
            duration_ms=0,
            message=f'Connection timeout at {url}',
            detail=f'Timeout after {timeout[1]}s',
            suggestion="Network timeout - check connection or proxy settings",
            metadata={'timeout': timeout}
        )
    except requests.ConnectionError as e:
        return ValidationResult(
            name='endpoint',
            status=Status.FAILED,
            duration_ms=0,
            message=f'Cannot connect to {url}',
            detail=str(e),
            suggestion="Connection refused - check URL and network",
            metadata={'error': 'connection'}
        )


@register_strategy('openai_compatible')
def _test_openai_compatible(url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """OpenAI compatible format: POST /v1/chat/completions."""
    base = url.rstrip('/')
    if not base.endswith('/v1'):
        base = f'{base}/v1'
    
    endpoint = f'{base}/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        **config.get('headers', {})
    }
    body = {
        'model': model_id,
        'max_tokens': 50,
        'messages': [{'role': 'user', 'content': 'Say hello in one word.'}]
    }
    
    timeout = config.get('timeout', (5, 30))
    
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            return ValidationResult(
                name='model',
                status=Status.SUCCESS,
                duration_ms=0,
                message=f'Model responded: {content[:100]}',
                detail=None,
                suggestion=None,
                metadata={'response': content}
            )
        else:
            return ValidationResult(
                name='model',
                status=Status.FAILED,
                duration_ms=0,
                message=f'HTTP {resp.status_code}',
                detail=resp.text[:500],
                suggestion=f"Model inference failed (HTTP {resp.status_code}) - check model ID",
                metadata={'status_code': resp.status_code}
            )
    except requests.Timeout:
        return ValidationResult(
            name='model',
            status=Status.FAILED,
            duration_ms=0,
            message='Model inference timeout',
            detail=f'Timeout after {timeout[1]}s',
            suggestion="Model inference timeout - try a faster model or check network",
            metadata={'timeout': timeout}
        )
    except Exception as e:
        return ValidationResult(
            name='model',
            status=Status.FAILED,
            duration_ms=0,
            message=str(e)[:200],
            detail=str(e),
            suggestion="Unexpected error - check logs",
            metadata={'error': str(e)}
        )


@register_strategy('anthropic_compatible')
def _test_anthropic_compatible(url: str, api_key: str, model_id: str, config: dict) -> ValidationResult:
    """Anthropic compatible format: POST /v1/messages."""
    base = url.rstrip('/')
    if not base.endswith('/v1'):
        base = f'{base}/v1'
    
    endpoint = f'{base}/messages'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01',
        **config.get('headers', {})
    }
    body = {
        'model': model_id,
        'max_tokens': 50,
        'messages': [{'role': 'user', 'content': 'Say hello in one word.'}]
    }
    
    timeout = config.get('timeout', (5, 30))
    
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=timeout)
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get('content', [{}])[0].get('text', '')
            return ValidationResult(
                name='model',
                status=Status.SUCCESS,
                duration_ms=0,
                message=f'Model responded: {content[:100]}',
                detail=None,
                suggestion=None,
                metadata={'response': content}
            )
        else:
            return ValidationResult(
                name='model',
                status=Status.FAILED,
                duration_ms=0,
                message=f'HTTP {resp.status_code}',
                detail=resp.text[:500],
                suggestion=f"Model inference failed (HTTP {resp.status_code}) - check model ID",
                metadata={'status_code': resp.status_code}
            )
    except requests.Timeout:
        return ValidationResult(
            name='model',
            status=Status.FAILED,
            duration_ms=0,
            message='Model inference timeout',
            detail=f'Timeout after {timeout[1]}s',
            suggestion="Model inference timeout - try a faster model or check network",
            metadata={'timeout': timeout}
        )
    except Exception as e:
        return ValidationResult(
            name='model',
            status=Status.FAILED,
            duration_ms=0,
            message=str(e)[:200],
            detail=str(e),
            suggestion="Unexpected error - check logs",
            metadata={'error': str(e)}
        )


# Public API functions

def test_endpoint(base_url: str, api_key: str, config: dict = None) -> ValidationResult:
    """Test API endpoint connectivity using provider-specific strategy.
    
    Args:
        base_url: The API base URL
        api_key: The API key
        config: Provider config with 'test_strategy', 'timeout', 'retry', etc.
    
    Returns:
        ValidationResult with status, message, and suggestions
    """
    if config is None:
        from core.providers import get_provider_config
        config = get_provider_config(base_url)
    
    strategy = config.get('test_strategy', 'anthropic_compatible')
    
    # Endpoint test uses direct_post strategy (or equivalent)
    if strategy == 'direct_post':
        test_func = _test_direct_post
    elif strategy == 'openai_compatible':
        # For OpenAI, we can use the same endpoint
        test_func = lambda url, key, model, cfg: _test_openai_compatible(url, key, model, cfg)
    else:
        test_func = lambda url, key, model, cfg: _test_anthropic_compatible(url, key, model, cfg)
    
    # Apply retry wrapper
    wrapped = with_retry(config)(test_func)
    
    # Use a dummy model for endpoint test (just checking connectivity)
    dummy_model = 'test-model'
    return wrapped(base_url, api_key, dummy_model, config)


def test_model(base_url: str, api_key: str, model_id: str, config: dict = None) -> ValidationResult:
    """Test model inference using provider-specific strategy.
    
    Args:
        base_url: The API base URL
        api_key: The API key
        model_id: The model ID to test
        config: Provider config with 'test_strategy', 'timeout', 'retry', etc.
    
    Returns:
        ValidationResult with status, message, and suggestions
    """
    if config is None:
        from core.providers import get_provider_config
        config = get_provider_config(base_url)
    
    strategy = config.get('test_strategy', 'anthropic_compatible')
    
    if strategy == 'direct_post':
        test_func = _test_direct_post
    elif strategy == 'openai_compatible':
        test_func = _test_openai_compatible
    else:
        test_func = _test_anthropic_compatible
    
    # Apply retry wrapper
    wrapped = with_retry(config)(test_func)
    
    return wrapped(base_url, api_key, model_id, config)


def test_opencode_cli(model_id: str = '', timeout: int = 60) -> ValidationResult:
    """Test OpenCode CLI by running a real query.
    
    Args:
        model_id: Optional model ID hint
        timeout: Command timeout in seconds
    
    Returns:
        ValidationResult with CLI test status
    """
    test_prompt = 'Reply with exactly one word: hello'
    commands = [
        ['opencode', 'run', test_prompt],
        ['opencode', 'run', '--print-logs', test_prompt],
    ]
    
    start = time.time()
    
    if not shutil.which('opencode'):
        return ValidationResult(
            name='cli',
            status=Status.FAILED,
            duration_ms=int((time.time() - start) * 1000),
            message='OpenCode CLI not found on PATH',
            detail=None,
            suggestion="OpenCode CLI not installed - go back and install first",
            metadata={'commands_tried': commands}
        )
    
    for cmd in commands:
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, 'NO_COLOR': '1', 'CI': '1', 'FORCE_COLOR': '0'},
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return ValidationResult(
                    name='cli',
                    status=Status.FAILED,
                    duration_ms=int((time.time() - start) * 1000),
                    message='CLI command timed out',
                    detail=f'Command: {" ".join(cmd)}',
                    suggestion="CLI timeout - check if opencode is responsive",
                    metadata={'timeout': timeout}
                )
            
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
                    duration_ms=int((time.time() - start) * 1000),
                    message=f'CLI exit {proc.returncode} {"✓" if ok else "✗"}',
                    detail=combined[-1000:] if combined else None,
                    suggestion=None if ok else "CLI failed - run 'opencode doctor' to check configuration",
                    metadata={'command': ' '.join(cmd), 'exit_code': proc.returncode}
                )
        except Exception as e:
            continue
    
    return ValidationResult(
        name='cli',
        status=Status.FAILED,
        duration_ms=int((time.time() - start) * 1000),
        message='OpenCode CLI query failed',
        detail=str(e),
        suggestion="CLI error - check installation with 'npm list -g opencode-ai'",
        metadata={}
    )


def test_config_written() -> ValidationResult:
    """Check if opencode.jsonc config file exists.
    
    Returns:
        ValidationResult with config file status
    """
    start = time.time()
    config_path = Path.home() / '.config' / 'opencode' / 'opencode.jsonc'
    
    if config_path.exists():
        try:
            content = config_path.read_text(encoding='utf-8')
            return ValidationResult(
                name='config',
                status=Status.SUCCESS,
                duration_ms=int((time.time() - start) * 1000),
                message=f'Config file written: {config_path}',
                detail=content[:500] if len(content) > 500 else content,
                suggestion=None,
                metadata={'path': str(config_path), 'size': len(content)}
            )
        except Exception as e:
            return ValidationResult(
                name='config',
                status=Status.WARNING,
                duration_ms=int((time.time() - start) * 1000),
                message=f'Config file exists but cannot read: {e}',
                detail=str(e),
                suggestion="Config file permission issue - check file permissions",
                metadata={'path': str(config_path)}
            )
    else:
        return ValidationResult(
            name='config',
            status=Status.FAILED,
            duration_ms=int((time.time() - start) * 1000),
            message='Config file not found',
            detail=f'Expected at: {config_path}',
            suggestion="Config not written - go back and regenerate configuration",
            metadata={'expected_path': str(config_path)}
        )


def read_config_file() -> str:
    """Read the generated opencode.jsonc and return its content.
    
    Returns:
        Config file content or empty string if not found
    """
    config_path = Path.home() / '.config' / 'opencode' / 'opencode.jsonc'
    if config_path.exists():
        try:
            return config_path.read_text(encoding='utf-8')
        except Exception:
            pass
    return ''


# Backward compatibility - support old dict-style results
def _to_legacy_dict(result: ValidationResult) -> dict:
    """Convert ValidationResult to legacy dict format for backward compatibility."""
    return {
        'ok': result.ok,
        'message': result.message,
        'detail': result.detail,
        'suggestion': result.suggestion,
        **result.metadata
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/core/test_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/core/test_validator.py src/core/validator.py
git commit -m "refactor: implement strategy-pattern validators with retry and suggestions"
```

---

### Task 5: Enhance Verify Page with Progress and Diagnostics

**Files:**
- Modify: `src/ui/pages/verify.py` (complete rewrite)

**Interfaces:**
- Consumes: `ValidationEngine`, `ValidationReport`, `ValidationResult`, `Status`, `format_duration`
- Produces: Enhanced `VerifyPage` with progress bar, status labels, diagnostic boxes

- [ ] **Step 1: Analyze current verify.py structure**

Read current file to understand existing UI patterns.

- [ ] **Step 2: Write enhanced verify.py**

```python
# src/ui/pages/verify.py
"""Enhanced verification page with parallel validation, progress, and diagnostics."""
import tkinter as tk
from tkinter import ttk
import threading

from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, PixelToggle, BasePage, ScrollableFrame
from i18n import t

# Import new validation system
from core.validation_engine import ValidationEngine
from core.validation_result import ValidationResult, ValidationReport, Status, format_duration
from core.providers import get_provider_config


class VerifyPage(BasePage):
    """Enhanced verification page with real-time progress and diagnostic suggestions."""
    
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'verify'
        app.set_key_hint('[Enter]完成  [Esc]返回修改')
        
        # Title
        tk.Label(self, text=f'✓ {t("verify.title")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()
        
        # Progress section
        self._progress_frame = tk.Frame(self, bg=COLORS['bg'])
        self._progress_frame.pack(fill='x', padx=40, pady=(10, 5))
        
        self._progress_label = tk.Label(self._progress_frame, text='⏳ 准备验证...', 
                                        bg=COLORS['bg'], fg=COLORS['yellow'],
                                        font=(FONTS['body']['family'], FONTS['body']['size']))
        self._progress_label.pack(anchor='w')
        
        # Custom styled progress bar
        self._progress = ttk.Progressbar(self._progress_frame, mode='determinate', 
                                         length=400, maximum=100)
        self._progress.pack(fill='x', pady=(5, 0))
        
        # Status labels for each test
        self._status_frame = tk.Frame(self, bg=COLORS['bg'])
        self._status_frame.pack(fill='x', padx=40, pady=(5, 0))
        
        self._status_labels = {}
        tests = [
            ('endpoint', '🔌 API Endpoint'),
            ('model', '🤖 Model Inference'),
            ('cli', '💻 OpenCode CLI'),
            ('config', '📄 Config File'),
        ]
        for key, label in tests:
            row = tk.Frame(self._status_frame, bg=COLORS['bg'])
            row.pack(fill='x', pady=2)
            lbl = tk.Label(row, text=f'○ {label}', bg=COLORS['bg'], fg=COLORS['dark_gray'],
                          font=(FONTS['log']['family'], FONTS['log']['size']))
            lbl.pack(anchor='w')
            self._status_labels[key] = lbl
        
        # Scrollable results area
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(pady=5, padx=15, fill='both', expand=True)
        
        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        self.finish_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_finish)
        self.finish_btn.pack(side='left', padx=5)
        self.finish_btn.set_enabled(False)
        
        # Start tests
        self._run_tests()
    
    def _update_progress(self, name: str, value: float):
        """Thread-safe progress update via after()."""
        def update():
            self._progress['value'] = value * 100
            
            # Update status label
            if name in self._status_labels:
                text = self._status_labels[name].cget('text')
                base = text[2:]  # Remove status icon
                if value < 1.0:
                    self._status_labels[name].configure(
                        text=f'⏳ {base}',
                        fg=COLORS['yellow']
                    )
                
            # Update progress label
            progress_pct = int(value * 100)
            self._progress_label.configure(text=f'⏳ 验证中... {progress_pct}%')
        
        self.after(0, update)
    
    def _update_status(self, name: str, status: Status, message: str):
        """Update status label for a completed test."""
        def update():
            if name in self._status_labels:
                text = self._status_labels[name].cget('text')[2:]  # Remove old icon
                if status == Status.SUCCESS:
                    icon, color = '✓', COLORS['neon_green']
                elif status == Status.WARNING:
                    icon, color = '⚠', COLORS['yellow']
                else:
                    icon, color = '✗', COLORS['red']
                self._status_labels[name].configure(text=f'{icon} {text}', fg=color)
        
        self.after(0, update)
    
    def _run_tests(self):
        """Run validation tests in background thread."""
        def run():
            # Get provider config for context
            provider_config = get_provider_config(self.app.state.base_url)
            
            # Create engine
            engine = ValidationEngine(self.app.state)
            engine.on_progress = self._update_progress
            
            # Run all tests
            report = engine.run_all()
            
            # Show results
            self.after(0, lambda: self._show_report(report))
        
        threading.Thread(target=run, daemon=True).start()
    
    def _show_report(self, report: ValidationReport):
        """Display validation report with diagnostic suggestions."""
        # Hide progress frame
        self._progress_frame.pack_forget()
        self._status_frame.pack_forget()
        
        # Update progress label to summary
        total_time = format_duration(report.total_duration_ms)
        status_text = '✅ 全部通过' if report.overall_status == Status.SUCCESS else \
                     '⚠ 部分通过' if report.overall_status == Status.WARNING else '❌ 验证失败'
        summary = tk.Label(self, text=f'{status_text} · 耗时 {total_time}', 
                          bg=COLORS['bg'], fg=COLORS['neon_green'] if report.overall_status == Status.SUCCESS else COLORS['yellow'],
                          font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold'))
        summary.pack(pady=(10, 5))
        
        # Show each result
        for result in report.results:
            self._show_result(result)
        
        # Show diagnostic suggestions for failures
        failed = report.get_failed()
        if failed:
            self._section('🔧 修复建议')
            for result in failed:
                if result.suggestion:
                    self._suggestion_box(result.name, result.suggestion)
        
        # Show config file if successful
        config_result = next((r for r in report.results if r.name == 'config'), None)
        if config_result and config_result.ok:
            self._section('📄 生成的 opencode.jsonc')
            self._jsonc_terminal(config_result.detail or '', config_result.metadata.get('path', ''))
        
        # Enable finish button
        self.finish_btn.set_enabled(True)
    
    def _section(self, text: str):
        """Add a section header."""
        tk.Frame(self.scroll.inner, bg=COLORS['bg'], height=6).pack()
        tk.Label(self.scroll.inner, text=text, bg=COLORS['bg'], fg=COLORS['yellow'],
                font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                    anchor='w', padx=15, pady=(6, 2))
    
    def _show_result(self, result: ValidationResult):
        """Show a single validation result."""
        row = tk.Frame(self.scroll.inner, bg=COLORS['bg'])
        row.pack(fill='x', padx=25, pady=2)
        
        # Icon based on status
        if result.status == Status.SUCCESS:
            icon, color = '✓', COLORS['neon_green']
        elif result.status == Status.WARNING:
            icon, color = '⚠', COLORS['yellow']
        else:
            icon, color = '✗', COLORS['red']
        
        # Icon label
        tk.Label(row, text=icon, bg=COLORS['bg'], fg=color,
                font=(FONTS['body']['family'], FONTS['body']['size']), width=2).pack(side='left')
        
        # Message
        duration = format_duration(result.duration_ms)
        msg = f"{result.message[:80]} ({duration})"
        tk.Label(row, text=msg, bg=COLORS['bg'], fg=color,
                font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w').pack(side='left', padx=4)
    
    def _suggestion_box(self, test_name: str, suggestion: str):
        """Show a diagnostic suggestion box."""
        box = tk.Frame(self.scroll.inner, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
        box.pack(fill='x', padx=25, pady=3)
        
        title = tk.Label(box, text=f'💡 {test_name}', bg=COLORS['dark_gray'], 
                        fg=COLORS['neon_green'], font=(FONTS['body']['family'], FONTS['body']['size'], 'bold'))
        title.pack(anchor='w', padx=8, pady=(4, 2))
        
        text = tk.Label(box, text=suggestion, bg=COLORS['dark_gray'],
                       fg=COLORS['white'], font=(FONTS['log']['family'], FONTS['log']['size']),
                       wraplength=600, justify='left')
        text.pack(anchor='w', padx=8, pady=(0, 4))
    
    def _jsonc_terminal(self, content: str, path: str):
        """Display JSONC in a terminal-style block."""
        term = tk.Frame(self.scroll.inner, bg=COLORS['black'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', padx=20, pady=4)
        
        # Title bar
        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=18)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text=f'┌── {path} ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)
        
        # Content
        line_count = min(content.count('\n') + 1, 16)
        text = tk.Text(term, height=line_count, bg=COLORS['black'],
                      fg=COLORS['neon_green'], font=(FONTS['log']['family'], FONTS['log']['size']),
                      relief='flat', padx=8, pady=4, wrap='none', state='disabled')
        text.pack(fill='x')
        
        # Colorize API key
        text.tag_configure('masked', foreground=COLORS['yellow'])
        text.configure(state='normal')
        for line in content.split('\n'):
            if 'apiKey' in line:
                text.insert('end', line + '\n', 'masked')
            else:
                text.insert('end', line + '\n')
        text.configure(state='disabled')
    
    def _on_finish(self):
        """Navigate to finish page."""
        from ui.pages.finish import FinishPage
        self.app.show_page(FinishPage, 'finish')
    
    def _on_key_next(self):
        """Handle Enter key."""
        if self.finish_btn.is_enabled():
            self._on_finish()
```

- [ ] **Step 3: Update theme for ttk progressbar (if needed)**

Check if ttk progressbar needs custom styling for 8-bit theme:

```python
# In src/ui/theme.py, add if not present:
def configure_progressbar(style):
    """Configure ttk progressbar with dark theme."""
    style.configure('Horizontal.TProgressbar',
                   background=COLORS['neon_green'],
                   troughcolor=COLORS['dark_gray'])
```

- [ ] **Step 4: Manual test**

Run the application and verify:
1. Progress bar shows during validation
2. Status labels update in real-time
3. Each test result displays correctly
4. Diagnostic suggestions appear for failures
5. Config file displays in terminal block

- [ ] **Step 5: Commit**

```bash
git add src/ui/pages/verify.py
git commit -m "feat: enhanced verify page with progress, diagnostics, and parallel validation"
```

---

## Self-Review Checklist

- [ ] **Spec coverage**: All requirements from design doc implemented
  - Provider configs with strategies ✓
  - Unified result structures ✓
  - Parallel validation engine ✓
  - Strategy-pattern validators ✓
  - Enhanced UI with progress ✓
- [ ] **Placeholder scan**: No TBD/TODO/"implement later"
- [ ] **Type consistency**: Function signatures match between tasks
- [ ] **Import consistency**: All imports use `src.core` or `core` consistently
- [ ] **Backward compatibility**: Old `run_all()` still works
- [ ] **UI theme**: Progress bar styled for 8-bit pixel theme

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-15-verification-optimization-plan.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
