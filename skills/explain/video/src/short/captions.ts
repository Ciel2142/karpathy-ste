// Which caption chunk and which word of it show at a frame. Pure, with a type-only import, so
// Node can run this file directly: the Python tests import it without a bundler.
//
// Frames are relative to the scene start, as in the timeline's `captions`.

import type { CaptionChunk } from "../types";

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
