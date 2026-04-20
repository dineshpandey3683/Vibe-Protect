#!/usr/bin/env python3
"""
Build Chrome-Web-Store-compliant extension icons for Vibe Protect.

Pipeline
--------
1. Ask Gemini Nano Banana (``gemini-3.1-flash-image-preview``) to render a
   single high-res master icon — a clean gold shield on a near-black
   square with a very subtle redaction glyph inside.
2. Pillow post-processes the master: trim to a centered square,
   high-quality Lanczos downsample to each required size.
3. Write ``icon16.png`` / ``icon32.png`` / ``icon48.png`` /
   ``icon128.png`` into ``/app/extension/icons/`` atomically.

Chrome Web Store only strictly requires the 128×128; Chrome itself uses
16 (toolbar), 32 (Windows taskbar), 48 (management page), 128 (store).
We ship all four so every surface looks crisp.

Usage::

    python scripts/generate_icons.py                    # normal run
    python scripts/generate_icons.py --force            # regenerate master
    python scripts/generate_icons.py --master-only      # debug: only master
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

from emergentintegrations.llm.chat import LlmChat, UserMessage

APP_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = APP_ROOT / "extension" / "icons"
MASTER_PATH = ICONS_DIR / "_master_1024.png"
SIZES = (16, 32, 48, 128)

PROMPT = (
    "A clean, minimalist app-icon illustration. Square canvas with a "
    "near-black background (#0A0A0A). Centered: a solid amber-gold shield "
    "(#FACC15) rendered flat, no bevels, no gradients, no rim-light. "
    "Inside the shield, a single thin black horizontal redaction bar "
    "spanning ~60% of the shield width, positioned at vertical midpoint. "
    "No text, no letters, no numbers, no other glyphs. Razor-sharp edges "
    "for clean pixel-scaling. Plenty of breathing room: shield fills ~70% "
    "of the canvas with even margin on all sides. Style: modern "
    "developer-tool icon, legible at 16×16 pixels."
)


async def generate_master(out: Path) -> None:
    load_dotenv(APP_ROOT / "backend" / ".env")
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("✖ EMERGENT_LLM_KEY not found in /app/backend/.env", file=sys.stderr)
        sys.exit(2)

    chat = (
        LlmChat(
            api_key=api_key,
            session_id="vibe-protect-icon-master",
            system_message="You generate pixel-crisp app icons.",
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )

    _, images = await chat.send_message_multimodal_response(UserMessage(text=PROMPT))
    if not images:
        print("✖ Gemini returned no images", file=sys.stderr)
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(images[0]["data"]))
    print(f"✅ master icon: {out} ({out.stat().st_size // 1024} KB)")


def downsample_master(master: Path, sizes: tuple[int, ...]) -> None:
    """Produce icon16/32/48/128 from the master via Lanczos resampling.

    Normalises the master to a square first (crop to shortest side,
    centered) so non-square model output doesn't stretch the shield.
    """
    img = Image.open(master).convert("RGBA")
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

    for size in sizes:
        out = ICONS_DIR / f"icon{size}.png"
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        # Tiny optimisation: quantise 16/32 to preserve hard edges; leave
        # 48/128 as truecolour so the gold stays punchy.
        if size <= 32:
            resized = resized.convert("RGBA")
        tmp = out.with_suffix(".png.tmp")
        resized.save(tmp, format="PNG", optimize=True)
        tmp.replace(out)
        print(f"✅ {out.name:<14}  {out.stat().st_size:>6} B")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Vibe Protect extension icons.")
    ap.add_argument("--force", action="store_true",
                    help="regenerate the master icon even if it already exists")
    ap.add_argument("--master-only", action="store_true",
                    help="stop after generating the master — skip downsampling")
    args = ap.parse_args()

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    if args.force or not MASTER_PATH.exists():
        asyncio.run(generate_master(MASTER_PATH))
    else:
        print(f"• reusing existing master: {MASTER_PATH}  (use --force to regenerate)")

    if args.master_only:
        return 0

    downsample_master(MASTER_PATH, SIZES)
    print(f"\n✅ {len(SIZES)} icon(s) written to {ICONS_DIR}")
    print("   Next step: python /app/cli/vibe_protect_enterprise.py --build-chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
