// The motion helpers of a film scene. A scene reads the frame once and passes it in, so every
// helper here is a pure function of numbers: p and lin turn a frame into a 0..1 progress, lerp,
// mix and mixColor spend that progress on a number, a point or a colour.
//
// This file is plain TypeScript with no imports, so Node can run it directly: the Python tests
// import it without a bundler.

// The fraction of `len` frames done at `frame` since `start`, clamped to 0..1. A `len` of 0 or
// less is a step: 0 before `start`, 1 from `start` on.
const done = (frame: number, start: number, len: number): number => {
  if (len <= 0) return frame >= start ? 1 : 0;
  return Math.min(1, Math.max(0, (frame - start) / len));
};

// Eased progress: 0 up to `start`, the cubic in-out curve over `len` frames, then 1.
export const p = (frame: number, start: number, len: number): number => {
  const u = done(frame, start, len);
  return u < 0.5 ? 4 * u * u * u : 1 - (2 - 2 * u) ** 3 / 2;
};

// Linear progress: the same ramp as p, without the easing.
export const lin = (frame: number, start: number, len: number): number => done(frame, start, len);

// a + (b - a) * t. It does not clamp, so a t outside 0..1 runs past the ends.
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export type Pt = { x: number; y: number };

export const mix = (a: Pt, b: Pt, t: number): Pt => ({ x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) });

const HEX = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i;
const RGB = /^rgb\((\d{1,3}), (\d{1,3}), (\d{1,3})\)$/;

// The channels of "#rrggbb" (either case) or "rgb(r, g, b)"; anything else is refused.
const channels = (colour: string): number[] => {
  const hex = HEX.exec(colour);
  if (hex) return [hex[1], hex[2], hex[3]].map((h) => parseInt(h, 16));
  const rgb = RGB.exec(colour);
  if (rgb) return [rgb[1], rgb[2], rgb[3]].map(Number);
  throw new Error(`mixColor: not a colour: "${colour}"`);
};

// The colour t of the way from a to b, as "rgb(r, g, b)". t is clamped to 0..1, so the ends are
// the two colours themselves; each channel is rounded to the nearest whole number. The result
// is a valid input again.
export const mixColor = (a: string, b: string, t: number): string => {
  const from = channels(a);
  const to = channels(b);
  const k = Math.min(1, Math.max(0, t));
  const [r, g, bl] = from.map((v, i) => Math.round(lerp(v, to[i], k)));
  return `rgb(${r}, ${g}, ${bl})`;
};
