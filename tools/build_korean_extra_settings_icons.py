#!/usr/bin/env python3
"""Generate Korean Merge Extra Settings icon BMPs from upstream reference art.

The upstream localized media set contains the current 640x480 settings frames
and the 118x92 Extra Settings button states.  We keep the artwork/palette,
remove language-specific text in the header/button areas, and redraw Korean
labels.  Output remains paletted BMP so mmarch can pack it into an icons LOD.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    return draw.textbbox((0, 0), text, font=font, stroke_width=0)


def draw_centered(
    image: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    center_x: int,
    y: int,
    fill: tuple[int, int, int],
    stroke_fill: tuple[int, int, int] | None = None,
    stroke_width: int = 0,
) -> None:
    draw = ImageDraw.Draw(image)
    bbox = text_bbox(draw, text, font)
    width = bbox[2] - bbox[0]
    draw.text(
        (center_x - width // 2, y),
        text,
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=stroke_width,
    )


def quantize_like(image: Image.Image, palette_source: Image.Image) -> Image.Image:
    if palette_source.mode != "P":
        palette_source = palette_source.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    return image.convert("RGB").quantize(palette=palette_source, dither=Image.Dither.NONE)


def redraw_header(source: Image.Image, font_path: str) -> Image.Image:
    image = source.convert("RGB")
    # Keep the original metal frame.  Only clear the black inner sign where the
    # language-specific logo is painted.
    ImageDraw.Draw(image).rectangle((158, 24, 491, 108), fill=(5, 0, 0))

    title_font = ImageFont.truetype(font_path, 31)
    sub_font = ImageFont.truetype(font_path, 16)
    draw_centered(
        image,
        "마이트 앤 매직",
        title_font,
        325,
        35,
        (244, 82, 14),
        stroke_fill=(80, 15, 3),
        stroke_width=1,
    )
    draw_centered(
        image,
        "6·7·8 머지",
        sub_font,
        325,
        77,
        (232, 96, 24),
        stroke_fill=(70, 15, 4),
        stroke_width=1,
    )
    return image


def make_background(source: Image.Image, font_path: str, keybinds: bool) -> Image.Image:
    image = redraw_header(source, font_path)
    if keybinds:
        title_font = ImageFont.truetype(font_path, 18)
        # The upstream keybind grid begins below this line; the Chinese reference
        # intentionally has this region blank, which makes it a safe canvas.
        draw_centered(
            image,
            "추가 키 설정",
            title_font,
            320,
            165,
            (242, 108, 28),
            stroke_fill=(70, 20, 5),
            stroke_width=1,
        )
    return quantize_like(image, source)


def multiline_mask(size: tuple[int, int], font_path: str) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    font = ImageFont.truetype(font_path, 28)
    lines = ["추가", "설정"]
    bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [b[2] - b[0] for b in bboxes]
    heights = [b[3] - b[1] for b in bboxes]
    gap = 1
    total_h = sum(heights) + gap
    y = (size[1] - total_h) // 2 - 2
    for line, width, height in zip(lines, widths, heights):
        x = (size[0] - width) // 2
        draw.text((x, y), line, font=font, fill=255)
        y += height + gap
    return mask


def make_button(source: Image.Image, font_path: str, glow: bool) -> Image.Image:
    w, h = source.size
    bg = (8, 0, 0) if glow else (6, 0, 0)
    image = Image.new("RGB", (w, h), bg)
    mask = multiline_mask((w, h), font_path)

    if glow:
        # Match Merge's mouse-over state: broad red/orange halo plus a tight
        # yellow core around the glyphs.
        broad = mask.filter(ImageFilter.GaussianBlur(6))
        tight = mask.filter(ImageFilter.GaussianBlur(2))
        orange = Image.new("RGB", (w, h), (145, 35, 4))
        yellow = Image.new("RGB", (w, h), (255, 135, 14))
        image = Image.composite(orange, image, broad.point(lambda p: min(170, p)))
        image = Image.composite(yellow, image, tight.point(lambda p: min(145, p)))

    gold = Image.new("RGB", (w, h), (255, 193, 18))
    image = Image.composite(gold, image, mask)
    return quantize_like(image, source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font", required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    source_files = {
        "ExSetScr2.bmp": False,
        "ExSetScrK.bmp": True,
    }

    for name, keybinds in source_files.items():
        source = Image.open(args.source / name)
        if source.size != (640, 480):
            raise SystemExit(f"unexpected {name} dimensions: {source.size}")
        out = make_background(source, args.font, keybinds)
        out.save(args.output / name, format="BMP")
        out.convert("RGB").save(args.output / (Path(name).stem + ".png"))

    for name, glow in (("ExtSetDw.bmp", False), ("ExtSetUp.bmp", True)):
        source = Image.open(args.source / name)
        if source.size != (118, 92):
            raise SystemExit(f"unexpected {name} dimensions: {source.size}")
        out = make_button(source, args.font, glow)
        out.save(args.output / name, format="BMP")
        out.convert("RGB").save(args.output / (Path(name).stem + ".png"))

    for name in ("ExSetScr2.bmp", "ExSetScrK.bmp", "ExtSetDw.bmp", "ExtSetUp.bmp"):
        im = Image.open(args.output / name)
        if im.mode != "P":
            raise SystemExit(f"{name} is not an 8-bit paletted BMP: mode={im.mode}")
        print(f"{name}: {im.size}, mode={im.mode}")


if __name__ == "__main__":
    main()
