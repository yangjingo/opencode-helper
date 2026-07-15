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
        app.set_key_hint('[安装完成后 Enter]继续')

        tk.Label(self, text=t('install.title'), bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # Command display
        cmd_frame = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
        cmd_frame.pack(pady=8, padx=40, fill='x')
        tk.Label(cmd_frame, text='$ npm install -g opencode-ai --verbose',
                 bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(padx=10, pady=5)

        self.terminal = PixelTerminal(self, width=82, height=14, title='npm-install')
        self.terminal.pack(pady=5, padx=20, fill='both', expand=True)
        self.progress = PixelProgress(self, width=520, height=28)
        self.progress.pack(pady=6)

        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        self.next_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next)
        self.next_btn.pack(side='left', padx=5)
        self.next_btn.set_enabled(False)
        self._start_install()

    def _start_install(self):
        self._line_count = 0
        def log(msg):
            self._line_count += 1
            # Estimate progress from npm output (npm has ~200 lines for a full install)
            pct = min(95, self._line_count * 95 / 180)
            self._safe_after(0, lambda p=pct: self.progress.set_progress(p))
            self._safe_after(0, lambda m=msg: self.terminal.write(m))

        def run():
            from core.installer import install_npm
            log('[npm] Starting installation...')
            success = install_npm(progress_callback=log)
            self._safe_after(0, lambda s=success: self.progress.set_progress(100 if s else 0))
            self._safe_after(0, lambda s=success: self.progress.set_text('Done!' if s else 'Failed'))
            if success:
                self._safe_after(0, lambda: self.next_btn.set_enabled(True))
        threading.Thread(target=run, daemon=True).start()

    def _on_next(self):
        from ui.pages.config_model import ConfigModelPage
        self.app.show_page(ConfigModelPage, 'config_model')

    def _on_key_next(self):
        from ui.pages.config_model import ConfigModelPage
        self.app.show_page(ConfigModelPage, 'config_model')
