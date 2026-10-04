#!/usr/bin/env python3
"""Make the checked-in background fixture clip, tests/fixtures/bg-1s.mp4.

Usage: make_bg_fixture.py <output.mp4>

30 PNG frames of 64x64 (a diagonal stripe pattern that moves one step per frame) are written
with the standard library only (zlib and struct), then the workspace's `remotion ffmpeg` encodes
them as H.264 at 30 fps, no audio: a 1.000 s clip of about 3 KB. The workspace ffmpeg has no
lavfi and no rawvideo input, so image2 with PNG frames is the way in.

The Remotion CLI is <ws>/app/node_modules/.bin/remotion, ws = $EXPLAIN_VIDEO_WORKSPACE or
~/karpathy/video-workspace (set up by scripts/video-workspace.sh).

stdout: the output path. Exit 0 on success, 1 when the CLI is missing or ffmpeg fails, 2 for usage.
"""

import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

USAGE = "usage: make_bg_fixture.py <output.mp4>"
SIZE = 64
FRAMES = 30
FPS = 30
BAND = 8  # stripe width in pixels
# Two stripe colours: a deep purple and a green, so the clip reads as a picture, not as noise.
COLORS = ((72, 28, 120), (60, 200, 110))


def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png_bytes(width, height, rows):
    """An 8-bit RGB PNG; `rows` is a list of `height` byte strings of 3 * width bytes."""
    raw = b"".join(b"\x00" + row for row in rows)  # filter type 0 (none) on every row
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


def frame_rows(index):
    """Diagonal stripes that move one pixel pair per frame, so every frame differs."""
    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            row += bytes(COLORS[((x + y + 2 * index) // BAND) % 2])
        rows.append(bytes(row))
    return rows


def remotion_cli():
    ws = os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or str(Path.home() / "karpathy" / "video-workspace")
    return Path(ws) / "app" / "node_modules" / ".bin" / "remotion"


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    out = Path(argv[0]).resolve()
    cli = remotion_cli()
    if not cli.exists():
        print("make_bg_fixture: FAIL no remotion CLI at %s: run scripts/video-workspace.sh" % cli)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bg-fixture-") as tmp:
        for i in range(1, FRAMES + 1):
            (Path(tmp) / ("f%02d.png" % i)).write_bytes(png_bytes(SIZE, SIZE, frame_rows(i)))
        encode = [
            str(cli), "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(FPS), "-i", str(Path(tmp) / "f%02d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
            str(out),
        ]
        done = subprocess.run(encode, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not out.exists():
        print("make_bg_fixture: FAIL ffmpeg exit %d: %s" % (done.returncode, done.stderr.strip()))
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
