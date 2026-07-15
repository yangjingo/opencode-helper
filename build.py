"""PyInstaller build script for opencode-helper.exe v2.0 — optimized with UPX + version info."""
import sys, os, subprocess, shutil

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
        # Strip debug symbols
        '--strip',
    ]

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

    # Cleanup
    if os.path.exists(version_file):
        os.remove(version_file)

    exe_path = os.path.join('dist', f'{APP_NAME}.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f'Build complete: {exe_path} ({size_mb:.1f} MB)')
    else:
        print(f'Build failed — {exe_path} not found')

if __name__ == '__main__':
    build()
