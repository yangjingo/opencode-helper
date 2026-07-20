"""Environment detection results page — async detection with full settings display."""
import tkinter as tk
import threading, json
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage, ScrollableFrame
from i18n import t
from core.detector import detect_all, _mask_key, clear_cache

class EnvironmentPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'environment'
        self._pending_report = None
        app.set_key_hint('[Enter]继续  [Esc]返回  [R]重新检测')

        tk.Label(self, text=f'🔍 {t("env.title")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(pady=5, padx=15, fill='both', expand=True)

        self._loading_label = tk.Label(self.scroll.inner, text='⏳ 检测中...', bg=COLORS['bg'],
                                        fg=COLORS['yellow'], font=(FONTS['body']['family'], FONTS['body']['size']))
        self._loading_label.pack(pady=20)

        # One full-width action row: every control gets a grid column, so
        # “下一步” never leaves a large visual gap after the primary action.
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=6, fill='x', padx=12)
        for column in range(4):
            btn_frame.grid_columnconfigure(column, weight=1, uniform='environment-actions')

        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).grid(
            row=0, column=0, padx=3, sticky='ew')
        self.redetect_btn = PixelButton(btn_frame, text=f'[ {t("env.redetect")} ]', command=self._run_detection)
        self.redetect_btn.grid(row=0, column=1, padx=3, sticky='ew')
        self.primary_btn = PixelButton(btn_frame, text='[ 修复 / 安装 OpenCode ]', command=self._on_primary_action)
        self.primary_btn.grid(row=0, column=2, padx=3, sticky='ew')
        self.primary_btn.set_enabled(False)
        self.next_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next)
        self.next_btn.grid(row=0, column=3, padx=3, sticky='ew')
        self.next_btn.set_enabled(False)

        self._run_detection()
        app.root.bind('<KeyPress-r>', lambda e: self._run_detection())
        app.root.bind('<KeyPress-R>', lambda e: self._run_detection())

    def _run_detection(self):
        self.scroll.clear()
        self._pending_report = None
        self.next_btn.set_enabled(False)
        self.primary_btn.set_enabled(False)
        self._loading_label = tk.Label(self.scroll.inner, text='⏳ 检测中...', bg=COLORS['bg'],
                                        fg=COLORS['yellow'], font=(FONTS['body']['family'], FONTS['body']['size']))
        self._loading_label.pack(pady=20)
        self._dots = 0
        self._animate_loading()
        clear_cache()
        def _run():
            report = detect_all()
            self._pending_report = report
        threading.Thread(target=_run, daemon=True).start()
        self.after(100, self._poll_result)

    def _animate_loading(self):
        if not self._destroyed and not self._pending_report:
            try:
                self._dots = (self._dots + 1) % 4
                self._loading_label.configure(text='⏳ 检测中' + '.' * self._dots)
            except Exception:
                return
            self.after(300, self._animate_loading)

    def _poll_result(self):
        if self._destroyed:
            return
        try:
            if self._pending_report is not None:
                self._render_results(self._pending_report)
                self._pending_report = None
            else:
                self.after(100, self._poll_result)
        except Exception:
            pass

    # ── Render ───────────────────────────────────────────────────────────────

    def _render_results(self, report: dict):
        self._loading_label.destroy()
        self.app.state.env_report = report

        # ═══ System ═══
        self._section('💻 System')
        self._row_ok('OS', report['os_name'] + '  ' + report['os_version'], report['os_ok'])
        self._row_ok('Disk', f'{report["disk_free_gb"]} GB free', report['disk_ok'])

        # ═══ Runtime ═══
        self._section('📦 Runtime')
        # Node.js
        if report.get('node_installed'):
            node_val = f'{report["node_version"]}  @ {report.get("node_path", "")}'
        else:
            node_val = t('detect.not_installed')
        self._row_ok('Node.js', node_val, report.get('node_ok', False))
        # npm
        if report.get('npm_installed'):
            npm_val = f'v{report["npm_version"]}  @ {report.get("npm_path", "")}'
        else:
            npm_val = t('detect.not_installed')
        self._row_ok('npm', npm_val, report.get('npm_ok', False))
        # OpenCode
        if report.get('opencode_installed'):
            oc_ver = report.get('opencode_version', '')
            oc_path = report.get('opencode_path', '')
            if oc_ver:
                oc_val = f'{oc_ver}  @ {oc_path}'
            else:
                oc_val = f'installed  @ {oc_path}'
        else:
            oc_val = t('detect.not_installed')
        self._row_ok('OpenCode', oc_val, report.get('opencode_installed', False))
        runtime_ready = bool(report.get('node_ok')) and bool(report.get('npm_ok'))
        opencode_ready = bool(report.get('opencode_installed'))
        if not runtime_ready:
            self.primary_btn.configure(text='[ 一键修复环境 ]')
        elif not opencode_ready:
            self.primary_btn.configure(text='[ 一键安装 OpenCode ]')
        else:
            self.primary_btn.configure(text='[ 更新 OpenCode ]')
        self.primary_btn.set_enabled(True)

        # ═══ Claude / LLM Env Vars ═══
        claude_env = report.get('claude_env_vars', {})
        if claude_env:
            self._section('🤖 Claude / LLM Environment Variables')
            for var_name, var_value in claude_env.items():
                if any(k in var_name.upper() for k in ['API_KEY', 'AUTH_TOKEN', 'TOKEN']):
                    display_val = _mask_key(var_value)
                else:
                    display_val = var_value if len(var_value) <= 55 else var_value[:52] + '...'
                self._env_var_row(var_name, display_val)

        # ═══ Claude Code settings.json (USER) ═══
        claude_settings = report.get('claude_settings', {})
        claude_raw = report.get('claude_settings_raw', '')
        claude_path = report.get('claude_settings_path', '~/.claude/settings.json')
        claude_readable = report.get('claude_settings_readable', False)

        if claude_path or claude_raw:
            self._section('📁 ~/.claude/settings.json')
            if claude_readable and claude_settings:
                self._json_terminal_block(claude_raw, claude_path)
            elif claude_raw:
                self._raw_text_block(claude_raw, claude_path, '⚠ JSON parse failed — showing raw content')
            else:
                self._empty_hint('文件为空或不可读')

        # ═══ Claude Code settings.json (PROJECT) ═══
        project_settings = report.get('project_settings', {})
        project_raw = report.get('project_settings_raw', '')
        project_path = report.get('project_claude_path', '')
        project_readable = report.get('project_settings_readable', False)

        if project_raw or (project_settings and project_path):
            proj_settings_file = project_path + '/settings.json' if project_path else '.claude/settings.json'
            self._section(f'📁 {proj_settings_file}')
            if project_readable and project_settings:
                self._json_terminal_block(project_raw, proj_settings_file)
            elif project_raw:
                self._raw_text_block(project_raw, proj_settings_file, '⚠ JSON parse failed — showing raw content')
            else:
                self._empty_hint('文件为空或不可读')

        # ═══ Project .claude files ═══
        project_files = report.get('project_files', [])
        if project_files:
            self._section('📂 .claude/ 项目配置文件')
            list_frame = tk.Frame(self.scroll.inner, bg=COLORS['bg'])
            list_frame.pack(fill='x', padx=25, pady=2)
            for f in project_files:
                tk.Label(list_frame, text=f'  ▸ {f["name"]}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                         font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w')

        # ═══ Proxy — 3 sources ═══
        self._section('🌐 Proxy 检测 (环境变量 + 系统代理 + WinHTTP)')

        # Source 1: Environment variables
        env_vars = report.get('env_vars', {})
        if env_vars:
            self._subsection('📋 环境变量')
            for var_name, var_value in env_vars.items():
                display_val = var_value if len(var_value) <= 55 else var_value[:52] + '...'
                self._env_var_row(var_name, display_val)
        else:
            self._subsection('📋 环境变量')
            self._empty_hint('(未设置 HTTP_PROXY / HTTPS_PROXY / NO_PROXY)')

        # Source 2: Windows system proxy (registry)
        sys_enabled = report.get('system_proxy_enabled', False)
        sys_server = report.get('system_proxy_server', '')
        sys_bypass = report.get('system_proxy_bypass', '')
        self._subsection('🖥 Windows 系统代理 (注册表)')
        if sys_enabled and sys_server:
            self._row_ok('状态', '已启用', True)
            self._row_ok('代理服务器', sys_server, True)
            if sys_bypass:
                self._row_ok('绕过列表', sys_bypass, True)
        else:
            self._empty_hint('(未启用系统代理)')

        # Source 3: WinHTTP proxy
        winhttp_direct = report.get('winhttp_direct', True)
        winhttp_proxy = report.get('winhttp_proxy', '')
        winhttp_bypass = report.get('winhttp_bypass', '')
        self._subsection('🔧 WinHTTP 代理 (netsh)')
        if winhttp_direct:
            self._empty_hint('(WinHTTP 直连，无代理)')
        else:
            self._row_ok('代理服务器', winhttp_proxy or '(未设置)', not winhttp_direct)
            if winhttp_bypass:
                self._row_ok('绕过列表', winhttp_bypass, True)

        # Summary warning
        if report.get('proxy_detected', False):
            note = tk.Frame(self.scroll.inner, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
            note.pack(fill='x', padx=25, pady=(8, 2))
            sources = []
            if env_vars: sources.append('环境变量')
            if sys_enabled: sources.append('系统代理')
            if not winhttp_direct: sources.append('WinHTTP')
            tk.Label(note, text=f'⚠ 检测到代理 ({", ".join(sources)})，安装后将自动生成 launcher 脚本清除代理',
                     bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                     font=(FONTS['log']['family'], FONTS['log']['size'])).pack(padx=8, pady=4)
        else:
            self._empty_hint('✅ 未检测到任何代理配置')

        self._update_next_button()

    # ── UI Helpers ───────────────────────────────────────────────────────────

    def _section(self, text: str):
        tk.Frame(self.scroll.inner, bg=COLORS['bg'], height=6).pack()
        tk.Label(self.scroll.inner, text=text, bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=15, pady=(8, 4))

    def _subsection(self, text: str):
        tk.Label(self.scroll.inner, text=text, bg=COLORS['bg'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'], 'bold')).pack(
                     anchor='w', padx=25, pady=(4, 1))

    def _row_ok(self, label: str, value: str, ok: bool):
        row_frame = tk.Frame(self.scroll.inner, bg=COLORS['bg'])
        row_frame.pack(fill='x', pady=2, padx=25)
        icon = t('status.pass') if ok else t('status.fail')
        color = COLORS['neon_green'] if ok else COLORS['red']
        tk.Label(row_frame, text=icon, bg=COLORS['bg'], fg=color,
                 font=(FONTS['body']['family'], FONTS['body']['size']), width=2).pack(side='left')
        tk.Label(row_frame, text=f'{label}:', bg=COLORS['bg'], fg=COLORS['white'],
                 font=(FONTS['body']['family'], FONTS['body']['size']), width=12, anchor='w').pack(side='left')
        tk.Label(row_frame, text=value, bg=COLORS['bg'], fg=color,
                 font=(FONTS['body']['family'], FONTS['body']['size']), anchor='w').pack(side='left', padx=(5, 0))

    def _env_var_row(self, var_name: str, value: str):
        row = tk.Frame(self.scroll.inner, bg=COLORS['dark_gray'])
        row.pack(fill='x', padx=25, pady=2)
        tk.Label(row, text=var_name, bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['log']['family'], FONTS['log']['size'], 'bold'), width=22, anchor='w').pack(side='left', padx=6, pady=3)
        tk.Label(row, text='=', bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(side='left')
        tk.Label(row, text=value, bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                 font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w').pack(side='left', padx=(2, 6), pady=3)

    def _json_terminal_block(self, raw_json: str, path: str):
        """Display settings.json as a pixel terminal code block with neon styling."""
        # Terminal frame
        term = tk.Frame(self.scroll.inner, bg=COLORS['black'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', padx=20, pady=3)

        # Title bar: ┌── path ──┐
        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=20)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text=f'┌── {path} ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)
        tk.Label(bar, text='JSON', bg=COLORS['dark_gray'], fg=COLORS['dark_gray'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='right', padx=6)

        # JSON content with simple colorization
        text = tk.Text(term, height=min(16, raw_json.count('\n') + 2), bg=COLORS['black'],
                      fg=COLORS['neon_green'], insertbackground=COLORS['neon_green'],
                      font=(FONTS['log']['family'], FONTS['log']['size']),
                      relief='flat', padx=8, pady=4, wrap='none', state='disabled')
        text.pack(fill='x')

        # Colorize: keys in yellow, strings in green, numbers in white, booleans in red/green
        text.tag_configure('key', foreground=COLORS['yellow'])
        text.tag_configure('str', foreground=COLORS['neon_green'])
        text.tag_configure('num', foreground=COLORS['white'])
        text.tag_configure('bool_t', foreground=COLORS['neon_green'])
        text.tag_configure('bool_f', foreground=COLORS['red'])
        text.tag_configure('null', foreground=COLORS['dark_gray'])
        text.tag_configure('brace', foreground=COLORS['white'])
        text.tag_configure('comment', foreground=COLORS['dark_gray'])

        text.configure(state='normal')
        try:
            parsed = json.loads(raw_json)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            for line in formatted.split('\n'):
                # Very simple syntax highlighting
                import re
                # Highlight keys
                highlighted = re.sub(r'"([^"]+)"(\s*):', lambda m: f'"{m.group(1)}"{m.group(2)}:', line)
                if highlighted.strip():
                    text.insert('end', highlighted + '\n')
        except Exception:
            text.insert('end', raw_json)

        text.configure(state='disabled')

        # Bottom bar
        bot = tk.Frame(term, bg=COLORS['dark_gray'], height=4)
        bot.pack(fill='x')

    def _raw_text_block(self, raw: str, path: str, warning: str = ''):
        """Display raw file content when JSON parsing fails."""
        term = tk.Frame(self.scroll.inner, bg=COLORS['bg_darker'], relief='solid', borderwidth=2,
                       highlightbackground=COLORS['red_dim'], highlightthickness=1)
        term.pack(fill='x', padx=20, pady=3)

        if warning:
            tk.Label(term, text=warning, bg=COLORS['bg_darker'], fg=COLORS['red'],
                     font=(FONTS['small']['family'], FONTS['small']['size'])).pack(anchor='w', padx=8, pady=(4, 0))

        text = tk.Text(term, height=min(10, raw.count('\n') + 2), bg=COLORS['bg_darker'],
                      fg=COLORS['white'], font=(FONTS['log']['family'], FONTS['log']['size']),
                      relief='flat', padx=8, pady=4, wrap='none', state='disabled')
        text.pack(fill='x')
        text.configure(state='normal')
        text.insert('end', raw[:2000])
        text.configure(state='disabled')

    def _empty_hint(self, text: str = '(none)'):
        tk.Label(self.scroll.inner, text=f'    {text}', bg=COLORS['bg'], fg=COLORS['dark_gray'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=30, pady=2)

    # ── Navigation ───────────────────────────────────────────────────────────

    def _update_next_button(self):
        report = self.app.state.env_report
        blocked = not report.get('os_ok', False) or not report.get('disk_ok', False)
        self.next_btn.set_enabled(not blocked)

    def _on_next(self):
        report = self.app.state.env_report
        need_node = not report.get('node_ok', False)
        need_npm = not report.get('npm_ok', False)
        if need_node or need_npm:
            from tkinter import messagebox
            problems = []
            if need_node: problems.append('Node.js')
            if need_npm: problems.append('npm')
            msg = '检测到以下问题需要修复：\n\n' + '\n'.join(f'  ✗ {p}' for p in problems)
            msg += '\n\n是否自动修复？'
            if messagebox.askyesno('环境问题', msg):
                from ui.pages.env_fix import EnvFixPage
                self.app.show_page(EnvFixPage, 'env_fix')
            else:
                self._go_next()
        else:
            self._go_next()

    def _on_upgrade(self):
        """Open the same live terminal page in upgrade mode."""
        self.app.state.opencode_action = 'upgrade'
        from ui.pages.install import InstallPage
        self.app.show_page(InstallPage, 'install')

    def _on_primary_action(self):
        """Dispatch the single contextual action shown in the compact bar."""
        report = self.app.state.env_report
        if not (report.get('node_ok') and report.get('npm_ok')):
            self._on_fix_missing()
        elif not report.get('opencode_installed'):
            self._on_install_opencode()
        else:
            self._on_upgrade()

    def _on_fix_missing(self):
        """Run the domestic-mirror PowerShell repair without a confirmation dialog."""
        from ui.pages.env_fix import EnvFixPage
        self.app.show_page(EnvFixPage, 'env_fix')

    def _on_install_opencode(self):
        self.app.state.opencode_action = 'install'
        from ui.pages.install import InstallPage
        self.app.show_page(InstallPage, 'install')

    def _go_next(self):
        report = self.app.state.env_report
        if report.get('opencode_installed', False):
            from ui.pages.config_model import ConfigModelPage
            self.app.show_page(ConfigModelPage, 'config_model')
        else:
            from ui.pages.install import InstallPage
            self.app.show_page(InstallPage, 'install')

    def _on_key_next(self):
        self._on_next()
