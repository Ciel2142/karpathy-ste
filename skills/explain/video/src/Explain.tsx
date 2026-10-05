// The composition Explain: it renders a brainrot timeline with Short, which lays out the scenes,
// the captions and the background.
import { Short } from "./short/Short";
import type { Timeline } from "./types";

export function Explain(timeline: Timeline) {
  return <Short {...timeline} />;
}
