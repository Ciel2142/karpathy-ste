#!/bin/bash
# video-workspace.sh: set up the Remotion workspace for the explain video rung, outside the
# repo and without global installs. Idempotent; the first run downloads, later runs only sync.
#
#   video-workspace.sh [--engine kokoro|say]          (default kokoro)
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   <ws>/app      the synced video/ sources plus node_modules (public/ is left alone)
#   <ws>/bg-stage where pick_background.py stages the brainrot background clip; <ws>/app/public/bg
#                 is the relative symlink ../../bg-stage to it, so it must exist (an empty one is
#                 made here). It lies beside the app, where no version's sync reaches it.
#   <ws>/backgrounds    the default folder of brainrot background clips (EXPLAIN_BRAINROT_BACKGROUNDS)
#   <ws>/models   the Kokoro model files (--engine kokoro only)
#
#   exit 0  the workspace is ready ("workspace: ok <ws>" is the last line)
#   exit 1  a step failed ("workspace: FAIL <step> ..." is the last line)
#   exit 2  usage
#
# Each costly step prints its cost on stdout before it starts:
#   workspace: npm ci (about 55 s, 503 MB)              lock changed or never installed
#   workspace: browser (Chrome Headless Shell, 193 MB)  after each npm ci
#   workspace: download <name> (<size>)                 each missing Kokoro file
# and "workspace: downloaded <name>" once that file is checked and in place. curl runs with
# -sS: no progress meter, only its error message.
# npm ci runs when node_modules/.explain-lock-sha is missing or differs from the sha256 of
# package-lock.json. The stamp is written once npm ci and the browser step both succeeded,
# so a failed browser download is retried on the next run.

set -u

usage() {
    echo "usage: video-workspace.sh [--engine kokoro|say]" >&2
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
case "$engine" in kokoro | say) ;; *) usage ;; esac

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

# 1. Sources. node_modules/ and public/ (the render's audio) stay as they are; anything else in
# the app that video/ lacks is deleted, a stage left in <app>/bg-stage by earlier versions too.
# The stage and the clip folder are made beside the app so that the public/bg symlink the picker
# keeps never dangles: a dangling link in public/ breaks the bundler, and with it every render.
# For the same reason a public/bg link that does not resolve (the absolute link to
# <app>/bg-stage of earlier versions, or a stage deleted by hand) is removed; the picker makes
# it again. A link that resolves, or a real directory, is left alone, and no link is followed.
mkdir -p "$app" "$models" || fail "mkdir $ws"
rsync -a --delete --exclude /node_modules/ --exclude /public/ \
    "$skill/video/" "$app/" || fail "sync $skill/video/ to $app/"
mkdir -p "$ws/backgrounds" || fail "mkdir $ws/backgrounds"
mkdir -p "$ws/bg-stage" || fail "mkdir $ws/bg-stage"
if [ -L "$app/public/bg" ] && [ ! -e "$app/public/bg" ]; then
    rm -f "$app/public/bg" || fail "rm dangling link $app/public/bg"
fi

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

# 4. Kokoro model files: download to <name>.part, check the sha256, then move into place.
fetch_model() {
    local name="$1" size="$2" want="$3" part="$models/$1.part" got
    [ -f "$models/$name" ] && return 0
    echo "workspace: download $name ($size)"
    if ! curl -fsSL -o "$part" "$model_base/$name"; then
        rm -f "$part"
        fail "download $name"
    fi
    got=$(sha256 "$part") || got="unreadable"
    if [ "$got" != "$want" ]; then
        rm -f "$part"
        fail "checksum $name expected $want got $got"
    fi
    mv "$part" "$models/$name" || fail "mv $part"
    echo "workspace: downloaded $name"
}

if [ "$engine" = "kokoro" ]; then
    fetch_model kokoro-v1.0.onnx "325 MB" beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a
    fetch_model voices-v1.0.bin "28 MB" bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d
fi

echo "workspace: ok $ws"
exit 0
