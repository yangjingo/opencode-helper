"""Environment auto-fix page."""
import tkinter as tk
import threading
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, PixelTerminal, PixelProgress, BasePage
from i18n import t
from core.env_fixer import auto_fix_environment
from core.detector import clear_cache, detect_all

class EnvFixPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'env_fix'
        app.set_key_hint('[Enter]继续  [Esc]跳过')

        tk.Label(self, text=f'🔧 {t("env.autofix")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        self.terminal = PixelTerminal(self, width=80, height=14, title='auto-fix')
        self.terminal.pack(pady=5, padx=20, fill='both', expand=True)
        self.progress = PixelProgress(self, width=500, height=28)
        self.progress.pack(pady=8)

        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("btn.skip")} ]', command=self._on_skip).pack(side='left', padx=5)
        self.next_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next)
        self.next_btn.pack(side='left', padx=5)
        self.next_btn.set_enabled(False)
        self._start_fix()

    def _start_fix(self):
        def run():
            def log(msg):
                self._safe_after(10, lambda m=msg: self.terminal.write(m))
            log('▶ Running auto-fix...')
            results = auto_fix_environment(self.app.state.env_report, progress_callback=log)
            # A Node MSI updates machine PATH only for newly started processes.
            # Re-run the robust detector anyway: it also sees the installed
            # binary directly, without requiring the user to restart Explorer.
            clear_cache()
            refreshed = detect_all()
            self.app.state.env_report = refreshed
            if refreshed.get('node_ok') and refreshed.get('npm_ok'):
                log('✓ 修复后复检通过：Node.js 与 npm 已就绪。')
            else:
                log('⚠ 修复命令已执行，但仍未检测到完整环境。请完成 UAC 安装后点击“重新检测”。')
                log(f'  nodejs={results.get("nodejs", "not-needed")}, npm_registry={results.get("npm_registry", "not-needed")}')
            self._safe_after(10, lambda: self.progress.set_progress(100))
            self._safe_after(10, lambda: self.progress.set_text('复检完成'))
            self._safe_after(10, lambda: self.next_btn.set_enabled(True))
        threading.Thread(target=run, daemon=True).start()

    def _on_skip(self):
        from ui.pages.install import InstallPage
        self.app.show_page(InstallPage, 'install')

    def _on_next(self):
        from ui.pages.install import InstallPage
        self.app.show_page(InstallPage, 'install')

    def _on_key_next(self):
        self._on_next()

    def _on_key_back(self):
        self._on_skip()
