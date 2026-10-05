// The prompt: the command `/explain` and its subject, in mono type, the subject in yellow. It is typed
// in the middle of the stage, then docks at the top left and stays there. Film gives how many characters
// are typed, the opacity of the caret and how far the prompt has docked.
import type { ReactElement } from "react";
import { C, Mono, STAGE, lerp } from "../kit";

export const COMMAND = "/explain ";
const ADVANCE = 0.6; // Mono sets each character 0.6 of its size wide (kit/text.tsx)
const TYPED_SIZE = 48;
const TYPED_Y = 250;
const DOCKED = { x: 64, y: 84, size: 28 };

export function Prompt(props: {
  subject: string;
  command: number; // characters of the command typed
  typed: number; // characters of the subject typed
  caret: number; // opacity of the caret
  dock: number; // 0 in the middle of the stage, 1 docked at the top left
}): ReactElement {
  const { subject, command, typed, caret, dock } = props;
  const columns = COMMAND.length + Array.from(subject).length;
  const size = lerp(TYPED_SIZE, DOCKED.size, dock);
  const x = lerp((STAGE.width - columns * ADVANCE * TYPED_SIZE) / 2, DOCKED.x, dock);
  const y = lerp(TYPED_Y, DOCKED.y, dock);
  const column = ADVANCE * size;
  const shown = command + typed;
  return (
    <g>
      <Mono x={x} y={y} size={size} text={COMMAND.slice(0, command)} weight={500} />
      <Mono
        x={x + COMMAND.length * column}
        y={y}
        size={size}
        text={Array.from(subject).slice(0, typed).join("")}
        fill={C.yellow}
        weight={500}
      />
      <rect
        x={x + shown * column + 2}
        y={y - 0.8 * size}
        width={0.08 * size}
        height={size}
        fill={C.text}
        opacity={caret}
      />
    </g>
  );
}
