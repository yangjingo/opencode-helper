"""Model and endpoint matrix derived from docs/china-provider-guide.md."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


DOCS_MODELS = [
    ('DeepSeek', 'https://api.deepseek.com/v1', 'deepseek-v4-flash',
     'openai_compatible', 'https://api.deepseek.com/v1/chat/completions'),
    ('Qwen Coding Plan', 'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1', 'qwen3.7-plus',
     'anthropic_compatible', 'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages'),
    ('GLM Coding Plan', 'https://open.bigmodel.cn/api/coding/paas/v4', 'glm-5.2',
     'openai_compatible', 'https://open.bigmodel.cn/api/coding/paas/v4/chat/completions'),
    ('Moonshot', 'https://api.moonshot.cn/v1', 'moonshot-v1-8k',
     'openai_compatible', 'https://api.moonshot.cn/v1/chat/completions'),
    ('MiniMax', 'https://api.minimaxi.com/v1', 'MiniMax-M2.7',
     'openai_compatible', 'https://api.minimaxi.com/v1/chat/completions'),
    ('Xiaomi MiMo', 'https://api.xiaomimimo.com/v1', 'mimo-v2.5-pro',
     'openai_compatible', 'https://api.xiaomimimo.com/v1/chat/completions'),
    ('LongCat', 'https://api.longcat.chat/openai/v1', 'LongCat-2.0',
     'openai_compatible', 'https://api.longcat.chat/openai/v1/chat/completions'),
    ('Qianfan', 'https://qianfan.baidubce.com/v2', 'ernie-4.5-turbo-128k',
     'openai_compatible', 'https://qianfan.baidubce.com/v2/chat/completions'),
    ('Local vLLM', 'http://127.0.0.1:8000/v1', 'local-model',
     'openai_compatible', 'http://127.0.0.1:8000/v1/chat/completions'),
]


@pytest.mark.parametrize('_name,base_url,model,strategy,expected_url', DOCS_MODELS)
def test_docs_model_inference_matrix(_name, base_url, model, strategy, expected_url):
    from core.providers import get_provider_config
    from core.validator import test_model
    from core.validation_result import Status

    response = MagicMock(status_code=200, text='')
    response.json.return_value = (
        {'content': [{'text': 'ok'}]} if strategy == 'anthropic_compatible'
        else {'choices': [{'message': {'content': 'ok'}}]}
    )
    with patch('core.validator.requests.post', return_value=response) as post:
        config = get_provider_config(base_url)
        assert config['test_strategy'] == strategy
        result = test_model(base_url, 'mock-key', model, config)

    assert result.status == Status.SUCCESS
    assert post.call_args.args[0] == expected_url
    assert post.call_args.kwargs['json']['model'] == model


@pytest.mark.parametrize('_name,base_url,model,_strategy,_expected_url', DOCS_MODELS)
def test_docs_config_generation_matrix(_name, base_url, model, _strategy, _expected_url):
    from core.config_writer import generate_config

    class State:
        provider_name = ''
        display_name = ''
        api_key = 'mock-key'
        api_style = ''
        model_id = model
        model_name = model
        reasoning = True
        thinking = True

    State.base_url = base_url
    config = json.loads(generate_config(State()))
    provider_id, configured_model = config['model'].split('/', 1)
    assert configured_model == model
    assert provider_id in config['provider']
    assert model in config['provider'][provider_id]['models']
