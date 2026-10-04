#!/usr/bin/env python3
"""Choose the background of a brainrot short and write it into build/timeline.json (spec 4.4).

Usage: pick_background.py <timeline.json> <remotion-cli> <app-dir> --dir <clips> [--seed <int>]

<clips> is the background folder, <remotion-cli> the workspace's node_modules/.bin/remotion and
<app-dir> the workspace app (<ws>/app). Only *.mp4, *.mov and *.webm files count, matched
case-insensitively; hidden files and directories are ignored.

Order. The clips are `sorted(names)` shuffled by random.Random(seed); the seed is --seed, else
$EXPLAIN_BRAINROT_SEED, else random. For each clip, `<remotion-cli> ffprobe` (cwd <app-dir>,
stdin /dev/null, 60 s) reads the streams and the duration. A clip that cannot be probed, has no
video stream or no positive duration is skipped; the first good clip wins. A missing or empty
folder, or one with no good clip, gives the generated runner.

Placement. The video is totalFrames / fps long. A clip at least that long (within 1 ms) gets a
random start in [0, clip - video] and plays once; a shorter clip starts at 0 and loops.

Staging. Remotion's static server answers 404 for a file that is itself a symlink, and the
bundler copies regular files from public/ into every bundle but re-links symlinks. So the picker
empties <app-dir>/bg-stage/ on every run, stages the clip there as the regular file
clip<.ext lowercased> (a hard link to the clip's realpath, else a copy), and points the symlink
<app-dir>/public/bg at bg-stage. A path through that directory symlink is served. A generated
run leaves bg-stage empty and the link in place, so public/ never holds a dangling link.

The timeline is rewritten in place (indent 2) with a `background` key:
  {"kind": "clip", "file": <name>, "src": "bg/clip<.ext>", "start": <s>, "seconds": <s>,
   "loop": <bool>}              start is rounded down and seconds rounded to 3 places
  {"kind": "generated"}

stdout, in order: one `background: SKIP <file> (<cause>)` per skipped clip (unindented), then
  background: ok <name> @<start %.1f> s[ (loop)]   or   background: ok generated
or `background: FAIL <cause>` (cannot read or write the timeline, cannot stage the clip, or
`--dir <dir> is inside the app workspace`).
Exit 0 ok, 1 FAIL, 2 usage (the usage line and an error line on stderr). Stdlib only.

--dir must not be, or lie under, <app-dir>/bg-stage or <app-dir>/public: the picker empties both
on every run, so such a folder would lose its clips. That is a misconfiguration, not a missing
folder, and the picker refuses it (FAIL, exit 1) before it touches anything.
"""

import argparse
import contextlib
import json
import math
import os
import random
import shutil
import subprocess
import sys

USAGE = "pick_background.py <timeline.json> <remotion-cli> <app-dir> --dir <clips> [--seed <int>]"
EXTENSIONS = (".mp4", ".mov", ".webm")
PROBE_TIMEOUT = 60       # seconds
SHORT_TOLERANCE = 0.001  # a clip this much shorter than the video still counts as equal
STAGE = "bg-stage"
SEED_ENV = "EXPLAIN_BRAINROT_SEED"


class Fail(Exception):
    """A failure main() prints as `background: FAIL <message>` and exits 1 on."""


def say(line):
    print(line, flush=True)


def reason(err):
    """The short text of an exception: the OS message without the path for an OSError."""
    if isinstance(err, OSError) and err.strerror:
        return err.strerror
    return str(err)


