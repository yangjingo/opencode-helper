"""Generate and write opencode.jsonc configuration."""
import os, json
from pathlib import Path

CONFIG_TEMPLATE = """{{
  "$schema": "https://opencode.ai/config.json",

  // {display_name}
  "provider": {{
    "{provider_name}": {{
      "name": "{display_name}",
      "options": {{
        "apiKey": "{api_key}",
        "baseURL": "{base_url}"
      }},
      "models": {{
        "{model_id}": {{
          "name": "{model_name}",
          "reasoning": {reasoning},
          "thinking": {thinking}
        }}
      }}
    }}
  }},

  "model": "{provider_name}/{model_id}",

  "autoupdate": true
}}"""


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
    return CONFIG_TEMPLATE.format(
        provider_name=state.provider_name,
        display_name=state.display_name,
        api_key=state.api_key,
        base_url=state.base_url,
        model_id=state.model_id,
        model_name=state.model_name,
        reasoning=str(state.reasoning).lower(),
        thinking=str(state.thinking).lower(),
    )

def write_config(content: str, path: str = None) -> str:
    if path is None:
        config_dir = Path.home() / '.config' / 'opencode'
        config_dir.mkdir(parents=True, exist_ok=True)
        path = str(config_dir / 'opencode.jsonc')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
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
