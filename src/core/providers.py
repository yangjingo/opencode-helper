"""
Provider configuration and detection module.

This module contains provider-specific configurations for testing strategies,
timeouts, retries, and model resolution.
"""

from typing import Dict, List, Optional, Any


# Provider configuration dictionary
# Each provider has specific testing strategies, timeouts, and available models
PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
    'dashscope': {
        'name': '阿里百炼 Coding Plan',
        # Anthropic 兼容接口：baseURL 含 /v1，策略自动追加 /messages
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 15),  # (connect timeout, read timeout)
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
        'name': 'DeepSeek',
        # 官方提供原生 Anthropic 兼容接口（OpenCode/Claude Code 用此）
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {'anthropic-version': '2023-06-01'},
        'default_test_model': 'deepseek-v4-flash',
        'available_models': [
            'deepseek-v4-flash', 'deepseek-v4-pro',
            # 旧名（2026-07-24 弃用），保留兼容
            'deepseek-chat', 'deepseek-reasoner',
        ],
    },
    'openai': {
        'name': 'OpenAI',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'gpt-4o',
        'available_models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    },
    'anthropic': {
        'name': 'Anthropic',
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {},
        'default_test_model': 'claude-sonnet-4',
        'available_models': ['claude-opus-4', 'claude-sonnet-4', 'claude-haiku-4'],
    },
    'glm': {
        'name': '智谱 GLM Coding Plan',
        # 官方 Anthropic 兼容接口（Claude Code / OpenCode 用此）
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {'anthropic-version': '2023-06-01'},
        'default_test_model': 'glm-5.2',
        'available_models': [
            'glm-5.2', 'glm-4.7', 'glm-4.6', 'glm-4.5',
        ],
        # GLM 的 Anthropic 兼容 endpoint（供 Claude / OpenCode 使用）
        'base_url': 'https://open.bigmodel.cn/api/anthropic',
    },
    'default': {
        'name': 'Default',
        'test_strategy': 'anthropic_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {},
        'default_test_model': 'claude-sonnet-4',
        'available_models': [],
    }
}


# URL patterns for provider detection
# Order matters: GLM is checked BEFORE anthropic because its endpoint
# (open.bigmodel.cn/api/anthropic) contains the substring 'anthropic'.
PROVIDER_URL_PATTERNS: Dict[str, List[str]] = {
    'dashscope': [
        'dashscope.aliyuncs.com',
        'coding.dashscope.aliyuncs.com',
    ],
    'glm': [
        'bigmodel.cn',
        'open.bigmodel',
    ],
    'deepseek': [
        'api.deepseek.com',
        'deepseek.com',
    ],
    'openai': [
        'api.openai.com',
        'openai.com',
    ],
    'anthropic': [
        'api.anthropic.com',
        'anthropic.com',
    ],
}


def _detect_provider(base_url: str) -> str:
    """
    Detect the provider from the base URL.

    Args:
        base_url: The API base URL to analyze.

    Returns:
        The provider key ('dashscope', 'deepseek', 'openai', 'anthropic')
        or 'default' if no match is found.
    """
    if not base_url:
        return 'default'

    base_url_lower = base_url.lower()

    for provider, patterns in PROVIDER_URL_PATTERNS.items():
        for pattern in patterns:
            if pattern in base_url_lower:
                return provider

    return 'default'


def get_provider_config(base_url: str) -> Dict[str, Any]:
    """
    Get the provider configuration based on the base URL.

    Args:
        base_url: The API base URL to analyze.

    Returns:
        The provider configuration dictionary for the detected provider.
        Returns the 'default' configuration if no specific provider is detected.
    """
    provider = _detect_provider(base_url)
    return PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG['default']).copy()


def resolve_test_model(provider_config: Dict[str, Any], user_model_id: Optional[str]) -> str:
    """
    Determine the model ID to use for testing.

    Priority:
    1. User configured model_id (if non-empty)
    2. Provider configured default_test_model

    Using the user-configured model_id is more realistic for testing,
    but if empty or None, we fall back to the provider's default model
    to ensure the test can execute.

    Args:
        provider_config: The provider configuration dictionary.
        user_model_id: The model ID configured by the user (may be None or empty).

    Returns:
        The model ID to use for testing.
    """
    if user_model_id and user_model_id.strip():
        return user_model_id.strip()

    return provider_config.get('default_test_model', 'unknown')


def get_available_models(provider_key: str) -> List[str]:
    """
    Get the list of available models for a provider.

    Args:
        provider_key: The provider key (e.g., 'dashscope', 'openai').

    Returns:
        List of available model IDs for the provider.
    """
    config = PROVIDER_CONFIG.get(provider_key, PROVIDER_CONFIG['default'])
    return config.get('available_models', []).copy()


def get_provider_name(provider_key: str) -> str:
    """
    Get the display name for a provider.

    Args:
        provider_key: The provider key.

    Returns:
        The display name of the provider.
    """
    config = PROVIDER_CONFIG.get(provider_key, PROVIDER_CONFIG['default'])
    return config.get('name', provider_key)
