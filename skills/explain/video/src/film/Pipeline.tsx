// The pipeline of the film: the place of the artifact at the left, the line it travels, the four checks
// (the gates) in their order, and the handoff at the right end. It draws what Film tells it, as progress
// values from 0 to 1 and colours; it reads no frame. The geometry is exported, so that Film puts the
// artifact card on the same line.
import type { ReactElement } from "react";
import { C, Draw, Mark, Sans } from "../kit";

export const LINE_Y = 420;
// The artifact card at the start of the line, and its middle once it is past the handoff.
export const SLOT = { cx: 136, cy: LINE_Y, w: 144, h: 84 };
export const READY_CX = 1144;
export const HANDOFF_X = 1012;

const LINE_START = SLOT.cx + SLOT.w / 2;
const STEP = (HANDOFF_X - LINE_START) / 5; // four gates, evenly between the card and the handoff
const RING = 26;
const LABEL_Y = 482;
// Just below the labels: where a line from a gate down to the panel under the pipeline starts.
export const UNDER_LABELS = LABEL_Y + 14;
const LABEL_SIZE = 20;

// The checks of verify.sh, in the order they run. The narration of scene gates says each name, so Film
// shows a label at the word mark of its name.
export const GATES = ["self-contained", "render", "citations", "prose"].map((name, k) => ({
  name,
  x: LINE_START + (k + 1) * STEP,
}));

// How one gate looks: the ring, its label and the check mark inside it.
export type GateLook = {
  ring: number; // opacity of the ring
  stroke: string;
  fill: string;
  label: number; // opacity of the label
  labelFill: string;
  check: number; // how much of the green check is drawn
};

export function Pipeline(props: {
  slot: number; // opacity of the empty place of the artifact
  line: number; // how much of the line is drawn
  handoff: number; // opacity of the handoff line and its label
  gates: GateLook[];
}): ReactElement {
  const { slot, line, handoff, gates } = props;
  return (
    <g>
      <rect
        x={SLOT.cx - SLOT.w / 2}
        y={SLOT.cy - SLOT.h / 2}
        width={SLOT.w}
        height={SLOT.h}
        rx={8}
        fill="none"
        stroke={C.line}
        strokeWidth={2.5}
        strokeDasharray="8 7"
        opacity={slot}
      />
      <Draw d={`M ${LINE_START} ${LINE_Y} L ${HANDOFF_X} ${LINE_Y}`} t={line} stroke={C.line} width={3} />
      <line
        x1={HANDOFF_X}
        y1={LINE_Y - SLOT.h / 2}
        x2={HANDOFF_X}
        y2={LINE_Y + SLOT.h / 2}
        stroke={C.muted}
        strokeWidth={2.5}
        strokeDasharray="6 6"
        opacity={handoff}
      />
      <Sans
        x={HANDOFF_X}
        y={LABEL_Y}
        size={LABEL_SIZE}
        text="handoff"
        fill={C.muted}
        opacity={handoff}
        anchor="middle"
      />
      {GATES.map((gate, k) => (
        <g key={gate.name}>
          <circle
            cx={gate.x}
            cy={LINE_Y}
            r={RING}
            fill={gates[k].fill}
            stroke={gates[k].stroke}
            strokeWidth={3}
            opacity={gates[k].ring}
          />
          <Mark kind="check" x={gate.x} y={LINE_Y} t={gates[k].check} scale={1.5} />
          <Sans
            x={gate.x}
            y={LABEL_Y}
            size={LABEL_SIZE}
            text={gate.name}
            fill={gates[k].labelFill}
            opacity={gates[k].label}
            anchor="middle"
          />
        </g>
      ))}
    </g>
  );
}
