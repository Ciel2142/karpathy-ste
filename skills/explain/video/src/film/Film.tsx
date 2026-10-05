// The worked example: how /explain checks an artifact before handoff. One picture for the whole film: an
// object stays where it was drawn and changes with the narration, and nothing clears the stage. The
// objects are the prompt, the three forms, the artifact card, the pipeline of four gates, the code card
// and the word bar.
//
// Every motion starts at a mark of `at`: at(id) and at(id, { sentence }) where the voice starts a sentence,
// at(id, { word }) about where it says a word. A number written here is a length in frames, never a
// position in time. A motion from a sentence mark ends within about 20 frames, before the middle of the
// sentence, where the stills are cut. This file holds the timing; the other files of the directory draw.
import type { ReactElement } from "react";
import { useCurrentFrame } from "remotion";
import { C, CodeCard, Draw, Mark, Mono, lerp, lin, lineY, mixColor, p } from "../kit";
import type { Card } from "../kit";
import { Document, FormLabel, FORM_X, PAGE, Sheet, Video } from "./Forms";
import { GATES, Pipeline, READY_CX, SLOT, UNDER_LABELS } from "./Pipeline";
import type { GateLook } from "./Pipeline";
import { COMMAND, Prompt } from "./Prompt";
import type { Props } from "./script.gen";
import { BAR_TOP, WORDS, WordBar } from "./WordBar";

const SUBJECT = "skills/explain"; // the subject of the script
const FILE = "index.html"; // the file verify.sh reads
const PER_CHAR = 1.25; // frames to type one character
const FADE = 12;
const MOVE = 20;
const STAGGER = 5; // frames between the gates of one motion
const PER_CELL = 0.6; // frames between two cells of the word bar
const CELL_FILL = 3; // frames to fill one cell

// Line 138 of cite_check.py compares the two normalised strings: columns of `_normalize(snippet)` and of
// `lines[line_no - 1]`. Line 139 is the failure it reports.
const COMPARED = [
  { from: 7, to: 26 },
  { from: 45, to: 63 },
];
const HOLDS_LINE = 138;
const FAILS_LINE = 139;
// The code card and the word bar take turns in the panel under the pipeline: they share its top.
const CODE: Card = { x: 166, y: BAR_TOP, width: 948, size: 20 };
const CODE_RISE = 16; // the code card opens from this far below its place

