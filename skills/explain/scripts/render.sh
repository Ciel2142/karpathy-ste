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
# The format is script.json's "format": "film" when the key is absent, or "brainrot" or "clip". Any
# other value stops the script stage with "script: FAIL script: format must be film, brainrot or
# clip", so the format is read once the check of that stage has passed. A clip is a film of at
# most 60 s: a clip run is a film run (eleven stages, "scene" and "guard", composition Film, the
# film stills). A film run has eleven stages, a brainrot run ten: the film has "scene" and
# "guard", brainrot has "background".
#
#   exit 0  all stages of the format passed
#   exit 1  a stage failed; the stages after it do not run; or HUP, INT or TERM stopped the run
#           (no FAIL line)
#   exit 2  usage, no <output-dir>/script.json, or script.json is not valid JSON (one line
#           on stderr)
#
# stdout carries one line per stage, in this order, up to the first FAIL (the film prints no
# "background" line; brainrot prints no "scene" and no "guard" line):
#   script: ok (<n> scenes)                 check, transcript.py, verify.sh: no synthesis yet
#   workspace: ok <ws>                      video-workspace.sh --engine <engine>, then the run
#                                           directory (below)
#   scene: ok (<n> files)                   film only: check_scene.py checks <output-dir>/scene; its
#                                           <n> *.ts and *.tsx files (not script.gen.ts) replace
#                                           src/film of the run directory; build-timeline.mjs --types
#                                           writes script.gen.ts there; tsc, with the run directory
#                                           as its project, type-checks the lot. The stage comes
#                                           before the narration, so a fault costs no synthesis
#   narration (<engine>): ok [(fallback: <cause>)]      narrate.sh; <engine> as used; a
#                                           brainrot script narrates at --speed 1.2
#   timeline (<n> scenes, <s> s): ok        build/timeline.json; check_budgets.py reads the
#                                           limits from it (film scene <= 30 s, total <= 150 s;
#                                           clip 30 s and 60 s; brainrot 30 s and 90 s)
#   guard (<n> frames): ok                  film only: composition Film rendered at the <n> checkFrames
#                                           of the timeline alone, into build/guard.mp4, log
#                                           build/guard.log; FilmStage measures the text at each of
#                                           those frames (off the canvas, too small, over another text;
#                                           spec 7.3) and fails the pass at the first fault. The stage
#                                           runs before the render, so a fault costs no full render
#   background: ok <name> @<start> s[ (loop)]   brainrot only: pick_background.py chooses the
#   background: ok generated                    clip, or the generated runner, into the timeline
#   render (<s> s, <ratio> render-min/video-min)[ (limit 2.0)]: ok      log build/render.log
#   container: ok (<s> s)                   \
#   sync: ok                                 > video/check_render.sh
#   stills (<n>): ok <review-dir>           /
#   transcript: ok                          transcript.py --narrator (a brainrot run also
#                                           --background, read from the timeline), then verify.sh
# The render stage renders composition Film for a film or a clip and composition Explain for a
# brainrot script. The stills of a film (a clip too) are cut at the checkFrames of its timeline:
# still-NN-<scene-id>-s<k>.png at the middle of sentence k of a scene and
# still-NN-<scene-id>-end.png at its last frame.
# A failing stage prints "<stage>: FAIL <cause>" and, below it, the tool's output indented
# by two spaces (render: the last 40 log lines). The cost lines of video-workspace.sh and
# the lines of narrate.sh (a FALLBACK line among them) are printed indented as they come, and
# so are the "background: SKIP <file> (<cause>)" lines of the picker (a clip it could not use)
# and anything the picker prints on stderr. The picker's own FAIL line (an invalid
# EXPLAIN_BRAINROT_SEED among its causes) is the stage's FAIL line; a picker that fails without
# one (a usage error) gives "background: FAIL pick_background.py exit <n>" below that indented
# output.
#
# The scene stage has five FAIL lines. Each stops the run with exit 1 before the narration; the run
# directory goes by the EXIT trap:
#   scene: FAIL no scene directory: <path>
#       <output-dir>/scene is not a directory: absent, or there but not a directory (a link is
#       followed). <path> is that path, <output-dir> by its real path; the tool's line follows,
#       indented.
#   scene: FAIL <first cause of check_scene.py>
#       The scene is refused: no Film.tsx, <name> is a directory, <name> is not a .ts or .tsx file,
#       Film.tsx has no "export function Film(", or an import or a token that the rules refuse
#       (<file>:<line>: <cause>). Every cause follows, indented, the first among them. Nothing was
#       copied. (A tool that fails with no FAIL line of its own gives as the cause its first line
#       that holds ": FAIL", else its first non-empty line, else "no output".)
#   scene: FAIL cannot copy the scene to <run>/src/film
#       The removal of src/film, its making or a cp failed. Nothing follows.
#   scene: FAIL types: <cause>
#       build-timeline.mjs --types failed; its output follows, indented.
#   scene: FAIL tsc: <first error line>
#       tsc exited non-zero. The first error line is the first line of its output with "error TS",
#       else its first line that is not empty, else "exit <n>". Only the first 20 lines of its
#       output follow, indented; the rest goes with the run directory (tsc.log in it). "src/film/"
#       is written "scene/" in them and in the stage line.
#
# The guard stage has five FAIL lines. Each stops the run with exit 1 before the render; the run
# directory goes by the EXIT trap. A marker in the log of the pass fails the stage whatever the exit
# code of the pass: a cancel that the CLI reads late, or never, cannot pass the guard.
#   guard: FAIL frame <f> (scene <id>): <fault>[; <fault>...]
#       FilmStage measured a fault at check frame <f> of scene <id>. The line comes from the first log
#       line that holds "guard: FAIL frame " or "MARK scene " (whichever comes first); when that line
#       holds "guard: FAIL frame ", it is the text from that marker to the end of the line: the
#       message that FilmStage gave to cancelRender, with no "Error" prefix and no code frame below
#       it. Nothing follows; the log stays in <out>/build/guard.log.
#   guard: FAIL mark: scene <id>: <cause>
#       The scene code threw a mark error of spec 6 (kit/marks.ts: a word that the narration does not
#       say, a sentence past the last one, a scene that does not exist) at a check frame. The line comes
#       from the first log line that holds "guard: FAIL frame " or "MARK scene " (whichever comes
#       first); when that line holds "MARK scene ", it is "guard: FAIL mark: scene " and then the text
#       after "MARK scene " of the message, as marks.ts wrote it, with no "Error" prefix and no code
#       frame below it ("guard: FAIL mark: " is only the prefix that the stage prints: the stage does
#       not look for it in the log). Nothing follows; the log stays in <out>/build/guard.log.
#       A mark error in code that no check frame reaches is not caught by the guard: it ends the
#       render stage with "render: FAIL remotion render exit 1", its MARK line in
#       <out>/build/render.log.
#   guard: FAIL remotion render exit <n> (log <out>/build/guard.log)
#       The pass exited non-zero and its log holds neither marker (the CLI failed on its own: no
#       browser, a bundle error, a clip it could not fetch). The last 40 log lines follow, indented.
#   guard: FAIL cannot read <out>/build/timeline.json
#       The timeline is absent or not JSON, or holds no checkFrames, or a frame that is not an
#       integer of 0 or more. No pass runs.
#   guard: FAIL cannot copy <out>/<clip>
#       A narration clip of the timeline could not be copied into the run directory. No pass runs.
#
# The render ratio is advisory: "(limit 2.0)" only marks a ratio above 2.0. The engine of
# the timeline and of the Narrator row is the one in audio/durations.json, so a Kokoro run
# that fell back to say says so. The Narrator row reads "kokoro (af_heart)", "say" or
# "say (fallback: <cause>)". Once stage 1 passes, a video.mp4, the stills and build/guard.mp4 of
# an earlier run are removed, so a later FAIL never leaves them next to the new transcript.
#
# Each render compiles in a run directory of its own, <ws>/runs/run.<pid>.<6 chars>, so two
# renders can run at the same time and render.sh writes nothing under <ws>/app. It holds a
# copy of the skill's video/ (without a top-level node_modules or public of the checkout, and
# without __pycache__; owner-writable, so that a read-only skill tree gives a copy that can be
# removed), node_modules as a link to the shared <ws>/app/node_modules, and public/ with the
# narration clips in public/audio (brainrot: also the picker's bg-stage/ behind public/bg). A film
# puts its scene only there: the scene stage replaces src/film of this copy, and nothing of the
# scene reaches <ws>/app or the shared node_modules. The clips go into public/audio from the
# output directory before the render and, for a film only (the guard pass is film only), before the
# guard pass as well: with --muted the renderer leaves the sound out of guard.mp4, but it still
# fetches the clip of every audio of a rendered frame.
# The workspace stage makes it, before its ok line, after it has removed each run directory
# of <ws>/runs (an entry named run.*; other entries stay) modified more than a day (1440 min)
# ago: what a killed render left. <ws>/runs may be a symlink to a directory.
# A failure gives "workspace: FAIL cannot make a run directory in <ws>/runs". An EXIT trap
# removes it after a pass, a FAIL, or HUP, INT or TERM. render.sh does not signal its
# children: a signal to render.sh alone takes effect when the running tool returns, or at
# once while a stage reads a tool's lines as they come (workspace, narration, background),
# and that tool is left running; a signal to the process group (Ctrl-C, timeout) stops the
# tool as well. The Remotion CLI is the exception: TERM and HUP only make it kill its browser,
# and the render goes on with a new one, so render.sh waits for the CLI to end before it exits
# and removes the run directory. The Remotion CLI runs with cwd <ws>/runs/<run>: every path it
# gets is absolute, and provenance.root must be an absolute existing directory. The tsc of the
# scene stage runs there as well, with no argument, and so does the Remotion CLI of the guard pass,
# as the render's does: render.sh waits for each of them to end in the same way, so that a tsc or a
# CLI which outlives the signal never writes into a removed run directory.

