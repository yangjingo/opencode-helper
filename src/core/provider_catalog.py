"""Provider and API-shape inference used by Claude Code migration.

The important distinction is protocol, not brand: OpenCode requires an AI SDK
adapter for a custom endpoint.  Guessing that every endpoint is Anthropic
compatible (the old behaviour) silently produced unusable configurations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    npm: str | None
    api_style: str
    built_in: bool = False
    native_api: str | None = None


# These IDs are OpenCode's built-in providers.  They do not need an npm adapter.
_OFFICIAL_HOSTS = {
    "api.deepseek.com": ("deepseek", "DeepSeek", "openai"),
}

_HOST_NAMES = (
    ("localhost", "vllm", "Local vLLM"),
    ("127.0.0.1", "vllm", "Local vLLM"),
    ("::1", "vllm", "Local vLLM"),
    ("dashscope.aliyuncs.com", "dashscope", "Alibaba DashScope"),
    ("bigmodel.cn", "zhipu", "Zhipu AI"),
    ("moonshot.cn", "moonshot", "Moonshot AI"),
    ("minimaxi.com", "minimax", "MiniMax"),
    ("baidubce.com", "qianfan", "Baidu Qianfan"),
    ("xiaomimimo.com", "mimo", "Xiaomi MiMo"),
    ("longcat.chat", "longcat", "LongCat"),
    ("open.bigmodel", "zhipu", "Zhipu AI"),
)


def normalize_provider_id(value: str) -> str:
    """Return an OpenCode-safe custom provider ID."""
    result = re.sub(r"[^a-z0-9_-]+", "-", (value or "custom").lower()).strip("-_")
    return result or "custom"


def _host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").lower()


def infer_api_style(base_url: str) -> str:
    """Infer the API family without changing a user supplied endpoint."""
    value = (base_url or "").lower().rstrip("/")
    if "anthropic" in value or "messages" in value or "api.anthropic.com" in value:
        return "anthropic"
    if "/responses" in value or "api.openai.com" in value:
        return "openai"
    # The OpenAI compatible chat-completions API is the safest default for an
    # unknown gateway.  It is also OpenCode's documented custom-provider path.
    return "openai-compatible"


def resolve_provider(base_url: str, preferred_id: str = "", api_style: str = "") -> ProviderSpec:
    """Map an endpoint to a valid OpenCode provider configuration.

    Chinese official endpoints retain their built-in IDs. Other endpoints use a
    custom provider with the documented adapter, so a proxy or regional endpoint
    cannot be accidentally treated as a native OpenCode provider.
    """
    host = _host(base_url)
    style = api_style if api_style in {"anthropic", "openai", "openai-compatible"} else infer_api_style(base_url)
    normalized_url = (base_url or '').rstrip('/')
    # GLM Coding Plan is not the public Anthropic-compatible API. OpenCode has
    # a dedicated built-in provider for its Coding Plan transport, configured
    # with the provider-level ``api`` field (not options.baseURL + an SDK npm).
    if host == 'open.bigmodel.cn' and '/api/coding/paas/v4' in normalized_url:
        return ProviderSpec('zhipuai', 'Zhipu AI Coding Plan', None, 'native', True,
                            native_api=normalized_url)
    # A few vendors expose a second Anthropic-compatible route alongside their
    # native OpenAI-compatible one.  That route needs the Anthropic adapter,
    # not the vendor's built-in OpenAI provider.
    if host in _OFFICIAL_HOSTS and not (host == 'api.deepseek.com' and style == 'anthropic'):
        provider_id, display_name, official_style = _OFFICIAL_HOSTS[host]
        return ProviderSpec(provider_id, display_name, None, official_style, True)

    provider_id = ""
    display_name = ""
    for pattern, known_id, known_name in _HOST_NAMES:
        if pattern in host:
            provider_id, display_name = known_id, known_name
            break
    normalized_preferred = normalize_provider_id(preferred_id) if preferred_id else ''
    # A caller may deliberately name a gateway (for example a migrated Claude
    # endpoint). Preserve that identity unless it is the same as the detected
    # provider; protocol selection still comes from the URL/import metadata.
    if normalized_preferred and normalized_preferred != 'custom' and normalized_preferred != provider_id:
        npm = "@ai-sdk/anthropic" if style == "anthropic" else (
            "@ai-sdk/openai" if style == "openai" else "@ai-sdk/openai-compatible"
        )
        return ProviderSpec(normalized_preferred, preferred_id, npm, style, False)
    if not provider_id:
        provider_id = normalize_provider_id(preferred_id or host.split(".")[0] or "custom")
        display_name = preferred_id or host or "Custom provider"

    npm = "@ai-sdk/anthropic" if style == "anthropic" else (
        "@ai-sdk/openai" if style == "openai" else "@ai-sdk/openai-compatible"
    )
    return ProviderSpec(provider_id, display_name, npm, style, False)
