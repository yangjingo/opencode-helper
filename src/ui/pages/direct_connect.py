"""A dedicated page for launching OpenCode without inherited proxy variables."""
import tkinter as tk

from core.proxy_manager import direct_connection_commands
from ui.theme import COLORS, FONTS
from ui.widgets import BasePage, PixelButton


class DirectConnectPage(BasePage):
    """Show safe, copyable ways to launch OpenCode directly."""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'direct_connect'
        self._commands = direct_connection_commands()
        self._feedback = None
        app.set_key_hint('[Esc]返回  [1]复制永久配置  [2]复制临时命令')

        tk.Label(self, text='🌐 直连启动 OpenCode', bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(12, 3))
        tk.Label(self, text='仅清除当前 OpenCode 进程继承的代理变量；系统代理设置不会被修改。',
                 bg=COLORS['bg'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size'])).pack()
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=620).pack(pady=(5, 8))

        self._command_card(
            title='01  永久生效 · Windows PowerShell Profile',
            detail='写入 $PROFILE。以后在 PowerShell 中执行 opencode 都会自动绕过代理。',
            command=self._commands['powershell_profile'],
            key='powershell_profile',
        )
        self._command_card(
            title='02  临时生效 · Windows PowerShell',
            detail='只影响这一条命令；关闭窗口或下次直接运行 opencode 时代理设置仍保持原状。',
            command=self._commands['powershell_once'],
            key='powershell_once',
        )

        self._feedback = tk.Label(self, text='', bg=COLORS['bg'], fg=COLORS['neon_green'],
                                  font=(FONTS['log']['family'], FONTS['log']['size']))
        self._feedback.pack(pady=(4, 0))
        actions = tk.Frame(self, bg=COLORS['bg'])
        actions.pack(pady=(4, 8))
        PixelButton(actions, text='[ ▶ 立即直连启动 ]', command=self._launch_direct).pack(side='left', padx=5)
        PixelButton(actions, text='[ ← 返回完成页 ]', command=app.go_back).pack(side='left', padx=5)

    def _command_card(self, title: str, detail: str, command: str, key: str):
        card = tk.Frame(self, bg=COLORS['dark_gray'], relief='ridge', borderwidth=2)
        card.pack(fill='x', padx=38, pady=5)
        header = tk.Frame(card, bg=COLORS['dark_gray'])
        header.pack(fill='x', padx=10, pady=(7, 2))
        tk.Label(header, text=title, bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(side='left')
        PixelButton(header, text='[ 📋 复制命令 ]', command=lambda: self._copy_command(key)).pack(side='right')
        tk.Label(card, text=detail, bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['small']['family'], FONTS['small']['size']),
                 anchor='w', justify='left', wraplength=620).pack(fill='x', padx=10)

        terminal = tk.Text(card, height=9 if key == 'powershell_profile' else 3,
                           bg=COLORS['black'], fg=COLORS['neon_green'],
                           font=(FONTS['log']['family'], FONTS['log']['size']),
                           relief='sunken', borderwidth=2, padx=8, pady=5, wrap='word')
        terminal.pack(fill='x', padx=10, pady=(5, 8))
        terminal.insert('1.0', command)
        terminal.configure(state='disabled')

    def _copy_command(self, key: str):
        command = self._commands[key]
        self.clipboard_clear()
        self.clipboard_append(command)
        self.update()
        self._feedback.configure(text='✓ 已复制。请粘贴到对应终端执行。')
        self.after(2200, lambda: self._feedback and self._feedback.winfo_exists() and self._feedback.configure(text=''))

    def _launch_direct(self):
        try:
            from core.cli_launcher import launch_opencode_cli
            launch_opencode_cli(direct=True, install_path=self.app.state.install_path)
            self._feedback.configure(text='✓ 已打开 PowerShell，并以直连方式启动 OpenCode。')
        except OSError as exc:
            self._feedback.configure(text=f'✗ 无法启动终端：{exc}')

    def _on_key_number(self, number: int):
        if number == 1:
            self._copy_command('powershell_profile')
        elif number == 2:
            self._copy_command('powershell_once')
