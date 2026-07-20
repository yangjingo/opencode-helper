"""Custom 8-bit game style pixel widgets for OpenCode Helper v2.0."""
import tkinter as tk
import time
from .theme import COLORS, FONTS, BORDER_CHARS

# ── PixelButton ────────────────────────────────────────────────────────────────

class PixelButton(tk.Button):
    """3D pixel-relief button with click animation and neon-green styling."""

    def __init__(self, parent, text="", command=None, **kw):
        super().__init__(parent, text=text, command=command,
                         bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                         activebackground=COLORS['neon_green'], activeforeground=COLORS['bg'],
                         font=(FONTS['button']['family'], FONTS['button']['size']),
                         relief='raised', borderwidth=4, padx=16, pady=5, cursor='hand2', **kw)
        self._orig_relief = 'raised'
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)

    def _on_enter(self, e):
        self.configure(bg=COLORS['dark_green'])

    def _on_leave(self, e):
        self.configure(bg=COLORS['dark_gray'], relief=self._orig_relief)

    def _on_press(self, e):
        self.configure(relief='sunken')

    def _on_release(self, e):
        self.configure(relief='raised')

    def set_enabled(self, enabled: bool):
        if enabled:
            self.configure(state='normal', fg=COLORS['neon_green'])
        else:
            self.configure(state='disabled', fg=COLORS['dark_gray'])

# ── PixelEntry ─────────────────────────────────────────────────────────────────

class PixelEntry(tk.Entry):
    """Pixel-themed text input with block cursor."""

    def __init__(self, parent, placeholder="", show=None, **kw):
        super().__init__(parent, bg=COLORS['deep_purple'], fg=COLORS['neon_green'],
                         insertbackground=COLORS['neon_green'], insertwidth=10,
                         relief='sunken', borderwidth=3,
                         font=(FONTS['body']['family'], FONTS['body']['size']),
                         show=show, **kw)
        self._placeholder = placeholder
        if placeholder:
            self.insert(0, placeholder)
            self.configure(fg=COLORS['dark_gray'])
            self.bind('<FocusIn>', self._on_focus_in)
            self.bind('<FocusOut>', self._on_focus_out)

    def _on_focus_in(self, e):
        if self.get() == self._placeholder:
            self.delete(0, 'end')
            self.configure(fg=COLORS['neon_green'])

    def _on_focus_out(self, e):
        if not self.get():
            self.insert(0, self._placeholder)
            self.configure(fg=COLORS['dark_gray'])

# ── PixelProgress ──────────────────────────────────────────────────────────────

