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
