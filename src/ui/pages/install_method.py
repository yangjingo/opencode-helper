"""Install method selection page — npm vs .exe."""
import tkinter as tk
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage
from i18n import t

class InstallMethodPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'install_method'
        self.method_var = tk.StringVar(value=app.state.install_method)
        app.set_key_hint('[Enter]确认  [Esc]返回  [1]npm  [2]exe')

        tk.Label(self, text=t('install.method.title'), bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 8))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # npm option
        npm_frame = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        npm_frame.pack(pady=12, padx=40, fill='x')
        tk.Radiobutton(npm_frame, text=f'[1] {t("install.method.npm")}', variable=self.method_var,
                       value='npm', bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                       selectcolor=COLORS['deep_purple'],
                       font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(anchor='w', padx=10, pady=5)
        tk.Label(npm_frame, text='  npm install -g opencode-ai\n  轻量安装，需要 Node.js ≥18',
                 bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=30, pady=(0, 8))

        # exe option
        exe_frame = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        exe_frame.pack(pady=5, padx=40, fill='x')
        tk.Radiobutton(exe_frame, text=f'[2] {t("install.method.exe")}', variable=self.method_var,
                       value='exe', bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                       selectcolor=COLORS['deep_purple'],
                       font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(anchor='w', padx=10, pady=5)
        tk.Label(exe_frame, text='  下载独立安装包 (~150MB)\n  自带运行时，无需 Node.js',
                 bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(anchor='w', padx=30, pady=(0, 8))

        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=12)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next).pack(side='left', padx=5)

    def _on_next(self):
        self.app.state.install_method = self.method_var.get()
        if self.method_var.get() == 'exe':
            from ui.pages.install_path import InstallPathPage
            self.app.show_page(InstallPathPage, 'install_path')
        else:
            from ui.pages.install import InstallPage
            self.app.show_page(InstallPage, 'install')

    def _on_key_next(self):
        self._on_next()

    def _on_key_number(self, n: int):
        if n == 1:
            self.method_var.set('npm')
        elif n == 2:
            self.method_var.set('exe')
