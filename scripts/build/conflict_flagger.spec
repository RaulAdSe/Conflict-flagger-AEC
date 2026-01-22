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
    'ifcopenshell.util.representation',
    'ifcopenshell.util.shape',
    'ifcopenshell.util.shape_builder',
    'ifcopenshell.util.placement',
    # ifcopenshell.api is required by util.shape_builder (transitive dependency)
    'ifcopenshell.api',
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

    # Scientific computing (not used - MAJOR SIZE SAVINGS ~45MB)
    'matplotlib',
    'scipy',
    'numpy',
    'numpy.libs',
    'numpy.core',
    'numpy.fft',
    'numpy.linalg',
    'numpy.random',
    'numpy.testing',

    # Shapely/GEOS (pulled by ifcopenshell but NOT used ~4MB)
    'shapely',
    'Shapely.libs',

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

    # Unused PIL codecs (~8MB savings)
    'PIL._avif',
    'PIL._webp',
    'PIL._imagingcms',

    # OpenSSL (not used ~6MB)
    'ssl',
    '_ssl',

    # Heavy ifcopenshell submodules not needed for basic parsing
    # Note: ifcopenshell.api is needed by util modules, don't exclude it
    'ifcopenshell.draw',
    'ifcopenshell.mvd',
    'ifcopenshell.express',
    'ifcopenshell.validate',
]

import os
PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), '..', '..'))

a = Analysis(
    [os.path.join(PROJ_ROOT, 'src/app_comparator.py')],
    pathex=[PROJ_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJ_ROOT, 'src/parsers'), 'parsers'),
        (os.path.join(PROJ_ROOT, 'src/matching'), 'matching'),
        (os.path.join(PROJ_ROOT, 'src/comparison'), 'comparison'),
        (os.path.join(PROJ_ROOT, 'src/reporting'), 'reporting'),
        (os.path.join(PROJ_ROOT, 'src/phases'), 'phases'),
        (os.path.join(PROJ_ROOT, 'docs/design/Servitec logo.png'), 'docs/design'),  # Logo for both platforms
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

# Strip Tcl/Tk locale and timezone data (~4MB savings, faster Wine startup)
a.datas = [d for d in a.datas if 'tzdata' not in d[0]]
a.datas = [d for d in a.datas if '/msgs/' not in d[0] or 'en.' in d[0] or 'en_' in d[0]]

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
