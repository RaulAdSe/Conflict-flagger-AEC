# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Conflict Flagger AEC
Builds cross-platform desktop application
- macOS: .app bundle
- Windows: single-file .exe
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect ifcopenshell data files and hidden imports
ifcopenshell_datas = collect_data_files('ifcopenshell')
ifcopenshell_hiddenimports = collect_submodules('ifcopenshell')

block_cipher = None

a = Analysis(
    ['src/app_comparator.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/parsers', 'parsers'),
        ('src/matching', 'matching'),
        ('src/comparison', 'comparison'),
        ('src/reporting', 'reporting'),
        ('app_design/Servitec logo.png', 'app_design'),
    ] + ifcopenshell_datas,
    hiddenimports=[
        'ifcopenshell',
        'ifcopenshell.util',
        'ifcopenshell.util.element',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ] + ifcopenshell_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'pytest_cov',
        'matplotlib',
        'scipy',
        'numpy.testing',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    # macOS: Create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Flagger',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
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
        strip=False,
        upx=True,
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
    # Windows: Single-file executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='ConflictFlaggerAEC',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
