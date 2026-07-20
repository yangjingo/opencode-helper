"""Verification page — sequential validation with progress + diagnostics.

Runs model inference, config and CLI validation in that order, showing each
completed result immediately, then renders actionable diagnostic suggestions.
then renders results with actionable diagnostic suggestion boxes for failures.
Preserves the 8-bit pixel theme.
"""
import tkinter as tk
from tkinter import ttk
import threading

from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage, ScrollableFrame
from i18n import t

from core.validation_engine import ValidationEngine
from core.validation_result import ValidationReport, ValidationResult, Status, format_duration


# Test display order and labels
_TESTS = [
    ('model', '🤖 模型推理'),
    ('config', '📄 配置文件'),
    ('cli', '💻 OpenCode CLI'),
]


class VerifyPage(BasePage):
    """Verification page with progress bar, live status, and diagnostics."""

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'verify'
        app.set_key_hint('[Enter]完成  [Esc]返回修改')

        tk.Label(self, text=f'✓ {t("verify.title")}', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold')).pack(pady=(10, 5))
        tk.Frame(self, bg=COLORS['neon_green'], height=1, width=500).pack()

        # ── Progress section ──
        self._progress_frame = tk.Frame(self, bg=COLORS['bg'])
        self._progress_frame.pack(fill='x', padx=40, pady=(10, 5))

        self._progress_label = tk.Label(
            self._progress_frame, text='⏳ 准备验证...', bg=COLORS['bg'], fg=COLORS['yellow'],
            font=(FONTS['body']['family'], FONTS['body']['size']))
        self._progress_label.pack(anchor='w')

        self._configure_progressbar_style()
        self._progress = ttk.Progressbar(
            self._progress_frame, style='Neon.Horizontal.TProgressbar',
            mode='determinate', length=400, maximum=100)
        self._progress.pack(fill='x', pady=(5, 0))

        # ── Per-test status labels ──
        self._status_frame = tk.Frame(self, bg=COLORS['bg'])
        self._status_frame.pack(fill='x', padx=40, pady=(5, 0))

        self._status_labels = {}
        for key, label in _TESTS:
            row = tk.Frame(self._status_frame, bg=COLORS['bg'])
            row.pack(fill='x', pady=1)
            lbl = tk.Label(row, text=f'○ {label}', bg=COLORS['bg'], fg=COLORS['dark_gray'],
                           font=(FONTS['log']['family'], FONTS['log']['size']))
            lbl.pack(anchor='w')
            self._status_labels[key] = lbl

        # ── Scrollable results area ──
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(pady=5, padx=15, fill='both', expand=True)

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg=COLORS['bg'])
        btn_frame.pack(pady=8)
        PixelButton(btn_frame, text=f'[ {t("btn.back")} ]', command=app.go_back).pack(side='left', padx=5)
        self.finish_btn = PixelButton(btn_frame, text=f'[ {t("btn.next")} ]', command=self._on_finish)
        self.finish_btn.pack(side='left', padx=5)
        self.finish_btn.set_enabled(False)

        self._run_tests()

    def _configure_progressbar_style(self):
        """Style ttk progressbar to match the 8-bit neon theme."""
        style = ttk.Style()
        try:
            style.configure('Neon.Horizontal.TProgressbar',
                            troughcolor=COLORS['dark_gray'],
                            background=COLORS['neon_green'],
                            bordercolor=COLORS['dark_gray'],
                            lightcolor=COLORS['neon_green'],
                            darkcolor=COLORS['neon_green'])
        except Exception:
            pass

    # ── Progress callbacks (thread-safe via after) ────────────────────────────

    def _update_progress(self, name: str, value: float):
        """Engine progress callback — runs in worker thread."""
        def update():
            self._progress['value'] = value * 100
            pct = int(value * 100)
            self._progress_label.configure(text=f'⏳ 验证中... {pct}%')
            # Mark tests not yet completed as "running"
            for key, _ in _TESTS:
                current = self._status_labels[key].cget('text')
                if current.startswith('○') and value > 0:
                    pass  # leave pending ones gray
        self.after(0, update)

    def _on_validation_result(self, name: str, result: ValidationResult, value: float):
        """Refresh the matching row only after that real check completes."""
        def update():
            self._mark_status(name, result.status)
            self._progress['value'] = value * 100
            self._progress_label.configure(text=f'✓ 已完成 {name} · {int(value * 100)}%')
        self.after(0, update)

    def _mark_status(self, name: str, status: Status):
        """Update a test's status label with the appropriate icon/color."""
        def update():
            if name not in self._status_labels:
                return
            text = self._status_labels[name].cget('text')
            base = text[2:] if len(text) > 2 else text  # strip old icon
            if status == Status.SUCCESS:
                icon, color = '✓', COLORS['neon_green']
            elif status == Status.WARNING:
                icon, color = '⚠', COLORS['yellow']
            else:
                icon, color = '✗', COLORS['red']
            self._status_labels[name].configure(text=f'{icon} {base}', fg=color)
        self.after(0, update)

    # ── Test orchestration ────────────────────────────────────────────────────

    def _run_tests(self):
        """Run validation in a background thread."""
        def run():
            try:
                engine = ValidationEngine(self.app.state)
                engine.on_progress = self._update_progress
                engine.on_result = self._on_validation_result
                report = engine.run_all()
            except Exception as e:
                # Build a minimal failed report if the engine itself crashes
                from core.validation_result import ValidationReport, ValidationResult, Status
                report = ValidationReport(
                    results=[ValidationResult('engine', Status.FAILED, 0, f'引擎错误: {e}',
                                              str(e), '验证引擎异常，请重试', {})],
                    total_duration_ms=0, overall_status=Status.FAILED)
            self.after(0, lambda: self._show_report(report))

        threading.Thread(target=run, daemon=True).start()

    # ── Report rendering ──────────────────────────────────────────────────────

    def _show_report(self, report: ValidationReport):
        """Render the final report: summary, results, diagnostics, config."""
        # Mark all statuses from the report
        for r in report.results:
            self._mark_status(r.name, r.status)

        # Replace progress label with summary
        total_time = format_duration(report.total_duration_ms)
        if report.overall_status == Status.SUCCESS:
            summary_txt, summary_color = '✅ 全部验证通过', COLORS['neon_green']
        elif report.overall_status == Status.WARNING:
            summary_txt, summary_color = '⚠ 部分验证通过', COLORS['yellow']
        else:
            summary_txt, summary_color = '❌ 验证未通过', COLORS['red']
        self._progress_label.configure(
            text=f'{summary_txt} · 耗时 {total_time}', fg=summary_color)
        self._progress['value'] = 100

        # Results section
        self._section('📋 测试结果')
        for r in report.results:
            self._result_row(r)

        # Diagnostics section (only failures with suggestions)
        failed = report.get_failed()
        if failed:
            self._section('🔧 修复建议')
            for r in failed:
                if r.suggestion:
                    self._suggestion_box(r.name, r.suggestion)

        # Config file preview (if written)
        config_r = next((r for r in report.results if r.name == 'config'), None)
        if config_r and config_r.ok:
            from core.validator import read_config_file
            content = read_config_file()
            if content:
                self._section('📄 生成的 opencode.jsonc')
                path = config_r.metadata.get('path', '~/.config/opencode/opencode.jsonc')
                self._jsonc_terminal(content, path)

        # Tail message
        tail_color = COLORS['neon_green'] if report.overall_status == Status.SUCCESS else COLORS['yellow']
        tail_msg = '\n✅ 全部验证通过！' if report.overall_status == Status.SUCCESS \
            else '\n⚠ 部分测试未通过，可返回修改配置'
        tk.Label(self.scroll.inner, text=tail_msg, bg=COLORS['bg'], fg=tail_color,
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=15, pady=(8, 4))

        self.finish_btn.set_enabled(True)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _section(self, text: str):
        tk.Frame(self.scroll.inner, bg=COLORS['bg'], height=6).pack()
        tk.Label(self.scroll.inner, text=text, bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=15, pady=(6, 2))

    def _result_row(self, r: ValidationResult):
        """Display a single result with icon + message + duration."""
        if r.status == Status.SUCCESS:
            icon, color = '✓', COLORS['neon_green']
        elif r.status == Status.WARNING:
            icon, color = '⚠', COLORS['yellow']
        else:
            icon, color = '✗', COLORS['red']

        row = tk.Frame(self.scroll.inner, bg=COLORS['bg'])
        row.pack(fill='x', padx=25, pady=2)
        tk.Label(row, text=icon, bg=COLORS['bg'], fg=color,
                 font=(FONTS['body']['family'], FONTS['body']['size']), width=2).pack(side='left')
        duration = format_duration(r.duration_ms)
        msg = f'{r.message[:90]} ({duration})'
        tk.Label(row, text=msg, bg=COLORS['bg'], fg=color,
                 font=(FONTS['log']['family'], FONTS['log']['size']), anchor='w').pack(
                     side='left', padx=4)

    def _suggestion_box(self, test_name: str, suggestion: str):
        """Diagnostic suggestion box with 8-bit styling."""
        box = tk.Frame(self.scroll.inner, bg=COLORS['dark_gray'], relief='ridge', borderwidth=1)
        box.pack(fill='x', padx=25, pady=3)
        tk.Label(box, text=f'💡 {test_name}', bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=8, pady=(4, 2))
        tk.Label(box, text=suggestion, bg=COLORS['dark_gray'], fg=COLORS['white'],
                 font=(FONTS['log']['family'], FONTS['log']['size']),
                 wraplength=600, justify='left').pack(anchor='w', padx=8, pady=(0, 4))

    def _jsonc_terminal(self, content: str, path: str):
        """Terminal-style JSONC display with masked API key in yellow."""
        term = tk.Frame(self.scroll.inner, bg=COLORS['black'], relief='solid', borderwidth=2,
                        highlightbackground=COLORS['neon_green'], highlightthickness=1)
        term.pack(fill='x', padx=20, pady=4)

        bar = tk.Frame(term, bg=COLORS['dark_gray'], height=18)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text=f'┌── {path} ──', bg=COLORS['dark_gray'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=6)

        line_count = min(content.count('\n') + 1, 16)
        text = tk.Text(term, height=line_count, bg=COLORS['black'],
                       fg=COLORS['neon_green'], font=(FONTS['log']['family'], FONTS['log']['size']),
                       relief='flat', padx=8, pady=4, wrap='none', state='disabled')
        text.pack(fill='x')
        text.tag_configure('masked', foreground=COLORS['yellow'])
        text.configure(state='normal')
        for line in content.split('\n'):
            if 'apiKey' in line:
                text.insert('end', line + '\n', 'masked')
            else:
                text.insert('end', line + '\n')
        text.configure(state='disabled')

    # ── Navigation ────────────────────────────────────────────────────────────

    def _on_finish(self):
        from ui.pages.finish import FinishPage
        self.app.show_page(FinishPage, 'finish')

    def _on_key_next(self):
        if hasattr(self.finish_btn, 'is_enabled') and self.finish_btn.is_enabled():
            self._on_finish()
        elif self.finish_btn.winfo_ismapped():
            self._on_finish()
