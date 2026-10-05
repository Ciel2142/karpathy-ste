// The strokes of a film scene. Draw makes a path draw itself: the stroke is one dash as long as the path
// (pathLength counts that length as 1), pushed along by the dash offset, so `t` from 0 to 1 shows the path
// from its start to its end. Mark is a check or a cross drawn that way.
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
const MARKS: Record<"check" | "cross", { d: string; stroke: string }> = {
  check: { d: "M -6.5 0 L -2 4.5 L 6.5 -4.5", stroke: C.green },
  cross: { d: "M -6.5 -6.5 L 6.5 6.5 M 6.5 -6.5 L -6.5 6.5", stroke: C.red },
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
  const { d, stroke } = MARKS[kind];
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <Draw d={d} t={t} stroke={stroke} width={3} opacity={opacity} />
    </g>
  );
}
