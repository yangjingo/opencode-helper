"""Finish page — summary plus copyable download and launch actions."""
import tkinter as tk
import os, subprocess, webbrowser
from pathlib import Path
from core.proxy_manager import DIRECT_POWERSHELL_COMMAND
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage
from ui.animations import CelebrationParticles
from i18n import t

DESKTOP_DOWNLOAD_URL = 'https://opencode.ai/zht/download/stable/windows-x64-nsis'

class FinishPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'finish'
        self._launch_command = DIRECT_POWERSHELL_COMMAND
        self._feedback = None
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
        card.pack(pady=(5, 3), padx=40, fill='x')

        tk.Label(card, text='📥 下载桌面版 OpenCode', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(pady=(6, 2))
        tk.Label(card, text='桌面 exe 自动读取 CLI 配置，无需重复配置，安装即用',
                 bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack()

        url_frame = tk.Frame(card, bg=COLORS['deep_purple'], relief='sunken', borderwidth=1)
        url_frame.pack(pady=5, padx=15, fill='x')
        tk.Label(url_frame, text=DESKTOP_DOWNLOAD_URL, bg=COLORS['deep_purple'], fg=COLORS['neon_green'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack(padx=6, pady=3)

        PixelButton(card, text='[ 📥 打开下载页面 ]', command=self._open_download).pack(pady=(1, 5))

        # CLI launch card — mirrors the download card and makes the exact
        # PowerShell command visible before the user starts a terminal.
        launch_card = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        launch_card.pack(pady=3, padx=40, fill='x')

        tk.Label(launch_card, text='🚀 启动 OpenCode', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(pady=(6, 1))
        tk.Label(launch_card, text='打开 PowerShell，清除当前终端的 HTTP/HTTPS 代理后启动',
                 bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack()

        command_frame = tk.Frame(launch_card, bg=COLORS['deep_purple'], relief='sunken', borderwidth=1,
                                 cursor='hand2')
        command_frame.pack(pady=5, padx=15, fill='x')
        command_label = tk.Label(
            command_frame, text=self._launch_command,
            bg=COLORS['deep_purple'], fg=COLORS['neon_green'], cursor='hand2',
            font=(FONTS['small']['family'], FONTS['small']['size']),
            justify='left', anchor='w', wraplength=620,
        )
        command_label.pack(fill='x', padx=6, pady=4)
        command_frame.bind('<Button-1>', lambda _event: self._copy_launch_command())
        command_label.bind('<Button-1>', lambda _event: self._copy_launch_command())

        launch_actions = tk.Frame(launch_card, bg=COLORS['dark_gray'])
        launch_actions.pack(pady=(0, 5))
        PixelButton(launch_actions, text='[ 📋 复制命令 ]', command=self._copy_launch_command).pack(side='left', padx=4)
        PixelButton(launch_actions, text=f'[ 🚀 {t("finish.launch")} ]', command=self._launch).pack(side='left', padx=4)

        # Action buttons
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=(3, 0))
        PixelButton(btn_frame, text=f'[ 📂 {t("finish.config_dir")} ]', command=self._open_config).pack(side='left', padx=4)
        PixelButton(btn_frame, text=f'[ 🏠 {t("finish.close")} ]', command=self.app.root.destroy).pack(side='left', padx=4)

        self._feedback = tk.Label(self, text='', bg=COLORS['bg'], fg=COLORS['neon_green'],
                                  font=(FONTS['small']['family'], FONTS['small']['size']))
        self._feedback.pack(pady=(2, 0))

        # Celebration canvas
        self.canvas = tk.Canvas(self, width=740, height=38, bg=COLORS['bg'], highlightthickness=0)
        self.canvas.pack(pady=1)
        self._celebration = CelebrationParticles(self.canvas, 740, 38)
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
            from core.cli_launcher import launch_opencode_cli
            launch_opencode_cli(direct=True, install_path=self.app.state.install_path)
            self._show_feedback('✓ 已打开 PowerShell 并启动 OpenCode。')
        except OSError as exc:
            self._show_feedback(f'✗ 无法启动终端：{exc}', error=True)

    def _copy_launch_command(self):
        self.clipboard_clear()
        self.clipboard_append(self._launch_command)
        self.update()
        self._show_feedback('✓ 启动命令已复制。')

    def _show_feedback(self, message: str, *, error: bool = False):
        if not self._feedback or not self._feedback.winfo_exists():
            return
        self._feedback.configure(text=message, fg=COLORS['red'] if error else COLORS['neon_green'])
        self.after(2400, self._clear_feedback)

    def _clear_feedback(self):
        if self._feedback and self._feedback.winfo_exists():
            self._feedback.configure(text='')

    def _open_config(self):
        config_dir = Path.home() / '.config' / 'opencode'
        if config_dir.exists():
            subprocess.Popen(['explorer', str(config_dir)], shell=True)

    def _open_direct_connect(self):
        from ui.pages.direct_connect import DirectConnectPage
        self.app.show_page(DirectConnectPage, 'direct_connect')

    def _open_download(self):
        webbrowser.open(DESKTOP_DOWNLOAD_URL)

    def destroy(self):
        self._celebration.stop()
        super().destroy()

    def _on_key_next(self):
        self.app.root.destroy()
