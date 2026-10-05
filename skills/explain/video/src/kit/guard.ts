// The guard of a film (spec 7.3): the rules that the text of a checked frame must keep. FilmStage measures
// every <text> of the stage at each frame of the timeline's checkFrames and hands the measures here; a
// frame with a fault ends the guard pass of render.sh with `guardLine` as the message of cancelRender.
// This file is the pipeline's, as makeAt is: a scene does not import it (kit/index.ts does not export it).
//
// A text is measured when it holds a character that is not white space and its opacity (the product of
// the opacities of the element and of its groups up to the stage) is 0.1 or more. Its faults:
//   OFFCANVAS "<t>"            its box passes an edge of the canvas by more than 1 px
//   SMALLTEXT <px> px "<t>"     its size on the canvas is below minText
//   OVERLAP "<a>" | "<b>"      its box and the box of a later text overlap by more than 2 px on both axes
//
// What the guard does not see, so that nobody relies on it: a frame that is not checked; anything that is
// not text, such as a shape over a label; a text of the background colour or behind an opaque shape, which
// is measured as if visible and can only raise a false alarm. Those cases stay with the stills.
//
// This file is plain TypeScript with no imports, so Node can run it directly: the Python tests import it
// without a bundler.

// A box on the canvas, in canvas pixels.
export type Box = { left: number; top: number; right: number; bottom: number };

// One <text> of the stage as FilmStage measured it: its content, its opacity, its size on the canvas in px
// and its box.
export type Measured = { text: string; opacity: number; px: number; box: Box };

const SHOWN_FAULTS = 5; // faults written in the line; the others are counted
const QUOTED = 24; // code points of a text quoted in a fault
const MIN_OPACITY = 0.1;
const EDGE = 1; // px a box may pass an edge of the canvas by
const MARGIN = 2; // px two boxes may overlap by on an axis

// A text as a fault quotes it: each run of white space made one space, trimmed, cut to its first 24 code
// points, with no ellipsis.
export const shortText = (text: string): string =>
  Array.from(text.replace(/\s+/g, " ").trim()).slice(0, QUOTED).join("");

const quoted = (t: Measured): string => `"${shortText(t.text)}"`;

const isMeasured = (t: Measured): boolean => /\S/.test(t.text) && t.opacity >= MIN_OPACITY;

const isOffCanvas = (box: Box, canvas: { width: number; height: number }): boolean =>
  box.left < -EDGE || box.top < -EDGE || box.right > canvas.width + EDGE || box.bottom > canvas.height + EDGE;

// The overlap on an axis is the smaller end minus the larger start.
const overlaps = (a: Box, b: Box): boolean =>
  Math.min(a.right, b.right) - Math.max(a.left, b.left) > MARGIN &&
  Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > MARGIN;

// The faults of one frame, text by text in document order: the text's OFFCANVAS, then its SMALLTEXT, then
// one OVERLAP with each later text that it overlaps, in document order. A text that is not measured takes
// part in no rule.
export const faultsOf = (
  texts: readonly Measured[],
  canvas: { width: number; height: number },
  minText: number,
): string[] => {
  const shown = texts.filter(isMeasured);
  return shown.flatMap((t, k) => [
    ...(isOffCanvas(t.box, canvas) ? [`OFFCANVAS ${quoted(t)}`] : []),
    ...(t.px < minText ? [`SMALLTEXT ${t.px.toFixed(1)} px ${quoted(t)}`] : []),
    ...shown
      .slice(k + 1)
      .filter((later) => overlaps(t.box, later.box))
      .map((later) => `OVERLAP ${quoted(t)} | ${quoted(later)}`),
  ]);
};

// The stage line of a frame with faults: its first five faults joined by "; ", then " (+<n> more)" when
// there are more.
export const guardLine = (frame: number, scene: string, faults: readonly string[]): string => {
  const more = faults.length - SHOWN_FAULTS;
  return (
    `guard: FAIL frame ${frame} (scene ${scene}): ${faults.slice(0, SHOWN_FAULTS).join("; ")}` +
    (more > 0 ? ` (+${more} more)` : "")
  );
};
