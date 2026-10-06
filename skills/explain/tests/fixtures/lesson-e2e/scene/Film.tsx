// The fixture clip of the lesson E2E: three scenes of the worked example (subject, gates and handoff), on
// one picture. The prompt is typed and the pipeline is sketched with the artifact card at its start; the
// line is drawn through the four gates and each gate is named; the checks run, citations fails and then
// passes, and the card moves past the handoff. Each text is 19 px or more (the floor of a clip), and the one
// text in C.muted, the handoff label, is 22 px.
//
// Every motion starts at a mark of `at`. A number written here is a length in frames, never a position in
// time. This file holds the timing; the other files of the directory draw.
import type { ReactElement } from "react";
import { useCurrentFrame } from "remotion";
import { C, lin, mixColor, p } from "../kit";
import { Document } from "./Forms";
import { GATES, Pipeline, READY_CX, SLOT } from "./Pipeline";
import type { GateLook } from "./Pipeline";
import { COMMAND, Prompt } from "./Prompt";
import type { Props } from "./script.gen";

const SUBJECT = "skills/explain"; // the subject of the script
const PER_CHAR = 1.25; // frames to type one character
const FADE = 12;
const MOVE = 20;
const STAGGER = 5; // frames between the gates of one motion
const TURN = 7; // frames between two checks of one run, and to draw the mark of one: one after the other
const FAILING = 2; // the gate of the check that fails in handoff: citations
const LEAVE = 28; // frames for the card to cross from its place to past the handoff

export function Film(props: Props): ReactElement {
  const { at } = props;
  const frame = useCurrentFrame();
  // The progress, 0 to 1, of an eased motion of `len` frames from `start`.
  const ease = (start: number, len: number): number => p(frame, start, len);
  // The characters of `text` typed from `start`.
  const typedOf = (text: string, start: number): number => {
    const n = Array.from(text).length;
    return Math.floor(lin(frame, start, n * PER_CHAR) * n);
  };

  // subject: "/explain" is typed as the voice starts and the subject, in yellow, as the voice names it.
  // Then the pipeline is sketched: the empty place of the artifact, four checks and the handoff. The card
  // comes into the empty place as the voice says "artifact".
  const command = typedOf(COMMAND, at("subject"));
  const subjectAt = at("subject", { word: "subject" });
  const typed = typedOf(SUBJECT, subjectAt);
  const caretEnd = subjectAt + Array.from(SUBJECT).length * PER_CHAR + FADE;
  const caret = ease(at("subject"), 2) * (1 - ease(caretEnd, 6));
  const sketch = at("subject", { sentence: 2 });
  const slotIn = ease(sketch, 8);
  const ringIn = GATES.map((_, k) => ease(sketch + (k + 1) * STAGGER, 8));
  const handoffIn = ease(sketch + (GATES.length + 1) * STAGGER, 8);
  const cardIn = ease(at("subject", { word: "artifact" }), FADE);

  // gates: the line is drawn from the card through the gates, in order. Then each gate is named.
  const line = ease(at("gates"), MOVE);
  // Gate k lights as the tip of the line passes it: at (k + 1) / 5 of the line, give or take 4%.
  const reached = (k: number): number => lin(line, (k + 1) / (GATES.length + 1) - 0.04, 0.08);
  const named = GATES.map((gate) => ease(at("gates", { word: gate.name }), 8));

  // handoff: the checks run in turn, left to right. Self-contained and render pass (a green check),
  // citations fails (the gate turns red and takes a red cross), and the run goes on: prose passes after it.
  // Then citations passes too: its cross gives way to a green check, so all four pass. The card moves past
  // the handoff and turns green, and the empty place it left comes back at the start of the line.
  const ran = GATES.map((_, k) => ease(at("handoff") + k * TURN, TURN));
  const fixAt = at("handoff", { sentence: 2 });
  const fixed = ease(fixAt, 8);
  const passed = GATES.map((_, k) => (k === FAILING ? ease(fixAt + 4, 10) : ran[k]));
  const leave = ease(fixAt + 4, LEAVE);
  const slotBack = ease(fixAt + 14, 10);
  const ready = ease(fixAt + 18, 10);

  // The look of each gate: muted until the line reaches it, red while it fails, green once it passed.
  const tint = (colour: string): string => mixColor(C.bg, colour, 0.16);
  const gates: GateLook[] = GATES.map((_, k) => {
    const lit = mixColor(C.line, C.text, reached(k));
    const failed = k === FAILING ? ran[k] : 0;
    const green = k === FAILING ? fixed : passed[k];
    return {
      ring: ringIn[k],
      stroke: mixColor(mixColor(lit, C.red, failed), C.green, green),
      fill: mixColor(mixColor(C.bg, tint(C.red), failed), tint(C.green), green),
      label: named[k],
      check: passed[k],
      cross: failed,
      crossOpacity: 1 - fixed,
    };
  });

  // The artifact card at the start of the line, then past the handoff.
  const box = { ...SLOT, cx: SLOT.cx + (READY_CX - SLOT.cx) * leave };
  const cardStroke = mixColor(C.text, C.green, ready);
  const cardFill = mixColor(C.panel, mixColor(C.panel, C.green, 0.2), ready);

  return (
    <g>
      <Pipeline slot={slotIn * (1 - cardIn) + slotBack} line={line} handoff={handoffIn} gates={gates} />
      <Document box={box} stroke={cardStroke} fill={cardFill} opacity={cardIn} label="artifact" />
      <Prompt subject={SUBJECT} command={command} typed={typed} caret={caret} />
    </g>
  );
}
