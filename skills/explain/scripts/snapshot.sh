#!/bin/bash
# snapshot.sh: render an HTML file to PNG with headless Chrome, then cut review tiles.
#
#   snapshot.sh <input.html> <output.png> [width=1920] [height=1080] [scale=2]
#   env SNAPSHOT_TIMEOUT   seconds the watchdog waits for the PNG (default 60)
#
#   exit 0  the PNG and every tile exist with the asserted sizes
#   exit 1  render failed, timeout, or a size mismatch (message on stderr)
#   exit 2  usage (missing/unreadable input, bad numbers)
#
# The PNG is width*scale x height*scale. Tiles of at most 1920x1080 go to
# <output dir>/review/<stem>-NN.png (row-major, NN from 01). stdout carries one
# "wrote <path> <W>x<H>" line per produced file; everything else goes to stderr.
#
# Reproduced facts this script works around (spec section 5.4):
# - Chrome 154 with a fresh --user-data-dir writes the screenshot and then never
#   exits, and macOS has no timeout(1): Chrome runs in the background in its own
#   process group and a watchdog kills the group once the PNG is complete or the
#   timeout elapses.
# - sips treats --cropOffset 0 0 as "no offset" and crops the centre, and returns
#   the whole image for a crop flush with the bottom edge: the PNG is padded by
#   one pixel on every side and every crop is offset by (y+1) (x+1).

set -u

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TILE_W=1920
TILE_H=1080
PNG_TRAILER="49454e44ae426082"   # IEND chunk type + CRC: the last 8 bytes of a whole PNG

work=""          # temp dir: Chrome profile and the padded copy
chrome_pid=""
chrome_stopped=0
owns_outputs=0   # set once this run starts writing the PNG and tiles
out_abs=""
review=""
stem=""

usage() {
    echo "snapshot.sh: $1" >&2
    echo "usage: snapshot.sh <input.html> <output.png> [width=1920] [height=1080] [scale=2]" >&2
    exit 2
}

fail() {
    echo "snapshot.sh: $1" >&2
    exit 1
}

# A positive decimal integer without a leading zero (bash arithmetic reads 08 as octal).
is_count() {
    case "$1" in
        '' | 0* | *[!0-9]*) return 1 ;;
    esac
    return 0
}

# Kill Chrome's process group, then sweep by profile path until the process table
# stays clear for 3 polls in a row (0.6 s): a helper forked while the group was
# being killed would otherwise escape. Returns 1 if a process survives 5 s.
stop_chrome() {
    [ "$chrome_stopped" -eq 0 ] || return 0
    if [ -n "$chrome_pid" ]; then
        kill -KILL -- "-$chrome_pid" 2>/dev/null
        wait "$chrome_pid" 2>/dev/null
    fi
    [ -n "$work" ] || return 0
    local clear=0 tries=0
    while [ "$clear" -lt 3 ]; do
        [ "$tries" -lt 25 ] || return 1
        if pgrep -f "$work" >/dev/null 2>&1; then
            pkill -KILL -f "$work" 2>/dev/null
            clear=0
        else
            clear=$((clear + 1))
        fi
        sleep 0.2
        tries=$((tries + 1))
    done
    chrome_stopped=1
}

cleanup() {
    local status=$?
    trap - EXIT
    trap '' PIPE   # stderr may be gone; finish the cleanup regardless
    stop_chrome || echo "snapshot.sh: Chrome processes survived the kill: $work" >&2
    [ -n "$work" ] && rm -rf "$work"
    if [ "$status" -ne 0 ] && [ "$owns_outputs" -eq 1 ]; then
        rm -f "$out_abs"
        remove_tiles
    fi
    exit "$status"
}

remove_tiles() {
    [ -n "$review" ] && [ -d "$review" ] || return 0
    rm -f "$review/$stem"-[0-9][0-9].png "$review/$stem"-[0-9][0-9][0-9].png
}

dims() {
    sips -g pixelWidth -g pixelHeight "$1" 2>/dev/null |
        awk '/pixelWidth:/ { w = $2 } /pixelHeight:/ { h = $2 } END { if (w && h) print w "x" h }'
}

expect_size() {
    local got
    got=$(dims "$1")
    [ "$got" = "$2" ] || fail "size mismatch: $1 is ${got:-unreadable}, expected $2"
}

