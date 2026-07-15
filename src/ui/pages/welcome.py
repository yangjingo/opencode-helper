"""Welcome page — Canvas pixel-block logo for accurate 'OpenCode Helper' display."""
import tkinter as tk
from ui.theme import COLORS, FONTS
from ui.widgets import PixelButton, BasePage
from i18n import t

# ── Pixel letter bitmaps (5x7 grid per letter, 1=lit 0=dark) ──────────────────
# Characters A-Z rendered as 5-wide × 7-tall pixel blocks

PIXEL_FONT = {
    'O': ['01110','10001','10001','10001','10001','10001','01110'],
    'P': ['11110','10001','10001','11110','10000','10000','10000'],
    'E': ['11111','10000','10000','11110','10000','10000','11111'],
    'N': ['10001','11001','10101','10011','10001','10001','10001'],
    'C': ['01110','10001','10000','10000','10000','10001','01110'],
    'D': ['11110','10001','10001','10001','10001','10001','11110'],
    'H': ['10001','10001','10001','11111','10001','10001','10001'],
    'L': ['10000','10000','10000','10000','10000','10000','11111'],
    'R': ['11110','10001','10001','11110','10100','10010','10001'],
    ' ': ['00000','00000','00000','00000','00000','00000','00000'],
}

TITLE_TEXT = "OPENCODE HELPER"
LETTER_W = 5   # pixel columns per letter
LETTER_H = 7   # pixel rows per letter
BLOCK_SIZE = 4  # screen pixels per pixel-block
LETTER_GAP = 2  # blocks gap between letters

def _draw_pixel_text(canvas, text: str, start_x: int, start_y: int,
                     lit_color=None, dark_color=None, block_size: int = BLOCK_SIZE):
    """Draw text as colored pixel blocks on canvas. Returns total width drawn."""
    lit = lit_color or COLORS['neon_green']
    dark = dark_color or COLORS['bg_darker']
    bs = block_size
    x = start_x

    for ch in text.upper():
        glyph = PIXEL_FONT.get(ch, PIXEL_FONT[' '])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                fill = lit if bit == '1' else dark
                x1 = x + col * bs
                y1 = start_y + row * bs
                canvas.create_rectangle(x1, y1, x1 + bs, y1 + bs,
                                       fill=fill, outline='', tags='logo')
        x += (LETTER_W + LETTER_GAP) * bs
    return x - start_x

class WelcomePage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._page_name = 'welcome'
        app.set_key_hint('[Enter]开始  [Esc]退出')

        tk.Frame(self, bg=COLORS['bg'], height=20).pack()

        # ── Pixel-block logo canvas ──
        # Calculate dimensions
        total_letters = len(TITLE_TEXT)
        pixel_w = total_letters * (LETTER_W + LETTER_GAP) * BLOCK_SIZE - LETTER_GAP * BLOCK_SIZE
        pixel_h = LETTER_H * BLOCK_SIZE
        pad = 24
        canvas_w = pixel_w + pad * 2
        canvas_h = pixel_h + pad * 2 + 10

        logo_canvas = tk.Canvas(self, width=canvas_w, height=canvas_h,
                               bg=COLORS['bg'], highlightthickness=0)
        logo_canvas.pack(pady=(0, 8))

        # Outer pixel border
        logo_canvas.create_rectangle(6, 4, canvas_w - 6, canvas_h - 4,
                                    outline=COLORS['neon_green'], width=2)
        logo_canvas.create_rectangle(10, 8, canvas_w - 10, canvas_h - 8,
                                    outline=COLORS['dark_gray'], width=1)

        # Draw pixel text centered
        _draw_pixel_text(logo_canvas, TITLE_TEXT,
                        start_x=pad, start_y=pad + 6,
                        lit_color=COLORS['neon_green'],
                        dark_color=COLORS['bg_darker'])

        # Subtitle
        tk.Label(self, text='OpenCode Helper', bg=COLORS['bg'], fg=COLORS['neon_green'],
                 font=(FONTS['huge']['family'], FONTS['huge']['size'], 'bold')).pack(pady=(6, 2))
        tk.Label(self, text='一键配置 OpenCode CLI + 桌面端共享配置', bg=COLORS['bg'], fg=COLORS['white'],
                 font=(FONTS['body']['family'], FONTS['body']['size'])).pack(pady=(0, 12))

        # Separator
        tk.Frame(self, bg=COLORS['neon_green'], height=2, width=420).pack(pady=(0, 16))

        # Start button
        self.start_btn = PixelButton(self, text=f'[ ▶  {t("welcome.start")}  ]', command=self._on_start)
        self.start_btn.pack(pady=8)

        # Version
        tk.Label(self, text='v2.0  ·  by whyj  ·  8-bit edition',
                 bg=COLORS['bg'], fg=COLORS['yellow'],
                 font=(FONTS['small']['family'], FONTS['small']['size'])).pack(side='bottom', pady=(0, 10))
        self.start_btn.focus_set()

    def _on_start(self):
        from core.detector import detect_claude_config
        config = detect_claude_config()
        if config['claude_config_found']:
            from ui.pages.migration import MigrationPage
            self.app.show_page(MigrationPage, 'migration')
        else:
            from ui.pages.environment import EnvironmentPage
            self.app.show_page(EnvironmentPage, 'environment')

    def _on_key_next(self):
        self._on_start()

    def _on_key_back(self):
        self.app.root.destroy()
