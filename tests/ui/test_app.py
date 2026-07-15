import sys, os, tkinter as tk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def test_wizard_state_defaults():
    from app import WizardState
    state = WizardState()
    assert state.install_method == 'npm'
    assert state.reasoning is True
    assert state.thinking is True
    assert state.env_report == {}
    assert state.migration_items == []

def test_wizard_state_to_dict():
    from app import WizardState
    state = WizardState(provider_name='test', api_key='sk-123')
    d = state.to_dict()
    assert d['provider_name'] == 'test'
    assert d['api_key'] == 'sk-123'

def test_app_creates():
    import tkinter as tk
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError:
        import pytest; pytest.skip("Tkinter not available")
    from app import App
    app = App(root)
    assert app is not None
    assert app.state is not None
    assert app.state.install_method == 'npm'
    root.destroy()
