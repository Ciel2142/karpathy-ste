#!/bin/bash
# capture_landscape_baseline.sh: render the full video template from a git ref and keep its
# stills as the baseline of tests/test_landscape_regression.py. Run it BEFORE the first edit
# of the scene components, from the commit that still has the old layout.
#
#   capture_landscape_baseline.sh <ref> [--force]
#   env EXPLAIN_VIDEO_WORKSPACE   workspace root (default $HOME/karpathy/video-workspace)
#
#   <ws>/regression/landscape-baseline/
#     script.json         templates/video-script.json of this checkout (all five components),
#                         provenance.root = this checkout's skills/explain
#     audio/              the narration the baseline was rendered with; the test reuses it
#     build/timeline.json the timeline of that render
#     review/*.png        the stills of that render
#     BASE                the hash of <ref>, written last: no BASE, no baseline
#
#   exit 0  the baseline is captured
#   exit 1  the render of <ref> failed (no BASE is written)
#   exit 2  usage, an unknown <ref>, or a baseline with a BASE already exists and --force is
#           not given (re-capturing from a tree that already has the refactor would make the
#           regression compare the new code with itself)
#
# <ref> is rendered from a detached git worktree in a temp dir, removed on every exit path:
# video-workspace.sh syncs that worktree's video/ into <ws>/app, so the sources of <ref> are
# the ones that draw. With --force the old baseline is emptied first. The Remotion workspace
# is left holding the sources of <ref> until the next render.sh run syncs its own.

set -eu

usage() {
    echo "usage: capture_landscape_baseline.sh <ref> [--force]" >&2
    exit 2
}

ref=""
force=""
while [ $# -gt 0 ]; do
    case "$1" in
        --force)
            force=1
            shift
            ;;
        -*) usage ;;
        *)
            [ -z "$ref" ] || usage
            ref="$1"
            shift
            ;;
    esac
done
[ -n "$ref" ] || usage

# The skill may be reached through a symlink (~/.claude/skills/explain); pwd -P resolves it.
self="$0"
case "$self" in */*) ;; *) self="./$self" ;; esac
tests=$(cd "${self%/*}" && pwd -P)
skill="${tests%/*}"
ws="${EXPLAIN_VIDEO_WORKSPACE:-$HOME/karpathy/video-workspace}"
baseline="$ws/regression/landscape-baseline"

hash=$(git -C "$skill" rev-parse --verify --quiet "$ref^{commit}") || {
    echo "capture_landscape_baseline.sh: unknown ref: $ref" >&2
    exit 2
}
if [ -f "$baseline/BASE" ] && [ -z "$force" ]; then
    echo "capture_landscape_baseline.sh: a baseline from $(< "$baseline/BASE") exists at $baseline; pass --force to replace it" >&2
    exit 2
fi

tmp=""
cleanup() {
    [ -z "$tmp" ] || git -C "$skill" worktree remove --force "$tmp" > /dev/null 2>&1 || true
    [ -z "$tmp" ] || rm -rf "$tmp"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

tmp=$(mktemp -d "${TMPDIR:-/tmp}/landscape-baseline.XXXXXX")
git -C "$skill" worktree add --quiet --detach "$tmp" "$hash"

mkdir -p "$baseline"
find "$baseline" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
python3 - "$skill" "$baseline/script.json" <<'PY'
import json, sys
root, out = sys.argv[1:3]
with open(root + "/templates/video-script.json", encoding="utf-8") as f:
    script = json.load(f)
script["provenance"]["root"] = root
with open(out, "w", encoding="utf-8") as f:
    json.dump(script, f, indent=2)
    f.write("\n")
PY

if ! "$tmp/skills/explain/scripts/render.sh" "$baseline" --engine say; then
    echo "capture_landscape_baseline.sh: the render of $hash failed" >&2
    exit 1
fi

# Keep only what the regression reads.
find "$baseline" -mindepth 1 -maxdepth 1 ! -name script.json ! -name audio ! -name build ! -name review \
    -exec rm -rf {} +
find "$baseline/build" -mindepth 1 -maxdepth 1 ! -name timeline.json -exec rm -rf {} +
printf '%s\n' "$hash" > "$baseline/BASE"
echo "baseline: ok $baseline (from $hash)"
exit 0
