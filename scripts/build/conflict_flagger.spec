# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Conflict Flagger AEC
Builds cross-platform desktop application
- macOS: .app bundle (optimized for size)
- Windows: onedir with .exe

SIZE OPTIMIZATION:
- Excludes pandas, pyarrow, IPython (not used by app)
- Excludes heavy ifcopenshell submodules not needed
- Uses strip=True for smaller binaries
- UPX disabled on macOS (doesn't work)
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

# Only collect essential ifcopenshell data (schema files)
# Don't use collect_submodules - it pulls in too much
ifcopenshell_datas = collect_data_files('ifcopenshell')

block_cipher = None

# Essential hidden imports only - what the app actually uses
essential_hiddenimports = [
    'ifcopenshell',
    'ifcopenshell.file',
    'ifcopenshell.entity_instance',
    'ifcopenshell.util',
    'ifcopenshell.util.element',
    'ifcopenshell.util.unit',
    'ifcopenshell.util.selector',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'tkinterdnd2',
]

# Extensive excludes to reduce bundle size
# These are packages that get pulled in but are NOT used by the app
size_excludes = [
    # Testing frameworks
    'pytest',
    'pytest_cov',
    'unittest',
    'doctest',

    # Scientific computing (not used)
    'matplotlib',
    'scipy',
    'numpy.testing',

    # Pandas and related (NOT USED - major size savings!)
    'pandas',
    'pandas.testing',
    'pyarrow',

    # IPython and related (NOT USED - pulled in by some deps)
    'IPython',
    'ipython',
    'jedi',
    'parso',
    'prompt_toolkit',
    'pygments',
    'traitlets',

    # ZeroMQ (NOT USED)
    'zmq',
    'pyzmq',

    # Async/network (NOT USED)
    'uvloop',
    'aiohttp',
    'aiofiles',

    # Database (NOT USED)
    'sqlalchemy',
    'sqlite3',

    # Crypto (NOT USED)
    'cryptography',
    'bcrypt',

    # Notebook/Jupyter (NOT USED)
    'nbformat',
    'notebook',
    'jupyter',
    'ipykernel',

    # JSON schema (NOT USED)
    'jsonschema',
    'jsonschema_specifications',

    # Other unused
    'certifi',
    'email',
    'pydoc',
    'lib2to3',
    'distutils',

    # Qt bindings (we use tkinter)
    'PyQt4',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'PIL.ImageQt',

    # Heavy ifcopenshell submodules not needed for basic parsing
    'ifcopenshell.api',
    'ifcopenshell.draw',
    'ifcopenshell.mvd',
    'ifcopenshell.express',
    'ifcopenshell.validate',
]

a = Analysis(
    ['src/app_comparator.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/parsers', 'parsers'),
        ('src/matching', 'matching'),
        ('src/comparison', 'comparison'),
        ('src/reporting', 'reporting'),
        ('src/phases', 'phases'),
        ('app_design/Servitec logo.png', 'app_design'),  # Logo for both platforms
    ] + ifcopenshell_datas,
    hiddenimports=essential_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=size_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out test and doc files from datas to save space
a.datas = [d for d in a.datas if '/tests/' not in d[0] and '/testing/' not in d[0]]
a.datas = [d for d in a.datas if not d[0].endswith('.rst') and not d[0].endswith('.md')]
a.datas = [d for d in a.datas if '/docs/' not in d[0] and '/doc/' not in d[0]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    # macOS: Create .app bundle (optimized)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Flagger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,           # Strip debug symbols - saves space
        upx=False,            # UPX doesn't work on macOS
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,     # Build for current architecture
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,           # Strip binaries in collect too
        upx=False,            # UPX doesn't work on macOS
        upx_exclude=[],
        name='Flagger',
    )

    app = BUNDLE(
        coll,
        name='Flagger.app',
        icon=None,
        bundle_identifier='com.servitec.flagger',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
else:
    # Windows: onedir executable (includes logo and all deps)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='ConflictFlaggerAEC',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,           # Strip debug symbols
        upx=True,             # UPX works on Windows
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='ConflictFlaggerAEC',
    )
