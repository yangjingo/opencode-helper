"""Warm ink/paper theme system for OpenCode Helper v2.0 — 8-bit game terminal style."""
import tkinter as tk
import os

# ── Warm ink palette (user-provided) ──────────────────────────────────────────
INK            = '#26251e'  # Display, body emphasis. Warm near-black.
BODY           = '#5a5852'  # Default running-text.
MUTED          = '#807d72'  # Sub-titles.
MUTED_SOFT     = '#a09c92'  # Disabled text.
HAIRLINE       = '#e6e5e0'  # 1px divider.
HAIRLINE_STRONG = '#cfcdc4'  # Stronger panel outline.

# ── Derived colors for pixel UI ───────────────────────────────────────────────
WARM_AMBER      = '#d4a83c'  # Accent: warm gold (replaces neon green)
WARM_AMBER_DIM  = '#6b5420'  # Dim amber for hover/inactive
WARM_RED         = '#c44b4b'  # Error/warning, warm tone
WARM_RED_DIM     = '#5c2020'  # Dim red
WARM_GREEN       = '#7a9a5e'  # Success, warm green
WARM_GREEN_DIM   = '#3a4a2a'  # Dim green

INK_LIGHT        = '#322f28'  # Card/panel background (lighter than bg)
INK_DARK         = '#1a1915'  # Terminal bg / deep input bg
INK_DARKER       = '#12110e'  # Darkest shade

COLORS = {
    # Core
    'bg':            INK,
    'bg_darker':     INK_DARKER,
    'bg_light':      INK_LIGHT,
    # Text
    'white':         BODY,           # Main text (was #e0e0e0)
    'muted':         MUTED,          # Secondary text
    'muted_soft':    MUTED_SOFT,     # Disabled
    # Accent (warm amber replaces neon green)
    'neon_green':    WARM_AMBER,
    'neon_green_dim':WARM_AMBER_DIM,
    # Status colors
    'red':           WARM_RED,
    'red_dim':       WARM_RED_DIM,
    'dark_green':    WARM_GREEN_DIM,
    # UI elements
    'dark_gray':     INK_LIGHT,      # Card/button bg (was #2a2a3e)
    'dark_gray2':    INK_DARK,       # Deeper bg
    'deep_purple':   INK_DARK,       # Input bg (was #1a1a2e)
    'black':         INK_DARKER,     # Terminal bg (was #000000)
    'yellow':        WARM_AMBER,     # Highlight = accent
    'yellow_dim':    WARM_AMBER_DIM,
    'border_dim':    HAIRLINE,       # Border subtle
    'glow':          '#3a3628',      # Warm glow (replaces green glow)
    # New warm-specific
    'divider':       HAIRLINE,
    'border_strong': HAIRLINE_STRONG,
}

FONTS = {
    'title':    {'family': 'Consolas', 'size': 15, 'weight': 'bold'},
    'body':     {'family': 'Consolas', 'size': 10},
    'log':      {'family': 'Consolas', 'size': 9},
    'button':   {'family': 'Consolas', 'size': 10},
    'heading':  {'family': 'Consolas', 'size': 12, 'weight': 'bold'},
    'small':    {'family': 'Consolas', 'size': 8},
    'huge':     {'family': 'Consolas', 'size': 18, 'weight': 'bold'},
    'pixel':    {'family': 'Consolas', 'size': 7},
}

BORDER_CHARS = {
    'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
    'h':  '═', 'v':  '║', 't':  '╦', 'b':  '╩',
    'l':  '╠', 'r':  '╣', 'c':  '╬',
    's':  '░', 'f':  '▓', 'h2': '─', 'v2': '│',
}

def apply(root: tk.Tk):
    root.configure(bg=COLORS['bg'])
    root.resizable(False, False)
    root.option_add('*Font', (FONTS['body']['family'], FONTS['body']['size']))

def pixel_border(canvas, x1, y1, x2, y2, color=None, width=2):
    color = color or COLORS['neon_green']
    canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
    inset = width + 1
    canvas.create_rectangle(x1+inset, y1+inset, x2-inset, y2-inset,
                           outline=COLORS['dark_gray'], width=1)

def pixel_line(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
               color=None, width: int = 1, dash: bool = False):
    color = color or COLORS['neon_green']
    kw = {'dash': (4, 4)} if dash else {}
    canvas.create_line(x1, y1, x2, y2, fill=color, width=width, **kw)

def pixel_panel(parent, title: str = '', bg_color=None) -> tk.Frame:
    bg = bg_color or COLORS['bg']
    outer = tk.Frame(parent, bg=bg)
    outer.inner = tk.Frame(outer, bg=bg)
    outer.inner.pack(fill='both', expand=True, padx=14, pady=10)
    return outer

def draw_pixel_header(canvas: tk.Canvas, x: int, y: int, width: int, text: str):
    canvas.create_text(x + width//2, y, text=text, fill=COLORS['neon_green'],
                      font=(FONTS['heading']['family'], FONTS['heading']['size'], 'bold'),
                      anchor='n')
