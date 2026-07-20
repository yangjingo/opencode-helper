"""Claude Code configuration migration page — full settings.json display + migration toggles."""
import os
import tkinter as tk, json
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, PixelToggle, BasePage, ScrollableFrame
from i18n import t
from core import cc_migrator
from core.detector import detect_claude_env_vars, detect_claude_config, _mask_key
from core.cc_migrator import extract_profile
from core.provider_catalog import resolve_provider

KEY_ICONS = {'api_key': '🔑', 'model': '🤖', 'mcp': '🔌', 'instructions': '📋', 'skills': '🛠'}
KEY_LABELS = {'api_key': 'API Key', 'model': 'Default Model', 'mcp': 'MCP Servers',
              'instructions': 'Instructions', 'skills': 'Skill'}

class MigrationPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'migration'
        app.set_key_hint('[Enter]迁移  [Esc]跳过  [1-9]切换选项')

        self.items = cc_migrator.scan()
        self.vars = []
        self._claude_config = detect_claude_config()

        # Header
        tk.Label(self, text=f'🔍 {t("migration.title")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 3))
        count_hint = f'发现 {len(self.items)} 项可迁移配置' if self.items else '未检测到可迁移配置'
        tk.Label(self, text=count_hint, bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack()
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack(pady=(4, 0))

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(pady=5, padx=15, fill='both', expand=True)

        # ── Section 1: Claude Code 环境变量 ──
        claude_env = detect_claude_env_vars().get('claude_env_vars', {})
        if claude_env:
            self._section_header('📋 Claude Code 环境变量')
            self._env_vars_terminal(claude_env)
        else:
            self._section_header('📋 Claude Code 环境变量')
            tk.Label(self.scroll.inner, text='    未检测到 Claude Code 环境变量', bg=COLORS['bg'],
                     fg=COLORS['dark_gray'], font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=20)

        # ── Section 2: settings.json 完整内容 ──
        # User-level ~/.claude/settings.json
        user_settings = self._claude_config.get('claude_settings', {})
        user_raw = self._claude_config.get('claude_settings_raw', '')
        user_path = self._claude_config.get('claude_settings_path', '')
        user_readable = self._claude_config.get('claude_settings_readable', False)

        if user_path:
            self._section_header('📁 ~/.claude/settings.json')
            self._json_terminal(user_raw, user_path, user_readable)
        else:
            self._section_header('📁 ~/.claude/settings.json')
            tk.Label(self.scroll.inner, text='    文件不存在', bg=COLORS['bg'],
                     fg=COLORS['dark_gray'], font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=20)

        # Project-level .claude/settings.json
        project_settings = self._claude_config.get('project_settings', {})
        project_raw = self._claude_config.get('project_settings_raw', '')
        project_path = self._claude_config.get('project_claude_path', '')
        project_readable = self._claude_config.get('project_settings_readable', False)

        if project_path and (project_raw or project_settings):
            proj_file = project_path + '/settings.json'
            self._section_header(f'📁 {proj_file}')
            self._json_terminal(project_raw, proj_file, project_readable)

        # ── Section 3: 可迁移的项目 ──
        if self.items:
            self._section_header('🔄 可迁移的项目')
            for idx, item in enumerate(self.items):
                self._migration_card(item, idx)
        else:
            self._section_header('🔄 可迁移的项目')
            tk.Label(self.scroll.inner, text='    未检测到可迁移配置', bg=COLORS['bg'],
                     fg=COLORS['dark_gray'], font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=20)

        # ── Bottom buttons ──
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("migration.skip")} ]', command=self._on_skip).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ ▶  {t("migration.migrate")}  ]', command=self._on_migrate).pack(side='left', padx=5)

    # ── JSON terminal block (same style as environment page) ─────────────────

    def _json_terminal(self, raw: str, path: str, readable: bool):
        """Display a settings.json file as a pixel terminal code block."""
        if not raw and not readable:
            tk.Label(self.scroll.inner, text='    (文件为空或不可读)', bg=COLORS['bg'],
                     fg=COLORS['dark_gray'], font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=25)
            return

        term = tk.Frame(self.scroll.inner, bg=COLORS['black'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', padx=10, pady=3)

        # Title bar
        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=18)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text=f'┌── {path} ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)
        tk.Label(bar, text='JSON', bg=COLORS['dark_gray'], fg=COLORS['dark_gray'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='right', padx=6)

        # Content
        line_count = raw.count('\n') + 1
        text = tk.Text(term, height=min(14, line_count + 1), bg=COLORS['black'],
                      fg=COLORS['neon_green'], insertbackground=COLORS['neon_green'],
                      font=(FONTS['log']['family'], FONTS['log']['size']),
                      relief='flat', padx=8, pady=4, wrap='none', state='disabled')
        text.pack(fill='x')

        text.configure(state='normal')
        try:
            parsed = json.loads(raw)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            # Mask API keys in display
            for line in formatted.split('\n'):
                line_lower = line.lower()
                if any(marker in line_lower for marker in ('apikey', 'api_key', 'token', 'secret')):
                    # Mask the value part
                    if ':' in line:
                        key_part, val_part = line.split(':', 1)
                        val_stripped = val_part.strip().strip('"').strip(',')
                        if len(val_stripped) > 8:
                            masked = val_stripped[:6] + '••••••••' + val_stripped[-4:]
                        else:
                            masked = '••••••••'
                        line = f'{key_part}: "{masked}",'
                text.insert('end', line + '\n')
        except Exception:
            text.insert('end', raw[:3000])

        text.configure(state='disabled')

        # Bottom bar
        bot = tk.Frame(term, bg=COLORS['dark_gray'], height=3)
        bot.pack(fill='x')

    # ── Env vars terminal block ──────────────────────────────────────────────

    def _env_vars_terminal(self, env_vars: dict):
        """Display Claude/LLM env vars in a pixel terminal block."""
        term = tk.Frame(self.scroll.inner, bg=COLORS['black'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', pady=4, padx=5)

        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=18)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='┌── environment variables ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)

        inner = tk.Frame(term, bg=COLORS['black'])
        inner.pack(fill='x', padx=8, pady=4)

        for var_name, var_value in env_vars.items():
            row = tk.Frame(inner, bg=COLORS['black'])
            row.pack(fill='x', pady=1)
            tk.Label(row, text=f'$env:{var_name}', bg=COLORS['black'], fg=COLORS['yellow'],
                     font=(FONTS['log']['family'], FONTS['log']['size'], 'bold'), width=30, anchor='w').pack(side='left')
            tk.Label(row, text='=', bg=COLORS['black'], fg=COLORS['white'],
                     font=(FONTS['log']['family'], FONTS['log']['size'])).pack(side='left')
            if any(k in var_name.upper() for k in ['API_KEY', 'AUTH_TOKEN', 'TOKEN']):
                display_val = _mask_key(var_value)
            else:
                display_val = var_value if len(var_value) <= 50 else var_value[:47] + '...'
            tk.Label(row, text=display_val, bg=COLORS['black'], fg=COLORS['neon_green'],
                     font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w').pack(side='left', padx=4)

    # ── Migration item card ──────────────────────────────────────────────────

    def _migration_card(self, item: dict, idx: int):
        """Render a single migration item in a pixel card."""
        card = tk.Frame(self.scroll.inner, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        card.pack(fill='x', pady=3, padx=5)

        var = tk.BooleanVar(value=item['checked'])
        self.vars.append(var)

        header = tk.Frame(card, bg=COLORS['dark_gray'])
        header.pack(fill='x', padx=10, pady=(6, 2))
        icon = KEY_ICONS.get(item['key'], '📄')
        label = KEY_LABELS.get(item['key'], item['key'])
        skill_name = ''
        if item['key'] == 'skills':
            # A skill's directory name is its canonical Claude/OpenCode name.
            skill_name = os.path.basename(os.path.dirname(item.get('source', '')))
            label = f'Skill: {skill_name or "(unnamed)"}'
        PixelToggle(header, text=f'{icon}  {label}', variable=var).pack(side='left')

        self.app.root.bind(str(idx + 1), lambda e, v=var: v.set(not v.get()))

        preview = item.get('preview', '')
        preview_color = COLORS['yellow'] if item['key'] == 'api_key' else COLORS['neon_green']

        if item['key'] == 'skills':
            tk.Label(card, text=f'     名称: {skill_name or "(unnamed)"}', bg=COLORS['dark_gray'],
                     fg=COLORS['neon_green'], font=(FONTS['body']['family'], FONTS['body']['size'], 'bold'),
                     anchor='w').pack(fill='x', padx=10)
            tk.Label(card, text=f'     {preview}', bg=COLORS['dark_gray'], fg=COLORS['white'],
                     font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w',
                     wraplength=550, justify='left').pack(fill='x', padx=10)
        elif item['key'] in ('api_key', 'model'):
            tk.Label(card, text=f'     {preview}', bg=COLORS['dark_gray'], fg=preview_color,
                     font=(FONTS['body']['family'], FONTS['body']['size'], 'bold'),
                     anchor='w').pack(fill='x', padx=10)
        else:
            tk.Label(card, text=f'     {preview}', bg=COLORS['dark_gray'], fg=COLORS['white'],
                     font=(FONTS['body']['family'], FONTS['body']['size']), anchor='w',
                     wraplength=550, justify='left').pack(fill='x', padx=10)

        src_frame = tk.Frame(card, bg=COLORS['dark_gray'])
        src_frame.pack(fill='x', padx=10, pady=(2, 6))
        source_text = os.path.abspath(item['source']) if item['key'] == 'skills' else item['source_name']
        source_prefix = '绝对路径' if item['key'] == 'skills' else '📁'
        tk.Label(src_frame, text=f'     {source_prefix}: {source_text}  →  {item["target"]}',
                 bg=COLORS['dark_gray'], fg=COLORS['dark_gray'],
                 font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w').pack(fill='x')

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _section_header(self, text: str):
        tk.Frame(self.scroll.inner, bg=COLORS['bg'], height=6).pack()
        tk.Label(self.scroll.inner, text=text, bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=15, pady=(8, 4))

    # ── Navigation ───────────────────────────────────────────────────────────

    def _on_skip(self):
        from ui.pages.environment import EnvironmentPage
        self.app.show_page(EnvironmentPage, 'environment')

    def _on_migrate(self):
        s = self.app.state
        for i, var in enumerate(self.vars):
            self.items[i]['checked'] = var.get()

        # Execute portable file migration first.
        cc_migrator.migrate(self.items)
        s.migration_items = self.items

        # Populate exactly the same effective profile shown on this page.
        profile = extract_profile(runtime_env=os.environ)
        selected = {item['key'] for item in self.items if item.get('checked')}
        migration = cc_migrator.migrate_profile_to_opencode(profile, selected)
        if migration.get('written'):
            if migration.get('base_url'):
                s.api_key = migration['api_key']
                s.base_url = migration['base_url']
                s.api_style = migration['api_style']
                s.model_id = migration['model_id']
                s.model_name = migration['model_id']
                s.provider_name = migration['provider_name']
                s.display_name = migration['display_name']
        else:
            # Preserve partial values for the model page when a custom Claude
            # gateway lacks enough information for an automatic write.
            if 'api_key' in selected and profile['api_key']:
                s.api_key = profile['api_key']
            if 'base_url' in selected and profile['base_url']:
                s.base_url = profile['base_url']
                s.api_style = profile['api_style']
            if 'model' in selected and profile['model_id']:
                s.model_id = profile['model_id']
            spec = resolve_provider(s.base_url, s.provider_name, s.api_style)
            s.provider_name = spec.provider_id
            if not s.display_name:
                s.display_name = spec.display_name

        from ui.pages.environment import EnvironmentPage
        self.app.show_page(EnvironmentPage, 'environment')

    def _on_key_next(self):
        self._on_migrate()

    def _on_key_back(self):
        self._on_skip()

    def _on_key_number(self, n: int):
        if 1 <= n <= len(self.vars):
            self.vars[n-1].set(not self.vars[n-1].get())
