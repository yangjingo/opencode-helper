"""Generate and write a valid OpenCode configuration."""
import os, json, re
from pathlib import Path
from core.provider_catalog import resolve_provider, normalize_provider_id


def sanitize_model_id(value: str) -> str:
    """Remove terminal color fragments accidentally pasted into a model ID."""
    model = str(value or '').strip()
    model = re.sub(r'\x1b\[[0-9;]*m', '', model)
    return re.sub(r'\[[0-9;]+m\]?$', '', model).strip()

def _clean_jsonc(content: str) -> str:
    """Remove comments from JSONC content, preserving URLs."""
    lines = []
    for line in content.split('\n'):
        # Only strip // comments that appear after non-string characters
        in_string = False
        cleaned = []
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_string = not in_string
                cleaned.append(line[i])
            elif line[i:i+2] == '//' and not in_string:
                break
            else:
                cleaned.append(line[i])
            i += 1
        lines.append(''.join(cleaned))
    return '\n'.join(lines)

def generate_config(state) -> str:
    """Create configuration using the adapter appropriate for the endpoint.

    ``json.dumps`` deliberately replaces string interpolation: API keys, URLs,
    and model names can contain quotes and must never make the config invalid.
    """
    spec = resolve_provider(getattr(state, 'base_url', ''), getattr(state, 'provider_name', ''),
                            getattr(state, 'api_style', ''))
    provider_id = spec.provider_id if getattr(state, 'base_url', '') else normalize_provider_id(getattr(state, 'provider_name', 'custom'))
    display_name = getattr(state, 'display_name', '') or spec.display_name
    model_id = sanitize_model_id(getattr(state, 'model_id', '')) or 'default'
    options = {}
    if getattr(state, 'api_key', ''):
        options['apiKey'] = state.api_key
    if getattr(state, 'base_url', '') and not spec.native_api:
        options['baseURL'] = state.base_url.rstrip('/')

    provider = {'name': display_name, 'models': {model_id: {
        'name': sanitize_model_id(getattr(state, 'model_name', '')) or model_id,
        'reasoning': bool(getattr(state, 'reasoning', False)),
        'thinking': bool(getattr(state, 'thinking', False)),
    }}}
    if spec.native_api:
        provider['api'] = spec.native_api
    if options:
        provider['options'] = options
    if spec.npm:
        provider['npm'] = spec.npm

    config = {
        '$schema': 'https://opencode.ai/config.json',
        'provider': {provider_id: provider},
        'model': f'{provider_id}/{model_id}',
        'autoupdate': True,
    }
    return json.dumps(config, ensure_ascii=False, indent=2) + '\n'

def write_config(content: str, path: str = None) -> str:
    """Write generated JSONC without discarding providers already configured.

    A migration normally adds one selected model. Replacing the entire file
    would silently remove other working providers. OpenCode login credentials
    live in ``auth.json`` and are intentionally never read or written here.
    """
    if path is None:
        config_dir = Path.home() / '.config' / 'opencode'
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / 'opencode.jsonc')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generated = json.loads(_clean_jsonc(content))
    target = Path(path)
    if target.exists():
        try:
            existing = json.loads(_clean_jsonc(target.read_text(encoding='utf-8')))
            if isinstance(existing, dict):
                merged = existing.copy()
                current_providers = existing.get('provider', {})
                added_providers = generated.get('provider', {})
                if isinstance(current_providers, dict) and isinstance(added_providers, dict):
                    current_providers = current_providers.copy()
                    # Remove the obsolete configuration produced by older
                    # Claude migrations once the native OpenCode Zhipu provider
                    # is being written. Other unrelated providers are retained.
                    if 'zhipuai' in added_providers:
                        for provider_id, provider in list(current_providers.items()):
                            if provider_id not in {'zhipu', 'glm'} or not isinstance(provider, dict):
                                continue
                            options = provider.get('options', {})
                            old_url = str(options.get('baseURL', '')) if isinstance(options, dict) else ''
                            if ('open.bigmodel.cn/api/anthropic' in old_url and
                                    provider.get('npm') == '@ai-sdk/anthropic'):
                                current_providers.pop(provider_id, None)
                    merged['provider'] = {**current_providers, **added_providers}
                current_mcp = existing.get('mcp', {})
                added_mcp = generated.get('mcp', {})
                if isinstance(current_mcp, dict) and isinstance(added_mcp, dict) and added_mcp:
                    merged['mcp'] = {**current_mcp, **added_mcp}
                # The selected model and generated schema/autoupdate values are
                # explicit user choices, so they take priority.
                merged.update({key: value for key, value in generated.items() if key not in {'provider', 'mcp'}})
                generated = merged
        except (OSError, json.JSONDecodeError):
            # A hand-edited invalid config must not prevent a new valid config
            # from being written.
            pass
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(generated, ensure_ascii=False, indent=2) + '\n')
    return path

DEFAULT_PRESETS = {
    "presets": [{
        "name": "OpenLab GLM-5.2", "provider": "openlab", "displayName": "OpenLab",
        "baseURL": "http://<IP:PORT>/v1", "modelId": "glm-5.2", "modelName": "GLM 5.2",
        "reasoning": True, "thinking": True,
    }]
}

def create_presets_file() -> str:
    config_dir = Path.home() / '.config' / 'opencode-helper'
    config_dir.mkdir(parents=True, exist_ok=True)
    presets_path = config_dir / 'presets.json'
    if not presets_path.exists():
        presets_path.write_text(json.dumps(DEFAULT_PRESETS, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(presets_path)

def load_presets() -> dict:
    presets_path = Path.home() / '.config' / 'opencode-helper' / 'presets.json'
    if not presets_path.exists():
        create_presets_file()
    return json.loads(presets_path.read_text(encoding='utf-8'))
