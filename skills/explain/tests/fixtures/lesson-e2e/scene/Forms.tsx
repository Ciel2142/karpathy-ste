// The artifact card: a document with a folded corner and the word "artifact" in it. Of the three forms of
// the worked example, the clip keeps only this one. Film gives its place, its colours and its opacity.
import type { ReactElement } from "react";
import { Sans } from "../kit";

const STROKE = 2.5;
const FOLD = 16; // the folded corner
const LABEL_SIZE = 22;

// The middle and the size of a document.
export type Box = { cx: number; cy: number; w: number; h: number };

export function Document(props: {
  box: Box;
  stroke: string;
  fill: string;
  opacity: number;
  label: string;
}): ReactElement | null {
  const { box, stroke, fill, opacity, label } = props;
  if (opacity <= 0) return null;
  const x0 = box.cx - box.w / 2;
  const y0 = box.cy - box.h / 2;
  const x1 = x0 + box.w;
  const y1 = y0 + box.h;
  return (
    <g opacity={opacity}>
      <path
        d={`M ${x0} ${y0} L ${x1 - FOLD} ${y0} L ${x1} ${y0 + FOLD} L ${x1} ${y1} L ${x0} ${y1} Z`}
        fill={fill}
        stroke={stroke}
        strokeWidth={STROKE}
        strokeLinejoin="round"
      />
      <path
        d={`M ${x1 - FOLD} ${y0} L ${x1 - FOLD} ${y0 + FOLD} L ${x1} ${y0 + FOLD}`}
        fill="none"
        stroke={stroke}
        strokeWidth={STROKE}
        strokeLinejoin="round"
      />
      <Sans x={box.cx} y={box.cy + 8} size={LABEL_SIZE} text={label} anchor="middle" />
    </g>
  );
}
