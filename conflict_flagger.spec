# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Conflict Flagger AEC
Builds cross-platform desktop application (.exe for Windows, .app for Mac)
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
    ] + ifcopenshell_datas,
    hiddenimports=[
        'ifcopenshell',
        'ifcopenshell.util',
        'ifcopenshell.util.element',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
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

# Platform-specific configuration
if sys.platform == 'darwin':
    # macOS App Bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Conflict Flagger AEC',
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
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Conflict Flagger AEC',
    )
    app = BUNDLE(
        coll,
        name='Conflict Flagger AEC.app',
        icon=None,
        bundle_identifier='com.conflictflagger.aec',
        info_plist={
            'CFBundleName': 'Conflict Flagger AEC',
            'CFBundleDisplayName': 'Conflict Flagger AEC',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
else:
    # Windows EXE
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
