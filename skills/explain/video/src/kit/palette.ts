// The colours, fonts and stage of a film scene. A film is a bespoke SVG drawn on the same dark
// ground as the rest of the video rung, so every scene takes its values from here instead of
// writing literals: the picture then matches the explainer scenes and the other films.
//
// This file is plain TypeScript with no imports, so Node can run it directly: the Python tests
// import it without a bundler.

// The nine colours of the film ground. A scene may mix two of them with mixColor (motion.ts),
// which reads "#rrggbb", so each value here stays in that form.
export const C: Record<
  "bg" | "panel" | "text" | "muted" | "line" | "blue" | "green" | "yellow" | "red",
  string
> = {
  bg: "#0f1115",
  panel: "#141820",
  text: "#ece9e4",
  muted: "#8b919b",
  line: "#4b525d",
  blue: "#58c4dd",
  green: "#83c167",
  yellow: "#f4d345",
  red: "#fc6255",
};

export const MONO = 'ui-monospace, "SF Mono", Menlo, monospace';
export const SANS = '-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif';

// The frame a film renders in: 1280 x 720 at 30 fps.
export const STAGE = { width: 1280, height: 720, fps: 30 } as const;

// The smallest text size, in px, that a film scene may draw.
export const MIN_TEXT = 14;