set -eu

MARK="__render_sh_exit__="
RATIO_LIMIT=2.0
BRAINROT_SPEED=1.2   # narrate.sh --speed of a brainrot script; a film keeps the default speed of narrate.sh

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
tsc="$app/node_modules/.bin/tsc"

root=""       # provenance.root
fmt="film"    # the script's format: film, brainrot or clip
used=""       # the engine that made the audio (durations.json)
fallback=""   # the fallback cause, empty when none
video_s=""    # video length in seconds (totalFrames / fps)
run=""        # the run directory of this render; "" until make_run_dir has made it

# The EXIT trap: remove the run directory after a pass, a FAIL or a signal. rm -rf on the
# directory itself removes its node_modules link and never follows it; a trailing slash or a
# glob after the name would delete the shared packages of every render. A directory that
# cannot be removed is left to the sweep of a later run, and the exit code stays the render's.
remove_run_dir() {
    [ -z "$run" ] || rm -rf "$run" || true
}
trap remove_run_dir EXIT
trap 'exit 1' HUP INT TERM

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
    # --check has accepted the format, so it is film, brainrot or clip.
    fmt=$(python3 -c '
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("format", "film"))
' "$script") || fail "script: FAIL cannot read $script"
    run_tool script python3 "$video/transcript.py" "$script" "$out"
    run_tool script "$scripts/verify.sh" "$out/index.html"
    echo "script: ok ($count scenes)"
}

