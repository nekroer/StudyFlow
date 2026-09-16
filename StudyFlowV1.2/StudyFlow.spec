# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6") +
    [
        "pycaw",
        "comtypes",
        "winotify"
    ]
)

datas = [
    ("app/assets", "app/assets"),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "pytest",
        "tkinter",
        "IPython",
        "jupyter",
        "notebook",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StudyFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="app/assets/icons/logo.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StudyFlow",
)