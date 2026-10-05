// The strokes of a film scene. Draw makes a path draw itself: the stroke is one dash as long as the path
// (pathLength counts that length as 1), pushed along by the dash offset, so `t` from 0 to 1 shows the path
// from its start to its end. Mark is a check or a cross drawn that way.
//
// `d` must be one subpath: a second `M` makes the browser restart the dash there, so each subpath would
// count as its own part of the length and the path would be whole before `t` reaches 1. A shape of several
// strokes is several Draws, each over its own part of `t`, as the cross of Mark is.
import type { ReactElement } from "react";
import { C } from "./palette";

export function Draw(props: {
  d: string;
  t: number;
  stroke: string;
  width?: number;
  opacity?: number;
}): ReactElement | null {
  const { d, t, stroke, width = 2, opacity = 1 } = props;
  if (t <= 0 || opacity <= 0) return null;
  return (
    <path
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity={opacity}
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - Math.min(t, 1)}
    />
  );
}

// Both marks are about 16 px wide at scale 1 with the round caps of a stroke of 3, centred on the origin.
// A mark of several strokes draws them one after the other, each over an equal part of `t`.
const MARKS: Record<"check" | "cross", { strokes: string[]; color: string }> = {
  check: { strokes: ["M -6.5 0 L -2 4.5 L 6.5 -4.5"], color: C.green },
  cross: { strokes: ["M -6.5 -6.5 L 6.5 6.5", "M 6.5 -6.5 L -6.5 6.5"], color: C.red },
};

export function Mark(props: {
  kind: "check" | "cross";
  x: number;
  y: number;
  t: number;
  scale?: number;
  opacity?: number;
}): ReactElement {
  const { kind, x, y, t, scale = 1, opacity = 1 } = props;
  const { strokes, color } = MARKS[kind];
  // The opacity belongs to the group, not to the strokes: two strokes that each had it would stack where
  // they cross (a cross at 0.8 would be 0.96 in its middle). The group fades the drawn mark as one.
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`} opacity={opacity}>
      {strokes.map((d, i) => (
        <Draw key={i} d={d} t={t * strokes.length - i} stroke={color} width={3} />
      ))}
    </g>
  );
}
