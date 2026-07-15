"""Integration tests — full page flow and config write."""
import sys, os, tkinter as tk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_full_page_flow(monkeypatch):
    from app import App
    root = tk.Tk(); root.withdraw()
    app = App(root)

    from ui.pages.welcome import WelcomePage
    app.show_page(WelcomePage)

    app.state.env_report = {
        'os_name': 'Windows', 'os_version': '10.0', 'os_ok': True,
        'node_installed': True, 'node_version': 'v20.11.0', 'node_ok': True,
        'npm_installed': True, 'npm_version': '10.0.0', 'npm_ok': True,
        'opencode_installed': False, 'disk_free_gb': 50.0, 'disk_ok': True,
        'proxy_detected': False, 'claude_config_found': False,
        'claude_settings': {}, 'project_settings': {},
        'claude_env_vars': {}, 'env_vars': {},
    }
    from ui.pages.environment import EnvironmentPage
    app.show_page(EnvironmentPage)
    assert app._current_page is not None

    from ui.pages.install_method import InstallMethodPage
    app.show_page(InstallMethodPage)
    assert app._current_page is not None

    from ui.pages.config_model import ConfigModelPage
    app.show_page(ConfigModelPage)
    assert app._current_page is not None

    from ui.pages.finish import FinishPage
    app.show_page(FinishPage)
    assert app._current_page is not None

    root.destroy()

def test_full_config_write_flow(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    from core.config_writer import generate_config, write_config
    from app import WizardState

    state = WizardState(provider_name='testlab', display_name='TestLab', api_key='sk-test-123',
                        base_url='http://192.168.1.1/v1', model_id='test-model', model_name='Test Model',
                        reasoning=True, thinking=False)
    content = generate_config(state)
    path = write_config(content, str(tmp_path / 'opencode.jsonc'))
    assert os.path.exists(path)
    written = open(path).read()
    assert 'testlab' in written
    assert 'sk-test-123' in written
