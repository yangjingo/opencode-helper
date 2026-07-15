"""Finish page — summary, desktop download guide, and 8-bit celebration explosion."""
import tkinter as tk
import subprocess, os, webbrowser
from pathlib import Path
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage
from ui.animations import CelebrationParticles
from i18n import t

DESKTOP_DOWNLOAD_URL = 'https://opencode.ai/zht/download/stable/windows-x64-nsis'

class FinishPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'finish'
        s = app.state
        app.set_key_hint('[Enter]关闭  [L]启动  [C]配置目录  [D]下载桌面版')

        # Title
        tk.Label(self, text=f'🎉 {t("finish.title")}', bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['huge']['family'], FONTS['huge']['size'], 'bold')).pack(pady=(10, 3))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # Summary
        summary = (
            f'OpenCode CLI   installed\n'
            f'Model           {s.provider_name}/{s.model_id}\n'
            f'Proxy           auto-handled\n'
            f'Config          ~/.config/opencode/opencode.jsonc'
        )
        tk.Label(self, text=summary, bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['body']['family'], FONTS['body']['size']), justify='left').pack(pady=(6, 4))

        # Desktop download card
        card = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        card.pack(pady=6, padx=40, fill='x')

        tk.Label(card, text='📥 下载桌面版 OpenCode', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(pady=(6, 2))
        tk.Label(card, text='桌面 exe 自动读取 CLI 配置，无需重复配置，安装即用',
                 bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack()

        url_frame = tk.Frame(card, bg=COLORS['deep_purple'], relief='sunken', borderwidth=1)
        url_frame.pack(pady=5, padx=15, fill='x')
        tk.Label(url_frame, text=DESKTOP_DOWNLOAD_URL, bg=COLORS['deep_purple'], fg=COLORS['neon_green'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(padx=6, pady=3)

        PixelButton(card, text='[ 📥 打开下载页面 ]', command=self._open_download).pack(pady=(2, 6))

        # Action buttons
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=4)
        PixelButton(btn_frame, text=f'[ 🚀 {t("finish.launch")} ]', command=self._launch).pack(pady=2)
        PixelButton(btn_frame, text=f'[ 📂 {t("finish.config_dir")} ]', command=self._open_config).pack(pady=2)
        PixelButton(btn_frame, text=f'[ 🏠 {t("finish.close")} ]', command=self.app.root.destroy).pack(pady=2)

        # Celebration canvas
        self.canvas = tk.Canvas(self, width=740, height=90, bg=COLORS['bg'], highlightthickness=0)
        self.canvas.pack(pady=5)
        self._celebration = CelebrationParticles(self.canvas, 740, 90)
        self._celebration.start()

        # Keyboard shortcuts
        app.root.bind('<KeyPress-l>', lambda e: self._launch())
        app.root.bind('<KeyPress-L>', lambda e: self._launch())
        app.root.bind('<KeyPress-c>', lambda e: self._open_config())
        app.root.bind('<KeyPress-C>', lambda e: self._open_config())
        app.root.bind('<KeyPress-d>', lambda e: self._open_download())
        app.root.bind('<KeyPress-D>', lambda e: self._open_download())

    def _launch(self):
        try:
            subprocess.Popen(['opencode'], shell=True)
        except Exception:
            pass

    def _open_config(self):
        config_dir = Path.home() / '.config' / 'opencode'
        if config_dir.exists():
            subprocess.Popen(['explorer', str(config_dir)], shell=True)

    def _open_download(self):
        webbrowser.open(DESKTOP_DOWNLOAD_URL)

    def destroy(self):
        self._celebration.stop()
        super().destroy()

    def _on_key_next(self):
        self.app.root.destroy()
