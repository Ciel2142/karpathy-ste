#!/bin/bash
# render.sh: the video rung's one command, from <output-dir>/script.json to a checked
# video.mp4, its review stills and the final transcript (spec: video rung).
#
#   render.sh <output-dir> [--engine kokoro|say]          (default kokoro)
#   env EXPLAIN_VIDEO_WORKSPACE        workspace root (default $HOME/karpathy/video-workspace)
#   env EXPLAIN_BRAINROT_BACKGROUNDS   brainrot only: the background clip folder (default
#                                      <ws>/backgrounds)
#   env EXPLAIN_BRAINROT_SEED          brainrot only: an integer that fixes the clip choice and
#                                      its start (pick_background.py reads it; default random)
#
# The format is script.json's "format" ("explainer" when absent, else "brainrot"), read once
# the script stage has passed. An explainer run has nine stages and a brainrot run ten.
#
#   exit 0  all stages of the format passed
#   exit 1  a stage failed; the stages after it do not run
#   exit 2  usage, no <output-dir>/script.json, or script.json is not valid JSON (one line
#           on stderr)
#
# stdout carries one line per stage, in this order, up to the first FAIL (the explainer
# prints no "background" line):
#   script: ok (<n> scenes)                 check, transcript.py, verify.sh: no synthesis yet
#   workspace: ok <ws>                      video-workspace.sh --engine <engine>
#   narration (<engine>): ok [(fallback: <cause>)]      narrate.sh; <engine> as used; a
#                                           brainrot script narrates at --speed 1.2
#   timeline (<n> scenes, <s> s): ok        build/timeline.json; check_budgets.py reads the
#                                           limits from it (explainer scene <= 60 s, total
#                                           <= 150 s; brainrot 30 s and 90 s)
#   background: ok <name> @<start> s[ (loop)]   brainrot only: pick_background.py chooses the
#   background: ok generated                    clip, or the generated runner, into the timeline
#   render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok      log build/render.log
#   container: ok (<s> s)                   \
#   sync: ok                                 > video/check_render.sh
#   stills (<n>): ok <review-dir>           /
#   transcript: ok                          transcript.py --narrator, then verify.sh
# A failing stage prints "<stage>: FAIL <cause>" and, below it, the tool's output indented
# by two spaces (render: the last 40 log lines). The cost lines of video-workspace.sh and
# the lines of narrate.sh (a FALLBACK line among them) are printed indented as they come, and
# so are the "background: SKIP <file> (<cause>)" lines of the picker (a clip it could not use)
# and anything the picker prints on stderr. A picker that fails without its own FAIL line (a
# usage error, or an invalid EXPLAIN_BRAINROT_SEED) gives "background: FAIL pick_background.py
# exit <n>" below that indented output.
#
# The render ratio is advisory: "(limit 2.0)" only marks a ratio above 2.0. The engine of
# the timeline and of the Narrator row is the one in audio/durations.json, so a Kokoro run
# that fell back to say says so. The Narrator row reads "kokoro (af_heart)", "say" or
# "say (fallback: <cause>)". Once stage 1 passes, a video.mp4 and the stills of an earlier
# run are removed, so a later FAIL never leaves them next to the new transcript. The
# Remotion CLI runs with cwd <ws>/app: every path it gets is absolute, and provenance.root
# must be an absolute existing directory.

set -eu

MARK="__render_sh_exit__="
RATIO_LIMIT=2.0
BRAINROT_SPEED=1.2   # narrate.sh --speed of a brainrot script; the explainer keeps its default

usage() {
    echo "usage: render.sh <output-dir> [--engine kokoro|say]" >&2
    exit 2
}

out_arg=""
engine="kokoro"
while [ $# -gt 0 ]; do
    case "$1" in
        --engine)
            [ $# -ge 2 ] || usage
            engine="$2"
            shift 2
            ;;
        -*) usage ;;
        *)
            [ -z "$out_arg" ] || usage
            out_arg="$1"
            shift
            ;;
    esac
done
[ -n "$out_arg" ] || usage
case "$engine" in kokoro | say) ;; *) usage ;; esac
if [ ! -f "$out_arg/script.json" ]; then
    echo "render.sh: no script.json in $out_arg" >&2
    exit 2
