#!/bin/bash
# check_render.sh: the container, speech-sync and still checks of a rendered explain video
# (stages 6 to 8 of render.sh).
#
#   check_render.sh <video.mp4> <timeline.json> <review-dir>
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   exit 0  all three checks passed
#   exit 1  a check failed; the checks after it do not run
#   exit 2  usage: wrong arguments, no video file, unreadable timeline
#
# stdout, one line per check, in this order, up to the first FAIL:
#   container: ok (<duration> s)
#              | FAIL streams <found> (expected one h264 video and one aac audio)
#              | FAIL size <w>x<h>, expected <W>x<H>       (the timeline's width and height)
#              | FAIL duration <d> s, expected <e> s        (more than 0.2 s apart)
#              | FAIL no Remotion CLI at <path> | FAIL ffprobe exit <code>
#   sync: ok | FAIL <scene id>: <cause>                     (from verify_sync.py)
#            | FAIL cannot extract the audio track | FAIL verify_sync.py exit <code>: <line>
#   stills (<n>): ok <review-dir> | stills: FAIL <name>: cannot extract
#
# A review dir whose basename is not "review" is refused first, before any file is read or
# emptied: "stills: FAIL review dir must be named review: <review-dir>", exit 1.
#
# The audio track goes to build/rendered-audio.wav next to the mp4. The review dir is
# emptied first, then holds one still per scene at from + max(leadFrames, FADE_FRAMES)
# (still-NN-<scene-id>.png) and one per cue at cueFrame + 15, clamped to the scene's last
# frame (still-NN-<scene-id>-<k>.png, k in frame order). A film (timeline format "film") has no
# cue frames: its review dir holds one still for the middle of each sentence
# (still-NN-<scene-id>-s<k>.png) and one for the last frame of each scene
# (still-NN-<scene-id>-end.png), at the frames of the timeline's checkFrames. A still for frame N
# is taken at (N - 0.5) / fps s: "-ss t" returns the first frame at or after t.
# The Remotion CLI of the workspace runs with cwd <ws>/app, so every path is made absolute.

set -eu

STILL_AFTER_CUE=15
# The frames FadeIn of src/sceneBody.tsx takes to bring a scene to full opacity: a scene still
# is taken no earlier, so a short lead (brainrot, 6) does not catch the panel mid-fade. The
# explainer lead (15) is longer, so its stills do not move.
FADE_FRAMES=8

usage() {
    echo "usage: check_render.sh <video.mp4> <timeline.json> <review-dir>" >&2
    exit 2
}

