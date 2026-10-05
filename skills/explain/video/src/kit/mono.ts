// The geometry of the monospace grid a film draws code on. A card holds a gutter of 4 columns for the
// line number, 2 columns of space, then the code; every character advances 0.6 of the font size and
// every row is 1.6 of it. Positions count code points, not UTF-16 units. The text components and the
// code card place and cut text with the functions here, so what they draw and what is measured agree.
//
// This file is plain TypeScript. Its one import is `import type`, which Node erases, so Node can run
// it directly: the Python tests import it without a bundler.
import type { Source } from "./source";

// How far a monospace character advances, as a fraction of the font size.
export const ADVANCE = 0.6;

// The width of `text` set in monospace at `size`: its code points, each one advance wide.
export const monoWidth = (text: string, size: number): number => [...text].length * (ADVANCE * size);

// A code card: its top-left corner, its outer width, and the font size of its code.
export type Card = { x: number; y: number; width: number; size: number };
// A full-width band behind one line of the source.
export type Band = { line: number; color: string; opacity: number };
// A colour on columns `from` up to `to` (code points, from 0) of one line of the source.
export type Tint = { line: number; from: number; to: number; color: string };
// A run of text in one colour (no `color`: the default text colour).
export type Span = { text: string; color?: string };

const PADDING = 16;
const GUTTER = 4; // columns for the line number
const GAP = 2; // columns between the gutter and the code
const ROW = 1.6; // the height of a row, as a fraction of the font size
// Added before a whole-column count is floored, so a card that fits k columns exactly does not
// lose one to rounding error (size 18, width 140: 4 columns, but 3.9999999999999996 in floats).
const SLACK = 1e-9;

// The x of column `index` of the code (from 0) in `card`.
export const colX = (card: Card, index: number): number =>
  card.x + PADDING + (GUTTER + GAP + index) * (ADVANCE * card.size);

// The baseline of source line `line` in `card`. It does not check that the source holds the line.
export const lineY = (card: Card, source: Source, line: number): number =>
  card.y + PADDING + card.size + (line - source.from) * (ROW * card.size);

// How many whole columns of code fit between the first column and the right padding of `card`.
export const fitColumns = (card: Card): number =>
  Math.max(0, Math.floor((card.x + card.width - PADDING - colX(card, 0)) / (ADVANCE * card.size) + SLACK));

// The outer height of a card that shows `lineCount` lines.
export const cardHeight = (card: Card, lineCount: number): number =>
  2 * PADDING + lineCount * (ROW * card.size);

// The colour of code point `index` under `tints`: the last tint that covers it wins.
const tintAt = (tints: readonly Tint[], index: number): string | undefined => {
  let color: string | undefined;
  for (const tint of tints) {
    if (tint.from <= index && index < tint.to) color = tint.color;
  }
  return color;
};

// `text` cut to `columns` code points and split into runs of one colour. A tint is clipped to the cut
// text, a later tint wins where two overlap, and neighbours of one colour are one span. A tint is read
// by its `from`, `to` and `color`: its `line` is for the caller, which picks the tints of this line.
export const lineSpans = (text: string, tints: readonly Tint[], columns: number): Span[] => {
  const chars = Array.from(text).slice(0, Math.max(0, columns));
  const colors = chars.map((_, i) => tintAt(tints, i));
  const spans: Span[] = [];
  let start = 0;
  for (let i = 1; i <= chars.length; i++) {
    if (i === chars.length || colors[i] !== colors[start]) {
      const run = chars.slice(start, i).join("");
      const color = colors[start];
      spans.push(color === undefined ? { text: run } : { text: run, color });
      start = i;
    }
  }
  return spans;
};

// Throws unless `line` is a line number that `source` holds, and names the range it does hold.
export const requireLine = (source: Source, line: number): void => {
  const last = source.from + source.lines.length - 1;
  if (!Number.isInteger(line) || line < source.from || line > last) {
    throw new Error(`CodeCard: line ${line} is outside ${source.path}:${source.from}-${last}`);
  }
};
