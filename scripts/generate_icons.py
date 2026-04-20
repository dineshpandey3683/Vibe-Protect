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
PROMO_DIR = APP_ROOT / "docs" / "chrome-store" / "promo"
MASTER_PATH = ICONS_DIR / "_master_1024.png"
PROMO_MASTER_PATH = PROMO_DIR / "_marquee_master.png"
SIZES = (16, 32, 48, 128)

# Chrome Web Store promotional asset specs. Small tile is required for
# category listings; marquee is required for Editor's Pick eligibility.
PROMO_SIZES = {
    "small":    (440, 280),   # small tile — shown on CWS category pages
    "marquee":  (1400, 560),  # marquee — required for Editor's Pick
}

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

PROMO_PROMPT = (
    "A wide 16:9 promotional banner for a developer security tool called "
    "Vibe Protect. Near-black background (#0A0A0A) with a subtle radial "
    "gradient fading to pure black at the edges. On the left third: a "
    "single large amber-gold shield (#FACC15), flat design, no gradients, "
    "containing a thin black horizontal redaction bar at its midpoint — "
    "identical to the product's app icon. On the right two-thirds: "
    "purely negative space (no text, no letters, no numbers, no UI "
    "mock-ups, no code snippets — completely empty dark area ready for "
    "marketing copy to be added later in a separate step). Style: "
    "modern, minimal, cinematic, professional developer-tool aesthetic. "
    "High contrast, crisp edges, zero noise."
)


async def generate_master(out: Path, prompt: str = PROMPT, session: str = "vibe-protect-icon-master") -> None:
    load_dotenv(APP_ROOT / "backend" / ".env")
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("✖ EMERGENT_LLM_KEY not found in /app/backend/.env", file=sys.stderr)
        sys.exit(2)

    chat = (
        LlmChat(
            api_key=api_key,
            session_id=session,
            system_message="You generate pixel-crisp app icons.",
        )
        .with_model("gemini", "gemini-3.1-flash-image-preview")
        .with_params(modalities=["image", "text"])
    )

    _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        print("✖ Gemini returned no images", file=sys.stderr)
        sys.exit(2)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(images[0]["data"]))
    print(f"✅ master: {out.relative_to(APP_ROOT)} ({out.stat().st_size // 1024} KB)")


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


def make_promo_tiles(master: Path) -> None:
    """Generate the CWS promo tiles from a wide 16:9 master.

    Small tile (440×280) is required for every CWS listing beyond a basic
    submission; marquee (1400×560) unlocks Editor's Pick eligibility.
    We center-crop the master to the target aspect ratio then Lanczos
    resize — preserves the shield's positioning on the left third.
    """
    img = Image.open(master).convert("RGB")
    mw, mh = img.size
    PROMO_DIR.mkdir(parents=True, exist_ok=True)

    for label, (tw, th) in PROMO_SIZES.items():
        target_ratio = tw / th
        src_ratio = mw / mh
        if src_ratio > target_ratio:
            # master is wider than target — crop left/right
            new_w = int(mh * target_ratio)
            left = (mw - new_w) // 2
            cropped = img.crop((left, 0, left + new_w, mh))
        else:
            # master is taller — crop top/bottom
            new_h = int(mw / target_ratio)
            top = (mh - new_h) // 2
            cropped = img.crop((0, top, mw, top + new_h))

        out = PROMO_DIR / f"{label}_{tw}x{th}.png"
        resized = cropped.resize((tw, th), Image.Resampling.LANCZOS)
        tmp = out.with_suffix(".png.tmp")
        resized.save(tmp, format="PNG", optimize=True)
        tmp.replace(out)
        print(f"✅ {out.relative_to(APP_ROOT)}  ({tw}×{th}, {out.stat().st_size // 1024} KB)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Vibe Protect extension icons.")
    ap.add_argument("--force", action="store_true",
                    help="regenerate the master icon even if it already exists")
    ap.add_argument("--master-only", action="store_true",
                    help="stop after generating the master — skip downsampling")
    ap.add_argument("--promo", action="store_true",
                    help="also generate CWS promotional tiles "
                         "(440×280 small + 1400×560 marquee)")
    ap.add_argument("--promo-only", action="store_true",
                    help="skip icon generation; only (re)generate promo tiles")
    args = ap.parse_args()

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    if not args.promo_only:
        if args.force or not MASTER_PATH.exists():
            asyncio.run(generate_master(MASTER_PATH))
        else:
            print(f"• reusing existing master: {MASTER_PATH.relative_to(APP_ROOT)}  (use --force to regenerate)")
        if not args.master_only:
            downsample_master(MASTER_PATH, SIZES)

    if args.promo or args.promo_only:
        print()
        if args.force or not PROMO_MASTER_PATH.exists():
            asyncio.run(generate_master(
                PROMO_MASTER_PATH,
                prompt=PROMO_PROMPT,
                session="vibe-protect-promo-master",
            ))
        else:
            print(f"• reusing existing promo master: {PROMO_MASTER_PATH.relative_to(APP_ROOT)}  (use --force to regenerate)")
        make_promo_tiles(PROMO_MASTER_PATH)

    print()
    if not args.promo_only:
        print(f"✅ {len(SIZES)} icon(s) written to {ICONS_DIR.relative_to(APP_ROOT)}")
    if args.promo or args.promo_only:
        print(f"✅ {len(PROMO_SIZES)} promo tile(s) written to {PROMO_DIR.relative_to(APP_ROOT)}")
    if not args.promo_only:
        print("   Next step: python /app/cli/vibe_protect_enterprise.py --build-chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
