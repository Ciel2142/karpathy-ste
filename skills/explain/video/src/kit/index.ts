// The one import of a film scene: `import { ... } from "../kit"`. It lists, name by name, what a scene may
// use: the palette and the motion helpers, the text and stroke components, the code card with its two
// position helpers, and the types of their arguments. It lists nothing else, so a scene that reaches for
// what the pipeline alone uses (`makeAt`, `MarkScene`, `sourceFromDisk`, `requireFromDisk`) or for an
// internal of a kit file (the grid arithmetic of mono.ts, `MonoRun`) does not compile.
import type { At } from "./marks";
import type { Source } from "./source";

export { C, MONO, SANS, STAGE, MIN_TEXT } from "./palette";
export { p, lin, lerp, mix, mixColor } from "./motion";
export type { Pt } from "./motion";
export type { Where, At } from "./marks";
export type { Source } from "./source";
export { Mono, Sans } from "./text";
export { Draw, Mark } from "./draw";
export { CodeCard, colX, lineY } from "./code";
export type { Band, Card, Tint } from "./code";

// What the stage hands a scene: `at` times a motion from the narration, `sources[id]` is a source that the
// pipeline read from disk, one for each id the script declares. `S` is the ids of the scenes, `R` the ids
// of the sources.
export type FilmProps<S extends string, R extends string> = {
  at: At<S>;
  sources: Record<R, Source>;
};
