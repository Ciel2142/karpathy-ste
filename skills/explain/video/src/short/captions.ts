// Which caption chunk and which word of it show at a frame. Pure, with a type-only import, so
// Node can run this file directly: the Python tests import it without a bundler.
//
// Frames are relative to the scene start, as in the timeline's `captions`.

import type { CaptionChunk } from "../types";

// The full caption size, and the number of characters of this size that fit the band on one line
// (about 46 px a bold character: 1000 px / 46 is 21, rounded down to 20 as a margin). The chunk
// cap `captionChars` of formats.json must not pass CAPTION_LINE_CHARS. A text that is longer
// than that (a code name that is alone in its chunk) is drawn smaller, so it still fits.
export const CAPTION_FONT = 76;
export const CAPTION_LINE_CHARS = 20;

// The font size, in px, for a caption text: CAPTION_FONT when it fits one line, else scaled down
// so that its width stays that of CAPTION_LINE_CHARS characters (rounded down).
export function captionFontSize(text: string): number {
  if (text.length <= CAPTION_LINE_CHARS) return CAPTION_FONT;
  return Math.floor((CAPTION_FONT * CAPTION_LINE_CHARS) / text.length);
}

// The chunk with `from <= frame < to`, and the index of its last word with `from <= frame`.
// A zero-length chunk (`from == to`, a word under about 17 ms) never matches, so it never
// shows. Before the first chunk, after the last, or in a gap between two there is no caption
// (null). At most one chunk is returned: the first match, if chunks ever overlapped.
export function activeCaption(
  captions: CaptionChunk[],
  frame: number,
): { chunk: CaptionChunk; word: number } | null {
  const chunk = captions.find((c) => c.from <= frame && frame < c.to);
  if (chunk === undefined) return null;
  let word = 0;
  for (let i = 0; i < chunk.words.length; i++) {
    if (chunk.words[i].from <= frame) word = i;
  }
  return { chunk, word };
}
