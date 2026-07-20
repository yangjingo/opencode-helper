import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_deepseek_official_endpoint_uses_builtin_provider():
    from core.provider_catalog import resolve_provider
    spec = resolve_provider('https://api.deepseek.com/v1')
    assert spec.provider_id == 'deepseek'
    assert spec.built_in is True
    assert spec.npm is None


def test_mainstream_anthropic_compatible_endpoints_use_anthropic_sdk():
    from core.provider_catalog import resolve_provider
    for url in [
        'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
        'https://open.bigmodel.cn/api/anthropic/v1',
        'https://api.deepseek.com/anthropic/v1',
    ]:
        assert resolve_provider(url).npm == '@ai-sdk/anthropic'


def test_zhipu_coding_plan_uses_its_native_opencode_provider():
    from core.provider_catalog import resolve_provider
    spec = resolve_provider('https://open.bigmodel.cn/api/coding/paas/v4')
    assert spec.provider_id == 'zhipuai'
    assert spec.built_in is True
    assert spec.npm is None
    assert spec.native_api == 'https://open.bigmodel.cn/api/coding/paas/v4'


def test_unknown_gateway_defaults_to_documented_openai_compatible_sdk():
    from core.provider_catalog import resolve_provider
    spec = resolve_provider('https://llm.example.internal/v1', 'Engineering Gateway')
    assert spec.provider_id == 'engineering-gateway'
    assert spec.npm == '@ai-sdk/openai-compatible'


def test_chinese_provider_hosts_are_recognized():
    from core.provider_catalog import resolve_provider
    cases = {
        'https://api.minimaxi.com/v1': 'minimax',
        'https://api.xiaomimimo.com/v1': 'mimo',
        'https://api.longcat.chat/openai/v1': 'longcat',
    }
    for url, provider_id in cases.items():
        assert resolve_provider(url).provider_id == provider_id
