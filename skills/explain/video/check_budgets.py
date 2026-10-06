#!/usr/bin/env python3
"""Check a timeline's length budgets (video rung).

Usage: check_budgets.py <timeline.json>

The limits are the timeline's own: maxSceneSeconds is the longest scene and maxTotalSeconds the
longest video, both in seconds (build-timeline.mjs writes them per format: film 30 and 150,
brainrot 30 and 90, clip 30 and 60). A scene is durationInFrames / fps seconds, the video
totalFrames / fps; a length equal to its limit passes.

stdout, one line, exit 0:
  ok <n> <total %.1f> <total %.3f>                 <n> scenes, total seconds
  FAIL scene <id> is <s %.1f> s (max <%g><tag>)    the first scene over its limit
  FAIL total <s %.1f> s (max <%g><tag>)            every scene fits, the video does not
<tag> names the format the way build-timeline.mjs (tagOf) does on its limit lines: ", film",
", brainrot" or ", clip".
Exit 2 (one line on stderr) for a usage error, a timeline that cannot be read, or one without a
usable format, fps, totalFrames, scenes[].durationInFrames, maxSceneSeconds or maxTotalSeconds;
there is no default format and no default limit. A usable format is "film", "brainrot" or "clip";
any other value, or no "format" key, is "<path>: no usable format", checked before the numbers.
Stdlib only.
"""

import json
import math
import sys

USAGE = "usage: check_budgets.py <timeline.json>"
FORMATS = ("film", "brainrot", "clip")  # the formats whose timelines build-timeline.mjs writes


class Unreadable(Exception):
    """A timeline check_budgets cannot judge: the message names the file and the missing key."""


def number(container, key, where, positive=False):
    """container[key] as a float; Unreadable when absent, not a finite number, or not > 0."""
    value = container.get(key) if isinstance(container, dict) else None
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if not ok or (positive and value <= 0):
        raise Unreadable("%s: no usable %s" % (where, key))
    return float(value)


def format_tag(timeline) -> str:
    """", <format>" of a film, brainrot or clip timeline (build-timeline.mjs tagOf); verdict has
    checked the format."""
    return ", %s" % timeline["format"]


def verdict(path):
    """The one-line verdict for the timeline at `path`."""
    try:
        with open(path, encoding="utf-8") as handle:
            timeline = json.load(handle)
    except (OSError, ValueError) as err:
        raise Unreadable("%s: %s" % (path, getattr(err, "strerror", None) or err))
    fmt = timeline.get("format") if isinstance(timeline, dict) else None
    if not (isinstance(fmt, str) and fmt in FORMATS):
        raise Unreadable("%s: no usable format" % path)
    fps = number(timeline, "fps", path, positive=True)
    max_scene = number(timeline, "maxSceneSeconds", path)
    max_total = number(timeline, "maxTotalSeconds", path)
    total = number(timeline, "totalFrames", path) / fps
    scenes = timeline.get("scenes")
    if not isinstance(scenes, list):
        raise Unreadable("%s: no usable scenes" % path)
    tag = format_tag(timeline)
    for scene in scenes:
        seconds = number(scene, "durationInFrames", path) / fps
        if seconds > max_scene:
            return "FAIL scene %s is %.1f s (max %g%s)" % (scene.get("id"), seconds, max_scene, tag)
    if total > max_total:
        return "FAIL total %.1f s (max %g%s)" % (total, max_total, tag)
    return "ok %d %.1f %.3f" % (len(scenes), total, total)


def main(argv):
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        print(verdict(argv[1]))
    except Unreadable as err:
        print("check_budgets.py: %s" % err, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
