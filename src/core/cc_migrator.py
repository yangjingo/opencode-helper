"""Discover Claude Code configuration and migrate the parts OpenCode can use.

Claude's settings are layered.  This module reads every user/project/local
layer, applies the documented precedence, and never mistakes a model alias
(``sonnet``) for a provider model ID.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable
from urllib.parse import urlparse
from core.config_writer import sanitize_model_id


def _mask_key(key: str) -> str:
    if len(key) <= 10:
        return key[:3] + '•••'
    return key[:6] + '••••••••' + key[-4:]


def _summarize_text(text: str, max_len: int = 60) -> str:
    first_line = text.strip().split('\n')[0] if text.strip() else '(empty)'
    return first_line[:max_len] + ('…' if len(first_line) > max_len else '')


def _opencode_endpoint(base_url: str, api_style: str) -> tuple[str, str]:
    """Translate a Claude-only endpoint into its OpenCode-native equivalent.

    GLM Coding Plan exposes ``/api/anthropic`` for Claude Code, but OpenCode
    has its own built-in Zhipu provider and must use the Coding API endpoint.
    Keeping the Claude URL during migration creates an unnecessary custom
    Anthropic provider instead of a native OpenCode configuration.
    """
    try:
        parsed = urlparse(base_url)
        path = parsed.path.rstrip('/')
        if parsed.hostname == 'open.bigmodel.cn' and path == '/api/anthropic':
            return 'https://open.bigmodel.cn/api/coding/paas/v4', ''
    except ValueError:
        pass
    return base_url, api_style


def _read_json(path: Path) -> tuple[dict, str, bool]:
    if not path.exists():
        return {}, '', False
    try:
        raw = path.read_text(encoding='utf-8')
        value = json.loads(raw)
        return (value if isinstance(value, dict) else {}), raw, isinstance(value, dict)
    except (OSError, json.JSONDecodeError):
        return {}, '', False


def settings_sources(home: Path | None = None, cwd: Path | None = None) -> list[dict]:
    """Return known settings sources in low-to-high precedence order."""
    home, cwd = home or Path.home(), cwd or Path.cwd()
    locations = [
        ('user', home / '.claude' / 'settings.json'),
        ('project', cwd / '.claude' / 'settings.json'),
        ('local', cwd / '.claude' / 'settings.local.json'),
    ]
    sources = []
    for scope, path in locations:
        settings, raw, readable = _read_json(path)
        sources.append({'scope': scope, 'path': path, 'settings': settings,
                        'raw': raw, 'readable': readable, 'exists': path.exists()})
    return sources


def effective_settings(home: Path | None = None, cwd: Path | None = None) -> tuple[dict, list[dict]]:
    """Shallow-merge settings layers; ``env`` is merged independently."""
    merged, sources = {}, settings_sources(home, cwd)
    merged_env = {}
    merged_mcp = {}
    for source in sources:
        value = source['settings']
        merged.update({key: val for key, val in value.items() if key not in {'env', 'mcpServers'}})
        env = value.get('env', {})
        if isinstance(env, dict):
            merged_env.update({key: str(val) for key, val in env.items() if val is not None})
        mcp_servers = value.get('mcpServers', {})
        if isinstance(mcp_servers, dict):
            merged_mcp.update({key: val for key, val in mcp_servers.items() if isinstance(val, dict)})
    if merged_env:
        merged['env'] = merged_env
    if merged_mcp:
        merged['mcpServers'] = merged_mcp
    return merged, sources


def extract_profile(runtime_env: dict | None = None, home: Path | None = None,
                    cwd: Path | None = None) -> dict:
    """Extract credentials, endpoint and real model with an explicit source.

    Process environment wins because it is what the currently running Claude
    process uses.  ``settings.local.json`` then overrides project and user
    settings, matching Claude Code's documented precedence.
    """
    settings, sources = effective_settings(home, cwd)
    env = dict(settings.get('env', {}))
    env.update(runtime_env or {})
    key = (env.get('ANTHROPIC_API_KEY') or env.get('CLAUDE_CODE_API_KEY') or
           env.get('ANTHROPIC_AUTH_TOKEN') or settings.get('apiKey', ''))
    anthropic_base_url = env.get('ANTHROPIC_BASE_URL', '')
    base_url = anthropic_base_url or settings.get('baseURL', '')
    model = (env.get('ANTHROPIC_MODEL') or env.get('ANTHROPIC_DEFAULT_SONNET_MODEL') or
             env.get('ANTHROPIC_DEFAULT_OPUS_MODEL') or env.get('ANTHROPIC_DEFAULT_HAIKU_MODEL') or '')
    # Claude aliases such as sonnet/opus/haiku are selections, not model IDs.
    alias = str(settings.get('model', ''))
    if not model and alias and alias.lower() not in {'sonnet', 'opus', 'haiku', 'default'}:
        model = alias
    api_style = 'anthropic' if anthropic_base_url else ''
    base_url, api_style = _opencode_endpoint(str(base_url), api_style)
    return {'api_key': str(key), 'base_url': str(base_url), 'model_id': sanitize_model_id(str(model)),
            # ANTHROPIC_BASE_URL is a Claude Code contract, not merely a URL
            # hint. Gateways often expose /v1 without the word "anthropic".
            'api_style': api_style,
            'model_alias': alias, 'settings': settings, 'sources': sources}


def _item(key: str, source: Path, source_name: str, target: Path, content: str, preview: str,
          checked: bool = True, action: str = 'copy') -> dict:
    return {'key': key, 'source': str(source.resolve()), 'source_name': source_name, 'target': str(target.resolve()),
            'content': content, 'preview': preview, 'checked': checked, 'action': action}


def scan() -> list[dict]:
    """Return credentials and portable instruction/skill migration candidates."""
    home, cwd = Path.home(), Path.cwd()
    profile = extract_profile(home=home, cwd=cwd)
    target_root = home / '.config' / 'opencode'
    items: list[dict] = []
    source_label = 'Claude settings (effective precedence)'
    if profile['api_key']:
        items.append(_item('api_key', home / '.claude' / 'settings.json', source_label,
                           target_root / 'opencode.jsonc', profile['api_key'], _mask_key(profile['api_key']),
                           action='configure'))
    if profile['base_url']:
        items.append(_item('base_url', home / '.claude' / 'settings.json', source_label,
                           target_root / 'opencode.jsonc', profile['base_url'], profile['base_url'], action='configure'))
    if profile['model_id']:
        items.append(_item('model', home / '.claude' / 'settings.json', source_label,
                           target_root / 'opencode.jsonc', profile['model_id'], profile['model_id'], action='configure'))
    mcp_servers = profile.get('settings', {}).get('mcpServers', {})
    if isinstance(mcp_servers, dict) and mcp_servers:
        names = ', '.join(str(name) for name in mcp_servers)
        items.append(_item('mcp', home / '.claude' / 'settings.json', source_label,
                           target_root / 'opencode.jsonc', json.dumps(mcp_servers, ensure_ascii=False),
                           f'{len(mcp_servers)} 个 MCP: {names}', action='configure'))

    # OpenCode accepts instructions through its config; preserve scope by copying
    # global memory to the global config directory and project memory in place.
    for path, label, target in [
        (home / '.claude' / 'CLAUDE.md', '~/.claude/CLAUDE.md', target_root / 'CLAUDE.md'),
        (cwd / 'CLAUDE.md', 'CLAUDE.md', cwd / '.opencode' / 'CLAUDE.md'),
        (cwd / '.claude' / 'CLAUDE.md', '.claude/CLAUDE.md', cwd / '.opencode' / 'CLAUDE.md'),
        (cwd / 'CLAUDE.local.md', 'CLAUDE.local.md', cwd / '.opencode' / 'CLAUDE.local.md'),
    ]:
        if path.exists() and path.is_file():
            content = path.read_text(encoding='utf-8')
            items.append(_item('instructions', path, label, target, content, _summarize_text(content)))

    # OpenCode already discovers Claude-compatible skill directories.  Copying
    # global skills to its native global path makes the conversion durable;
    # project skills are left in place and reported as compatible.
    for root, label, target_base, action in [
        (home / '.claude' / 'skills', '~/.claude/skills', target_root / 'skills', 'copy'),
        (cwd / '.claude' / 'skills', '.claude/skills', cwd / '.claude' / 'skills', 'compatible'),
    ]:
        if root.is_dir():
            for skill in root.glob('*/SKILL.md'):
                content = skill.read_text(encoding='utf-8')
                target = target_base / skill.parent.name / 'SKILL.md'
                items.append(_item('skills', skill, f'{label}/{skill.parent.name}/SKILL.md', target,
                                   content, _summarize_text(content), action=action))
    return items


def migrate(items: Iterable[dict]) -> list[str]:
    """Copy selected portable artifacts. Config values are consumed by the UI."""
    logs = []
    for item in items:
        if not item.get('checked'):
            continue
        try:
            if item.get('action') == 'configure':
                logs.append(f"[READY] {item['key']} prepared for OpenCode configuration")
                continue
            if item.get('action') == 'compatible':
                logs.append(f"[OK] {item['source_name']} is already OpenCode-compatible")
                continue
            target = Path(item['target'])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item['content'], encoding='utf-8')
            logs.append(f"[OK] {item['key']} migrated → {target}")
        except OSError as exc:
            logs.append(f"[ERROR] {item['key']}: {exc}")
    return logs


def _convert_mcp_servers(settings: dict) -> dict:
    """Convert Claude ``mcpServers`` entries to OpenCode's ``mcp`` schema."""
    converted = {}
    servers = settings.get('mcpServers', {}) if isinstance(settings, dict) else {}
    if not isinstance(servers, dict):
        return converted
    for name, server in servers.items():
        if not isinstance(server, dict):
            continue
        if server.get('url'):
            entry = {'type': 'remote', 'url': str(server['url']), 'enabled': True}
            if isinstance(server.get('headers'), dict) and server['headers']:
                entry['headers'] = server['headers']
        elif server.get('command'):
            args = server.get('args', [])
            command = [str(server['command'])]
            if isinstance(args, list):
                command.extend(str(arg) for arg in args)
            entry = {'type': 'local', 'command': command, 'enabled': True}
            if isinstance(server.get('env'), dict) and server['env']:
                entry['environment'] = {str(key): str(value) for key, value in server['env'].items()}
        else:
            continue
        converted[str(name)] = entry
    return converted