# The video, the stills and the guard video (build/guard.mp4, of a film run) of an earlier run:
# removed, for every format, once the script is valid.
clear_stale() {
    rm -f "$out/video.mp4" "$out/build/guard.mp4"
    [ ! -d "$out/review" ] || find "$out/review" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
}

# Remove each run directory of <ws>/runs (an entry named run.*) modified more than a day
# (1440 min) ago: the run directory of a render that was killed before its EXIT trap ran. Any
# other entry stays. -H: <ws>/runs may be a symlink to a directory, whose entries are swept; no
# link below it is followed. find hands each path to rm -rf as it is, with no trailing slash, so
# a node_modules link goes and the shared packages stay. A removal that fails is ignored.
sweep_old_runs() {
    find -H "$ws/runs" -mindepth 1 -maxdepth 1 -name 'run.*' -mmin +1440 -exec rm -rf {} + \
        2> /dev/null || true
}

# Make the run directory of this render: the entries of video/ except a top-level node_modules
# or public of the checkout (a directory, a file or a link) and __pycache__ at any depth, made
# owner-writable, then node_modules as a link to the shared packages and an empty public/.
make_run_dir() {
    local cause="workspace: FAIL cannot make a run directory in $ws/runs" entry
    mkdir -p "$ws/runs" || fail "$cause"
    sweep_old_runs
    run=$(mktemp -d "$ws/runs/run.$$.XXXXXX") || fail "$cause"
    for entry in "$video"/* "$video"/.[!.]* "$video"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue   # a pattern that matched nothing
        case "${entry##*/}" in node_modules | public | __pycache__) continue ;; esac
        cp -R "$entry" "$run" || fail "$cause"
    done
    # cp -R copies the modes of a read-only skill tree, and rm -rf cannot empty a directory the
    # owner cannot write. Before the link: once it exists, no recursive command but the removal
    # may run on $run.
    chmod -R u+w "$run" || fail "$cause"
    find "$run" -name __pycache__ -prune -exec rm -rf {} + || fail "$cause"
    ln -s "$app/node_modules" "$run/node_modules" || fail "$cause"
    mkdir "$run/public" || fail "$cause"
}

