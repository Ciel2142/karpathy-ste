// The text of a film scene. Mono sets a run on the monospace grid of mono.ts: the browser spreads it over
// exactly the width `monoWidth` measures and keeps its white space, so what a scene draws agrees with the
// columns of the code card and with its own arithmetic. Sans sets proportional text with no forced width.
// Both draw nothing for an empty text or an opacity of 0 or less.
import type { ReactElement } from "react";
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

const setText = (props: TextProps, family: string, grid?: Grid): ReactElement | null => {
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
      {text}
    </text>
  );
};

export function Mono(props: TextProps): ReactElement | null {
  return setText(props, MONO, { textLength: monoWidth(props.text, props.size), style: { whiteSpace: "pre" } });
}

export function Sans(props: TextProps): ReactElement | null {
  return setText(props, SANS);
}