def read_timeline(path):
    """(timeline dict, fps, totalFrames); Fail when it cannot be read or lacks them."""
    try:
        with open(path, encoding="utf-8") as handle:
            timeline = json.load(handle)
        fps, frames = timeline["fps"], timeline["totalFrames"]
    except (OSError, ValueError, KeyError, TypeError) as err:
        raise Fail("cannot read %s: %s" % (path, reason(err))) from err
    for key, value in (("fps", fps), ("totalFrames", frames)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value <= 0:
            raise Fail("cannot read %s: %s must be a positive number" % (path, key))
    return timeline, fps, frames


def write_timeline(path, timeline):
    """Rewrite the timeline as indent-2 JSON plus a newline, through a temp file and a rename."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(timeline, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except (OSError, ValueError) as err:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise Fail("cannot write %s: %s" % (path, reason(err))) from err


def same_file(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def inside_app(folder, app):
    """True when `folder` is, or lies under, <app>/bg-stage or <app>/public. The folder is compared
    by realpath, so a symlink or a dotted path into them counts; every ancestor is also compared
    with os.path.samefile, which catches a different letter case on a case-insensitive volume."""
    real_app = os.path.realpath(app)
    roots = set()
    for sub in (STAGE, "public"):
        roots.add(os.path.realpath(os.path.join(app, sub)))
        roots.add(os.path.join(real_app, sub))
    path = os.path.realpath(folder)
    while True:
        if any(path == root or same_file(path, root) for root in roots):
            return True
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent


def clear_path(path):
    """Remove whatever is at `path`. A symlink is removed itself and never followed."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.unlink(path)


def prepare_stage(app):
    """Empty <app>/bg-stage (made if missing) and point <app>/public/bg at it."""
    stage = os.path.abspath(os.path.join(app, STAGE))
    link = os.path.join(app, "public", "bg")
    try:
        clear_path(stage)
        os.makedirs(stage)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        clear_path(link)
        os.symlink(stage, link)
    except OSError as err:
        raise Fail("cannot prepare %s: %s" % (stage, reason(err))) from err
    return stage


def stage_clip(clip, app):
    """Put `clip` into <app>/bg-stage as the regular file clip<.ext lowercased>: a hard link to its
    realpath, or a copy when the link fails (another volume, permissions). Returns the staged path;
    raises OSError when both fail."""
    dest = os.path.join(app, STAGE, "clip" + os.path.splitext(clip)[1].lower())
    source = os.path.realpath(clip)
    try:
        os.link(source, dest)
    except OSError:
        try:
            shutil.copyfile(source, dest)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(dest)
            raise
    return dest


def list_clips(folder):
    """(sorted clip file names, a SKIP line or None). A missing folder is not an error."""
    try:
        entries = os.listdir(folder)
    except (FileNotFoundError, NotADirectoryError):
        return [], None
    except OSError as err:
        return [], "background: SKIP %s (cannot list: %s)" % (folder, reason(err))
    names = [
        name for name in entries
        if not name.startswith(".")
        and os.path.splitext(name)[1].lower() in EXTENSIONS
        and not os.path.isdir(os.path.join(folder, name))
    ]
    return sorted(names), None


def probe(remotion, clip, app):
    """(seconds, None) for a clip with a video stream and a positive duration, else (None, cause)."""
    command = [remotion, "ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type:format=duration", "-of", "json", clip]
    try:
        done = subprocess.run(
            command, cwd=app, stdin=subprocess.DEVNULL, capture_output=True,
            encoding="utf-8", errors="replace", timeout=PROBE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None, "ffprobe timed out"
    except OSError as err:
        return None, "cannot run ffprobe: %s" % reason(err)
    if done.returncode != 0:
        return None, "ffprobe exit %d" % done.returncode
    try:
        info = json.loads(done.stdout)
        has_video = any(s.get("codec_type") == "video" for s in info.get("streams", []))
        raw = info.get("format", {}).get("duration")
    except (ValueError, AttributeError, TypeError):
        return None, "ffprobe output unreadable"
    if not has_video:
        return None, "no video stream"
    try:
        seconds = float(raw)
    except (TypeError, ValueError):  # missing, or "N/A"
        seconds = 0.0
    if not math.isfinite(seconds) or seconds <= 0:
        return None, "no duration"
    return seconds, None


def first_good_clip(names, folder, remotion, app, rng):
    """(name, seconds) of the first probeable clip in seeded order, printing a SKIP line for each
    clip passed over; (None, None) when no clip is good."""
    order = list(names)
    rng.shuffle(order)
    for name in order:
        seconds, cause = probe(remotion, os.path.abspath(os.path.join(folder, name)), app)
        if cause is None:
            return name, seconds
        say("background: SKIP %s (%s)" % (name, cause))
    return None, None


def place(clip_seconds, video_seconds, rng):
    """(start, loop). A clip at least as long as the video starts somewhere in [0, clip - video],
    rounded down to 3 places so that start + video never passes the clip; a shorter one loops."""
    if clip_seconds + SHORT_TOLERANCE < video_seconds:
        return 0.0, True
    span = max(0.0, clip_seconds - video_seconds)
    return math.floor(rng.uniform(0, span) * 1000) / 1000, False


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="pick_background.py", usage=USAGE)
    parser.add_argument("timeline")
    parser.add_argument("remotion")
    parser.add_argument("app")
    parser.add_argument("--dir", required=True, dest="folder")
    parser.add_argument("--seed", type=int)
    return parser.parse_args(argv)


def resolve_seed(flag):
    """The seed: --seed, else $EXPLAIN_BRAINROT_SEED, else None (random). ValueError on a bad variable."""
    if flag is not None:
        return flag
    text = os.environ.get(SEED_ENV, "")
    return int(text) if text.strip() else None


def choose(args, rng, video_seconds):
    """The `background` value and the stage line; stages the clip when there is one."""
    names, note = list_clips(args.folder)
    if note:
        say(note)
    name, seconds = first_good_clip(names, args.folder, args.remotion, args.app, rng)
    if name is None:
        return {"kind": "generated"}, "background: ok generated"
    start, loop = place(seconds, video_seconds, rng)
    try:
        stage_clip(os.path.join(args.folder, name), args.app)
    except OSError as err:
        raise Fail("cannot stage %s: %s" % (name, reason(err))) from err
    ext = os.path.splitext(name)[1].lower()
    background = {"kind": "clip", "file": name, "src": "bg/clip" + ext,
                  "start": start, "seconds": round(seconds, 3), "loop": loop}
    return background, "background: ok %s @%.1f s%s" % (name, start, " (loop)" if loop else "")


def main(argv):
    args = parse_args(argv)
    try:
        seed = resolve_seed(args.seed)
    except ValueError:
        print("pick_background.py: %s must be an integer, got %r" % (SEED_ENV, os.environ[SEED_ENV]),
              file=sys.stderr)
        return 2
    try:
        if inside_app(args.folder, args.app):
            raise Fail("--dir %s is inside the app workspace" % args.folder)
        timeline, fps, frames = read_timeline(args.timeline)
        prepare_stage(args.app)
        background, line = choose(args, random.Random(seed), frames / fps)
        timeline["background"] = background
        write_timeline(args.timeline, timeline)
    except Fail as err:
        say("background: FAIL %s" % err)
        return 1
    say(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
