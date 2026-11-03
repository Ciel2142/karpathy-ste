// The bridge between two chapters of a movie (spec 4.4): a clip of three scenes on one picture. done: the
// question the chapter answered, in the top third, takes a green check. sofar: its answer comes in under
// it. next: the question of the next chapter rises into the lower third in yellow, and the first two labels
// go muted. Every text is 24 px or more (the clip floor is 19 px).
//
// movie.py bridges writes this file into bridges/<n>/scene/ and puts each label in place of its
// placeholder string, as a literal with each UTF-16 code unit escaped (\uXXXX), so that no word of a
// label reads as a refused token to check_scene.py. A label is wrapped here, at render time, into lines
// of at most WRAP characters. The layout leaves room for two lines of a question and four of an answer.
//
// Every motion starts at a mark of `at`. A number written here is a length in frames or a place on the
// stage, never a position in time.
import type { ReactElement } from "react";
import { useCurrentFrame } from "remotion";
import { C, Mark, Sans, mixColor, p } from "../kit";
import type { Props } from "./script.gen";

const DONE = "{{done}}";
const SOFAR = "{{sofar}}";
const NEXT = "{{next}}";

const WRAP = 60; // characters of one line at most; a longer word is a line of its own
const LEFT = 170; // x of each label
const DONE_Y = 170; // the first baseline of each label
const SOFAR_Y = 290;
const NEXT_Y = 520;
const QUESTION = { size: 28, step: 38, weight: 600 }; // size and line step in px
const ANSWER = { size: 26, step: 36, weight: 400 };
const LIFT = 40; // px that the next question rises
const FADE = 10;
const DRAW = 12;
const RISE = 12;

// The words of `text` in lines of at most WRAP code points.
const wrap = (text: string): string[] => {
  const lines: string[] = [];
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const last = lines.length - 1;
    if (last >= 0 && Array.from(lines[last]).length + 1 + Array.from(word).length <= WRAP) {
      lines[last] = lines[last] + " " + word;
    } else {
      lines.push(word);
    }
  }
  return lines;
};

// One label: the lines of `text`, one Sans each, from the baseline `y` down.
function Label(props: {
  text: string;
  y: number;
  look: { size: number; step: number; weight: number };
  fill: string;
  opacity: number;
}): ReactElement {
  const { text, y, look, fill, opacity } = props;
  return (
    <g>
      {wrap(text).map((line, k) => (
        <Sans
          key={k}
          x={LEFT}
          y={y + k * look.step}
          size={look.size}
          weight={look.weight}
          text={line}
          fill={fill}
          opacity={opacity}
        />
      ))}
    </g>
  );
}

export function Film(props: Props): ReactElement {
  const { at } = props;
  const frame = useCurrentFrame();

  // done: the question fades in as the voice starts, and its check draws.
  const doneIn = p(frame, at("done"), FADE);
  const check = p(frame, at("done"), DRAW);
  // sofar: the answer fades in under the question.
  const sofarIn = p(frame, at("sofar"), FADE);
  // next: the next question rises in, and the question and the answer before it go muted.
  const nextIn = p(frame, at("next"), RISE);
  const past = mixColor(C.text, C.muted, nextIn);

  return (
    <g>
      <Mark kind="check" x={LEFT - 34} y={DONE_Y - 10} t={check} scale={2.2} opacity={1 - 0.4 * nextIn} />
      <Label text={DONE} y={DONE_Y} look={QUESTION} fill={past} opacity={doneIn} />
      <Label text={SOFAR} y={SOFAR_Y} look={ANSWER} fill={past} opacity={sofarIn} />
      <Label text={NEXT} y={NEXT_Y + LIFT * (1 - nextIn)} look={QUESTION} fill={C.yellow} opacity={nextIn} />
    </g>
  );
}
