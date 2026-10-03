#!/bin/bash
# narrate.sh: one WAV per scene of a video script, Kokoro af_heart first, macOS say as the
# labelled fallback (spec: video rung).
#
#   narrate.sh <script.json> <audio-dir> [--engine kokoro|say]     (default kokoro)
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   exit 0  every scene has a WAV and <audio-dir>/durations.json is written
#   exit 1  the say path failed too (a "narration: FAIL <cause>" line says why)
#   exit 2  usage: missing argument, unknown --engine, no script file
#
# stdout: one "narration: <id> <engine> <seconds> s (synthesized|reused)" line per scene.
# When Kokoro cannot run, the first stdout line is
#   narration: FALLBACK say (<cause>)
# with <cause> one of: models missing: <name> | uv not found | uv run failed: <last stderr
# line> | kokoro clip failed: <scene id>: <message>. The same cause goes into durations.json
# ("fallback"), which render.sh copies into the transcript's Narrator row.
#
# Only builtins run before the uv check, so a PATH without uv (or even dirname) still
# reaches the say fallback.

set -eu

usage() {
    echo "usage: narrate.sh <script.json> <audio-dir> [--engine kokoro|say]" >&2
    exit 2
}

script=""
audio=""
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
case "$engine" in kokoro | say) ;; *) usage ;; esac
if [ ! -f "$script" ]; then
    echo "narrate.sh: no such script: $script" >&2
    exit 2
fi

# The skill is reached through the ~/.claude/skills/explain symlink; pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
scripts=$(cd "${self%/*}" && pwd -P)
narrate_py="$scripts/../video/narrate.py"
workspace="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
models="$workspace/models"

run_say() {
    if ! command -v python3 > /dev/null 2>&1; then
        echo "narration: FAIL python3 not found"
        exit 1
    fi
    if [ $# -gt 0 ]; then
        echo "narration: FALLBACK say ($1)"
        exec python3 "$narrate_py" --engine say --fallback "$1" "$script" "$audio"
    fi
    exec python3 "$narrate_py" --engine say "$script" "$audio"
}

[ "$engine" = "say" ] && run_say

for name in kokoro-v1.0.onnx voices-v1.0.bin; do
    [ -f "$models/$name" ] || run_say "models missing: $name"
done
command -v uv > /dev/null 2>&1 || run_say "uv not found"

err=$(mktemp)
trap 'rm -f "$err"' EXIT
rc=0
out=$(uv run --python 3.12 \
    --with kokoro-onnx==0.6.1 --with onnxruntime==1.30.0 --with soundfile==0.14.0 \
    --with numpy==2.5.3 --with espeakng-loader==0.2.4 \
    python3 "$narrate_py" --engine kokoro --models "$models" "$script" "$audio" 2> "$err") || rc=$?

last=""
while IFS= read -r line; do
    [ -n "$line" ] && last="$line"
done < "$err"
rm -f "$err"   # before any exec: exec skips the EXIT trap

if [ "$rc" -eq 0 ]; then
    printf '%s\n' "$out"
    exit 0
fi

if [ "$rc" -eq 3 ]; then
    # narrate.py ends its stdout with "narration: FAIL <cause>"; the cause is the fallback label.
    cause=""
    while IFS= read -r line; do
        case "$line" in "narration: FAIL "*) cause="${line#narration: FAIL }" ;; esac
    done <<< "$out"
    run_say "${cause:-kokoro clip failed}"
fi

run_say "uv run failed: ${last:-exit $rc}"
