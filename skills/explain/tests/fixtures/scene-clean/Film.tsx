// An export is what the stage draws: one function, Film, that takes the props.
// The import below renames the frame hook and keeps the interpolation as it is
import { useCurrentFrame as now, interpolate } from "remotion";
import type { ReactElement } from "react";
import {
  C,
  Draw,
} from "../kit";
import type { Props } from "./script.gen";
import { Part } from "./Part";
// <masks <useful <images as anyone : anything
export function Film(props: Props): ReactElement {
  const fade = interpolate(now(), [0, 30], [0, 1]);
  return (
    <g opacity={fade}>
      <Part />
    </g>
  );
}
