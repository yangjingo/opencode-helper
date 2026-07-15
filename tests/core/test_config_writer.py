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
