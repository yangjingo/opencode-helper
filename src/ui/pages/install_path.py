"""Install path selection page for .exe mode."""
import tkinter as tk, os
from tkinter import filedialog
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage
from i18n import t

class InstallPathPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'install_path'
        app.set_key_hint('[Enter]确认  [Esc]返回  [B]浏览')

        default_path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'Programs', 'OpenCode')
        self.path_var = tk.StringVar(value=app.state.install_path or default_path)

        tk.Label(self, text=t('install.path.title'), bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 8))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        path_frame = tk.Frame(self, bg=COLORS['bg'])
        path_frame.pack(pady=15, padx=40, fill='x')
        tk.Entry(path_frame, textvariable=self.path_var, bg=COLORS['deep_purple'], fg=COLORS['neon_green'],
                 font=(FONTS['body']['family'], FONTS['body']['size'])).pack(side='left', fill='x', expand=True)
        PixelButton(path_frame, text=f'[ {t("install.path.browse")} ]', command=self._browse).pack(side='left', padx=5)

        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=12)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_next).pack(side='left', padx=5)

        app.root.bind('<KeyPress-b>', lambda e: self._browse())
        app.root.bind('<KeyPress-B>', lambda e: self._browse())

    def _browse(self):
        path = filedialog.askdirectory(title='Select Install Location')
        if path:
            self.path_var.set(path)

    def _on_next(self):
        self.app.state.install_path = self.path_var.get()
        from ui.pages.install import InstallPage
        self.app.show_page(InstallPage, 'install')

    def _on_key_next(self):
        self._on_next()