png_complete() {
    [ -s "$1" ] || return 1
    [ "$(tail -c 8 "$1" | od -An -tx1 | tr -d ' \n')" = "$PNG_TRAILER" ]
}

# Percent-encode the characters that would end or corrupt a file:// URL path.
file_url() {
    local p=$1
    p=${p//\%/%25}
    p=${p// /%20}
    p=${p//\#/%23}
    p=${p//\?/%3F}
    echo "file://$p"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 141' PIPE
trap 'exit 143' TERM

# --- arguments ---------------------------------------------------------------

[ "$#" -ge 2 ] && [ "$#" -le 5 ] || usage "expected 2 to 5 arguments, got $#"
input=$1
output=$2
width=${3:-1920}
height=${4:-1080}
scale=${5:-2}
timeout=${SNAPSHOT_TIMEOUT:-60}

[ -f "$input" ] && [ -r "$input" ] || usage "input is not a readable file: $input"
case "$output" in
    *.png) ;;
    *) usage "output must end in .png: $output" ;;
esac
is_count "$width" || usage "width must be a positive integer: $width"
is_count "$height" || usage "height must be a positive integer: $height"
is_count "$scale" || usage "scale must be a positive integer: $scale"
is_count "$timeout" || usage "SNAPSHOT_TIMEOUT must be a positive integer: $timeout"
[ -x "$CHROME" ] || fail "Chrome not found: $CHROME"

input_abs="$(cd "$(dirname "$input")" && pwd -P)/$(basename "$input")"
out_dir=$(dirname "$output")
mkdir -p "$out_dir" || fail "cannot create output directory: $out_dir"
out_dir=$(cd "$out_dir" && pwd -P)
out_abs="$out_dir/$(basename "$output")"
stem=$(basename "$output" .png)
review="$out_dir/review"
png_w=$((width * scale))
png_h=$((height * scale))

# --- render ------------------------------------------------------------------

tmp_base=${TMPDIR:-/tmp}
work=$(mktemp -d "${tmp_base%/}/snapshot.XXXXXX") || fail "cannot create a temp directory"
owns_outputs=1
rm -f "$out_abs"   # a stale PNG would satisfy the watchdog at once

set -m   # job control: the background job gets its own process group
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --window-size="$width,$height" --force-device-scale-factor="$scale" \
    --user-data-dir="$work/profile" --screenshot="$out_abs" \
    "$(file_url "$input_abs")" >/dev/null 2>&1 &
chrome_pid=$!
set +m

polls=0
max_polls=$((timeout * 5))   # one poll every 0.2 s
until png_complete "$out_abs"; do
    [ "$polls" -lt "$max_polls" ] ||
        fail "timeout: Chrome wrote no PNG within ${timeout}s for $input_abs"
    sleep 0.2
    polls=$((polls + 1))
done
stop_chrome || fail "Chrome processes survived the kill: $work"

expect_size "$out_abs" "${png_w}x${png_h}"
wrote="wrote $out_abs ${png_w}x${png_h}"

# --- review tiles ------------------------------------------------------------

mkdir -p "$review" || fail "cannot create review directory: $review"
remove_tiles
padded="$work/padded.png"
sips --padToHeightWidth $((png_h + 2)) $((png_w + 2)) "$out_abs" --out "$padded" >/dev/null ||
    fail "sips could not pad $out_abs"
expect_size "$padded" "$((png_w + 2))x$((png_h + 2))"

n=0
y=0
while [ "$y" -lt "$png_h" ]; do
    tile_h=$TILE_H
    [ $((png_h - y)) -lt "$tile_h" ] && tile_h=$((png_h - y))
    x=0
    while [ "$x" -lt "$png_w" ]; do
        tile_w=$TILE_W
        [ $((png_w - x)) -lt "$tile_w" ] && tile_w=$((png_w - x))
        n=$((n + 1))
        tile="$review/$(printf '%s-%02d.png' "$stem" "$n")"
        sips -c "$tile_h" "$tile_w" --cropOffset $((y + 1)) $((x + 1)) "$padded" --out "$tile" >/dev/null ||
            fail "sips could not crop $tile"
        expect_size "$tile" "${tile_w}x${tile_h}"
        wrote="$wrote
wrote $tile ${tile_w}x${tile_h}"
        x=$((x + TILE_W))
    done
    y=$((y + TILE_H))
done

echo "$wrote"
