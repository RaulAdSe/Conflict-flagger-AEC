# -*- mode: python ; coding: utf-8 -*-
# WINDOWS ONEFILE BUILD - Single standalone .exe
import sys
from PyInstaller.utils.hooks import collect_data_files

ifcopenshell_datas = collect_data_files('ifcopenshell')

a = Analysis(
    ['src/app_comparator.py'],
    pathex=['.'],
    datas=[
        ('src/parsers', 'parsers'),
        ('src/matching', 'matching'),
        ('src/comparison', 'comparison'),
        ('src/reporting', 'reporting'),
        ('src/phases', 'phases'),
        ('app_design/Servitec logo.png', 'app_design'),
    ] + ifcopenshell_datas,
    hiddenimports=['ifcopenshell', 'ifcopenshell.util', 'ifcopenshell.util.element', 'openpyxl', 'PIL', 'PIL.Image', 'PIL.ImageTk', 'tkinterdnd2'],
    excludes=['pytest', 'matplotlib', 'scipy', 'pandas', 'pyarrow', 'IPython', 'jedi', 'zmq', 'cryptography', 'sqlalchemy'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ConflictFlaggerAEC',
    debug=False,
    strip=True,
    upx=True,
    console=False,
)