stage_workspace() {
    stream "workspace: ok " "workspace: FAIL " "$scripts/video-workspace.sh" --engine "$engine"
    if [ "$stream_rc" != "0" ]; then
        case "$held" in
            "workspace: FAIL "*) fail "$held" ;;
            *) fail "workspace: FAIL video-workspace.sh exit ${stream_rc:-unknown}" ;;
        esac
    fi
    make_run_dir
    echo "workspace: ok $ws"
}

# Film only. The scene of <out>/scene goes into the run directory in four steps: check_scene.py
# checks it by its text; src/film of the run directory is replaced by the scene's *.ts and *.tsx
# files (a hidden file and the author's script.gen.ts stay behind); build-timeline.mjs --types
# writes script.gen.ts there, the scene and source names of the script; tsc, with the run
# directory as its project, type-checks the lot. The stage runs before the narration, so that a
# fault in the picture costs no synthesis. The one recursive command on a path of $run is the
# removal of src/film: the node_modules link lies outside it, and a trailing slash or a glob
# after the name would reach the shared packages.
stage_scene() {
    local file cause="" first="" types line count=0 rc=0
    [ "$fmt" != "brainrot" ] || return 0
    run_tool scene python3 "$video/check_scene.py" "$out/scene"
    rm -rf "$run/src/film" && mkdir -p "$run/src/film" \
        || fail "scene: FAIL cannot copy the scene to $run/src/film"
    for file in "$out/scene"/*.ts "$out/scene"/*.tsx; do
        [ -f "$file" ] || continue   # a pattern that matched nothing
        [ "${file##*/}" != "script.gen.ts" ] || continue
        cp "$file" "$run/src/film/${file##*/}" \
            || fail "scene: FAIL cannot copy the scene to $run/src/film"
        count=$((count + 1))
    done
    types=$(node "$video/build-timeline.mjs" --types "$script" "$run/src/film/script.gen.ts" 2>&1) || {
        echo "scene: FAIL types: $(first_cause "$types")"
        printf '%s\n' "$types" | sed 's/^/  /'
        exit 1
    }
    # exec, as for the Remotion CLI in stage_render: render.sh waits for tsc itself. A subshell
    # would end at once on TERM or HUP, and the EXIT trap would remove the run directory while tsc
    # went on in it.
    (cd "$run" && exec "$tsc") > "$run/tsc.log" 2>&1 < /dev/null || rc=$?
    if [ "$rc" -ne 0 ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            case "$line" in *"error TS"*) cause="$line"; break ;; esac
            [ -n "$first" ] || first="$line"
        done < "$run/tsc.log"
        echo "scene: FAIL tsc: $(printf '%s\n' "${cause:-${first:-exit $rc}}" | sed 's|src/film/|scene/|g')"
        head -n 20 "$run/tsc.log" | sed -e 's|src/film/|scene/|g' -e 's/^/  /'
        exit 1
    fi
    echo "scene: ok ($count files)"
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

# The narration clips of the timeline (the audio of each scene) go from the output directory into the
# public directory of the run, where the renderer fetches them. $1 is the stage whose FAIL line a clip
# that cannot be copied prints.
copy_clips() {
    local stage="$1" clip
    mkdir -p "$run/public/audio"
    while IFS= read -r clip; do
        cp "$out/$clip" "$run/public/$clip" || fail "$stage: FAIL cannot copy $out/$clip"
    done <<< "$(python3 -c '
import json, sys
for s in json.load(open(sys.argv[1], encoding="utf-8"))["scenes"]:
    print(s["audio"])
' "$out/build/timeline.json")"
}

