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
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'deepseek-v4-flash',
        'available_models': [
            'deepseek-v4-flash', 'deepseek-v4-pro',
            # 旧名（2026-07-24 弃用），保留兼容
            'deepseek-chat', 'deepseek-reasoner',
        ],
    },
    'moonshot': {
        'name': 'Moonshot AI (Kimi)',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'moonshot-v1-8k',
        'available_models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
    },
    'minimax': {
        'name': 'MiniMax',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'MiniMax-M2.7',
        'available_models': ['MiniMax-M2.7', 'MiniMax-M2.7-highspeed',
                             'MiniMax-M2.5', 'MiniMax-M2.5-highspeed'],
    },
    'mimo': {
        'name': 'Xiaomi MiMo',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'mimo-v2.5-pro',
        'available_models': ['mimo-v2.5-pro'],
    },
    'longcat': {
        'name': 'LongCat',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'LongCat-2.0',
        'available_models': ['LongCat-2.0'],
    },
    'qianfan': {
        'name': '百度千帆',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.5},
        'headers': {},
        'default_test_model': 'ernie-4.5-turbo-128k',
        'available_models': ['ernie-4.5-turbo-128k'],
    },
    'glm': {
        'name': '智谱 GLM Coding Plan',
        # OpenCode 的 Coding API 使用 OpenAI Chat Completions；显式
        # /api/anthropic 地址会在 get_provider_config() 中切回 Anthropic。
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 3, 'backoff': 1.0},
        'headers': {},
        'default_test_model': 'glm-5.2',
        'available_models': [
            'glm-5.2', 'glm-4.7', 'glm-4.6', 'glm-4.5',
        ],
        'base_url': 'https://open.bigmodel.cn/api/coding/paas/v4',
    },
    'default': {
        'name': '自定义 / 内网网关',
        'test_strategy': 'openai_compatible',
        'timeout': (5, 30),
        'retry': {'times': 2, 'backoff': 1.0},
        'headers': {},
        'default_test_model': '',
        'available_models': [],
    }
}


# URL patterns for provider detection
# Order matters: Chinese vendor hostnames are specific and are checked first.
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
    'moonshot': [
        'moonshot.cn',
        'kimi.com',
    ],
    'minimax': ['minimaxi.com', 'minimax.io'],
    'mimo': ['xiaomimimo.com', 'mimo.mi.com'],
    'longcat': ['longcat.chat'],
    'qianfan': ['baidubce.com'],
}


def _detect_provider(base_url: str) -> str:
    """
    Detect the provider from the base URL.

    Args:
        base_url: The API base URL to analyze.

    Returns:
        The provider key ('dashscope', 'deepseek', 'glm', 'moonshot', 'minimax', 'mimo', 'longcat', 'qianfan')
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
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG['default']).copy()
    # Provider-specific catalogs are domestic-only, but any explicit Anthropic
    # Messages URL remains a valid protocol choice for Claude Code migration.
    if 'anthropic' in base_url.lower():
        config['test_strategy'] = 'anthropic_compatible'
        config['headers'] = {'anthropic-version': '2023-06-01'}
    # DeepSeek offers both its native OpenAI-compatible API and an Anthropic
    # compatible route used by Claude Code. Preserve that route when detected.
    return config


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
