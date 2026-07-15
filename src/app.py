"""Main application window, page routing, wizard state, and navigation."""
import tkinter as tk
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from ui.theme import COLORS, FONTS, apply as apply_theme

# ── Wizard State ──────────────────────────────────────────────────────────────

@dataclass
class WizardState:
    install_method: str = 'npm'
    install_path: str = ''
    provider_name: str = ''
    display_name: str = ''
    api_key: str = ''
    base_url: str = ''
    model_id: str = ''
    model_name: str = ''
    reasoning: bool = True
    thinking: bool = True
    env_report: Dict[str, Any] = field(default_factory=dict)
    cc_config_found: bool = False
    migration_items: List[Dict[str, Any]] = field(default_factory=list)
    preset: str = ''

    def to_dict(self) -> dict:
        return {
            'install_method': self.install_method,
            'install_path': self.install_path,
            'provider_name': self.provider_name,
            'display_name': self.display_name,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model_id': self.model_id,
            'model_name': self.model_name,
            'reasoning': self.reasoning,
            'thinking': self.thinking,
        }

# ── Page step mapping ──────────────────────────────────────────────────────────

_PAGE_STEP: Dict[str, int] = {
    'welcome': 1, 'migration': 2, 'environment': 3, 'env_fix': 4,
    'install_method': 5, 'install_path': 5, 'install': 6,
    'config_model': 7, 'verify': 8, 'finish': 10,
}
_TOTAL_STEPS = 10

def get_page_step(name: str) -> int:
    return _PAGE_STEP.get(name, 0)

# ── Step Indicator ────────────────────────────────────────────────────────────

class StepIndicator(tk.Frame):
    """8-bit pixel step indicator: ⬤⬤⬤⬤○ 4/10"""

    def __init__(self, parent, total: int = _TOTAL_STEPS):
        super().__init__(parent, bg=COLORS['bg'])
        self._total = total
        self._current = 0

        self._label = tk.Label(
            self, text='', bg=COLORS['bg'], fg=COLORS['neon_green'],
            font=(FONTS['body']['family'], FONTS['body']['size']),
        )
        self._label.pack(side='bottom', pady=(0, 4))

    def set_step(self, step: int):
        self._current = step
        filled = '⬤' * step
        empty = '○' * (self._total - step)
        self._label.configure(text=f'{filled}{empty}  {step}/{self._total}')

# ── Page Transition Animation ─────────────────────────────────────────────────

def _animate_transition(old_frame, new_frame, callback, duration_ms: int = 80):
    """Quick pixel fade: old fades out, new fades in."""
    if old_frame:
        old_frame.place_forget()
    new_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    # Simple instant swap for pixel style (feels snappier than animation)
    if old_frame:
        old_frame.destroy()
    callback()

# ── App ───────────────────────────────────────────────────────────────────────

class App:
    WINDOW_WIDTH = 760
    WINDOW_HEIGHT = 560

    def __init__(self, root: tk.Tk):
        self.root = root
        self.state = WizardState()
        self._current_page = None
        self._page_history: list = []  # list of (page_class, page_name) tuples

        root.title('OpenCode Helper v2.0')
        root.geometry(f'{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}')
        apply_theme(root)

        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - self.WINDOW_WIDTH) // 2
        y = (sh - self.WINDOW_HEIGHT) // 2
        root.geometry(f'+{x}+{y}')

        # Main layout: content + step indicator + key hints
        self.container = tk.Frame(root, bg=COLORS['bg'])
        self.container.pack(fill='both', expand=True)

        # Content area (pages draw here)
        self.content_frame = tk.Frame(self.container, bg=COLORS['bg'])
        self.content_frame.pack(fill='both', expand=True, padx=2, pady=(2, 0))

        # Bottom bar: step indicator + keyboard hint
        bottom = tk.Frame(self.container, bg=COLORS['bg'], height=32)
        bottom.pack(fill='x', side='bottom', pady=(0, 2))
        bottom.pack_propagate(False)

        self.step_indicator = StepIndicator(bottom)
        self.step_indicator.pack(side='left', padx=10)

        self._key_hint = tk.Label(
            bottom, text='[Enter]继续  [Esc]返回',
            bg=COLORS['bg'], fg=COLORS['dark_gray'],
            font=(FONTS['log']['family'], FONTS['log']['size']),
        )
        self._key_hint.pack(side='right', padx=10)

        # Global keyboard bindings
        root.bind('<Return>', self._on_enter)
        root.bind('<Escape>', self._on_escape)
        for i in range(1, 10):
            root.bind(str(i), lambda e, n=i: self._on_number(n))

    def show_page(self, page_class, page_name: str = ''):
        """Navigate to a new page, destroying the old one."""
        old = self._current_page
        if self._current_page:
            self._page_history.append((type(self._current_page), self._current_page._page_name))

        self._current_page = page_class(self.content_frame, self)
        self._current_page._page_name = page_name or page_class.__name__
        self._current_page.place(relx=0, rely=0, relwidth=1, relheight=1)

        step = get_page_step(self._current_page._page_name)
        self.step_indicator.set_step(step)

        if old:
            old.destroy()

    def go_back(self):
        """Go to the previous page."""
        if self._page_history:
            prev_cls, prev_name = self._page_history.pop()
            old = self._current_page
            self._current_page = prev_cls(self.content_frame, self)
            self._current_page._page_name = prev_name
            self._current_page.place(relx=0, rely=0, relwidth=1, relheight=1)

            step = get_page_step(prev_name)
            self.step_indicator.set_step(step)

            if old:
                old.destroy()

    def set_key_hint(self, text: str):
        self._key_hint.configure(text=text)

    def _on_enter(self, event):
        if self._current_page and hasattr(self._current_page, '_on_key_next'):
            self._current_page._on_key_next()

    def _on_escape(self, event):
        if self._current_page and hasattr(self._current_page, '_on_key_back'):
            self._current_page._on_key_back()

    def _on_number(self, n: int):
        if self._current_page and hasattr(self._current_page, '_on_key_number'):
            self._current_page._on_key_number(n)

    def run(self):
        from ui.pages.welcome import WelcomePage
        self.show_page(WelcomePage, 'welcome')
        self.root.mainloop()
