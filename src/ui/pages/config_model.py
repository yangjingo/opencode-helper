"""Model configuration form page — auto-detects env vars + settings.json + dynamic presets."""
import tkinter as tk
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, PixelEntry, PixelToggle, BasePage
from i18n import t
from core.detector import detect_claude_env_vars, detect_claude_config

# No hardcoded presets — only what the user actually has

class ConfigModelPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'config_model'
        s = app.state
        app.set_key_hint('[Enter]下一步  [Esc]返回  [T]测试连接')

        # ── Auto-detect from 3 sources ──
        # 1. Environment variables (HIGHEST)
        claude_env = detect_claude_env_vars().get('claude_env_vars', {})
        env_api_key = (claude_env.get('ANTHROPIC_API_KEY', '')
                       or claude_env.get('CLAUDE_CODE_API_KEY', '')
                       or claude_env.get('ANTHROPIC_AUTH_TOKEN', ''))
        env_base_url = claude_env.get('ANTHROPIC_BASE_URL', '')
        env_model = (claude_env.get('ANTHROPIC_MODEL', '')
                     or claude_env.get('ANTHROPIC_DEFAULT_SONNET_MODEL', '')
                     or claude_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL', ''))

        if env_api_key:
            s.api_key = env_api_key
        if env_base_url:
            s.base_url = env_base_url
        if env_model:
            s.model_id = env_model

        # 2. ~/.claude/settings.json + project settings
        cc = detect_claude_config()
        for settings_src in [cc.get('claude_settings', {}), cc.get('project_settings', {})]:
            if not settings_src:
                continue
            # Top-level keys (fallback only — env object wins below)
            if not s.api_key and 'apiKey' in settings_src:
                s.api_key = settings_src['apiKey']
            if not s.base_url and 'baseURL' in settings_src:
                s.base_url = settings_src['baseURL']

            # Nested env object — this IS the real config, overwrites top-level
            nested_env = settings_src.get('env', {})
            if isinstance(nested_env, dict):
                env_key = (nested_env.get('ANTHROPIC_API_KEY', '')
                           or nested_env.get('ANTHROPIC_AUTH_TOKEN', '')
                           or nested_env.get('CLAUDE_CODE_API_KEY', ''))
                env_url = nested_env.get('ANTHROPIC_BASE_URL', '')
                env_model = (nested_env.get('ANTHROPIC_DEFAULT_SONNET_MODEL', '')
                             or nested_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL', '')
                             or nested_env.get('ANTHROPIC_MODEL', ''))
                if env_key:
                    s.api_key = env_key
                if env_url:
                    s.base_url = env_url
                if env_model:
                    s.model_id = env_model  # overwrites top-level 'model'!

        # Derive provider_name from base_url if still empty
        # Order matters: bigmodel/glm must precede anthropic, since GLM's
        # Anthropic-compatible URL (open.bigmodel.cn/api/anthropic) contains
        # the substring 'anthropic'.
        if not s.provider_name and s.base_url:
            for hint in ['bigmodel', 'glm', 'zhipu', 'dashscope', 'alibaba',
                         'aliyun', 'qwen', 'deepseek', 'openlab', 'openai',
                         'anthropic']:
                if hint in s.base_url.lower():
                    s.provider_name = hint
                    break
        if not s.provider_name:
            s.provider_name = 'custom'

        # Auto-convert known provider base URLs (全部 Anthropic 兼容接口)
        _KNOWN_PROVIDERS = {
            # DeepSeek 官方 Anthropic 兼容接口
            'deepseek':  'https://api.deepseek.com/anthropic',
            # 智谱 GLM 的 Anthropic 兼容 endpoint（供 Claude / OpenCode 使用）
            'bigmodel':  'https://open.bigmodel.cn/api/anthropic',
            'glm':       'https://open.bigmodel.cn/api/anthropic',
            'zhipu':     'https://open.bigmodel.cn/api/anthropic',
            'openai':    'https://api.openai.com/v1',
            'anthropic': 'https://api.anthropic.com/v1',
            # 阿里百炼 Coding Plan 专属 endpoint
            'dashscope': 'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
            'alibaba':   'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
            'aliyun':    'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
            'qwen':      'https://coding.dashscope.aliyuncs.com/apps/anthropic/v1',
        }
        for key, target in _KNOWN_PROVIDERS.items():
            if key in s.base_url.lower() and s.base_url.rstrip('/') != target.rstrip('/'):
                s.base_url = target
                break

        # ── Build preset list: detected model + Custom template ──
        presets = []
        detected_name = s.model_id or ''

        if detected_name:
            presets.append((detected_name, {
                'provider': s.provider_name or '',
                'display': s.display_name or detected_name,
                'url': s.base_url or '',
                'model_id': s.model_id,
                'model_name': s.model_name or detected_name,
                'api_key': s.api_key or '',
                'reasoning': s.reasoning,
                'thinking': s.thinking,
            }))

        # Custom is a guided template with placeholder hints
        presets.append(('Custom', {
            'provider': '',
            'display': '',
            'url': '',
            'model_id': '',
            'model_name': '',
            'api_key': '',
            'reasoning': True,
            'thinking': True,
            '_placeholders': {
                'provider_name': '输入 Provider (如 deepseek, openlab)',
                'display_name': '显示名称 (如 DeepSeek)',
                'api_key': 'sk-your-api-key-here',
                'base_url': 'https://api.example.com/v1',
                'model_id': 'your-model-id',
                'model_name': '模型显示名称',
            }
        }))

        initial_preset = detected_name if detected_name else 'Custom'

        self._presets = presets

        # ── UI ──
        auto_fields = []
        if s.api_key:
            auto_fields.append('API Key')
        if s.model_id:
            auto_fields.append(f'Model ({s.model_id})')
        if s.base_url:
            auto_fields.append('Base URL')

        tk.Label(self, text=f'⚙ {t("config.title")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # Preset selector
        preset_frame = tk.Frame(self, bg=COLORS['bg'])
        preset_frame.pack(fill='x', padx=40, pady=(8, 5))
        tk.Label(preset_frame, text='Model:', bg=COLORS['bg'], fg=COLORS['white'],
                 font=(FONTS['body']['family'], FONTS['body']['size'])).pack(side='left')
        self.preset_var = tk.StringVar(value=initial_preset)
        preset_names = [p[0] for p in presets]
        preset_menu = tk.OptionMenu(preset_frame, self.preset_var, *preset_names, command=self._on_preset)
        preset_menu.configure(bg=COLORS['deep_purple'], fg=COLORS['neon_green'])
        preset_menu.pack(side='left', padx=5)

        # Auto-fill hint
        if auto_fields:
            hint = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
            hint.pack(fill='x', padx=40, pady=(0, 5))
            tk.Label(hint, text=f'🔄 已自动填入: {", ".join(auto_fields)}',
                     bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                     font=(FONTS['log']['family'], FONTS['log']['size'])).pack(padx=8, pady=(3, 0))
            if s.base_url:
                tk.Label(hint, text=f'⚠ Base URL 已自动转换: {s.base_url} ，请确认是否正确',
                         bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                         font=(FONTS['small']['family'], FONTS['small']['size'])).pack(padx=8, pady=(0, 3))

        # Form fields — use detected values, or empty (placeholders shown if Custom)
        has_detected = bool(detected_name)
        fields = [
            ('Provider Name:', 'provider_name', s.provider_name if has_detected else '', False),
            ('Display Name:', 'display_name', s.display_name if has_detected else '', False),
            ('API Key:', 'api_key', s.api_key if has_detected else '', False),
            ('Base URL:', 'base_url', s.base_url if has_detected else '', False),
            ('Model ID:', 'model_id', s.model_id if has_detected else '', False),
            ('Model Name:', 'model_name', s.model_name if has_detected else '', False),
        ]
        self.entries = {}
        for label_text, key, val, is_secret in fields:
            row = tk.Frame(self, bg=COLORS['bg'])
            row.pack(fill='x', padx=40, pady=3)
            tk.Label(row, text=label_text, bg=COLORS['bg'], fg=COLORS['white'],
                     font=(FONTS['body']['family'], FONTS['body']['size']), width=15, anchor='w').pack(side='left')
            entry = PixelEntry(row, show='*' if is_secret else None)
            entry.pack(side='left', fill='x', expand=True)
            if val:
                entry.delete(0, 'end')
                entry.insert(0, str(val))
                entry.configure(fg=COLORS['neon_green'])
            self.entries[key] = entry

        # If starting with Custom preset, show placeholder guidance
        if initial_preset == 'Custom':
            self._on_preset('Custom')

        # Toggles
        toggle_frame = tk.Frame(self, bg=COLORS['bg'])
        toggle_frame.pack(pady=8)
        self.reasoning_var = tk.BooleanVar(value=s.reasoning)
        self.thinking_var = tk.BooleanVar(value=s.thinking)
        PixelToggle(toggle_frame, text='Reasoning', variable=self.reasoning_var).pack(side='left', padx=10)
        PixelToggle(toggle_frame, text='Thinking', variable=self.thinking_var).pack(side='left', padx=10)

        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ 📋 预览 ]', command=self._on_preview).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("config.test")} ]', command=self._on_test).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next).pack(side='left', padx=5)

        # Preview area (hidden initially)
        self._preview_frame = tk.Frame(self, bg=COLORS['bg'])
        self._preview_visible = False

        app.root.bind('<KeyPress-t>', lambda e: self._on_test())
        app.root.bind('<KeyPress-T>', lambda e: self._on_test())

    def _on_preset(self, choice):
        for name, vals in self._presets:
            if name == choice:
                km = {'provider': 'provider_name', 'display': 'display_name', 'url': 'base_url',
                      'model_id': 'model_id', 'model_name': 'model_name', 'api_key': 'api_key'}
                placeholders = vals.get('_placeholders', {})
                s = self.app.state
                for k, v in vals.items():
                    if k.startswith('_'):
                        continue
                    mapped = km.get(k)
                    if mapped and mapped in self.entries:
                        self.entries[mapped].delete(0, 'end')
                        if v:
                            self.entries[mapped].insert(0, str(v))
                            self.entries[mapped].configure(fg=COLORS['neon_green'])
                        elif choice == 'Custom' and mapped in placeholders:
                            self.entries[mapped].insert(0, placeholders[mapped])
                            self.entries[mapped].configure(fg=COLORS['muted_soft'])
                        elif choice == 'Custom':
                            # No placeholder — leave empty
                            pass
                        else:
                            # Non-Custom, value empty — restore from state
                            fallback = getattr(s, mapped, '')
                            if fallback:
                                self.entries[mapped].insert(0, str(fallback))
                                self.entries[mapped].configure(fg=COLORS['neon_green'])
                self.reasoning_var.set(vals.get('reasoning', True))
                self.thinking_var.set(vals.get('thinking', True))
                break

    def _save_state(self):
        s = self.app.state
        # Collect all placeholder values to skip them on save
        placeholders = set()
        for _, vals in self._presets:
            for v in vals.get('_placeholders', {}).values():
                placeholders.add(v)

        def _val(key):
            v = self.entries[key].get()
            return '' if v in placeholders else v

        s.provider_name = _val('provider_name')
        s.display_name = _val('display_name')
        s.api_key = _val('api_key')
        s.base_url = _val('base_url')
        s.model_id = _val('model_id')
        s.model_name = _val('model_name')
        s.reasoning = self.reasoning_var.get()
        s.thinking = self.thinking_var.get()

        # provider_name is required — derive from base_url if empty
        # bigmodel/glm precede anthropic — GLM's URL contains 'anthropic'.
        if not s.provider_name and s.base_url:
            for hint in ['bigmodel', 'glm', 'zhipu', 'dashscope', 'alibaba',
                         'aliyun', 'qwen', 'deepseek', 'openlab', 'openai',
                         'anthropic']:
                if hint in s.base_url.lower():
                    s.provider_name = hint
                    break
        if not s.provider_name:
            s.provider_name = 'custom'
        if not s.display_name:
            s.display_name = s.provider_name

    def _on_preview(self):
        """Show the generated JSONC in a terminal block with copy button."""
        self._save_state()
        from core.config_writer import generate_config

        if self._preview_visible:
            self._preview_frame.pack_forget()
            self._preview_visible = False
            return

        jsonc = generate_config(self.app.state)

        # Clear previous preview
        for w in self._preview_frame.winfo_children():
            w.destroy()

        # Separator
        tk.Frame(self._preview_frame, bg=COLORS['neon_green'], height=1, width=500).pack(pady=(8, 4))

        # Terminal-style JSONC display
        term = tk.Frame(self._preview_frame, bg=COLORS['black'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', padx=30, pady=4)

        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=18)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='┌── opencode.jsonc preview ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)

        line_count = jsonc.count('\n') + 1
        text = tk.Text(term, height=min(12, line_count + 1), bg=COLORS['black'],
                      fg=COLORS['neon_green'], font=(FONTS['log']['family'], FONTS['log']['size']),
                      relief='flat', padx=8, pady=4, wrap='none')
        text.pack(fill='x')
        text.insert('1.0', jsonc)
        text.configure(state='disabled')

        # Copy button
        copy_frame = tk.Frame(self._preview_frame, bg=COLORS['bg'])
        copy_frame.pack(pady=4)
        PixelButton(copy_frame, text='[ 📋 一键复制 JSONC ]', command=lambda: self._on_copy(jsonc)).pack()

        self._preview_frame.pack(fill='x')
        self._preview_visible = True

    def _on_copy(self, content: str):
        """Copy JSONC content to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(content)
        # Brief visual feedback
        self._copy_feedback = tk.Label(self._preview_frame, text='✓ 已复制到剪贴板!',
                                       bg=COLORS['bg'], fg=COLORS['neon_green'],
                                       font=(FONTS['log']['family'], FONTS['log']['size']))
        self._copy_feedback.pack(pady=2)
        self.after(2000, self._clear_feedback)

    def _clear_feedback(self):
        if hasattr(self, '_copy_feedback') and self._copy_feedback:
            self._copy_feedback.destroy()
            self._copy_feedback = None

    def _on_test(self):
        self._save_state()
        from ui.pages.verify import VerifyPage
        self.app.show_page(VerifyPage, 'verify')

    def _on_next(self):
        self._save_state()
        from core.config_writer import generate_config, write_config
        write_config(generate_config(self.app.state))
        from core.proxy_manager import generate_launcher_scripts, write_shell_profile_wrapper
        generate_launcher_scripts(self.app.state.install_path, self.app.state.install_method)
        write_shell_profile_wrapper(self.app.state.install_method)
        from ui.pages.verify import VerifyPage
        self.app.show_page(VerifyPage, 'verify')

    def _on_key_next(self):
        self._on_next()

    def _on_key_number(self, n: int):
        if n == 1:
            self._on_test()
