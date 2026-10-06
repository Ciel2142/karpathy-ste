#!/bin/bash
# narrate.sh: one WAV per scene of a video script. The first-choice engine is Kokoro af_heart for
# lang en and Silero xenia for lang ru; macOS say is the labelled fallback (spec: video rung).
#
#   narrate.sh <script.json> <audio-dir> [--engine kokoro|silero|say] [--speed <d.d>]
#   --engine  kokoro, silero or say; without it, the engine that narrate.py --check prints for the
#             script's lang (kokoro for en, silero for ru). say speaks either lang, with the default
#             voice for en and Milena for ru; it runs at once and is not labelled a fallback
#   --speed   one digit, a full stop, one digit, from 0.5 to 2.0 (default 1.0); every engine and
#             the say fallback use it (say at 175 wpm times the speed, no -r at 1.0); lang ru
#             narrates at 1.0 only
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   exit 0  every scene has a WAV and <audio-dir>/durations.json is written
#   exit 1  the say path failed too (a "narration: FAIL <cause>" line says why), python3 is not on
#           PATH, or narrate.py --check exited with a code other than 0 and 2 (its output is printed)
#   exit 2  usage: missing argument, unknown --engine, bad --speed, no script file; or narrate.py
#           --check exited 2 (a script error: its "narration: FAIL" lines are printed)
#
# python3 is needed first: narrate.py --check reads the script (standard library only, no model
# loaded) and prints the engine to run. Its exit 2 and its other failures end the run with no
# fallback. Its output must be exactly kokoro, silero or say, else "narration: FAIL narrate.py
# --check printed no engine" and exit 1.
#
# stdout: one "narration: <id> <engine> <seconds> s (synthesized|reused)" line per scene.
# When the first-choice engine cannot run, the first stdout line is
#   narration: FALLBACK say (<cause>)
# with <cause> one of: models missing: <name> (kokoro-v1.0.onnx, voices-v1.0.bin or v5_3_ru.pt) |
# uv not found | the text after "narration: FAIL " of the last such line on the stdout of the
# engine's run (kokoro clip failed: <scene id>: <message> | silero clip failed: <scene id>:
# <message> | model sha mismatch: v5_3_ru.pt | a wrong sample rate | ...) | uv run failed: <last
# stderr line> (else uv run failed: exit <code>). Any non-zero exit of the engine's run falls
# back, uv's own exit 2 too. The same cause goes into durations.json ("fallback"), which
# render.sh copies into the transcript's Narrator row.

set -eu

usage() {
    echo "usage: narrate.sh <script.json> <audio-dir> [--engine kokoro|silero|say] [--speed <d.d>]" >&2
    exit 2
}

script=""
audio=""
engine=""
speed="1.0"
while [ $# -gt 0 ]; do
    case "$1" in
        --engine)
            [ $# -ge 2 ] || usage
            engine="$2"
            shift 2
            ;;
        --speed)
            [ $# -ge 2 ] || usage
            speed="$2"
            shift 2
            ;;
        -*) usage ;;
        *)
            if [ -z "$script" ]; then
                script="$1"
            elif [ -z "$audio" ]; then
                audio="$1"
            else
                usage
            fi
            shift
            ;;
    esac
done
[ -n "$script" ] && [ -n "$audio" ] || usage
case "$engine" in "" | kokoro | silero | say) ;; *) usage ;; esac
# --speed: <digit>.<digit> from 0.5 to 2.0, checked on the two digits read as 5..20.
case "$speed" in [0-9].[0-9]) ;; *) usage ;; esac
tenths="${speed%.*}${speed#*.}"
{ [ "$tenths" -ge 5 ] && [ "$tenths" -le 20 ]; } || usage
if [ ! -f "$script" ]; then
    echo "narrate.sh: no such script: $script" >&2
    exit 2
fi

# The skill may be reached through a symlink (~/.claude/skills/explain); pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
scripts=$(cd "${self%/*}" && pwd -P)
narrate_py="$scripts/../video/narrate.py"
workspace="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
models="$workspace/models"

run_say() {
    if [ $# -gt 0 ]; then
        echo "narration: FALLBACK say ($1)"
        exec python3 "$narrate_py" --engine say --fallback "$1" --speed "$speed" "$script" "$audio"
    fi
    exec python3 "$narrate_py" --engine say --speed "$speed" "$script" "$audio"
}

# narrate.py --check first: it validates the script and prints the engine to run. Its stdout is
# captured; its stderr stays on the terminal.
if ! command -v python3 > /dev/null 2>&1; then
    echo "narration: FAIL python3 not found"
    exit 1
fi
check_rc=0
if [ -n "$engine" ]; then
    checked=$(python3 "$narrate_py" --check --engine "$engine" --speed "$speed" "$script") || check_rc=$?
else
    checked=$(python3 "$narrate_py" --check --speed "$speed" "$script") || check_rc=$?
fi
if [ "$check_rc" -ne 0 ]; then
    [ -z "$checked" ] || printf '%s\n' "$checked"
    [ "$check_rc" -eq 2 ] && exit 2
    exit 1
fi
case "$checked" in
    kokoro | silero | say) engine="$checked" ;;
    *)
        echo "narration: FAIL narrate.py --check printed no engine"
        exit 1
        ;;
esac

[ "$engine" = "say" ] && run_say

case "$engine" in
    kokoro) model_files="kokoro-v1.0.onnx voices-v1.0.bin" ;;
    silero) model_files="v5_3_ru.pt" ;;
esac
for name in $model_files; do
    [ -f "$models/$name" ] || run_say "models missing: $name"
done
command -v uv > /dev/null 2>&1 || run_say "uv not found"

err=$(mktemp)
trap 'rm -f "$err"' EXIT
rc=0
if [ "$engine" = "silero" ]; then
    out=$(uv run --python 3.12 \
        --with torch==2.14.1 --with numpy==2.5.3 \
        python3 -W ignore::SyntaxWarning "$narrate_py" --engine silero --models "$models" --speed "$speed" "$script" "$audio" 2> "$err") || rc=$?
else
    out=$(uv run --python 3.12 \
        --with kokoro-onnx==0.6.1 --with onnxruntime==1.30.0 --with soundfile==0.14.0 \
        --with numpy==2.5.3 --with espeakng-loader==0.2.4 \
        python3 "$narrate_py" --engine kokoro --models "$models" --speed "$speed" "$script" "$audio" 2> "$err") || rc=$?
fi

last=""
while IFS= read -r line; do
    [ -n "$line" ] && last="$line"
done < "$err"
rm -f "$err"   # before any exec: exec skips the EXIT trap

if [ "$rc" -eq 0 ]; then
    printf '%s\n' "$out"
    exit 0
fi

# Any other exit falls back. narrate.py ends a failed run with "narration: FAIL <cause>" on stdout;
# that cause is the fallback label. uv's own failures print none, so the label is its last stderr line.
cause=""
while IFS= read -r line; do
    case "$line" in "narration: FAIL "*) cause="${line#narration: FAIL }" ;; esac
done <<< "$out"
run_say "${cause:-uv run failed: ${last:-exit $rc}}"
