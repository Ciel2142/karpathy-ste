"""Subprocess tests for scripts/snapshot.sh (spec section 5.4).

Each test runs the script with TMPDIR pointed at a private directory, so the
script's fresh --user-data-dir lives there. Every Chrome process carries that
path on its command line, which lets a test prove that no Chrome survives the
run, and that the temporary profile is removed afterwards. Process patterns are
always per-test paths, never a fixture name, so a concurrent run of this suite
cannot make another run fail.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "scripts", "snapshot.sh")
PLAIN = os.path.join(HERE, "fixtures", "snap-plain.html")
HANG = os.path.join(HERE, "fixtures", "snap-hang.html")
FRAGMENT = os.path.join(HERE, "fixtures", "snap-fragment.html")

RED = (0xCC, 0x00, 0x00)
WHITE = (0xFF, 0xFF, 0xFF)


def png_size(path):
    out = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
        capture_output=True, text=True, check=True,
    ).stdout
    width = int(re.search(r"pixelWidth: (\d+)", out).group(1))
    height = int(re.search(r"pixelHeight: (\d+)", out).group(1))
    return width, height


def pixel(png, x, y, scratch):
    """Return the (R, G, B) of one pixel, read from a sips-made BMP copy."""
    bmp = os.path.join(scratch, os.path.basename(png) + ".bmp")
    subprocess.run(
        ["sips", "-s", "format", "bmp", png, "--out", bmp],
        capture_output=True, check=True,
    )
    with open(bmp, "rb") as handle:
        data = handle.read()
    offset = struct.unpack("<I", data[10:14])[0]
    width, height = struct.unpack("<ii", data[18:26])
    bpp = struct.unpack("<H", data[28:30])[0]
    row_size = ((bpp * width + 31) // 32) * 4
    row = y if height < 0 else abs(height) - 1 - y
    start = offset + row * row_size + x * (bpp // 8)
    blue, green, red = data[start:start + 3]
    return red, green, blue


def write_tiny_png(path):
    """Write a complete 2x2 white PNG (it ends with the IEND chunk)."""
    def chunk(kind, body):
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body)))
    header = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    rows = b"".join(b"\x00" + b"\xff" * 6 for _ in range(2))
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def close(actual, expected):
    return all(abs(a - e) <= 24 for a, e in zip(actual, expected))


def assert_close(case, actual, expected, label):
    case.assertTrue(
        close(actual, expected),
        "%s: pixel %r, expected about %r" % (label, actual, expected),
    )


class SnapshotTest(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._dir.name)
        self.tmp = os.path.join(self.root, "tmp")
        self.out = os.path.join(self.root, "out")
        os.mkdir(self.tmp)
        os.mkdir(self.out)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(self._kill_strays)

    def _kill_strays(self):
        subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)

    def run_script(self, *args, timeout=None, fragment=None):
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("SNAPSHOT_FRAGMENT", None)
        if timeout is not None:
            env["SNAPSHOT_TIMEOUT"] = str(timeout)
        if fragment is not None:
            env["SNAPSHOT_FRAGMENT"] = fragment
        started = time.monotonic()
        proc = subprocess.run(
            [SCRIPT] + list(args), capture_output=True, text=True, env=env,
            timeout=120,
        )
        return proc, time.monotonic() - started

    def assert_no_chrome_left(self, *patterns):
        for pattern in (self.tmp,) + patterns:
            found = subprocess.run(
                ["pgrep", "-f", pattern], capture_output=True, text=True,
            ).stdout.split()
            if found:
                listing = subprocess.run(
                    ["ps", "-o", "pid,ppid,pgid,etime,command", "-p", ",".join(found)],
                    capture_output=True, text=True,
                ).stdout
                self.fail("processes left matching %s:\n%s" % (pattern, listing))
        self.assertEqual(os.listdir(self.tmp), [], "temp profile not removed")

    def tiles(self, stem):
        review = os.path.join(self.out, "review")
        return sorted(
            name for name in os.listdir(review)
            if re.fullmatch(re.escape(stem) + r"-\d{2,}\.png", name)
        )

    def test_sheet_1920x1080_at_scale_2_gives_4_full_tiles(self):
        png = os.path.join(self.out, "sheet.png")
        proc, _ = self.run_script(PLAIN, png, "1920", "1080", "2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(png_size(png), (3840, 2160))
        names = self.tiles("sheet")
        self.assertEqual(
            names, ["sheet-01.png", "sheet-02.png", "sheet-03.png", "sheet-04.png"])
        review = os.path.join(self.out, "review")
        for name in names:
            self.assertEqual(png_size(os.path.join(review, name)), (1920, 1080), name)
        self.assertIn("wrote %s 3840x2160" % png, proc.stdout)
        self.assertEqual(len(proc.stdout.strip().splitlines()), 5, proc.stdout)
        self.assert_no_chrome_left(png)

    def test_tiles_are_the_four_quadrants_not_centre_crops(self):
        """The 8 px border becomes 16 px at scale 2; it frames the whole image, so it
        shows only on the outer edges of each quadrant, and the outermost corner pixels
        must be border, not sips padding. A capture race was seen once in 35 runs: the
        bottom border was missing from the PNG. On a corner mismatch the test logs it
        and re-renders once before it fails.
        """
        png = os.path.join(self.out, "quad.png")
        review = os.path.join(self.out, "review")
        tile = lambda n: os.path.join(review, "quad-0%d.png" % n)
        probes = (
            (1, 0, 0, RED, "01 top-left"), (1, 1919, 1079, WHITE, "01 bottom-right"),
            (2, 1919, 0, RED, "02 top-right"), (2, 0, 1079, WHITE, "02 bottom-left"),
            (3, 0, 1079, RED, "03 bottom-left"), (3, 1919, 0, WHITE, "03 top-right"),
            (4, 1919, 1079, RED, "04 bottom-right"), (4, 0, 0, WHITE, "04 top-left"),
        )

        def mismatches():
            proc, _ = self.run_script(PLAIN, png, "1920", "1080", "2")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            found = []
            for n, x, y, expected, label in probes:
                actual = pixel(tile(n), x, y, self.root)
                if not close(actual, expected):
                    found.append("%s: pixel %r, expected about %r" % (label, actual, expected))
            return found

        found = mismatches()
        if found:
            sys.stderr.write("\ncorner probe mismatch, re-rendering once: %s\n"
                             % "; ".join(found))
            found = mismatches()
        self.assertEqual(found, [])
        self.assert_no_chrome_left(png)

    def test_tall_page_1440x6000_gives_6_tiles_last_row_clamped(self):
        png = os.path.join(self.out, "page.png")
        proc, _ = self.run_script(PLAIN, png, "1440", "6000", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(png_size(png), (1440, 6000))
        names = self.tiles("page")
        self.assertEqual(names, ["page-%02d.png" % n for n in range(1, 7)])
        review = os.path.join(self.out, "review")
        sizes = [png_size(os.path.join(review, name)) for name in names]
        self.assertEqual(sizes, [(1440, 1080)] * 5 + [(1440, 600)])
        self.assert_no_chrome_left(png)

    def test_rerun_on_its_own_output_leaves_exactly_4_tiles(self):
        png = os.path.join(self.out, "again.png")
        review = os.path.join(self.out, "review")
        os.mkdir(review)
        # A stale tile from an earlier, larger render of the same stem.
        open(os.path.join(review, "again-07.png"), "wb").close()
        for _ in range(2):
            proc, _ = self.run_script(PLAIN, png, "1920", "1080", "2")
            self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self.tiles("again"),
            ["again-01.png", "again-02.png", "again-03.png", "again-04.png"])
        self.assertEqual(png_size(png), (3840, 2160))

    def test_missing_input_is_a_usage_error_and_writes_no_png(self):
        png = os.path.join(self.out, "none.png")
        proc, _ = self.run_script(os.path.join(self.root, "absent.html"), png)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotEqual(proc.stderr.strip(), "")
        self.assertFalse(os.path.exists(png))
        self.assert_no_chrome_left()

    def test_bad_numbers_are_a_usage_error(self):
        png = os.path.join(self.out, "bad.png")
        for args in (["0"], ["wide"], ["1920", "-5"], ["1920", "1080", "1.5"]):
            proc, _ = self.run_script(PLAIN, png, *args)
            self.assertEqual(proc.returncode, 2, (args, proc.stderr))
        proc, _ = self.run_script(PLAIN, png, timeout="soon")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse(os.path.exists(png))

    def test_timeout_on_a_page_that_never_loads_kills_chrome(self):
        png = os.path.join(self.out, "hang.png")
        proc, elapsed = self.run_script(HANG, png, "1920", "1080", "1", timeout=1)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("timeout", proc.stderr.lower())
        self.assertLess(elapsed, 5)
        self.assertFalse(os.path.exists(png))
        self.assertFalse(os.path.exists(os.path.join(self.out, "review")))
        self.assert_no_chrome_left(png)

    def test_stale_png_at_the_output_path_does_not_satisfy_the_watchdog(self):
        png = os.path.join(self.out, "stale.png")
        write_tiny_png(png)
        self.assertEqual(png_size(png), (2, 2))
        proc, _ = self.run_script(HANG, png, "1920", "1080", "1", timeout=1)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        # Removed before launch, the stale PNG cannot end the wait: the run must
        # reach the watchdog timeout, not judge the 2x2 file's size.
        self.assertIn("timeout", proc.stderr.lower())
        self.assertNotIn("size mismatch", proc.stderr)
        self.assertFalse(os.path.exists(png))
        self.assert_no_chrome_left(png)

    def test_fragment_env_reaches_the_page_url(self):
        plain_png = os.path.join(self.out, "nofrag.png")
        frag_png = os.path.join(self.out, "frag.png")
        proc, _ = self.run_script(FRAGMENT, plain_png, "600", "500", "1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc, _ = self.run_script(FRAGMENT, frag_png, "600", "500", "1", fragment="verify")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # The red block exists only when the page sees location.hash == "#verify".
        assert_close(self, pixel(frag_png, 300, 200, self.root), RED, "with #verify")
        assert_close(self, pixel(plain_png, 300, 200, self.root), WHITE, "no fragment")
        self.assert_no_chrome_left(plain_png, frag_png)

    def test_bad_fragment_is_a_usage_error(self):
        png = os.path.join(self.out, "badfrag.png")
        for value in ("a b", "x#y", "../up", "a?b"):
            proc, _ = self.run_script(PLAIN, png, fragment=value)
            self.assertEqual(proc.returncode, 2, (value, proc.stderr))
            self.assertIn("SNAPSHOT_FRAGMENT", proc.stderr)
        self.assertFalse(os.path.exists(png))


if __name__ == "__main__":
    unittest.main()
