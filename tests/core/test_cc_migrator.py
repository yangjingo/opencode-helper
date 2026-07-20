import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_scan_finds_settings(tmp_path, monkeypatch):
    from core import cc_migrator
    from pathlib import Path
    claude_dir = tmp_path / '.claude'
    claude_dir.mkdir()
    (claude_dir / 'settings.json').write_text(json.dumps({'apiKey': 'sk-ant-test', 'model': 'claude-sonnet-5'}))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(Path, 'cwd', lambda: tmp_path)
    items = cc_migrator.scan()
    api_key_items = [i for i in items if i['key'] == 'api_key']
    assert len(api_key_items) > 0

def test_scan_empty_when_no_claude(tmp_path, monkeypatch):
    from core import cc_migrator
    from pathlib import Path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(Path, 'cwd', lambda: tmp_path)
    items = cc_migrator.scan()
    assert items == []

def test_migrate_writes_instructions(tmp_path):
    from core import cc_migrator
    target_dir = tmp_path / 'opencode'
    target_dir.mkdir(parents=True)
    item = {'key': 'instructions', 'source': 'CLAUDE.md', 'content': '# My Instructions\nBe helpful.',
            'target': str(target_dir / 'instructions.md'), 'checked': True}
    logs = cc_migrator.migrate([item])
    assert len(logs) > 0
    assert os.path.exists(item['target'])

def test_migrate_skips_unchecked(tmp_path):
    from core import cc_migrator
    target_dir = tmp_path / 'opencode'
    target_dir.mkdir(parents=True)
    item = {'key': 'instructions', 'source': 'CLAUDE.md', 'content': '# Skip',
            'target': str(target_dir / 'instructions.md'), 'checked': False}
    logs = cc_migrator.migrate([item])
    assert logs == []

def test_migrate_copies_skills(tmp_path):
    from core import cc_migrator
    skills_src = tmp_path / 'skills'
    skills_src.mkdir()
    (skills_src / 'my-skill.md').write_text('# My Skill')
    target_dir = tmp_path / 'opencode' / 'skills'
    target_dir.mkdir(parents=True)
    item = {'key': 'skills', 'source': str(skills_src / 'my-skill.md'),
            'content': '# My Skill', 'target': str(target_dir / 'my-skill.md'), 'checked': True}
    logs = cc_migrator.migrate([item])
    assert os.path.exists(item['target'])

def test_extract_profile_honors_local_settings_and_real_model(tmp_path):
    from core.cc_migrator import extract_profile
    claude = tmp_path / '.claude'
    claude.mkdir()
    (claude / 'settings.json').write_text(json.dumps({'env': {
        'ANTHROPIC_API_KEY': 'user-key', 'ANTHROPIC_BASE_URL': 'https://user.example/v1',
        'ANTHROPIC_DEFAULT_SONNET_MODEL': 'user-model'}}))
    (claude / 'settings.local.json').write_text(json.dumps({'env': {
        'ANTHROPIC_API_KEY': 'local-key', 'ANTHROPIC_BASE_URL': 'https://local.example/anthropic',
        'ANTHROPIC_DEFAULT_SONNET_MODEL': 'local-model'}}))
    profile = extract_profile(runtime_env={}, home=tmp_path, cwd=tmp_path)
    assert profile['api_key'] == 'local-key'
    assert profile['base_url'] == 'https://local.example/anthropic'
    assert profile['model_id'] == 'local-model'


def test_effective_settings_merges_mcp_servers_across_scopes(tmp_path):
    from core.cc_migrator import effective_settings

    user = tmp_path / '.claude'
    project = tmp_path / 'project' / '.claude'
    user.mkdir()
    project.mkdir(parents=True)
    (user / 'settings.json').write_text(json.dumps({
        'mcpServers': {'user-mcp': {'command': 'npx', 'args': ['user-server']}},
    }), encoding='utf-8')
    (project / 'settings.json').write_text(json.dumps({
        'mcpServers': {'project-mcp': {'url': 'https://mcp.example.test'}},
    }), encoding='utf-8')
    settings, _ = effective_settings(home=tmp_path, cwd=tmp_path / 'project')
    assert set(settings['mcpServers']) == {'user-mcp', 'project-mcp'}

def test_extract_profile_does_not_migrate_claude_alias_as_model(tmp_path):
    from core.cc_migrator import extract_profile
    claude = tmp_path / '.claude'
    claude.mkdir()
    (claude / 'settings.json').write_text(json.dumps({'model': 'sonnet'}))
    profile = extract_profile(runtime_env={}, home=tmp_path, cwd=tmp_path)
    assert profile['model_id'] == ''