def migrate_profile_to_opencode(profile: dict, selected_keys: set[str] | None = None,
                                path: str | None = None) -> dict:
    """Convert an effective Claude profile and immediately write OpenCode config.

    This is the durable part of the migration. The old UI only copied values
    into transient wizard state, so closing the helper before the model page
    left ``opencode.jsonc`` unchanged. Known providers may supply a documented
    default model when Claude only stores an alias such as ``sonnet``.
    """
    from core.config_writer import generate_config, write_config
    from core.provider_catalog import resolve_provider
    from core.providers import get_provider_config, resolve_test_model

    selected = selected_keys if selected_keys is not None else {'api_key', 'base_url', 'model', 'mcp'}
    converted_mcp = (_convert_mcp_servers(profile.get('settings', {}))
                     if 'mcp' in selected else {})
    base_url = str(profile.get('base_url', '')) if 'base_url' in selected else ''
    if not base_url and not converted_mcp:
        return {'written': False, 'reason': 'missing_base_url'}

    detected_model = sanitize_model_id(str(profile.get('model_id', '')))
    if detected_model and 'model' not in selected:
        model_id = ''
    else:
        model_id = detected_model or (resolve_test_model(get_provider_config(base_url), '') if base_url else '')
    if base_url and (not model_id or model_id == 'unknown') and not converted_mcp:
        return {'written': False, 'reason': 'missing_model'}

    api_style = str(profile.get('api_style', ''))
    spec = resolve_provider(base_url, api_style=api_style) if base_url else None
    api_key = str(profile.get('api_key', '')) if 'api_key' in selected else ''
    generated = {'$schema': 'https://opencode.ai/config.json'}
    if base_url and model_id:
        state = SimpleNamespace(
            provider_name=spec.provider_id,
            display_name=spec.display_name,
            api_key=api_key,
            base_url=base_url,
            api_style=api_style,
            model_id=model_id,
            model_name=model_id,
            reasoning=True,
            thinking=True,
        )
        generated = json.loads(generate_config(state))
    if converted_mcp:
        generated['mcp'] = converted_mcp
    config_path = write_config(json.dumps(generated, ensure_ascii=False), path)
    result = {
        'written': True,
        'path': config_path,
        'api_key': api_key,
        'base_url': base_url,
        'api_style': api_style,
        'model_id': model_id,
        'mcp_names': list(converted_mcp),
    }
    if spec and model_id:
        result.update({
            'provider_name': spec.provider_id,
            'display_name': spec.display_name,
            'model_ref': f'{spec.provider_id}/{model_id}',
        })
    return result
