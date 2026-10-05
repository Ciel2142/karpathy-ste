"""Tests for ink_extent and differing_pixels in png_diff.py, on synthetic 8-bit RGB PNGs written
with zlib and struct (no render needed). Each test names the mutation that turns it red."""

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_diff import differing_pixels, ink_extent


def write_png(path, width, height, ink):
    """An all-white RGB PNG of width x height with one pixel set per (x, y) -> (r, g, b) in `ink`,
    every scanline filter type 0 (None)."""
    raw = b""
    for y in range(height):
        raw += b"\x00" + b"".join(bytes(ink.get((x, y), (255, 255, 255))) for x in range(width))

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


class InkExtentCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory(prefix="explain-png-diff-")
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)

    def png(self, name, ink, width=10, height=10):
        path = self.dir / name
        write_png(path, width, height, ink)
        return path

    # red: ink_extent counting white as ink (an empty box returns a box, not None)
    def test_ink_extent_none_on_white(self):
        path = self.png("white.png", {})
        self.assertIsNone(ink_extent(path, 0, 10, 0, 10))

    # red: x and y swapped in the result tuple; an inclusive-exclusive mix-up (x_max 7 for a pixel
    # at x 6); the box ignored (the pixel at x 2 still counted for x0 = 4)
    def test_ink_extent_box(self):
        path = self.png("two.png", {(2, 3): (0, 0, 0), (6, 7): (0, 0, 0)})
        self.assertEqual(ink_extent(path, 0, 10, 0, 10), (2, 6, 3, 7))
        self.assertEqual(ink_extent(path, 4, 10, 0, 10), (6, 6, 7, 7))

    # red: the box bound taken as inclusive (the pixel at x 6 counted for x1 = 6)
    def test_ink_extent_box_is_half_open(self):
        path = self.png("edge.png", {(6, 7): (0, 0, 0)})
        self.assertIsNone(ink_extent(path, 0, 6, 0, 10))
        self.assertEqual(ink_extent(path, 0, 7, 0, 10), (6, 6, 7, 7))
        self.assertIsNone(ink_extent(path, 0, 10, 0, 7))

    # red: the level ignored: a pixel at 215 (40 below white, not more) counted as ink, or the
    # test run on a channel other than "any"
    def test_ink_extent_level(self):
        path = self.png("grey.png", {(1, 1): (215, 215, 215), (5, 5): (214, 255, 255)})
        self.assertEqual(ink_extent(path, 0, 10, 0, 10), (5, 5, 5, 5))
        self.assertEqual(ink_extent(path, 0, 10, 0, 10, level=39), (1, 5, 1, 5))


class DifferingPixelsCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory(prefix="explain-png-diff-")
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)

    # red: the level parameter ignored (a fixed threshold of 40 or of 16)
    def test_differing_pixels_level(self):
        a, b = self.dir / "a.png", self.dir / "b.png"
        write_png(a, 4, 1, {})
        write_png(b, 4, 1, {(2, 0): (255, 235, 255)})   # 20 below white in one channel of one pixel
        self.assertEqual(differing_pixels(a, b, 0, 4, 0, 1, level=16), 1)
        self.assertEqual(differing_pixels(a, b, 0, 4, 0, 1, level=40), 0)


if __name__ == "__main__":
    unittest.main()
