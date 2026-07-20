"""Launch OpenCode in a visible terminal instead of a hidden helper process."""
from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path

from core.proxy_manager import DIRECT_POWERSHELL_COMMAND


def resolve_opencode_executable(install_path: str = '') -> str:
    """Return an executable command that a newly opened terminal can run.

    npm/fnm often exposes both ``opencode.ps1`` and ``opencode.cmd``. A fresh
    PowerShell may block the script or not inherit fnm's temporary PATH, so
    prefer the concrete CMD shim and pass its absolute path to the terminal.
    """
    if install_path:
        candidate = Path(install_path) / 'opencode.exe'
        if candidate.is_file():
            return str(candidate)
    for name in ('opencode.cmd', 'opencode.exe', 'opencode'):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    if sys.platform.startswith('win'):
        try:
            result = subprocess.run(['where.exe', 'opencode.cmd'], capture_output=True,
                                    text=True, timeout=3, check=False)
            for line in result.stdout.splitlines():
                candidate = line.strip()
                if candidate and Path(candidate).is_file():
                    return candidate
        except (OSError, subprocess.SubprocessError):
            pass
    return 'opencode'


def _powershell_invoke(executable: str) -> str:
    """Build a PowerShell call expression for an absolute executable path."""
    return "& '" + executable.replace("'", "''") + "'"


def launch_opencode_cli(*, direct: bool = False, install_path: str = '') -> subprocess.Popen:
    """Open an interactive OpenCode terminal and return its process.

    The desktop helper is a windowed application, so spawning ``opencode``
    directly gives it no usable console and users see no visible result. On
    Windows we explicitly create PowerShell with ``-NoExit`` so both OpenCode
    and any error message remain visible to the user.
    """
    executable = resolve_opencode_executable(install_path)
    invocation = _powershell_invoke(executable)
    command = f'{DIRECT_POWERSHELL_COMMAND.rsplit("; opencode", 1)[0]}; {invocation}' if direct else invocation
    if sys.platform.startswith('win'):
        creation_flags = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)
        return subprocess.Popen(
            ['powershell.exe', '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', command],
            creationflags=creation_flags,
        )
    # The packaged app is Windows-focused, but keep development environments
    # usable as well.
    return subprocess.Popen(['bash', '-lc', command], start_new_session=True)
