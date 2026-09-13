#!/usr/bin/env python3
"""
KBD2 icon builder
Version: 2.1.0

Builds KBD2's icon from Tim's own KBD2 artwork (icon/KBD2Icon_source.png),
which already contains the 2 inside the monogram -- so nothing is composed
beside it any more.

Also writes KBD2_glyph.png, the same mark white on transparency, which the
app tints and draws in its own header.

    ../KBD/venv/bin/python make_icon.py

The source art (icon/KBDIcon_source.png) is black on white with no alpha, so
the first step is to recover a transparency mask from its luminance: black
becomes opaque, white becomes clear, and the grey anti-aliased edges keep
their softness.

The tile is GREEN, not KBD's blue, and deliberately: the two apps sit next to
each other in the Dock and in /Applications, and a colour tells them apart at
a glance far better than a small digit does.

Outputs, all under icon/:
    KBD2.iconset/    the ten PNGs iconutil wants
    KBD2.icns        the app icon
    KBD2_1024.png    a full-size preview
"""

import os
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(HERE, "icon")
SOURCE = os.path.join(ICON_DIR, "KBD2Icon_source.png")

MASTER = 1024
CORNER_RADIUS = 0.2237          # macOS rounded-square proportion
BODY_INSET = 0.055              # transparent margin around the rounded square
MARK_SCALE = 0.74               # monogram width as a fraction of the square
DIGIT_TUCK = 0.04               # gap between mark and digit, same fraction

# KBD2's default key green, top and bottom of a gentle vertical gradient.
FIELD_TOP = (252, 252, 252)
FIELD_BOTTOM = (232, 232, 236)
INK = (198, 40, 129)            # sampled from Tim's artwork

FONT_CANDIDATES = [
    "/System/Library/Fonts/SFNSDisplay.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]

ICONSET_FILES = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]


def load_mask():
    """Opacity recovered from how far each pixel is from WHITE.

    v2.0.0 used luminance, which is right for black ink and wrong for
    colored ink: a saturated hue reads as fairly light, so it is rendered
    too transparent and the icon looks washed out. The darkest channel is
    the honest measure of "how much ink is here" for any hue on white.
    """
    source = Image.open(SOURCE).convert("RGB")
    darkest = source.split()[0]
    for channel in source.split()[1:]:
        darkest = Image.eval(Image.merge("L", (darkest,)), lambda v: v)
        darkest = ImageChops.darker(darkest, channel)
    return Image.eval(darkest, lambda level: 255 - level)


def ink_colour():
    """The artwork's own colour at its most opaque, un-premultiplied against
    the white it was drawn on -- so the tile shows Tim's magenta, not a
    lighter version of it blended with the page."""
    source = Image.open(SOURCE).convert("RGB")
    mask = load_mask()
    best, best_alpha = (0, 0, 0), 0
    for x in range(0, source.size[0], 7):
        for y in range(0, source.size[1], 7):
            a = mask.getpixel((x, y))
            if a > best_alpha:
                best_alpha, best = a, source.getpixel((x, y))
    if best_alpha == 0:
        return INK
    a = best_alpha / 255.0
    return tuple(max(0, min(255, int(round((c - 255 * (1 - a)) / a))))
                 for c in best)


def coloured_mark(mask, rgb):
    """The monogram in one flat colour, on transparency, trimmed to its ink."""
    mark = Image.new("RGBA", mask.size, rgb + (0,))
    mark.putalpha(mask)
    box = mark.getbbox()
    return mark.crop(box) if box else mark


def rounded_square(size, fill_top, fill_bottom):
    """A rounded square with a vertical gradient, on transparency."""
    inset = int(size * BODY_INSET)
    body = size - inset * 2
    radius = int(body * CORNER_RADIUS)

    gradient = Image.new("RGB", (1, body))
    for y in range(body):
        blend = y / max(body - 1, 1)
        gradient.putpixel((0, y), tuple(
            int(fill_top[i] + (fill_bottom[i] - fill_top[i]) * blend)
            for i in range(3)))
    gradient = gradient.resize((body, body))

    mask = Image.new("L", (body, body), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, body - 1, body - 1], radius=radius, fill=255)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(gradient, (inset, inset), mask)
    return canvas


def digit_image(height, rgb):
    """A white 2 as tall as the monogram, trimmed to its own ink."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, int(height * 1.5))
                break
            except OSError:
                continue
    else:
        font = ImageFont.load_default()

    scratch = Image.new("RGBA", (int(height * 3), int(height * 3)), (0, 0, 0, 0))
    ImageDraw.Draw(scratch).text((height, height), "2", font=font, fill=rgb + (255,))
    box = scratch.getbbox()
    return scratch.crop(box) if box else scratch


def build_master():
    """The artwork on a near-white rounded tile. Nothing is composed beside
    it: Tim's KBD2 mark already carries its own 2."""
    canvas = rounded_square(MASTER, FIELD_TOP, FIELD_BOTTOM)
    mark = coloured_mark(load_mask(), ink_colour())

    width = int(MASTER * MARK_SCALE)
    height = int(width * mark.size[1] / mark.size[0])
    mark = mark.resize((width, height), Image.LANCZOS)

    canvas.alpha_composite(mark, ((MASTER - width) // 2,
                                  (MASTER - height) // 2))
    return canvas


def main():
    # The header glyph: the same mark, white on transparency, tinted at
    # runtime to whatever contrasts with the key colour.
    mark = coloured_mark(load_mask(), (255, 255, 255))
    mark.save(os.path.join(ICON_DIR, "KBD2_glyph.png"))

    master = build_master()
    master.save(os.path.join(ICON_DIR, "KBD2_1024.png"))

    iconset = os.path.join(ICON_DIR, "KBD2.iconset")
    os.makedirs(iconset, exist_ok=True)
    for name, size in ICONSET_FILES:
        master.resize((size, size), Image.LANCZOS).save(
            os.path.join(iconset, name))

    print("icon/KBD2_glyph.png written")
    subprocess.run(["iconutil", "-c", "icns", iconset,
                    "-o", os.path.join(ICON_DIR, "KBD2.icns")], check=True)
    print("icon/KBD2.icns written")


if __name__ == "__main__":
    main()
