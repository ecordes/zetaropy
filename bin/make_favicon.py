"""Rasterize favicon.svg's design to favicon.ico and apple-touch-icon.png.

The mark: a slate Z whose diagonal steps through a horizontal middle
bar, so the strokes also read as an E -- Zeta's Z, Entropy's E. The
middle bar is picked out in Zeta's near-black, which keeps the step
legible at tab size. On top, one cat ear per cat: Zeta's black on the
left, Entropy's coat gray on the right, all on the site's cream in a
rounded square.

The geometry here mirrors favicon.svg exactly; change them together.
Stdlib only (no imaging libraries on this machine): shapes are drawn
by point-in-polygon tests with 4x4 supersampling, then encoded with
zlib/struct.

    python3 bin/make_favicon.py
"""

import os
import struct
import zlib

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

CREAM = (0xF7, 0xF3, 0xEB)
SLATE = (0x45, 0x60, 0x79)        # bars and connectors
NEAR_BLACK = (0x33, 0x38, 0x3D)   # middle bar and left ear, Zeta's coat
EAR_ENTROPY = (0x84, 0x94, 0xA2)  # right ear, his gray coat

# All coordinates in favicon.svg's 64x64 space.
EAR_LEFT = [(16, 20), (18, 5), (28, 19)]
EAR_RIGHT = [(48, 20), (46, 5), (36, 19)]
SLATE_SHAPES = [
    [(13, 20), (49, 20), (49, 27), (13, 27)],   # top bar
    [(41, 27), (49, 27), (43, 35), (35, 35)],   # upper connector
    [(19, 42), (27, 42), (21, 50), (13, 50)],   # lower connector
    [(13, 50), (49, 50), (49, 57), (13, 57)],   # bottom bar
]
MIDDLE_BAR = [(19, 35), (43, 35), (43, 42), (19, 42)]


def in_polygon(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                inside = not inside
        j = i
    return inside


def in_rounded_rect(x, y, size, radius):
    dx = max(radius - x, 0.0, x - (size - radius))
    dy = max(radius - y, 0.0, y - (size - radius))
    return dx * dx + dy * dy <= radius * radius


def color_at(x, y):
    """Topmost color at a point in the 64x64 design space.
    SVG draw order is bg, ears, slate shapes, middle bar -- test in reverse."""
    if in_polygon(x, y, MIDDLE_BAR):
        return NEAR_BLACK
    for poly in SLATE_SHAPES:
        if in_polygon(x, y, poly):
            return SLATE
    if in_polygon(x, y, EAR_LEFT):
        return NEAR_BLACK
    if in_polygon(x, y, EAR_RIGHT):
        return EAR_ENTROPY
    return CREAM


def render(size, corner_radius=13.0, samples=4):
    """RGBA rows at the given pixel size, 4x4 supersampled."""
    scale = 64.0 / size
    radius = corner_radius * size / 64.0
    step = 1.0 / samples
    total = samples * samples
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            hit = 0
            r = g = b = 0
            for sy in range(samples):
                for sx in range(samples):
                    fx = px + (sx + 0.5) * step
                    fy = py + (sy + 0.5) * step
                    if not in_rounded_rect(fx, fy, size, radius):
                        continue
                    c = color_at(fx * scale, fy * scale)
                    hit += 1
                    r += c[0]; g += c[1]; b += c[2]
            if hit == 0:
                row += b"\x00\x00\x00\x00"
            else:
                row += bytes((round(r / hit), round(g / hit), round(b / hit),
                              round(255 * hit / total)))
        rows.append(bytes(row))
    return rows


def encode_png(rows, size):
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def encode_ico(images):
    """images: [(size, png_bytes)] -- ICO may embed PNGs directly."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    blobs = b""
    for size, png in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0,
                               1, 32, len(png), offset)
        blobs += png
        offset += len(png)
    return header + entries + blobs


def main():
    ico = []
    for size in (16, 32, 48):
        png = encode_png(render(size), size)
        ico.append((size, png))
        print(f"  {size}x{size}: {len(png)} bytes")
    with open("favicon.ico", "wb") as fh:
        fh.write(encode_ico(ico))

    # iOS ignores alpha and applies its own mask: opaque, square corners.
    png180 = encode_png(render(180, corner_radius=0.0), 180)
    with open("apple-touch-icon.png", "wb") as fh:
        fh.write(png180)
    print(f"  180x180 apple-touch-icon: {len(png180)} bytes")


if __name__ == "__main__":
    main()
