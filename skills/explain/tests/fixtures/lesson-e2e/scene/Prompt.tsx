// The prompt: the command `/explain` and its subject, in mono type, the subject in yellow. It is typed
// in the middle of the stage and stays there. Film gives how many characters are typed and the opacity of
// the caret.
import type { ReactElement } from "react";
import { C, Mono, STAGE } from "../kit";

export const COMMAND = "/explain ";
const ADVANCE = 0.6; // Mono sets each character 0.6 of its size wide (kit/text.tsx)
const SIZE = 48;
const Y = 250;

export function Prompt(props: {
  subject: string;
  command: number; // characters of the command typed
  typed: number; // characters of the subject typed
  caret: number; // opacity of the caret
}): ReactElement {
  const { subject, command, typed, caret } = props;
  const columns = COMMAND.length + Array.from(subject).length;
  const column = ADVANCE * SIZE;
  const x = (STAGE.width - columns * column) / 2;
  const shown = command + typed;
  return (
    <g>
      <Mono x={x} y={Y} size={SIZE} text={COMMAND.slice(0, command)} weight={500} />
      <Mono
        x={x + COMMAND.length * column}
        y={Y}
        size={SIZE}
        text={Array.from(subject).slice(0, typed).join("")}
        fill={C.yellow}
        weight={500}
      />
      <rect
        x={x + shown * column + 2}
        y={Y - 0.8 * SIZE}
        width={0.08 * SIZE}
        height={SIZE}
        fill={C.text}
        opacity={caret}
      />
    </g>
  );
}