fi
out=$(cd "$out_arg" && pwd -P)
script="$out/script.json"
if ! err=$(python3 -c '
import json, sys
try:
    json.load(open(sys.argv[1], encoding="utf-8"))
except ValueError as e:
    print(e)
    sys.exit(1)
' "$script" 2>&1); then
    echo "render.sh: $script is not valid JSON: ${err##*$'\n'}" >&2
    exit 2
fi

# The skill may be reached through a symlink (~/.claude/skills/explain); pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
scripts=$(cd "${self%/*}" && pwd -P)
video="${scripts%/*}/video"
ws="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
app="$ws/app"
remotion="$app/node_modules/.bin/remotion"

root=""       # provenance.root
fmt="explainer"   # the script's format: explainer, or brainrot
used=""       # the engine that made the audio (durations.json)
fallback=""   # the fallback cause, empty when none
video_s=""    # video length in seconds (totalFrames / fps)

fail() {
    echo "$1"
    exit 1
}

# The cause of a failed tool: its first "FAIL <cause>" line (without "FAIL "), else its
# first "<check>: FAIL ..." line, else its first non-empty line.
first_cause() {
    local line any=""
    while IFS= read -r line; do
        case "$line" in "FAIL "*) printf '%s\n' "${line#FAIL }"; return ;; esac
    done <<< "$1"
    while IFS= read -r line; do
        case "$line" in *": FAIL"*) printf '%s\n' "$line"; return ;; esac
        [ -n "$any" ] || any="$line"
    done <<< "$1"
    printf '%s\n' "${any:-no output}"
}

# Run a tool; on failure print "<stage>: FAIL <cause>", then its output indented, and stop.
run_tool() {
    local stage="$1" output rc=0
    shift
    output=$("$@" 2>&1) || rc=$?
    [ "$rc" -eq 0 ] && return 0
    echo "$stage: FAIL $(first_cause "$output")"
    printf '%s\n' "$output" | sed 's/^/  /'
    exit 1
}

# Run a tool and print its output lines indented as they come, except a line starting with
# $1 or $2: the last such line goes to $held. The exit code goes to $stream_rc.
stream() {
    local keep1="$1" keep2="$2" line
    shift 2
    held=""
    stream_rc=""
    while IFS= read -r line; do
        case "$line" in
            "$MARK"*) stream_rc="${line#"$MARK"}" ;;
            "$keep1"* | "$keep2"*) held="$line" ;;
            *) printf '  %s\n' "$line" ;;
        esac
    done < <(rc=0; "$@" 2>&1 < /dev/null || rc=$?; printf '%s%s\n' "$MARK" "$rc")
}

# The Narrator row of the transcript: the engine that made the audio, the Kokoro voice
# (narrate.py's af_heart), or the fallback cause.
narrator_text() {
    local used="$1" fallback="$2"
    if [ -n "$fallback" ]; then
        printf '%s (fallback: %s)\n' "$used" "$fallback"
    elif [ "$used" = "kokoro" ]; then
        printf 'kokoro (af_heart)\n'
    else
        printf '%s\n' "$used"
    fi
}

now() {
    python3 -c 'import time; print("%.3f" % time.time())'
}

