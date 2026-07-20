import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class FakeState:
    provider_name = 'openlab'
    display_name = 'OpenLab'
    api_key = 'sk-test-key'
    base_url = 'http://10.0.0.1:8080/v1'
    model_id = 'glm-5.2'
    model_name = 'GLM 5.2'
    reasoning = True
    thinking = True
    install_method = 'npm'

def test_generate_config_contains_provider():
    from core import config_writer
    content = config_writer.generate_config(FakeState())
    assert '"openlab"' in content
    assert '"OpenLab"' in content
    assert '"sk-test-key"' in content

def test_generate_config_has_model_ref():
    from core import config_writer
    content = config_writer.generate_config(FakeState())
    assert '"model": "openlab/glm-5.2"' in content

def test_write_config_creates_file(tmp_path, monkeypatch):
    from core import config_writer
    from pathlib import Path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    content = config_writer.generate_config(FakeState())
    path = config_writer.write_config(content, str(tmp_path / 'opencode.jsonc'))
    assert os.path.exists(path)
    assert 'openlab' in open(path).read()

def test_generate_config_valid_json():
    from core import config_writer
    content = config_writer.generate_config(FakeState())
    cleaned = config_writer._clean_jsonc(content)
    parsed = json.loads(cleaned)
    assert parsed['model'] == 'openlab/glm-5.2'
    assert 'openlab' in parsed['provider']

def test_generate_config_uses_openai_compatible_adapter_for_custom_gateway():
    from core import config_writer
    content = config_writer.generate_config(FakeState())
    parsed = json.loads(content)
    provider = parsed['provider']['openlab']
    assert provider['npm'] == '@ai-sdk/openai-compatible'
    assert provider['options']['baseURL'] == 'http://10.0.0.1:8080/v1'

def test_generate_config_uses_anthropic_adapter_without_rewriting_url():
    from core import config_writer
    class AnthropicGateway(FakeState):
        provider_name = 'company-gateway'
        base_url = 'https://gateway.example.com/anthropic/v1'
    parsed = json.loads(config_writer.generate_config(AnthropicGateway()))
    provider = parsed['provider']['company-gateway']
    assert provider['npm'] == '@ai-sdk/anthropic'
    assert provider['options']['baseURL'] == 'https://gateway.example.com/anthropic/v1'


def test_generate_config_uses_zhipu_coding_plan_native_provider():
    from core import config_writer

    class ZhipuCodingPlan(FakeState):
        provider_name = 'zhipu'
        base_url = 'https://open.bigmodel.cn/api/coding/paas/v4'
        model_id = 'glm-5.2'

    parsed = json.loads(config_writer.generate_config(ZhipuCodingPlan()))
    provider = parsed['provider']['zhipuai']
    assert provider['api'] == 'https://open.bigmodel.cn/api/coding/paas/v4'
    assert provider['options']['apiKey'] == 'sk-test-key'
    assert 'npm' not in provider
    assert 'baseURL' not in provider['options']
    assert parsed['model'] == 'zhipuai/glm-5.2'

def test_deepseek_anthropic_route_does_not_use_openai_builtin():
    from core import config_writer
    class DeepSeekAnthropic(FakeState):
        provider_name = 'deepseek'
        base_url = 'https://api.deepseek.com/anthropic/v1'
    parsed = json.loads(config_writer.generate_config(DeepSeekAnthropic()))
    assert parsed['provider']['deepseek']['npm'] == '@ai-sdk/anthropic'

def test_generate_config_escapes_user_values():
    from core import config_writer
    class Quoted(FakeState):
        api_key = 'key"withquote'
    parsed = json.loads(config_writer.generate_config(Quoted()))
    assert parsed['provider']['openlab']['options']['apiKey'] == 'key"withquote'

def test_generate_config_strips_terminal_markup_from_model_id():
    from core import config_writer
    class MarkedModel(FakeState):
        model_id = 'glm-5.2[1m]'
        model_name = 'glm-5.2[1m]'
    parsed = json.loads(config_writer.generate_config(MarkedModel()))
    assert parsed['model'] == 'openlab/glm-5.2'
    assert 'glm-5.2' in parsed['provider']['openlab']['models']


def test_write_config_preserves_existing_providers_when_migrating(tmp_path):
    from core import config_writer

    target = tmp_path / 'opencode.jsonc'
    target.write_text(json.dumps({
        '$schema': 'https://opencode.ai/config.json',
        'provider': {'zhipuai': {'api': 'https://open.bigmodel.cn/api/coding/paas/v4'}},
        'model': 'zhipuai/glm-5.2',
    }), encoding='utf-8')
    incoming = json.dumps({
        '$schema': 'https://opencode.ai/config.json',
        'provider': {'deepseek': {'name': 'DeepSeek'}},
        'model': 'deepseek/deepseek-v4-flash',
        'autoupdate': True,
    })

    config_writer.write_config(incoming, str(target))
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert set(saved['provider']) == {'zhipuai', 'deepseek'}
    assert saved['model'] == 'deepseek/deepseek-v4-flash'


def test_write_config_replaces_legacy_zhipu_anthropic_migration(tmp_path):
    from core import config_writer

    target = tmp_path / 'opencode.jsonc'
    target.write_text(json.dumps({
        'provider': {'zhipu': {
            'npm': '@ai-sdk/anthropic',
            'options': {'baseURL': 'https://open.bigmodel.cn/api/anthropic'},
            'models': {'glm-5.2': {}},
        }},
        'model': 'zhipu/glm-5.2',
    }), encoding='utf-8')

    class NativeZhipu(FakeState):
        provider_name = 'zhipu'
        base_url = 'https://open.bigmodel.cn/api/coding/paas/v4'

    config_writer.write_config(config_writer.generate_config(NativeZhipu()), str(target))
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert 'zhipu' not in saved['provider']
    assert saved['model'] == 'zhipuai/glm-5.2'


def test_write_config_merges_existing_mcp_servers(tmp_path):
    from core import config_writer

    target = tmp_path / 'opencode.jsonc'
    target.write_text(json.dumps({
        'mcp': {'existing': {'type': 'local', 'command': ['existing']}},
    }), encoding='utf-8')
    config_writer.write_config(json.dumps({
        '$schema': 'https://opencode.ai/config.json',
        'mcp': {'migrated': {'type': 'local', 'command': ['migrated']}},
    }), str(target))
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert set(saved['mcp']) == {'existing', 'migrated'}
