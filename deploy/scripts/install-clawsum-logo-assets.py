#!/usr/bin/env python3
"""Install Clawsum lobster logo into marketing + icon sizes."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "sites" / "clawsum-com" / "assets"
INBOX = ASSETS / "_inbox"
HERMES = ROOT / "examples" / "hermes-cockpit" / "assets"
PLUGIN = ROOT / "examples" / "hermes-cockpit" / "plugin" / "clawsum-cockpit" / "dashboard" / "assets"


def main() -> None:
    wide = INBOX / "19f922c7_clawsum_logo_1mb.png"
    square = INBOX / "19f922c7_clawsum_logo_1mb_square.png"
    if not wide.exists() or not square.exists():
        raise SystemExit(f"missing inbox logos under {INBOX}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "logo.png").write_bytes(wide.read_bytes())
    (ASSETS / "logo-mark.png").write_bytes(square.read_bytes())

    mark = Image.open(square).convert("RGBA")
    for name, size in [
        ("favicon-32.png", 32),
        ("apple-touch-icon.png", 180),
        ("icon-192.png", 192),
        ("icon-512.png", 512),
    ]:
        im = mark.copy()
        im.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (7, 11, 16, 255))
        canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
        canvas.save(ASSETS / name, optimize=True)

    # OG image: use wide lockup on dark canvas 1200x630
    lockup = Image.open(wide).convert("RGBA")
    og = Image.new("RGBA", (1200, 630), (7, 11, 16, 255))
    lockup.thumbnail((1100, 520), Image.Resampling.LANCZOS)
    og.paste(lockup, ((1200 - lockup.width) // 2, (630 - lockup.height) // 2), lockup)
    og.convert("RGB").save(ASSETS / "og-image.jpg", quality=90, optimize=True)

    # Hermes copies
    for dest in (HERMES, PLUGIN):
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "logo.png").write_bytes((ASSETS / "logo.png").read_bytes())
        (dest / "crest.png").write_bytes((ASSETS / "logo-mark.png").read_bytes())

    print("installed logo.png + logo-mark.png + icons + og-image.jpg")


if __name__ == "__main__":
    main()
