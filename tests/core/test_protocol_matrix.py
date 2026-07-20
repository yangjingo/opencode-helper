"""Protocol matrix for official Chinese endpoints and local OpenAI servers."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class _State:
    api_key = 'mock-token'
    model_id = 'mock-model'
    model_name = 'Mock model'
    reasoning = True
    thinking = True
    api_style = ''


def test_common_endpoint_protocol_matrix():
    from core.provider_catalog import resolve_provider

    cases = [
        ('http://127.0.0.1:8000/v1', 'vllm', '@ai-sdk/openai-compatible'),
        ('https://dashscope.aliyuncs.com/compatible-mode/v1', 'dashscope', '@ai-sdk/openai-compatible'),
        ('https://coding.dashscope.aliyuncs.com/apps/anthropic', 'dashscope', '@ai-sdk/anthropic'),
        ('https://open.bigmodel.cn/api/anthropic/v1', 'zhipu', '@ai-sdk/anthropic'),
        ('https://api.moonshot.cn/v1', 'moonshot', '@ai-sdk/openai-compatible'),
        ('https://api.minimaxi.com/v1', 'minimax', '@ai-sdk/openai-compatible'),
        ('https://api.xiaomimimo.com/v1', 'mimo', '@ai-sdk/openai-compatible'),
        ('https://api.longcat.chat/openai/v1', 'longcat', '@ai-sdk/openai-compatible'),
        ('https://qianfan.baidubce.com/v2', 'qianfan', '@ai-sdk/openai-compatible'),
    ]
    for url, provider_id, npm in cases:
        spec = resolve_provider(url)
        assert spec.provider_id == provider_id
        assert spec.npm == npm


def test_plain_v1_is_openai_compatible_and_responses_uses_openai_sdk():
    from core.config_writer import generate_config

    class Vllm(_State):
        provider_name = ''
        display_name = ''
        base_url = 'http://127.0.0.1:8000/v1'

    class Responses(_State):
        provider_name = 'gateway'
        display_name = 'Gateway'
        base_url = 'https://gateway.internal/v1/responses'

    assert json.loads(generate_config(Vllm()))['provider']['vllm']['npm'] == '@ai-sdk/openai-compatible'
    assert json.loads(generate_config(Responses()))['provider']['gateway']['npm'] == '@ai-sdk/openai'
