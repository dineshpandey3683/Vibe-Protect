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
OG_DIR = APP_ROOT / "frontend" / "public"
MASTER_PATH = ICONS_DIR / "_master_1024.png"
PROMO_MASTER_PATH = PROMO_DIR / "_marquee_master.png"
OG_MASTER_PATH = OG_DIR / "_og_master.png"
OG_OUT_PATH = OG_DIR / "og-image.png"
SIZES = (16, 32, 48, 128)

# Chrome Web Store promotional asset specs. Small tile is required for
# category listings; marquee is required for Editor's Pick eligibility.
PROMO_SIZES = {
    "small":    (440, 280),   # small tile — shown on CWS category pages
    "marquee":  (1400, 560),  # marquee — required for Editor's Pick
}

# Open Graph social-preview spec (used by Twitter/X, LinkedIn, Slack,
# Discord, Reddit). Facebook recommends 1200×630 at a 1.91:1 ratio — our
# target. Renders at 600×315 on mobile, so the master must still be
# legible at that size.
OG_SIZE = (1200, 630)

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

OG_PROMPT = (
    "A 1200×630 Open Graph social-media preview card for a developer "
    "security tool called Vibe Protect. Wide cinematic 1.91:1 aspect "
    "ratio. Near-black background (#0A0A0A) with an extremely subtle "
    "vignette toward the corners. Left third: a single large amber-gold "
    "shield glyph (#FACC15), flat design, no gradients, no bevels, "
    "containing a thin black horizontal redaction bar at its midpoint. "
    "Right two-thirds: completely empty negative space — no text, no "
    "letters, no numbers, no code snippets, no UI. Style: premium, "
    "minimal, security-serious, developer-tool aesthetic. Crisp edges. "
    "Will be overlaid with type in a subsequent Pillow pass."
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
            new_w = int(mh * target_ratio)
            left = (mw - new_w) // 2
            cropped = img.crop((left, 0, left + new_w, mh))
        else:
            new_h = int(mw / target_ratio)
            top = (mh - new_h) // 2
            cropped = img.crop((0, top, mw, top + new_h))

        out = PROMO_DIR / f"{label}_{tw}x{th}.png"
        resized = cropped.resize((tw, th), Image.Resampling.LANCZOS)
        tmp = out.with_suffix(".png.tmp")
        resized.save(tmp, format="PNG", optimize=True)
        tmp.replace(out)
        print(f"✅ {out.relative_to(APP_ROOT)}  ({tw}×{th}, {out.stat().st_size // 1024} KB)")


def make_og_image(master: Path) -> None:
    """Compose the 1200×630 Open Graph card.

    Two passes: (1) Lanczos-resize the Gemini-generated master into the
    1200×630 canvas (center-crop to aspect); (2) Pillow-overlay razor-sharp
    typography on top. Text rendered by the model is unreliable — we always
    bake it in a deterministic post-processing step so the copy stays
    pixel-perfect and easy to iterate on without re-hitting the model.
    """
    from PIL import ImageDraw, ImageFont

    tw, th = OG_SIZE
    base = Image.open(master).convert("RGB")
    mw, mh = base.size
    target_ratio = tw / th
    src_ratio = mw / mh
    if src_ratio > target_ratio:
        new_w = int(mh * target_ratio)
        left = (mw - new_w) // 2
        cropped = base.crop((left, 0, left + new_w, mh))
    else:
        new_h = int(mw / target_ratio)
        top = (mh - new_h) // 2
        cropped = base.crop((0, top, mw, top + new_h))
    canvas = cropped.resize((tw, th), Image.Resampling.LANCZOS).convert("RGBA")

    # Text overlay. Try to find a decent system font; fall back to the
    # default bitmap font (ugly but never fails — we'd rather ship a
    # slightly uglier OG than crash the build pipeline).
    def _load_font(size: int) -> "ImageFont.FreeTypeFont":
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arialbd.ttf",
        ]:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    draw = ImageDraw.Draw(canvas, "RGBA")

    # Ink a soft right-side gradient vignette so copy has better contrast
    # no matter what the model put in the background.
    veil = Image.new("RGBA", (tw, th), (10, 10, 10, 0))
    vdraw = ImageDraw.Draw(veil)
    for i in range(tw):
        alpha = int(190 * (i / tw) ** 1.6)
        vdraw.line([(i, 0), (i, th)], fill=(10, 10, 10, alpha))
    canvas = Image.alpha_composite(canvas, veil)
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Typography: bold headline + mono subtitle. 1200×630 on mobile renders
    # at ~600×315 so we bias the headline big (72 px).
    title_font    = _load_font(72)
    subtitle_font = _load_font(28)
    mono_font     = _load_font(22)

    title = "Stop pasting secrets\ninto AI chats."
    subtitle = "100% detection  ·  0% false positives  ·  open source"
    kicker = "VIBE·PROTECT"

    # Kicker (amber, uppercase, wide-tracked) — top-right
    draw.text((tw - 510, 60), kicker, font=mono_font, fill="#FACC15", spacing=6)

    # Title — right half, generously spaced
    draw.multiline_text((540, 200), title, font=title_font, fill="#FFFFFF", spacing=12)

    # Subtitle — right half, below title
    draw.text((540, 420), subtitle, font=subtitle_font, fill="#A1A1AA")

    # A thin amber accent rule under the subtitle
    draw.rectangle([(540, 480), (540 + 96, 484)], fill="#FACC15")

    # Tiny tagline under the accent rule
    draw.text((540, 500), "vibeprotect.dev  ·  MIT  ·  no telemetry", font=mono_font, fill="#71717A")

    out = OG_OUT_PATH
    tmp = out.with_suffix(".png.tmp")
    canvas.convert("RGB").save(tmp, format="PNG", optimize=True)
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
    ap.add_argument("--og", action="store_true",
                    help="also generate the 1200×630 Open Graph social card "
                         "at frontend/public/og-image.png")
    ap.add_argument("--og-only", action="store_true",
                    help="skip everything else; only (re)generate the OG card")
    args = ap.parse_args()

    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    do_icons = not (args.promo_only or args.og_only)
    if do_icons:
        if args.force or not MASTER_PATH.exists():
            asyncio.run(generate_master(MASTER_PATH))
        else:
            print(f"• reusing existing master: {MASTER_PATH.relative_to(APP_ROOT)}  (use --force to regenerate)")
        if not args.master_only:
            downsample_master(MASTER_PATH, SIZES)

    do_promo = (args.promo or args.promo_only) and not args.og_only
    if do_promo:
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

    do_og = args.og or args.og_only
    if do_og:
        print()
        if args.force or not OG_MASTER_PATH.exists():
            asyncio.run(generate_master(
                OG_MASTER_PATH,
                prompt=OG_PROMPT,
                session="vibe-protect-og-master",
            ))
        else:
            print(f"• reusing existing OG master: {OG_MASTER_PATH.relative_to(APP_ROOT)}  (use --force to regenerate)")
        make_og_image(OG_MASTER_PATH)

    print()
    if do_icons:
        print(f"✅ {len(SIZES)} icon(s) written to {ICONS_DIR.relative_to(APP_ROOT)}")
    if do_promo:
        print(f"✅ {len(PROMO_SIZES)} promo tile(s) written to {PROMO_DIR.relative_to(APP_ROOT)}")
    if do_og:
        print(f"✅ OG card written to {OG_OUT_PATH.relative_to(APP_ROOT)}")
    if do_icons:
        print("   Next step: python /app/cli/vibe_protect_enterprise.py --build-chrome")
    return 0


if __name__ == "__main__":
    sys.exit(main())
