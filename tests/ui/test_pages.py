import sys, os, tkinter as tk
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def _create_root():
    """Create a withdrawn Tk root, skipping test if Tcl not available."""
    try:
        root = tk.Tk()
        root.withdraw()
        return root
    except tk.TclError:
        import pytest; pytest.skip("Tkinter not available")

def test_welcome_page_creates():
    from ui.pages.welcome import WelcomePage
    from app import App
    root = _create_root()
    app = App(root)
    page = WelcomePage(app.container, app)
    assert page is not None
    root.destroy()

def test_migration_page_creates(monkeypatch):
    from ui.pages.migration import MigrationPage
    from app import App
    def mock_scan():
        return [{'key': 'api_key', 'source': '/test/settings.json', 'source_name': '~/.claude/settings.json',
                 'target': '/test/opencode.jsonc', 'content': 'sk-test', 'preview': 'sk-tes••••st', 'checked': True}]
    monkeypatch.setattr('core.cc_migrator.scan', mock_scan)
    root = _create_root()
    app = App(root)
    page = MigrationPage(app.container, app)
    assert page is not None
    root.destroy()

def test_environment_page_creates(monkeypatch):
    from ui.pages.environment import EnvironmentPage
    from app import App
    def mock_detect():
        return {'os_name': 'Windows', 'os_version': '10.0', 'os_ok': True,
                'node_installed': True, 'node_version': 'v20.11.0', 'node_ok': True,
                'npm_installed': True, 'npm_version': '10.2.4', 'npm_ok': True,
                'opencode_installed': False, 'opencode_version': '', 'opencode_path': '',
                'disk_free_gb': 50.0, 'disk_ok': True,
                'proxy_detected': True, 'proxy_http': 'http://proxy:8080', 'proxy_https': '',
                'no_proxy': '', 'all_proxy': '',
                'env_vars': {'HTTP_PROXY': 'http://proxy:8080'},
                'system_proxy_enabled': False, 'system_proxy_server': '', 'system_proxy_bypass': '',
                'winhttp_direct': True, 'winhttp_proxy': '', 'winhttp_bypass': '',
                'claude_config_found': False, 'claude_settings_path': '', 'claude_skills_path': '',
                'project_claude_path': '',
                'claude_settings': {}, 'claude_settings_raw': '', 'claude_settings_readable': False,
                'project_settings': {}, 'project_settings_raw': '', 'project_settings_readable': False,
                'project_files': [],
                'claude_env_vars': {}}
    monkeypatch.setattr('core.detector.detect_all', mock_detect)
    root = _create_root()
    app = App(root)
    page = EnvironmentPage(app.container, app)
    page.place(relx=0, rely=0, relwidth=1, relheight=1)
    assert page is not None
    # Flush all pending after() callbacks before destroy
    for _ in range(5):
        root.update_idletasks()
        root.update()
        import time; time.sleep(0.05)
    page.destroy()
    root.update_idletasks()
    root.destroy()

def test_install_method_page_creates():
    from ui.pages.install_method import InstallMethodPage
    from app import App
    root = _create_root()
    app = App(root)
    page = InstallMethodPage(app.container, app)
    assert page is not None
    root.destroy()

def test_install_path_page_creates():
    from ui.pages.install_path import InstallPathPage
    from app import App
    root = _create_root()
    app = App(root)
    page = InstallPathPage(app.container, app)
    assert page is not None
    root.destroy()

def test_config_model_page_creates():
    from ui.pages.config_model import ConfigModelPage
    from app import App
    root = _create_root()
    app = App(root)
    page = ConfigModelPage(app.container, app)
    assert page is not None
    root.destroy()

def test_finish_page_creates():
    from ui.pages.finish import FinishPage
    from app import App
    root = _create_root()
    app = App(root)
    page = FinishPage(app.container, app)
    assert page is not None
    root.destroy()

def test_finish_page_displays_and_copies_launch_command():
    from ui.pages.finish import FinishPage
    from app import App
    root = _create_root()
    app = App(root)
    page = FinishPage(app.container, app)
    expected = 'Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY -ErrorAction SilentlyContinue; opencode'
    assert page._launch_command == expected
    page._copy_launch_command()
    assert root.clipboard_get() == expected
    root.destroy()

def test_direct_connect_page_creates_and_copies_powershell_command():
    from ui.pages.direct_connect import DirectConnectPage
    from app import App
    root = _create_root()
    app = App(root)
    page = DirectConnectPage(app.container, app)
    page._copy_command('powershell_once')
    assert root.clipboard_get().endswith('; opencode')
    root.destroy()
