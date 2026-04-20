"""
Vibe Protect — Windows installer build chain.

Pipeline:
    1. Export the canonical pattern list to patterns.json
    2. Generate a Windows-ready icon.ico from a Pillow-drawn amber shield
    3. Run PyInstaller against installer/vibe_desktop.spec → dist/vibe_desktop/
    4. Run Inno Setup ISCC on installer/setup.iss
       → dist/VibeProtect-Setup-<version>.exe

Usage:
    python installer/build_windows.py               # build everything
    python installer/build_windows.py --patterns    # just re-export patterns.json
    python installer/build_windows.py --icon        # just regenerate icon.ico

Requirements (install on your Windows build box):
    pip install pyinstaller pillow
    Inno Setup 6 (ISCC.exe in PATH or at its default location)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLI_DIR = ROOT / "cli"
DIST_DIR = ROOT / "dist"
VERSION_FILE = ROOT / "VERSION"


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip() or "0.0.0-dev"
    return "0.0.0-dev"


# ------------------------------------------------------------- patterns.json
def export_patterns() -> Path:
    """Write the 18 bundled patterns to installer/patterns.json so the installer
    can ship a human-readable, bundle-ready copy alongside the .exe."""
    sys.path.insert(0, str(CLI_DIR))
    from patterns import PATTERNS  # type: ignore

    out = {
        "version": read_version(),
        "description": "Bundled Vibe Protect pattern library (shipped with installer).",
        "patterns": [
            {
                "name": n,
                "regex": p,
                "description": d,
                "example": ex,
            }
            for n, p, d, ex in PATTERNS
        ],
    }
    target = HERE / "patterns.json"
    target.write_text(json.dumps(out, indent=2))
    print(f"✓ wrote {target} ({len(out['patterns'])} patterns)")
    return target


# ---------------------------------------------------------------- icon.ico
def generate_icon() -> Path:
    """Render the amber shield at multiple sizes and save as .ico."""
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        print("! Pillow not installed — skipping icon generation", file=sys.stderr)
        return HERE / "icon.ico"

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    # Draw at the largest size; Pillow will downscale to each listed size
    # when saving as .ico. Drawing small sizes independently and passing
    # `append_images` only keeps the first entry in the ICO.
    base_w, base_h = 256, 256
    img = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = base_w // 16
    d.rounded_rectangle(
        (pad, pad, base_w - pad, base_h - pad),
        radius=base_w // 7,
        fill=(250, 204, 21, 255),
    )
    cx, cy = base_w / 2, base_h / 2
    sz = base_w * 0.55
    d.polygon(
        [
            (cx, cy - sz / 2),
            (cx + sz / 2, cy - sz / 4),
            (cx + sz / 2, cy + sz / 4),
            (cx, cy + sz / 2),
            (cx - sz / 2, cy + sz / 4),
            (cx - sz / 2, cy - sz / 4),
        ],
        fill=(10, 10, 10, 255),
    )

    target = HERE / "icon.ico"
    img.save(target, format="ICO", sizes=sizes)
    print(f"✓ wrote {target} ({len(sizes)} sizes)")
    return target


# --------------------------------------------------------------- pyinstaller
def run_pyinstaller():
    spec = HERE / "vibe_desktop.spec"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(ROOT / "build"),
        str(spec),
    ]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"✓ PyInstaller → {DIST_DIR / 'vibe_desktop'}")


# ----------------------------------------------------------------- inno setup
def find_iscc() -> str:
    """Locate Inno Setup's ISCC.exe."""
    iscc = shutil.which("ISCC") or shutil.which("iscc.exe")
    if iscc:
        return iscc
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    raise RuntimeError(
        "ISCC.exe not found. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php "
        "and ensure ISCC is on PATH."
    )


def run_iscc(version: str):
    iscc = find_iscc()
    iss = HERE / "setup.iss"
    cmd = [iscc, f"/DVP_VERSION={version}", str(iss)]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(HERE))
    installer = DIST_DIR / f"VibeProtect-Setup-{version}.exe"
    if installer.exists():
        print(f"✓ installer → {installer}")
    else:
        print("! Inno Setup completed but installer .exe not found at expected path", file=sys.stderr)


# ---------------------------------------------------------------- entrypoint
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns", action="store_true", help="only export patterns.json")
    ap.add_argument("--icon", action="store_true", help="only generate icon.ico")
    ap.add_argument("--skip-iscc", action="store_true", help="build the exe but skip Inno Setup")
    args = ap.parse_args()

    version = read_version()
    print(f"=== building Vibe Protect v{version} (Windows) ===")

    if args.patterns:
        export_patterns()
        return 0
    if args.icon:
        generate_icon()
        return 0

    export_patterns()
    generate_icon()
    run_pyinstaller()

    if args.skip_iscc or sys.platform != "win32":
        print("(!) skipping Inno Setup step — run this on Windows with ISCC.exe installed")
        return 0

    run_iscc(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
