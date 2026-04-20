# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for building the Windows vibe_desktop.exe.

Invoked by installer/build_windows.py (or by CI).
"""
from PyInstaller.utils.hooks import collect_submodules
import os

# use a folder build (not --onefile) so Inno Setup can include the
# _internal/ directory and startup is faster on user machines.
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))
DESKTOP_ENTRY = os.path.join(APP_ROOT, "desktop", "vibe_desktop.py")
CLI_DIR = os.path.join(APP_ROOT, "cli")
ICON = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "icon.ico")

block_cipher = None

a = Analysis(
    [DESKTOP_ENTRY],
    pathex=[CLI_DIR],
    binaries=[],
    datas=[(ICON, ".")],
    hiddenimports=(
        collect_submodules("pyperclip")
        + collect_submodules("plyer")
        + collect_submodules("pystray")
        + collect_submodules("PIL")
        + ["patterns", "updater", "production_updater",
           "advanced_detector", "pattern_updater", "community_rules"]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vibe_desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vibe_desktop",
)
