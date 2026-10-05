// The limit of the prose check: a bar of 25 cells, one for each word a descriptive sentence may have. The
// cells fill one after the other and the bar stops green at the last one; the count beside it says how
// many are full. Film gives how full each cell is and how green the bar is.
import type { ReactElement } from "react";
import { C, Mono, Sans, mixColor } from "../kit";
import { GATES } from "./Pipeline";

export const WORDS = 25;
const CELL = 30;
const GAP = 8;
const HEIGHT = 36;
// The bar hangs from the prose gate (GATES[3]). It is centred on the stage, then moved by at most half the
// step from one cell to the next, so that the cell nearest to the gate is right under it: the line from the
// gate ends on that cell, not in a gap.
const CENTRED = 640 - (WORDS * CELL + (WORDS - 1) * GAP) / 2;
const UNDER_GATE = Math.round((GATES[3].x - CELL / 2 - CENTRED) / (CELL + GAP));
const LEFT = GATES[3].x - CELL / 2 - UNDER_GATE * (CELL + GAP);
export const BAR_TOP = 536;
const COUNT_X = LEFT + WORDS * (CELL + GAP) + 14;
const FILL = 0.6; // how strong the colour of a full cell is against the ground

export function WordBar(props: {
  opacity: number;
  full: (cell: number) => number; // how full cell `cell` (from 0) is, 0 to 1
  green: number;
}): ReactElement | null {
  const { opacity, full, green } = props;
  if (opacity <= 0) return null;
  const cells = Array.from({ length: WORDS }, (_, i) => i);
  const count = cells.filter((i) => full(i) >= 0.5).length;
  const ink = mixColor(C.muted, C.green, green); // the fill of a full cell, at FILL
  return (
    <g opacity={opacity}>
      {cells.map((i) => (
        <rect
          key={i}
          x={LEFT + i * (CELL + GAP)}
          y={BAR_TOP}
          width={CELL}
          height={HEIGHT}
          rx={4}
          fill={mixColor(C.bg, ink, FILL * full(i))}
          stroke={mixColor(C.line, C.green, green)}
          strokeWidth={2}
        />
      ))}
      <Mono
        x={COUNT_X}
        y={BAR_TOP + 27}
        size={26}
        text={String(count)}
        fill={mixColor(C.text, C.green, green)}
        weight={500}
      />
      <Sans x={COUNT_X} y={BAR_TOP + HEIGHT + 24} size={16} text="words" fill={C.muted} />
    </g>
  );
}