class PixelProgress(tk.Canvas):
    """8-bit block progress bar with incremental animation."""

    def __init__(self, parent, width=300, height=28, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=COLORS['bg'], highlightthickness=0, **kw)
        self._width = width
        self._height = height
        self._pct = 0
        self._text = "0%"
        self._block_ids = []
        self._draw()

    def _draw(self):
        self.delete('all')
        self._block_ids.clear()
        w, h = self._width, self._height
        # Outer pixel border
        self.create_rectangle(0, 0, w, h, outline=COLORS['neon_green'], width=2)
        # Pixel blocks
        block_w, gap = 14, 5
        blocks_total = max(1, (w - 18) // (block_w + gap))
        blocks_filled = int(blocks_total * self._pct / 100)
        x0 = 9
        for i in range(blocks_total):
            bx = x0 + i * (block_w + gap)
            by = 6
            fill = COLORS['neon_green'] if i < blocks_filled else COLORS['dark_gray']
            rid = self.create_rectangle(bx, by, bx + block_w, by + (h - 12),
                                        fill=fill, outline=COLORS['border_dim'], width=1)
            self._block_ids.append(rid)
        # Center text with shadow for readability
        cx, cy = w / 2, h / 2
        self.create_text(cx + 1, cy + 1, text=self._text, fill=COLORS['black'],
                         font=(FONTS['log']['family'], FONTS['log']['size']))
        self.create_text(cx, cy, text=self._text, fill=COLORS['white'],
                         font=(FONTS['log']['family'], FONTS['log']['size']))

    def set_progress(self, pct: float):
        """Set progress 0-100. Only redraws changed blocks."""
        new_pct = max(0, min(100, pct))
        if abs(new_pct - self._pct) < 0.5:
            return
        self._pct = new_pct
        self._text = f"{int(self._pct)}%"

        # Incremental: only update blocks that changed color
        block_w, gap = 14, 5
        blocks_total = max(1, (self._width - 18) // (block_w + gap))
        blocks_filled = int(blocks_total * self._pct / 100)

        for i, rid in enumerate(self._block_ids):
            fill = COLORS['neon_green'] if i < blocks_filled else COLORS['dark_gray']
            self.itemconfigure(rid, fill=fill)

        # Update text
        self.delete('progtext')
        cx, cy = self._width / 2, self._height / 2
        self.create_text(cx + 1, cy + 1, text=self._text, fill=COLORS['black'],
                         font=(FONTS['log']['family'], FONTS['log']['size']), tags='progtext')
        self.create_text(cx, cy, text=self._text, fill=COLORS['white'],
                         font=(FONTS['log']['family'], FONTS['log']['size']), tags='progtext')

    def set_text(self, text: str):
        self._text = text
        self.delete('progtext')
        cx, cy = self._width / 2, self._height / 2
        self.create_text(cx + 1, cy + 1, text=self._text, fill=COLORS['black'],
                         font=(FONTS['log']['family'], FONTS['log']['size']), tags='progtext')
        self.create_text(cx, cy, text=self._text, fill=COLORS['white'],
                         font=(FONTS['log']['family'], FONTS['log']['size']), tags='progtext')

# ── PixelToggle ────────────────────────────────────────────────────────────────

class PixelToggle(tk.Frame):
    """8-bit style toggle switch: [ ON ] / [ OFF ] with neon styling."""

    def __init__(self, parent, text="", variable=None, **kw):
        super().__init__(parent, bg=COLORS['bg'], **kw)
        self._var = variable or tk.BooleanVar(value=False)
        self._label_text = text

        self._btn = tk.Button(self, text='', command=self._toggle,
                              bg=COLORS['dark_gray'], fg=COLORS['neon_green'],
                              activebackground=COLORS['neon_green'], activeforeground=COLORS['bg'],
                              font=(FONTS['button']['family'], FONTS['button']['size']),
                              relief='raised', borderwidth=3, padx=8, pady=2,
                              cursor='hand2', width=8)
        self._btn.pack(side='left')

        if text:
            tk.Label(self, text=text, bg=COLORS['bg'], fg=COLORS['white'],
                     font=(FONTS['body']['family'], FONTS['body']['size'])).pack(side='left', padx=(6, 0))

        self._update_display()
        self._var.trace_add('write', lambda *a: self._update_display())

    def _toggle(self):
        self._var.set(not self._var.get())

    def _update_display(self):
        if self._var.get():
            self._btn.configure(text='[ ▣ ON ]', fg=COLORS['neon_green'],
                               bg=COLORS['dark_green'])
        else:
            self._btn.configure(text='[ □ OFF ]', fg=COLORS['dark_gray'],
                               bg=COLORS['dark_gray2'])

# ── PixelTerminal ──────────────────────────────────────────────────────────────

def terminal_message_tag(msg: str, requested_tag: str = 'info') -> str:
    """Choose a visual tag, giving executed shell commands priority.

    Background installers emit commands as ``$ ...`` or ``[PowerShell] $ ...``.
    Keeping this policy in the terminal makes every installer page consistent.
    """
    if requested_tag == 'info':
        line = (msg or '').lstrip()
        if line.startswith('$ ') or line.startswith('[PowerShell] $') or line.startswith('[CMD] $'):
            return 'command'
    return requested_tag

class PixelTerminal(tk.Frame):
    """Scrollable terminal with pixel border header/footer. Throttled for performance."""

    MAX_LINES = 5000

    def __init__(self, parent, width=70, height=12, title: str = 'terminal', **kw):
        super().__init__(parent, bg=COLORS['black'], **kw)
        self._throttle_ms = 50
        self._pending = []
        self._throttle_id = None

        # Top border bar
        top_bar = tk.Frame(self, bg=COLORS['black'], height=20)
        top_bar.pack(fill='x', side='top')
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text=f'┌── {title} ', bg=COLORS['black'], fg=COLORS['neon_green'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=4)

        # Text area
        text_frame = tk.Frame(self, bg=COLORS['black'])
        text_frame.pack(fill='both', expand=True, padx=4)

        self.text = tk.Text(text_frame, width=width, height=height,
                            bg=COLORS['black'], fg=COLORS['neon_green'],
                            insertbackground=COLORS['neon_green'],
                            font=(FONTS['log']['family'], FONTS['log']['size']),
                            relief='flat', borderwidth=0, padx=4, pady=2,
                            wrap='word', state='disabled')
        self.text.pack(fill='both', expand=True)

        # Bottom border
        bot_bar = tk.Frame(self, bg=COLORS['black'], height=16)
        bot_bar.pack(fill='x', side='bottom')
        bot_bar.pack_propagate(False)
        tk.Label(bot_bar, text='└' + '─' * 80, bg=COLORS['black'], fg=COLORS['neon_green'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='left', padx=4)

        # Tag configs
        self.text.tag_configure('info', foreground=COLORS['neon_green'])
        self.text.tag_configure('error', foreground=COLORS['red'])
        self.text.tag_configure('warn', foreground=COLORS['yellow'])
        self.text.tag_configure('success', foreground=COLORS['neon_green'])
        self.text.tag_configure(
            'command', foreground=COLORS['yellow'], background=COLORS['dark_gray2'],
            font=(FONTS['log']['family'], FONTS['log']['size'], 'bold'),
            lmargin1=6, lmargin2=6, spacing1=2, spacing3=2,
        )

        # Clipboard: Ctrl+C copy, Ctrl+A select all, right-click copy
        self.text.bind('<Control-c>', self._copy)
        self.text.bind('<Control-a>', self._select_all)
        self.text.bind('<Button-3>', self._right_click_copy)

        # Allow text selection even when disabled
        self.text.bind('<Button-1>', lambda e: self.text.focus_set())

    def _copy(self, event=None):
        try:
            sel = self.text.get('sel.first', 'sel.last')
            self.clipboard_clear()
            self.clipboard_append(sel)
        except Exception:
            pass  # no selection

    def _select_all(self, event=None):
        self.text.focus_set()
        self.text.tag_add('sel', '1.0', 'end')
        return 'break'

    def _right_click_copy(self, event=None):
        try:
            sel = self.text.get('sel.first', 'sel.last')
            self.clipboard_clear()
            self.clipboard_append(sel)
        except Exception:
            pass

    def write(self, msg: str, tag: str = 'info'):
        """Queue a message. Batched & throttled for performance."""
        self._pending.append((msg, terminal_message_tag(msg, tag)))
        if self._throttle_id is None:
            self._throttle_id = self.after(self._throttle_ms, self._flush)

    def _flush(self):
        self._throttle_id = None
        if not self._pending:
            return
        self.text.configure(state='normal')

        # Trim if too many lines
        line_count = int(self.text.index('end-1c').split('.')[0])
        overflow = line_count + len(self._pending) - self.MAX_LINES
        if overflow > 0:
            self.text.delete('1.0', f'{overflow + 1}.0')

        for msg, tag in self._pending:
            self.text.insert('end', msg + '\n', tag)
        self.text.see('end')
        self.text.configure(state='disabled')
        self._pending.clear()

    def clear(self):
        self._pending.clear()
        if self._throttle_id:
            self.after_cancel(self._throttle_id)
            self._throttle_id = None
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.configure(state='disabled')

# ── ScrollableFrame ────────────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    """Unified scrollable content area for pages. Eliminates duplicated Canvas+scrollbar code."""

    def __init__(self, parent, bg_color=None, **kw):
        bg = bg_color or COLORS['bg']
        super().__init__(parent, bg=bg, **kw)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)

        self.inner.bind('<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind canvas width to inner frame
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind('<Enter>', self._bind_mousewheel)
        self.canvas.bind('<Leave>', self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._win_id, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all('<MouseWheel>',
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units'))

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all('<MouseWheel>')

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()

# ── PixelPanel ─────────────────────────────────────────────────────────────────

class PixelPanel(tk.Frame):
    """8-bit game dialog panel with pixel border and title.

    ┌── Panel Title ──────────────────────┐
    │                                      │
    │   (content goes in panel.inner)      │
    │                                      │
    └──────────────────────────────────────┘
    """

    def __init__(self, parent, title: str = '', width: int = 600, **kw):
        super().__init__(parent, bg=COLORS['bg'], **kw)

        # Title bar
        if title:
            title_bar = tk.Frame(self, bg=COLORS['bg'], height=24)
            title_bar.pack(fill='x')
            title_bar.pack_propagate(False)
            tk.Label(title_bar, text=f'┌── {title} ', bg=COLORS['bg'], fg=COLORS['yellow'],
                     font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(side='left', padx=4)
            # Right border line
            sep = tk.Frame(title_bar, bg=COLORS['neon_green'], height=1)
            sep.pack(fill='x', side='bottom')

        # Content area
        self.inner = tk.Frame(self, bg=COLORS['bg'], padx=10, pady=6)
        self.inner.pack(fill='both', expand=True)

# ── BasePage ───────────────────────────────────────────────────────────────────

class BasePage(tk.Frame):
    """Base class for all wizard pages with lifecycle management.

    Provides:
      - _destroyed flag for safe cross-thread UI updates
      - _safe_after() for crash-proof tkinter after() calls
      - Keyboard navigation hooks: _on_key_next(), _on_key_back()
    """

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS['bg'])
        self.app = app
        self._destroyed = False
        self._page_name = ''

    def destroy(self):
        self._destroyed = True
        # Clean up any lingering after callbacks
        try:
            super().destroy()
        except Exception:
            pass

    def _safe_after(self, ms: int, callback, *args):
        """Schedule a callback. Safe to call from any thread — silently
        drops if the page has been destroyed."""
        if self._destroyed:
            return
        def _wrap():
            if not self._destroyed:
                try:
                    callback(*args)
                except Exception:
                    pass
        try:
            self.after(ms, _wrap)
        except Exception:
            pass  # widget destroyed between check and after() call

    def _on_key_next(self):
        """Override in subclass to handle Enter key."""
        pass

    def _on_key_back(self):
        """Override in subclass to handle Escape key."""
        self.app.go_back()

    def _on_key_number(self, n: int):
        """Override in subclass to handle number keys 1-9."""
        pass

    def _section_header(self, text: str):
        """Render a section header inside a ScrollableFrame inner."""
        parent = getattr(self, 'scroll', None)
        target = parent.inner if parent else self
        tk.Frame(target, bg=COLORS['bg'], height=4).pack()
        tk.Label(target, text=text, bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['body']['family'], FONTS['body']['size'], 'bold')).pack(
                     anchor='w', padx=15, pady=(6, 2))
