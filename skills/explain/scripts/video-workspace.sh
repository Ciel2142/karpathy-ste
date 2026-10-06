#!/bin/bash
# video-workspace.sh: set up the Remotion workspace for the explain video rung, outside the
# repo and without global installs. Idempotent; the first run downloads, later runs only check.
#
#   video-workspace.sh [--engine kokoro|silero|say]   (default kokoro)
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   <ws>/app      package.json and package-lock.json of the skill's video/, plus the installed
#                 node_modules and the install logs. Nothing else is written there, and
#                 nothing else in it is touched: no source is synced, so a file that older
#                 code left in <ws>/app or <ws>/bg-stage stays as it was found.
#   <ws>/runs     where render.sh keeps one directory for each running render (a copy of
#                 video/ with node_modules linked to <ws>/app/node_modules); made by render.sh
#   <ws>/backgrounds    the default folder of brainrot background clips (EXPLAIN_BRAINROT_BACKGROUNDS)
#   <ws>/models   the model files: kokoro-v1.0.onnx and voices-v1.0.bin (--engine kokoro) or
#                 v5_3_ru.pt, the Silero model (--engine silero); none for --engine say
#
#   exit 0  the workspace is ready ("workspace: ok <ws>" is the last line)
#   exit 1  a step failed ("workspace: FAIL <step> ..." is the last line)
#   exit 2  usage
#
# Each costly step prints its cost on stdout before it starts:
#   workspace: npm ci (about 55 s, 503 MB)              lock changed or never installed
#   workspace: browser (Chrome Headless Shell, 193 MB)  after each npm ci
#   workspace: download <name> (<size>)                 each missing Kokoro file; v5_3_ru.pt
#                                                       (145 MB) when missing or not the pinned bytes
# and "workspace: downloaded <name>" once that file is checked and in place. curl runs with
# -sS: no progress meter, only its error message. A Kokoro file in place is left alone; the
# Silero file in place is hashed and fetched again when it is not the pinned bytes. Each fetch
# downloads to <name>.<pid>.part, so two runs that fetch at once never write one file, and
# moves the checked file into place with mv. A fetch that stops (exit, HUP, INT, TERM) removes
# its own part file.
# npm ci runs when node_modules/.explain-lock-sha is missing or differs from the sha256 of
# package-lock.json. The stamp is written once npm ci and the browser step both succeeded,
# so a failed browser download is retried on the next run.

set -u

usage() {
    echo "usage: video-workspace.sh [--engine kokoro|silero|say]" >&2
    exit 2
}

engine="kokoro"
while [ $# -gt 0 ]; do
    case "$1" in
        --engine)
            [ $# -ge 2 ] || usage
            engine="$2"
            shift 2
            ;;
        *) usage ;;
    esac
done
case "$engine" in kokoro | silero | say) ;; *) usage ;; esac

# The skill may be reached through a symlink (~/.claude/skills/explain); pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
scripts=$(cd "${self%/*}" && pwd -P)
skill="${scripts%/*}"
ws="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
app="$ws/app"
models="$ws/models"
model_base="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"

fail() {
    echo "workspace: FAIL $1"
    exit 1
}

sha256() {
    local out
    out=$(shasum -a 256 "$1") || return 1
    printf '%s\n' "${out%% *}"
}

# 1. Package files. Only package.json and package-lock.json of video/ are copied to the app. A
# file whose bytes are already the same is not touched: a render that reads the lock file for
# its checksum at that moment sees a whole file. A changed file is copied to a temporary name in
# the app and renamed over the old one, so a reader sees the old file or the new one, never half.
# Nothing else in the app is created, changed or removed, and nothing in <ws>/bg-stage: the
# renders compile in <ws>/runs, and what older code left here is left as found.
mkdir -p "$app" "$models" || fail "mkdir $ws"
mkdir -p "$ws/backgrounds" || fail "mkdir $ws/backgrounds"
for name in package.json package-lock.json; do
    cmp -s "$skill/video/$name" "$app/$name" && continue
    tmp="$app/.$name.$$.tmp"
    if ! cp "$skill/video/$name" "$tmp" || ! mv -f "$tmp" "$app/$name"; then
        rm -f "$tmp"
        fail "copy package files to $app"
    fi
done

# 2 and 3. Dependencies and the headless browser, when the lock file changed.
lock_sha=$(sha256 "$app/package-lock.json") || fail "sha256 $app/package-lock.json"
stamp="$app/node_modules/.explain-lock-sha"
installed=""
[ -f "$stamp" ] && installed=$(< "$stamp")
if [ "$installed" != "$lock_sha" ]; then
    log="$app/npm-ci.log"
    echo "workspace: npm ci (about 55 s, 503 MB)"
    (cd "$app" && npm ci) > "$log" 2>&1 || fail "npm ci (log $log)"
    log="$app/browser-ensure.log"
    echo "workspace: browser (Chrome Headless Shell, 193 MB)"
    (cd "$app" && node_modules/.bin/remotion browser ensure) > "$log" 2>&1 \
        || fail "browser ensure (log $log)"
    printf '%s\n' "$lock_sha" > "$stamp" || fail "write $stamp"
fi

# 4. Model files: download to <name>.<pid>.part (a part file of this run alone), check the
# sha256, then move into place. A file in place is left alone, unless the caller passes
# "recheck": then it is hashed and fetched again when it does not match. While the part file
# exists, EXIT removes it, and HUP, INT and TERM exit 1 so that EXIT runs. Both traps are
# cleared once mv has put the file in place.
fetch_model() {
    local name="$1" size="$2" want="$3" url="$4" recheck="${5:-}" got
    if [ -f "$models/$name" ]; then
        [ "$recheck" = "recheck" ] || return 0
        got=$(sha256 "$models/$name") || got="unreadable"
        [ "$got" = "$want" ] && return 0
    fi
    part_file="$models/$name.$$.part"
    echo "workspace: download $name ($size)"
    trap 'rm -f "$part_file"' EXIT
    trap 'exit 1' HUP INT TERM
    curl -fsSL -o "$part_file" "$url" || fail "download $name"
    got=$(sha256 "$part_file") || got="unreadable"
    [ "$got" = "$want" ] || fail "checksum $name expected $want got $got"
    mv "$part_file" "$models/$name" || fail "mv $part_file"
    trap - EXIT HUP INT TERM
    echo "workspace: downloaded $name"
}

if [ "$engine" = "kokoro" ]; then
    fetch_model kokoro-v1.0.onnx "325 MB" beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a "$model_base/kokoro-v1.0.onnx"
    fetch_model voices-v1.0.bin "28 MB" bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d "$model_base/voices-v1.0.bin"
elif [ "$engine" = "silero" ]; then
    fetch_model v5_3_ru.pt "145 MB" f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c https://models.silero.ai/models/tts/ru/v5_3_ru.pt recheck
fi

echo "workspace: ok $ws"
exit 0