# Film only. The guard pass renders composition Film at the checkFrames of the timeline alone, one
# one-frame range each (a comma list of frames makes an image sequence, which an output named *.mp4
# refuses), into build/guard.mp4, in the run directory as the render stage does. FilmStage measures the
# text of each of those frames and ends the pass through cancelRender, with the stage line of the frame
# as the message, at the first frame with a fault (spec 7.3); the log holds that line. The pass needs
# the narration clips, so it copies them into the run directory as the render stage does: --muted
# leaves the sound out of guard.mp4, but the renderer still fetches the clip of every <Html5Audio> of a
# rendered frame, and a clip it cannot fetch ends the pass.
stage_guard() {
    local timeline="$out/build/timeline.json" log="$out/build/guard.log" info count ranges line rc=0
    [ "$fmt" != "brainrot" ] || return 0
    info=$(python3 - "$timeline" <<'PY'
import json, sys
try:
    frames = [check["frame"] for check in json.load(open(sys.argv[1], encoding="utf-8"))["checkFrames"]]
except (OSError, ValueError, KeyError, TypeError):
    sys.exit(1)
if not frames or not all(type(f) is int and f >= 0 for f in frames):
    sys.exit(1)
print(len(frames))
print(",".join("%d-%d" % (f, f) for f in frames))
PY
) || fail "guard: FAIL cannot read $timeline"
    count="${info%%$'\n'*}"
    ranges="${info#*$'\n'}"
    copy_clips guard
    # exec, as for the Remotion CLI in stage_render: render.sh waits for the CLI itself. A subshell
    # would end at once on TERM or HUP, and the EXIT trap would remove the run directory while the CLI,
    # which outlives both, goes on in it.
    (cd "$run" && exec "$remotion" render Film "$out/build/guard.mp4" "--frames=$ranges" \
        --concurrency=1 --muted --props "$timeline") > "$log" 2>&1 < /dev/null || rc=$?
    # The first marker of the log fails the stage whatever the exit code: a cancel that the CLI reads late,
    # or never, can still end the pass with exit 0. A frame fault is its own stage line, from its marker on;
    # a mark error of marks.ts (MARK scene <id>: <cause>) is given the stage's prefix, in place of its MARK.
    # The code frame below either repeats the source's text, and is never reached: the first line wins.
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            *"guard: FAIL frame "*) fail "guard: FAIL frame ${line#*guard: FAIL frame }" ;;
            *"MARK scene "*) fail "guard: FAIL mark: scene ${line#*MARK scene }" ;;
        esac
    done < "$log"
    if [ "$rc" -ne 0 ]; then
        echo "guard: FAIL remotion render exit $rc (log $log)"
        tail -n 40 "$log" | sed 's/^/  /'
        exit 1
    fi
    echo "guard ($count frames): ok"
}

# Brainrot only: the picker writes the background into the timeline. Its SKIP lines and its
# stderr (merged by stream) print indented; its one "background: ok ..." line is held back and
# printed unindented.
stage_background() {
    [ "$fmt" = "brainrot" ] || return 0
    stream "background: ok " "background: FAIL " python3 "$video/pick_background.py" \
        "$out/build/timeline.json" "$remotion" "$run" \
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
    local log="$out/build/render.log" t0 t1 rc=0 verdict composition=Explain
    [ "$fmt" = "brainrot" ] || composition=Film
    [ -x "$remotion" ] || fail "render: FAIL no Remotion CLI at $remotion"
    copy_clips render
    t0=$(now)
    # exec: render.sh waits for the CLI itself. A subshell would end at once on TERM or HUP, and
    # the EXIT trap would remove the run directory while the CLI, which outlives both, goes on
    # in it.
    (cd "$run" && exec "$remotion" render "$composition" "$out/video.mp4" \
        --props "$out/build/timeline.json") > "$log" 2>&1 < /dev/null || rc=$?
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

# The Background row of a brainrot transcript, from the timeline the picker wrote:
# "<file> @ <start %.1f> s" plus " (loop)" for a looping clip, or "generated". The space after
# the @ is the transcript's; the stage line of the picker has none.
background_text() {
    python3 - "$1" <<'PY'
import json, sys
b = json.load(open(sys.argv[1], encoding="utf-8"))["background"]
if b["kind"] == "generated":
    print("generated")
else:
    print("%s @ %.1f s%s" % (b["file"], b["start"], " (loop)" if b["loop"] else ""))
PY
}

stage_transcript() {
    local narrator timeline="$out/build/timeline.json" background bg_args=()
    narrator=$(narrator_text "$used" "$fallback")
    if [ "$fmt" = "brainrot" ]; then
        background=$(background_text "$timeline") || fail "transcript: FAIL cannot read $timeline"
        bg_args=(--background "$background")
    fi
    run_tool transcript python3 "$video/transcript.py" "$script" "$out" --narrator "$narrator" \
        ${bg_args[@]+"${bg_args[@]}"}
    run_tool transcript "$scripts/verify.sh" "$out/index.html"
    echo "transcript: ok"
}

stage_script
clear_stale
stage_workspace
stage_scene
stage_narration
stage_timeline
stage_guard
stage_background
stage_render
stage_checks
stage_transcript
exit 0