[ $# -eq 3 ] || usage
if [ "$(basename "$3")" != "review" ]; then
    echo "stills: FAIL review dir must be named review: $3"
    exit 1
fi
[ -f "$1" ] || { echo "check_render.sh: no such video: $1" >&2; exit 2; }
[ -f "$2" ] || { echo "check_render.sh: no such timeline: $2" >&2; exit 2; }

# The skill may be reached through a symlink (~/.claude/skills/explain); pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
video_dir=$(cd "${self%/*}" && pwd -P)
ws="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
app="$ws/app"
remotion="$app/node_modules/.bin/remotion"

absolute() {
    local dir
    dir=$(cd "$(dirname "$1")" && pwd -P)
    printf '%s/%s\n' "$dir" "$(basename "$1")"
}
mp4=$(absolute "$1")
timeline=$(absolute "$2")
mkdir -p "$3"
review=$(cd "$3" && pwd -P)
[ "$review" != "/" ] || usage

# The Remotion CLI (ffprobe, ffmpeg) with cwd <ws>/app and no stdin: ffmpeg reads keys from
# stdin, which would eat the still list of the loop below.
remo() {
    (cd "$app" && "$remotion" "$@") < /dev/null
}

# "<fps> <totalFrames> <width> <height>", then "<frame> <still name>" per still, in scene and
# frame order; for a film, one per entry of checkFrames, in its order. A film entry naming a
# scene that is not in scenes, or a film without checkFrames, is an unreadable timeline.
read_timeline() {
    python3 - "$timeline" "$STILL_AFTER_CUE" "$FADE_FRAMES" <<'PY'
import json, sys
t = json.load(open(sys.argv[1], encoding="utf-8"))
after, fade = int(sys.argv[2]), int(sys.argv[3])
print(t["fps"], t["totalFrames"], t["width"], t["height"])
if t.get("format") == "film":
    place = {s["id"]: n for n, s in enumerate(t["scenes"], 1)}
    for c in t["checkFrames"]:
        print(c["frame"], "still-%02d-%s-%s.png" % (place[c["scene"]], c["scene"], c["still"]))
else:
    for n, s in enumerate(t["scenes"], 1):
        start, last = s["from"], s["from"] + s["durationInFrames"] - 1
        print(start + max(s["leadFrames"], fade), "still-%02d-%s.png" % (n, s["id"]))
        for k, cue in enumerate(sorted(s["cueFrames"].values()), 1):
            print(min(start + cue + after, last), "still-%02d-%s-%d.png" % (n, s["id"], k))
PY
}

if ! info=$(read_timeline 2>&1); then
    echo "check_render.sh: cannot read timeline $timeline: ${info##*$'\n'}" >&2
    exit 2
fi
read -r fps total_frames width height <<< "${info%%$'\n'*}"
stills="${info#*$'\n'}"

fail() {
    echo "$1"
    exit 1
}

check_container() {
    local out rc=0 found size duration verdict
    [ -x "$remotion" ] || fail "container: FAIL no Remotion CLI at $remotion"
    out=$(remo ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 "$mp4" 2> /dev/null) \
        || rc=$?
    [ "$rc" -eq 0 ] || fail "container: FAIL ffprobe exit $rc"
    # "h264,video," lines -> "h264 video", sorted, comma separated.
    found=$(printf '%s\n' "$out" | tr ',' ' ' | awk 'NF { $1 = $1; print }' | sort | paste -s -d ',' - \
        | sed 's/,/, /g')
    [ "$found" = "aac audio, h264 video" ] \
        || fail "container: FAIL streams ${found:-none} (expected one h264 video and one aac audio)"
    size=$(remo ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x \
        "$mp4" 2> /dev/null) || rc=$?
    [ "$rc" -eq 0 ] || fail "container: FAIL ffprobe exit $rc"
    # "<w>x<h>"; this ffprobe prints a trailing separator ("1280x720x"), as it does for the
    # stream list above.
    size=$(printf '%s\n' "$size" | awk -F x 'NF { print $1 "x" $2; exit }')
    [ "$size" = "${width}x$height" ] || fail "container: FAIL size ${size:-none}, expected ${width}x$height"
    duration=$(remo ffprobe -v error -show_entries format=duration -of csv=p=0 "$mp4" 2> /dev/null) \
        || rc=$?
    [ "$rc" -eq 0 ] || fail "container: FAIL ffprobe exit $rc"
    verdict=$(awk -v d="$duration" -v n="$total_frames" -v r="$fps" 'BEGIN {
        e = n / r; diff = d - e; if (diff < 0) diff = -diff
        printf "%s %.2f %.2f\n", (d ~ /^[0-9]+(\.[0-9]+)?$/ && diff <= 0.2) ? "ok" : "bad", d, e }')
    set -- $verdict
    [ "$1" = "ok" ] || fail "container: FAIL duration $2 s, expected $3 s"
    echo "container: ok ($2 s)"
}

check_sync() {
    local build wav out rc=0 line
    build="$(dirname "$mp4")/build"
    wav="$build/rendered-audio.wav"
    mkdir -p "$build"
    remo ffmpeg -v error -y -i "$mp4" -vn -ac 1 -ar 16000 -f wav "$wav" > /dev/null 2>&1 \
        || fail "sync: FAIL cannot extract the audio track"
    out=$(python3 "$video_dir/verify_sync.py" "$wav" "$timeline" 2>&1) || rc=$?
    if [ "$rc" -eq 1 ]; then
        while IFS= read -r line; do
            case "$line" in "sync: FAIL "*) fail "$line" ;; esac
        done <<< "$out"
    fi
    [ "$rc" -eq 0 ] || fail "sync: FAIL verify_sync.py exit $rc: ${out##*$'\n'}"
    echo "sync: ok"
}

check_stills() {
    local frame name seek count=0
    find "$review" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    while read -r frame name; do
        seek=$(awk -v f="$frame" -v r="$fps" 'BEGIN { printf "%.4f", (f - 0.5) / r }')
        remo ffmpeg -v error -y -ss "$seek" -i "$mp4" -frames:v 1 "$review/$name" > /dev/null 2>&1 \
            && [ -s "$review/$name" ] \
            || fail "stills: FAIL $name: cannot extract"
        count=$((count + 1))
    done <<< "$stills"
    echo "stills ($count): ok $review"
}

check_container
check_sync
check_stills
exit 0
