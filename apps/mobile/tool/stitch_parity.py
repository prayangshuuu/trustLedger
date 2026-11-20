#!/usr/bin/env python3
"""Stitches mobile golden screenshots with web 390px screenshots side-by-side."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MEDIA = Path("docs/media")
PARITY = MEDIA / "parity"
PARITY.mkdir(parents=True, exist_ok=True)

SCREENS = [
    ("welcome", "Welcome Screen / Persona Selection"),
    ("consent", "Granular Source Consent"),
    ("score", "Score Meter & Decision Reveal"),
    ("reasons", "SHAP Attributions & Actionable Tips"),
    ("loan", "Loan Terms & Disbursal"),
]

FONT_PATH = Path("apps/mobile/assets/fonts/HindSiliguri-Bold.ttf")

try:
    title_font = ImageFont.truetype(str(FONT_PATH), 38)
    sub_font = ImageFont.truetype(str(FONT_PATH), 28)
except OSError:
    title_font = ImageFont.load_default()
    sub_font = ImageFont.load_default()

for key, title in SCREENS:
    mob_path = MEDIA / f"app_{key}.png"
    web_path = PARITY / f"web_{key}.png"
    if not mob_path.exists() or not web_path.exists():
        print(f"Skipping {key}: mob_exists={mob_path.exists()}, web_exists={web_path.exists()}")
        continue

    mob_img = Image.open(mob_path).convert("RGB")
    web_img = Image.open(web_path).convert("RGB")

    # Target height matches mobile image (2160)
    target_h = mob_img.height
    w_scale = target_h / web_img.height
    target_w = int(web_img.width * w_scale)
    web_resized = web_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    header_h = 140
    border_w = 6
    total_w = mob_img.width + target_w + border_w
    total_h = target_h + header_h

    # Branded canvas (#0F172A)
    canvas = Image.new("RGB", (total_w, total_h), (15, 23, 42))
    draw = ImageDraw.Draw(canvas)

    # Header text
    banner_text = f"TrustLedger — {title} (Visual Parity @ 390px)"
    draw.text((36, 28), banner_text, fill=(245, 185, 66), font=title_font)
    draw.text((36, 82), "Android App (Flutter Mobile)", fill=(20, 184, 166), font=sub_font)
    draw.text(
        (mob_img.width + border_w + 36, 82),
        "Flutter Web (CanvasKit, 390px viewport)",
        fill=(20, 184, 166),
        font=sub_font,
    )

    # Paste mobile on left
    canvas.paste(mob_img, (0, header_h))

    # Divider bar
    draw.rectangle(
        [mob_img.width, header_h, mob_img.width + border_w, total_h],
        fill=(30, 41, 59),
    )

    # Paste web on right
    canvas.paste(web_resized, (mob_img.width + border_w, header_h))

    out_file = PARITY / f"parity_{key}.png"
    canvas.save(out_file, "PNG", optimize=True)
    print(f"Generated {out_file} ({total_w}x{total_h})")

print("Parity side-by-side screenshots generated successfully.")
