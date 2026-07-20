"""Install progress page with real-time npm streaming."""
import tkinter as tk
import threading
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, PixelProgress, PixelTerminal, BasePage
from i18n import t

class InstallPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'install'
        self.is_upgrade = app.state.opencode_action == 'upgrade'
        app.set_key_hint('[安装完成后 Enter]继续')

        title = '正在升级 OpenCode' if self.is_upgrade else t('install.title')
        tk.Label(self, text=title, bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # Command display
        cmd_frame = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
        cmd_frame.pack(pady=8, padx=40, fill='x')
        self.command_text = 'npm config set registry https://registry.npmmirror.com; npm install -g opencode-ai@latest --verbose --registry https://registry.npmmirror.com'
        self.command_label = tk.Label(
            cmd_frame, text=f'$ {self.command_text}  [点击复制]', cursor='hand2',
            bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
            font=(FONTS['body']['family'], FONTS['body']['size'], 'bold'),
        )
        self.command_label.pack(padx=10, pady=5)
        self.command_label.bind('<Button-1>', self._copy_command)

        self.terminal = PixelTerminal(self, width=82, height=14, title='npm-install')
        self.terminal.pack(pady=5, padx=20, fill='both', expand=True)
        self.progress = PixelProgress(self, width=520, height=28)
        self.progress.pack(pady=6)

        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        self.retry_btn = PixelButton(btn_frame, text='[ 重试 ]', command=self._start_install)
        self.retry_btn.pack(side='left', padx=5)
        self.retry_btn.set_enabled(False)
        self.next_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next)
        self.next_btn.pack(side='left', padx=5)
        self.next_btn.set_enabled(False)
        self._start_install()

    def _start_install(self):
        self.retry_btn.set_enabled(False)
        self.next_btn.set_enabled(False)
        self._line_count = 0
        def log(msg):
            self._line_count += 1
            # Estimate progress from npm output (npm has ~200 lines for a full install)
            pct = min(95, self._line_count * 95 / 180)
            self._safe_after(0, lambda p=pct: self.progress.set_progress(p))
            self._safe_after(0, lambda m=msg: self.terminal.write(m))

        def run():
            from core.installer import install_npm, upgrade_npm
            log('[npm] Starting OpenCode upgrade...' if self.is_upgrade else '[npm] Starting OpenCode installation...')
            success = (upgrade_npm if self.is_upgrade else install_npm)(progress_callback=log)
            self._safe_after(0, lambda s=success: self.progress.set_progress(100 if s else 0))
            self._safe_after(0, lambda s=success: self.progress.set_text('Done!' if s else 'Failed'))
            if success:
                self._safe_after(0, lambda: self.next_btn.set_enabled(True))
            else:
                self._safe_after(0, lambda: self.retry_btn.set_enabled(True))
        threading.Thread(target=run, daemon=True).start()

    def _copy_command(self, _event=None):
        self.clipboard_clear()
        self.clipboard_append(self.command_text)
        self.command_label.configure(text=f'$ {self.command_text}  ✓ 已复制')
        self.after(1800, lambda: self.command_label.configure(
            text=f'$ {self.command_text}  [点击复制]') if not self._destroyed else None)

    def _on_next(self):
        self.app.state.opencode_action = 'install'
        from ui.pages.config_model import ConfigModelPage
        self.app.show_page(ConfigModelPage, 'config_model')

    def _on_key_next(self):
        from ui.pages.config_model import ConfigModelPage
        self.app.show_page(ConfigModelPage, 'config_model')
