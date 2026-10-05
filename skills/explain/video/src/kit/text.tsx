// The text of a film scene. Mono sets a run on the monospace grid of mono.ts: the browser spreads it over
// exactly the width `monoWidth` measures and keeps its white space, so what a scene draws agrees with the
// columns of the code card and with its own arithmetic. Sans sets proportional text with no forced width.
// Both draw nothing for an empty text or an opacity of 0 or less. MonoRun is the same monospace run for
// content that colours parts of it (the tspans of a code line).
import type { ReactElement, ReactNode } from "react";
import { C, MONO, SANS } from "./palette";
import { monoWidth } from "./mono";

type TextProps = {
  x: number;
  y: number;
  size: number;
  text: string;
  fill?: string;
  opacity?: number;
  anchor?: "start" | "middle" | "end";
  weight?: number;
};

// What only the monospace run carries: the width the grid gives it, and the white space it keeps.
type Grid = { textLength: number; style: { whiteSpace: "pre" } };

const setText = (props: TextProps, family: string, content: ReactNode, grid?: Grid): ReactElement | null => {
  const { x, y, size, text, fill = C.text, opacity = 1, anchor = "start", weight = 400 } = props;
  if (text === "" || opacity <= 0) return null;
  return (
    <text
      x={x}
      y={y}
      fontSize={size}
      fontFamily={family}
      fontWeight={weight}
      fill={fill}
      opacity={opacity}
      textAnchor={anchor}
      {...grid}
    >
      {content}
    </text>
  );
};

// The grid of a monospace run of `text` at `size`.
const monoGrid = ({ text, size }: TextProps): Grid => ({
  textLength: monoWidth(text, size),
  style: { whiteSpace: "pre" },
});

export function Mono(props: TextProps): ReactElement | null {
  return setText(props, MONO, props.text, monoGrid(props));
}

// A Mono whose content is `children`: the same characters as `text`, set in parts of other colours. The
// width and the white space come from `text`, so a run in parts is as wide as the run in one piece.
export function MonoRun(props: TextProps & { children: ReactNode }): ReactElement | null {
  return setText(props, MONO, props.children, monoGrid(props));
}

export function Sans(props: TextProps): ReactElement | null {
  return setText(props, SANS, props.text);
}
