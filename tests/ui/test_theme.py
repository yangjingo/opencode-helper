import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_colors_have_required_keys():
    from ui.theme import COLORS
    required = ['bg', 'neon_green', 'red', 'yellow', 'dark_gray', 'white', 'deep_purple']
    for key in required:
        assert key in COLORS, f"Missing color key: {key}"

def test_colors_are_hex():
    from ui.theme import COLORS
    for key, val in COLORS.items():
        assert val.startswith('#'), f"{key}: {val} is not hex"
        assert len(val) == 7, f"{key}: {val} wrong length"

def test_fonts_have_required_keys():
    from ui.theme import FONTS
    for key in ['title', 'body', 'log', 'button', 'heading']:
        assert key in FONTS, f"Missing font key: {key}"

def test_styles_have_required_keys():
    from ui.theme import STYLES
    for key in ['frame', 'button', 'label', 'entry', 'terminal']:
        assert key in STYLES, f"Missing style key: {key}"