export function Film(props: Props): ReactElement {
  const { at, sources } = props;
  const frame = useCurrentFrame();
  // The progress, 0 to 1, of an eased motion of `len` frames from `start`.
  const ease = (start: number, len: number): number => p(frame, start, len);
  // The characters of `text` typed from `start`.
  const typedOf = (text: string, start: number): number => {
    const n = Array.from(text).length;
    return Math.floor(lin(frame, start, n * PER_CHAR) * n);
  };

  // subject: "/explain" is typed as the voice starts and the subject, in yellow, as the voice names it.
  // Then the pipeline is sketched: the empty place of the artifact, four checks and the handoff.
  const command = typedOf(COMMAND, at("subject"));
  const subjectAt = at("subject", { word: "subject" });
  const typed = typedOf(SUBJECT, subjectAt);
  const caretEnd = subjectAt + Array.from(SUBJECT).length * PER_CHAR + FADE;
  const caret = ease(at("subject"), 2) * (1 - ease(caretEnd, 6));
  const sketch = at("subject", { sentence: 2 });
  const slotIn = ease(sketch, 8);
  const ringIn = GATES.map((_, k) => ease(sketch + (k + 1) * STAGGER, 8));
  const handoffIn = ease(sketch + (GATES.length + 1) * STAGGER, 8);

  // forms: the prompt docks at the top left and the three forms come in, in a row. Then the page is chosen.
  const dock = ease(at("forms"), 16);
  const formIn = [0, 1, 2].map((k) => ease(at("forms") + 6 + 4 * k, 10));
  const pageChosen = ease(at("forms", { sentence: 2 }), FADE);

  // artifact: the page becomes the artifact card in the empty place and the other two forms go muted.
  // Then the card gets its file name.
  const become = ease(at("artifact"), MOVE);
  const muted = ease(at("artifact"), FADE);
  const pageLabelOut = ease(at("artifact"), 8);
  const slotOut = ease(at("artifact") + 10, 10);
  const name = Array.from(FILE).slice(0, typedOf(FILE, at("artifact", { sentence: 2 }))).join("");

  // gates: the line is drawn from the card through the gates, in order. Then each gate is named.
  const line = ease(at("gates"), MOVE);
  // Gate k lights as the tip of the line passes it: at (k + 1) / 5 of the line, give or take 4%.
  const reached = (k: number): number => lin(line, (k + 1) / (GATES.length + 1) - 0.04, 0.08);
  const named = GATES.map((gate) => ease(at("gates", { word: gate.name }), 8));

  // cite: the citations gate is chosen. Then the code card of source `check` opens below the gates.
  const cited = ease(at("cite"), FADE) * (1 - ease(at("prose"), FADE));
  const opened = ease(at("cite", { sentence: 2 }), 14);

  // holds: the compared strings of line 138 are tinted and a check is drawn: the snippet is on the line.
  // Then line 139, the failure, gets a red band and a cross.
  const tinted = ease(at("holds"), 10);
  const holds = ease(at("holds") + 6, 12);
  const failsAt = at("holds", { sentence: 2 });
  const banded = ease(failsAt, 10);
  const fails = ease(failsAt + 4, 12);

  // prose: the code card fades and the prose gate is chosen. Then the word bar fills and stops green.
  const prosed = ease(at("prose"), FADE);
  const barAt = at("prose", { sentence: 2 });
  const barIn = ease(barAt, 6);
  const cellFull = (cell: number): number => ease(barAt + PER_CELL * cell, CELL_FILL);
  const barGreen = ease(barAt + (WORDS - 1) * PER_CELL + CELL_FILL, 6);

  // handoff: each gate gets a green check in turn. Then the card moves past the last gate and turns green.
  const passed = GATES.map((_, k) => ease(at("handoff") + k * STAGGER, 10));
  const leaveAt = at("handoff", { sentence: 2 });
  const leave = ease(leaveAt, MOVE);
  const ready = ease(leaveAt + 12, 10);

  // The look of each gate: muted until the line reaches it, blue while it is the chosen check, green once
  // it passed.
  const chosen = [0, 0, cited, prosed];
  const gates: GateLook[] = GATES.map((_, k) => {
    const lit = mixColor(mixColor(C.line, C.text, reached(k)), C.blue, chosen[k]);
    const done = passed[k];
    return {
      ring: ringIn[k],
      stroke: mixColor(lit, C.green, done),
      fill: mixColor(mixColor(C.bg, C.blue, 0.16 * chosen[k]), mixColor(C.bg, C.green, 0.16), done),
      label: named[k],
      labelFill: mixColor(mixColor(C.text, C.blue, chosen[k]), C.text, done),
      check: done,
    };
  });

  // The page in the row, the artifact card at the start of the line, then past the handoff.
  const box = {
    cx: lerp(PAGE.cx, SLOT.cx, become) + (READY_CX - SLOT.cx) * leave,
    cy: lerp(PAGE.cy, SLOT.cy, become),
    w: lerp(PAGE.w, SLOT.w, become),
    h: lerp(PAGE.h, SLOT.h, become),
  };
  const cardStroke = mixColor(mixColor(C.text, C.blue, pageChosen), C.green, ready);
  const cardFill = mixColor(mixColor(C.panel, C.blue, 0.16 * pageChosen), mixColor(C.panel, C.green, 0.2), ready);
  const otherInk = mixColor(C.text, C.muted, muted);
  const otherOpacity = lerp(1, 0.55, muted);

  const source = sources.check;
  const code = { ...CODE, y: CODE.y + CODE_RISE * (1 - opened) };
  const codeShown = opened * (1 - prosed);
  const markX = CODE.x + CODE.width + 34;
  const blue = mixColor(C.text, C.blue, tinted);
  // A line from a chosen gate down to the panel it opens under the pipeline.
  const drop = (x: number, bottom: number): string => `M ${x} ${UNDER_LABELS} L ${x} ${bottom}`;

  return (
    <g>
      <Pipeline slot={slotIn * (1 - slotOut)} line={line} handoff={handoffIn} gates={gates} />

      <Sheet look={{ stroke: otherInk, opacity: formIn[0] * otherOpacity }} />
      <Video look={{ stroke: otherInk, opacity: formIn[2] * otherOpacity }} />
      <FormLabel x={FORM_X.sheet} text="sheet" fill={otherInk} opacity={formIn[0] * otherOpacity} />
      <FormLabel
        x={FORM_X.page}
        text="page"
        fill={mixColor(C.text, C.blue, pageChosen)}
        opacity={formIn[1] * (1 - pageLabelOut)}
      />
      <FormLabel x={FORM_X.video} text="video" fill={otherInk} opacity={formIn[2] * otherOpacity} />

      {codeShown > 0 && (
        <g opacity={codeShown}>
          <Draw d={drop(GATES[2].x, code.y)} t={opened} stroke={C.blue} width={2.5} />
          <CodeCard
            card={code}
            source={source}
            bands={[{ line: FAILS_LINE, color: C.red, opacity: 0.3 * banded }]}
            tints={COMPARED.map((cols) => ({ line: HOLDS_LINE, ...cols, color: blue }))}
          />
          <Mono x={code.x} y={lineY(code, source, FAILS_LINE) + 50} size={16} text={source.path} fill={C.muted} />
          <Mark kind="check" x={markX} y={lineY(code, source, HOLDS_LINE) - 7} t={holds} scale={1.4} />
          <Mark kind="cross" x={markX} y={lineY(code, source, FAILS_LINE) - 7} t={fails} scale={1.2} />
        </g>
      )}

      <Draw d={drop(GATES[3].x, BAR_TOP)} t={barIn} stroke={mixColor(C.blue, C.green, passed[3])} width={2.5} />
      <WordBar opacity={barIn} full={cellFull} green={barGreen} />

      <Document
        box={box}
        stroke={cardStroke}
        fill={cardFill}
        opacity={formIn[1]}
        lines={1 - become}
        name={name}
        fullName={FILE}
      />

      <Prompt subject={SUBJECT} command={command} typed={typed} caret={caret} dock={dock} />
    </g>
  );
}
