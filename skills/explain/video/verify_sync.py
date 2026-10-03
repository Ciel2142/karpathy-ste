#!/usr/bin/env python3
"""Check where the narration sits in a rendered video's audio track (video rung).

Usage: verify_sync.py <wav> <timeline.json>

<wav> is the 16-bit mono track that check_render.sh extracts (16 kHz). RMS over 20 ms
windows; a window is voiced when its RMS exceeds 0.01 of full scale (about -40 dBFS). Per
scene of the timeline, the first voiced window must start within 0.25 s of
from + leadFrames, and the last voiced window must end more than 0.3 s before the scene
ends. Times on stdout are seconds from the scene start.

stdout, one line per scene, in timeline order:
  sync: <id> speech <first>-<last> s (lead <expected> s)
  sync: FAIL <id>: speech starts at <first> s, expected <expected> s ± 0.25
  sync: FAIL <id>: no speech
  sync: FAIL <id>: speech runs past the scene end
Exit 0 when every scene is placed, 1 when one is not, 2 (one line on stderr) for a usage
error or an input that cannot be read. Stdlib only.
"""

import json
import sys
import wave
from array import array

USAGE = "usage: verify_sync.py <wav> <timeline.json>"
WINDOW = 0.02          # seconds per RMS window
THRESHOLD = 0.01       # RMS, as a fraction of full scale, counted as voiced
LEAD_TOLERANCE = 0.25  # seconds
MIN_TAIL = 0.3         # seconds of silence the speech leaves before the scene end
FULL_SCALE = 32768.0


class InputError(Exception):
    """An input that cannot be read; main() prints it as one line and exits 2."""


def voiced_windows(path):
    """One bool per 20 ms window of the WAV: is its RMS above the threshold?"""
    try:
        with wave.open(path, "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise InputError("%s must be 16-bit mono" % path)
            rate = w.getframerate()
            samples = array("h")
            samples.frombytes(w.readframes(w.getnframes()))
    except (OSError, EOFError, wave.Error) as err:
        raise InputError("cannot read %s: %s" % (path, err)) from err
    if sys.byteorder == "big":
        samples.byteswap()
    size = int(rate * WINDOW)
    limit = (THRESHOLD * FULL_SCALE) ** 2 * size  # compare sums of squares: no sqrt per window
    return [sum(s * s for s in samples[i:i + size]) > limit
            for i in range(0, len(samples) - size + 1, size)]


def load_timeline(path):
    try:
        with open(path, encoding="utf-8") as f:
            timeline = json.load(f)
        fps = timeline["fps"]
        scenes = [(s["id"], s["from"], s["durationInFrames"], s["leadFrames"])
                  for s in timeline["scenes"]]
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise InputError("cannot read timeline %s: %s" % (path, err)) from err
    return fps, scenes


def check_scene(voiced, fps, scene):
    """The stdout line for one scene and whether it is placed."""
    scene_id, start, length, lead = scene
    lo = round(start / fps / WINDOW)
    hi = round((start + length) / fps / WINDOW)
    hits = [k for k in range(lo, min(hi, len(voiced))) if voiced[k]]
    if not hits:
        return "sync: FAIL %s: no speech" % scene_id, False
    first = (hits[0] - lo) * WINDOW
    last = (hits[-1] + 1 - lo) * WINDOW
    expected = lead / fps
    if abs(first - expected) > LEAD_TOLERANCE:
        return ("sync: FAIL %s: speech starts at %.2f s, expected %.2f s ± %.2f"
                % (scene_id, first, expected, LEAD_TOLERANCE)), False
    if (hi - lo) * WINDOW - last <= MIN_TAIL:
        return "sync: FAIL %s: speech runs past the scene end" % scene_id, False
    return "sync: %s speech %.2f-%.2f s (lead %.2f s)" % (scene_id, first, last, expected), True


def main(argv):
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        voiced = voiced_windows(argv[0])
        fps, scenes = load_timeline(argv[1])
    except InputError as err:
        print("verify_sync.py: %s" % err, file=sys.stderr)
        return 2
    placed = True
    for scene in scenes:
        line, ok = check_scene(voiced, fps, scene)
        print(line)
        placed = placed and ok
    return 0 if placed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
