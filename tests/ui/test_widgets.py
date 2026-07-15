import sys, os, tkinter as tk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def setup_root():
    root = tk.Tk()
    root.withdraw()
    return root

def test_pixel_button_creates():
    from ui.widgets import PixelButton
    root = setup_root()
    btn = PixelButton(root, text="Test", command=lambda: None)
    assert btn is not None
    assert btn['text'] == "Test"
    root.destroy()

def test_pixel_button_command():
    from ui.widgets import PixelButton
    root = setup_root()
    called = []; btn = PixelButton(root, text="Click", command=lambda: called.append(1))
    btn.invoke()
    assert called == [1]
    root.destroy()

def test_pixel_entry_creates():
    from ui.widgets import PixelEntry
    root = setup_root()
    entry = PixelEntry(root, placeholder="Enter text...")
    assert entry is not None
    root.destroy()

def test_pixel_entry_get_set():
    from ui.widgets import PixelEntry
    root = setup_root()
    entry = PixelEntry(root)
    entry.insert(0, "hello")
    assert entry.get() == "hello"
    root.destroy()

def test_pixel_progress_creates():
    from ui.widgets import PixelProgress
    root = setup_root()
    bar = PixelProgress(root, width=200, height=20)
    assert bar is not None
    root.destroy()

def test_pixel_progress_set_progress():
    from ui.widgets import PixelProgress
    root = setup_root()
    bar = PixelProgress(root, width=200, height=20)
    bar.set_progress(50)
    root.destroy()

def test_pixel_toggle_creates():
    from ui.widgets import PixelToggle
    root = setup_root()
    var = tk.BooleanVar(value=True)
    toggle = PixelToggle(root, text="Enable", variable=var)
    assert toggle is not None
    root.destroy()

def test_pixel_terminal_creates():
    from ui.widgets import PixelTerminal
    root = setup_root()
    term = PixelTerminal(root, width=60, height=10)
    assert term is not None
    root.destroy()

def test_pixel_terminal_write_and_clear():
    from ui.widgets import PixelTerminal
    root = setup_root()
    term = PixelTerminal(root, width=60, height=10)
    term.write("Hello World", "info")
    term.clear()
    root.destroy()
