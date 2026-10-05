"""A minimal PNG reader and pixel comparison for the video rung tests (stdlib only; PIL is not
available): 8-bit RGB or RGBA, not interlaced, which is what ffmpeg writes for a still."""

import zlib
from pathlib import Path


def read_png(path, rows):
    """The first `rows` scanlines of the PNG as (width, channels, [bytes per row])."""
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos, idat = 8, b""
    while pos < len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width = int.from_bytes(body[0:4], "big")
            depth, color, interlace = body[8], body[9], body[12]
            assert depth == 8 and color in (2, 6) and interlace == 0, (path, depth, color, interlace)
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw, stride, out, prev = zlib.decompress(idat), width * channels, [], bytearray(width * channels)
    for y in range(rows):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b, c = prev[i], prev[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out.append(line)
        prev = line
    return width, channels, out


def differing_pixels(png_a, png_b, x0, x1, y0, y1, level=40):
    """Pixels in [x0, x1) x [y0, y1) whose RGB differs by more than `level` in some channel."""
    _, ca, rows_a = read_png(png_a, y1)
    _, cb, rows_b = read_png(png_b, y1)
    count = 0
    for y in range(y0, y1):
        ra, rb = rows_a[y], rows_b[y]
        for x in range(x0, x1):
            if any(abs(ra[x * ca + k] - rb[x * cb + k]) > level for k in range(3)):
                count += 1
    return count


def ink_extent(png, x0, x1, y0, y1, level=40):
    """(x_min, x_max, y_min, y_max) of the pixels in the half-open box [x0, x1) x [y0, y1) that
    differ from white by more than `level` in some channel (the box is read as drawn on white), or
    None when the box holds none. The bounds of the result are pixel indexes, both ends included."""
    _, channels, rows = read_png(png, y1)
    found = None
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            if any(255 - row[x * channels + k] > level for k in range(3)):
                if found is None:
                    found = [x, x, y, y]
                else:
                    found = [min(found[0], x), max(found[1], x), found[2], y]
    return None if found is None else tuple(found)
