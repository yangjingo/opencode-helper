"""Claude Code configuration migration to OpenCode."""
import json
from pathlib import Path


def _mask_key(key: str) -> str:
    """Mask API key, showing only first 6 and last 4 chars."""
    if len(key) <= 10:
        return key[:3] + '•••'
    return key[:6] + '••••••••' + key[-4:]


def _summarize_text(text: str, max_len: int = 60) -> str:
    """Summarize text content to a single line preview."""
    first_line = text.strip().split('\n')[0]
    if len(first_line) > max_len:
        return first_line[:max_len] + '…'
    return first_line


def scan() -> list[dict]:
    """Scan for Claude Code configuration and return migration items.

    Each item: {
        key: str,          # 'api_key' | 'model' | 'instructions' | 'skills'
        source: str,       # source file path
        source_name: str,  # short display name for source
        target: str,       # target file path
        content: str,      # full content to migrate
        preview: str,      # human-readable summary of the content
        checked: bool,     # default checkbox state
    }
    """
    items = []
    home = Path.home()
    claude_dir = home / '.claude'
    project_claude = Path.cwd() / '.claude'
    opencode_config = home / '.config' / 'opencode'

    # --- settings.json ---
    settings_path = claude_dir / 'settings.json'
    if not settings_path.exists():
        settings_path = project_claude / 'settings.json'
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
            source_short = '~/.claude/settings.json'

            if 'apiKey' in settings:
                raw_key = settings['apiKey']
                items.append({
                    'key': 'api_key',
                    'source': str(settings_path),
                    'source_name': source_short,
                    'target': str(opencode_config / 'opencode.jsonc'),
                    'content': raw_key,
                    'preview': _mask_key(raw_key),
                    'checked': True,
                })

            if 'model' in settings:
                model = settings['model']
                # The top-level 'model' is a Claude alias (e.g. "sonnet").
                # The REAL model is in env.ANTHROPIC_DEFAULT_SONNET_MODEL.
                nested_env = settings.get('env', {})
                real_model = (nested_env.get('ANTHROPIC_DEFAULT_SONNET_MODEL', '')
                              or nested_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL', ''))
                display_model = real_model if real_model else model
                items.append({
                    'key': 'model',
                    'source': str(settings_path),
                    'source_name': source_short,
                    'target': str(opencode_config / 'opencode.jsonc'),
                    'content': real_model or model,
                    'preview': display_model,
                    'checked': True,
                })
        except (json.JSONDecodeError, IOError):
            pass

    # --- CLAUDE.md / AGENTS.md ---
    for md_name in ['CLAUDE.md', 'AGENTS.md']:
        md_path = claude_dir / md_name
        if md_path.exists():
            content = md_path.read_text(encoding='utf-8')
            items.append({
                'key': 'instructions',
                'source': str(md_path),
                'source_name': f'~/.claude/{md_name}',
                'target': str(opencode_config / 'instructions.md'),
                'content': content,
                'preview': _summarize_text(content),
                'checked': True,
            })

    # --- .claude/skills/ ---
    skills_dir = claude_dir / 'skills'
    if skills_dir.exists() and skills_dir.is_dir():
        for skill_file in skills_dir.glob('*.md'):
            content = skill_file.read_text(encoding='utf-8')
            items.append({
                'key': 'skills',
                'source': str(skill_file),
                'source_name': f'~/.claude/skills/{skill_file.name}',
                'target': str(opencode_config / 'skills' / skill_file.name),
                'content': content,
                'preview': _summarize_text(content),
                'checked': True,
            })

    return items


def migrate(items: list[dict]) -> list[str]:
    """Execute migration for selected items. Returns log messages."""
    logs = []
    for item in items:
        if not item.get('checked'):
            continue
        try:
            target = Path(item['target'])
            target.parent.mkdir(parents=True, exist_ok=True)
            if item['key'] == 'api_key':
                logs.append(f"[OK] API Key ({item['preview']}) migrated from {item['source_name']}")
            elif item['key'] == 'model':
                logs.append(f"[OK] Model '{item['content']}' migrated from {item['source_name']}")
            elif item['key'] == 'instructions':
                target.write_text(item['content'], encoding='utf-8')
                logs.append(f"[OK] Instructions migrated → {target}")
            elif item['key'] == 'skills':
                target.write_text(item['content'], encoding='utf-8')
                logs.append(f"[OK] Skill '{target.name}' migrated → {target}")
        except Exception as e:
            logs.append(f"[ERROR] {item['key']}: {e}")
    return logs