def test_extract_profile_converts_zhipu_claude_endpoint_to_opencode_native_endpoint(tmp_path):
    from core.cc_migrator import extract_profile
    from core.config_writer import generate_config

    profile = extract_profile(runtime_env={
        'ANTHROPIC_API_KEY': 'glm-key',
        'ANTHROPIC_BASE_URL': 'https://open.bigmodel.cn/api/anthropic',
        'ANTHROPIC_DEFAULT_SONNET_MODEL': 'glm-5.2',
    }, home=tmp_path, cwd=tmp_path)
    assert profile['base_url'] == 'https://open.bigmodel.cn/api/coding/paas/v4'
    assert profile['api_style'] == ''

    class State:
        provider_name = 'zhipu'
        display_name = 'Zhipu AI'
        api_key = profile['api_key']
        base_url = profile['base_url']
        api_style = profile['api_style']
        model_id = profile['model_id']
        model_name = profile['model_id']
        reasoning = True
        thinking = True

    config = json.loads(generate_config(State()))
    assert config['model'] == 'zhipuai/glm-5.2'
    assert config['provider']['zhipuai']['api'] == profile['base_url']
    assert 'npm' not in config['provider']['zhipuai']


def test_migrate_profile_immediately_writes_native_opencode_config(tmp_path):
    from core.cc_migrator import migrate_profile_to_opencode

    target = tmp_path / 'opencode.jsonc'
    target.write_text(json.dumps({
        'provider': {
            'zhipu': {
                'npm': '@ai-sdk/anthropic',
                'options': {'baseURL': 'https://open.bigmodel.cn/api/anthropic'},
                'models': {'glm-5.2': {}},
            },
            'deepseek': {'models': {'deepseek-v4-flash': {}}},
        },
        'model': 'zhipu/glm-5.2',
    }), encoding='utf-8')
    result = migrate_profile_to_opencode({
        'api_key': 'glm-key',
        'base_url': 'https://open.bigmodel.cn/api/coding/paas/v4',
        'api_style': '',
        'model_id': 'glm-5.2',
    }, path=str(target))

    assert result['written'] is True
    assert result['model_ref'] == 'zhipuai/glm-5.2'
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert saved['model'] == 'zhipuai/glm-5.2'
    assert set(saved['provider']) == {'zhipuai', 'deepseek'}
    assert saved['provider']['zhipuai']['api'] == 'https://open.bigmodel.cn/api/coding/paas/v4'


def test_migrate_profile_uses_documented_provider_default_when_claude_has_alias_only(tmp_path):
    from core.cc_migrator import migrate_profile_to_opencode

    target = tmp_path / 'opencode.jsonc'
    result = migrate_profile_to_opencode({
        'api_key': 'glm-key',
        'base_url': 'https://open.bigmodel.cn/api/coding/paas/v4',
        'api_style': '',
        'model_id': '',
    }, path=str(target))
    assert result['written'] is True
    assert result['model_ref'] == 'zhipuai/glm-5.2'


def test_migrate_profile_converts_and_merges_claude_mcp_servers(tmp_path):
    from core.cc_migrator import migrate_profile_to_opencode

    target = tmp_path / 'opencode.jsonc'
    target.write_text(json.dumps({
        'mcp': {'existing': {'type': 'local', 'command': ['existing']}},
    }), encoding='utf-8')
    result = migrate_profile_to_opencode({
        'api_key': '', 'base_url': '', 'api_style': '', 'model_id': '',
        'settings': {'mcpServers': {
            'local': {'command': 'uvx', 'args': ['server', '-y'], 'env': {'TOKEN': 'value'}},
            'remote': {'url': 'https://mcp.example.test', 'headers': {'X-Test': 'yes'}},
        }},
    }, selected_keys={'mcp'}, path=str(target))

    assert result['written'] is True
    assert set(result['mcp_names']) == {'local', 'remote'}
    saved = json.loads(target.read_text(encoding='utf-8'))
    assert set(saved['mcp']) == {'existing', 'local', 'remote'}
    assert saved['mcp']['local'] == {
        'type': 'local', 'command': ['uvx', 'server', '-y'], 'enabled': True,
        'environment': {'TOKEN': 'value'},
    }
    assert saved['mcp']['remote']['type'] == 'remote'
    assert saved['mcp']['remote']['headers'] == {'X-Test': 'yes'}

def test_scan_recognizes_standard_skill_directory(tmp_path, monkeypatch):
    from core import cc_migrator
    from pathlib import Path
    skill = tmp_path / '.claude' / 'skills' / 'release' / 'SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('---\nname: release\ndescription: release\n---\n')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(Path, 'cwd', lambda: tmp_path)
    items = cc_migrator.scan()
    skill_item = next(item for item in items if item['key'] == 'skills')
    assert skill_item['action'] == 'copy'
    assert skill_item['source'] == str(skill)
    assert os.path.isabs(skill_item['source'])
    assert os.path.isabs(skill_item['target'])
    assert skill_item['source_name'].endswith('/release/SKILL.md')
