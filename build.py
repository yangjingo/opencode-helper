"""Build and Authenticode-sign the OpenCode Helper Windows release."""
import sys, os, subprocess, shutil
from pathlib import Path

APP_NAME = 'opencode-helper'
ENTRY = 'src/main.py'
ICON = 'assets/icons/icon.ico'

VERSION_INFO = '''
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'whyj'),
         StringStruct(u'FileDescription', u'OpenCode Helper v2.0 — 8-bit Edition'),
         StringStruct(u'FileVersion', u'2.0.0'),
         StringStruct(u'InternalName', u'opencode-helper'),
         StringStruct(u'LegalCopyright', u'MIT'),
         StringStruct(u'OriginalFilename', u'opencode-helper.exe'),
         StringStruct(u'ProductName', u'OpenCode Helper'),
         StringStruct(u'ProductVersion', u'2.0.0')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

SIGN_PFX_ENV = 'OPENCODE_HELPER_SIGN_PFX'
SIGN_PFX_PASSWORD_ENV = 'OPENCODE_HELPER_SIGN_PFX_PASSWORD'
SIGN_THUMBPRINT_ENV = 'OPENCODE_HELPER_SIGN_THUMBPRINT'
SIGN_TIMESTAMP_ENV = 'OPENCODE_HELPER_TIMESTAMP_URL'
ALLOW_UNSIGNED_ENV = 'OPENCODE_HELPER_ALLOW_UNSIGNED'
DEFAULT_TIMESTAMP_URL = 'http://timestamp.digicert.com'


def _enabled(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def find_signtool() -> str | None:
    """Find the newest x64 SignTool from PATH or an installed Windows SDK."""
    resolved = shutil.which('signtool.exe') or shutil.which('signtool')
    if resolved:
        return resolved

    roots = [
        Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Windows Kits' / '10' / 'bin',
        Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Windows Kits' / '10' / 'bin',
    ]
    candidates: list[Path] = []
    for root in roots:
        if root.is_dir():
            candidates.extend(root.glob('*/x64/signtool.exe'))
    return str(sorted(candidates, reverse=True)[0]) if candidates else None


def signing_command(exe_path: str, signtool: str) -> list[str]:
    """Return a SignTool command without logging certificate secrets."""
    pfx = os.environ.get(SIGN_PFX_ENV, '').strip()
    thumbprint = ''.join(os.environ.get(SIGN_THUMBPRINT_ENV, '').split()).upper()
    if bool(pfx) == bool(thumbprint):
        raise RuntimeError(
            f'Set exactly one of {SIGN_PFX_ENV} or {SIGN_THUMBPRINT_ENV} for a signed release.'
        )

    command = [signtool, 'sign', '/fd', 'SHA256', '/td', 'SHA256', '/tr',
               os.environ.get(SIGN_TIMESTAMP_ENV, DEFAULT_TIMESTAMP_URL)]
    if pfx:
        certificate = Path(pfx).expanduser().resolve()
        if not certificate.is_file():
            raise RuntimeError(f'Code-signing certificate was not found: {certificate}')
        command.extend(['/f', str(certificate)])
        password = os.environ.get(SIGN_PFX_PASSWORD_ENV, '')
        if password:
            command.extend(['/p', password])
    else:
        if len(thumbprint) != 40 or any(char not in '0123456789ABCDEF' for char in thumbprint):
            raise RuntimeError(f'{SIGN_THUMBPRINT_ENV} must be a 40-character SHA-1 thumbprint.')
        command.extend(['/sha1', thumbprint, '/s', 'My'])
    command.append(exe_path)
    return command


def sign_and_verify(exe_path: str) -> None:
    """Sign a release and fail closed unless SignTool verifies Authenticode."""
    signtool = find_signtool()
    if not signtool:
        raise RuntimeError('signtool.exe was not found. Install the Windows SDK Signing Tools first.')

    command = signing_command(exe_path, signtool)
    identity = 'PFX file' if '/f' in command else 'Windows certificate store'
    print(f'Signing {exe_path} with SHA-256 ({identity})...')
    subprocess.run(command, check=True)
    subprocess.run([signtool, 'verify', '/pa', '/all', '/v', exe_path], check=True)
    print('Authenticode signature verified successfully.')

def find_upx() -> str | None:
    """Find UPX executable on PATH or in common locations."""
    upx = shutil.which('upx')
    if upx:
        return upx
    for loc in [r'C:\upx\upx.exe', r'C:\Program Files\upx\upx.exe']:
        if os.path.exists(loc):
            return loc
    return None

def build():
    allow_unsigned = _enabled(os.environ.get(ALLOW_UNSIGNED_ENV, ''))
    if sys.platform == 'win32' and not allow_unsigned:
        # Validate the signing prerequisites before spending time packaging.
        signing_command(os.path.join('dist', f'{APP_NAME}.exe'), 'signtool.exe')
        signtool = find_signtool()
        if not signtool:
            raise RuntimeError('Signed release required, but signtool.exe was not found.')

    # Write version info file
    version_file = 'version_info.txt'
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(VERSION_INFO)

    sep = ';' if sys.platform == 'win32' else ':'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--log-level', 'WARN',
        # Paths for module discovery
        '--paths', 'src',
        # Data files
        '--add-data', f'src{os.sep}i18n{os.sep}zh_CN.json{sep}i18n',
        '--add-data', f'src{os.sep}i18n{os.sep}en_US.json{sep}i18n',
        # Exclude heavy unused tkinter sub-modules
        '--exclude-module', 'tkinter.tix',
        '--exclude-module', 'tkinter.test',
        '--exclude-module', 'turtle',
        '--exclude-module', 'idlelib',
        # Exclude unused standard libs
        '--exclude-module', 'test',
        '--exclude-module', 'unittest',
        '--exclude-module', 'doctest',
        '--exclude-module', 'pydoc',
        '--exclude-module', 'distutils',
        '--exclude-module', 'setuptools',
        '--exclude-module', 'pip',
    ]

    # PyInstaller's --strip requires a GNU strip executable. It is useful on
    # Unix but unavailable on normal Windows installations and otherwise emits
    # one traceback per bundled DLL while producing the same valid EXE.
    if sys.platform != 'win32':
        cmd.append('--strip')

    # UPX compression if available
    upx_path = find_upx()
    if upx_path:
        print(f'UPX found: {upx_path}')
        cmd.extend(['--upx-dir', os.path.dirname(upx_path)])

    # Icon if available
    if os.path.exists(ICON):
        cmd.extend(['--icon', ICON])

    # Version info
    cmd.extend(['--version-file', version_file])

    # Entry point
    cmd.append(ENTRY)

    print(f'Building {APP_NAME} v2.0...')
    print(f'Command: {" ".join(cmd)}')
    subprocess.run(cmd, check=True)

    exe_path = os.path.join('dist', f'{APP_NAME}.exe')
    if sys.platform == 'win32' and not allow_unsigned:
        sign_and_verify(exe_path)
    elif sys.platform == 'win32':
        print(f'WARNING: unsigned development build explicitly allowed by {ALLOW_UNSIGNED_ENV}=1')

    # Ship only the release log beside the EXE, without a docs directory.
    release_log = Path('docs') / 'RELEASE.md'
    legacy_docs_target = Path('dist') / 'docs'
    if legacy_docs_target.exists():
        shutil.rmtree(legacy_docs_target)
    if release_log.is_file():
        release_target = Path('dist') / release_log.name
        shutil.copy2(release_log, release_target)
        print(f'Release log copied: {release_target}')

    # Cleanup
    if os.path.exists(version_file):
        os.remove(version_file)

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f'Build complete: {exe_path} ({size_mb:.1f} MB)')
    else:
        print(f'Build failed — {exe_path} not found')

if __name__ == '__main__':
    build()