stage_script() {
    local info count
    info=$(python3 - "$script" <<'PY'
import json, sys
s = json.load(open(sys.argv[1], encoding="utf-8"))
p = s.get("provenance") if isinstance(s, dict) else None
root = p.get("root") if isinstance(p, dict) else None
scenes = s.get("scenes") if isinstance(s, dict) else None
print(len(scenes) if isinstance(scenes, list) else 0)
print("root=" + (root if isinstance(root, str) else ""))
PY
) || fail "script: FAIL cannot read $script"
    count="${info%%$'\n'*}"
    root="${info#*$'\n'root=}"
    case "$root" in /*) ;; *) fail "script: FAIL provenance.root must be an absolute path" ;; esac
    [ -d "$root" ] || fail "script: FAIL provenance.root must be an existing directory: $root"
    run_tool script node "$video/build-timeline.mjs" --check "$script" --root "$root"
    # --check has accepted the format, so it is explainer or brainrot.
    fmt=$(python3 -c '
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("format", "explainer"))
' "$script") || fail "script: FAIL cannot read $script"
    run_tool script python3 "$video/transcript.py" "$script" "$out"
    run_tool script "$scripts/verify.sh" "$out/index.html"
    echo "script: ok ($count scenes)"
}

# The video and the stills of an earlier run: removed once the script is valid.
clear_stale() {
    rm -f "$out/video.mp4"
    [ ! -d "$out/review" ] || find "$out/review" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

stage_workspace() {
    stream "workspace: ok " "workspace: FAIL " "$scripts/video-workspace.sh" --engine "$engine"
    if [ "$stream_rc" != "0" ]; then
        case "$held" in
            "workspace: FAIL "*) fail "$held" ;;
            *) fail "workspace: FAIL video-workspace.sh exit ${stream_rc:-unknown}" ;;
        esac
    fi
    echo "workspace: ok $ws"
}

stage_narration() {
    local info speed_args=()
    [ "$fmt" != "brainrot" ] || speed_args=(--speed "$BRAINROT_SPEED")
    mkdir -p "$out/audio"
    stream "narration: FAIL " "narration: FAIL " \
        "$scripts/narrate.sh" "$script" "$out/audio" --engine "$engine" \
        ${speed_args[@]+"${speed_args[@]}"}
    if [ "$stream_rc" != "0" ]; then
        [ -n "$held" ] && fail "narration ($engine): FAIL ${held#narration: FAIL }"
        fail "narration ($engine): FAIL narrate.sh exit ${stream_rc:-unknown}"
    fi
    info=$(python3 - "$out/audio/durations.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(d["engine"])
print("fallback=" + (d.get("fallback") or ""))
PY
) || fail "narration ($engine): FAIL cannot read $out/audio/durations.json"
    used="${info%%$'\n'*}"
    fallback="${info#*$'\n'fallback=}"
    if [ -n "$fallback" ]; then
        echo "narration ($used): ok (fallback: $fallback)"
    else
        echo "narration ($used): ok"
    fi
}

stage_timeline() {
    local timeline="$out/build/timeline.json" verdict
    mkdir -p "$out/build"
    run_tool timeline node "$video/build-timeline.mjs" \
        "$script" "$out/audio/durations.json" "$used" "$timeline" --root "$root"
    verdict=$(python3 "$video/check_budgets.py" "$timeline") \
        || fail "timeline: FAIL cannot read $timeline"
    case "$verdict" in "FAIL "*) fail "timeline: $verdict" ;; esac
    set -- $verdict
    video_s="$4"
    echo "timeline ($2 scenes, $3 s): ok"
}

# Brainrot only: the picker writes the background into the timeline. Its SKIP lines and its
# stderr (merged by stream) print indented; its one "background: ok ..." line is held back and
# printed unindented.
stage_background() {
    [ "$fmt" = "brainrot" ] || return 0
    stream "background: ok " "background: FAIL " python3 "$video/pick_background.py" \
        "$out/build/timeline.json" "$remotion" "$app" \
        --dir "${EXPLAIN_BRAINROT_BACKGROUNDS:-$ws/backgrounds}"
    if [ "$stream_rc" != "0" ]; then
        case "$held" in
            "background: FAIL "*) fail "$held" ;;
            *) fail "background: FAIL pick_background.py exit ${stream_rc:-unknown}" ;;
        esac
    fi
    case "$held" in
        "background: ok "*) echo "$held" ;;
        *) fail "background: FAIL pick_background.py printed no result" ;;
    esac
}

stage_render() {
    local log="$out/build/render.log" clip t0 t1 rc=0 verdict
    [ -x "$remotion" ] || fail "render: FAIL no Remotion CLI at $remotion"
    rm -rf "$app/public/audio"
    mkdir -p "$app/public/audio"
    while IFS= read -r clip; do
        cp "$out/$clip" "$app/public/$clip" || fail "render: FAIL cannot copy $out/$clip"
    done <<< "$(python3 -c '
import json, sys
for s in json.load(open(sys.argv[1], encoding="utf-8"))["scenes"]:
    print(s["audio"])
' "$out/build/timeline.json")"
    t0=$(now)
    (cd "$app" && "$remotion" render Explain "$out/video.mp4" --props "$out/build/timeline.json") \
        > "$log" 2>&1 < /dev/null || rc=$?
    t1=$(now)
    if [ "$rc" -ne 0 ]; then
        echo "render: FAIL remotion render exit $rc (log $log)"
        tail -n 40 "$log" | sed 's/^/  /'
        exit 1
    fi
    verdict=$(awk -v a="$t0" -v b="$t1" -v v="$video_s" -v m="$RATIO_LIMIT" 'BEGIN {
        r = (b - a) / v
        printf "render (%.1f s, %.2f render-min/video-min)%s: ok\n", b - a, r, (r > m) ? " (limit " m ")" : "" }')
    echo "$verdict"
}

stage_checks() {
    "$video/check_render.sh" "$out/video.mp4" "$out/build/timeline.json" "$out/review" || exit 1
}

stage_transcript() {
    local narrator
    narrator=$(narrator_text "$used" "$fallback")
    run_tool transcript python3 "$video/transcript.py" "$script" "$out" --narrator "$narrator"
    run_tool transcript "$scripts/verify.sh" "$out/index.html"
    echo "transcript: ok"
}

stage_script
clear_stale
stage_workspace
stage_narration
stage_timeline
stage_background
stage_render
stage_checks
stage_transcript
exit 0
