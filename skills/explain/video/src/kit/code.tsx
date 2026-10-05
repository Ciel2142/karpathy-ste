// The code card of a film: a frame, the numbers and the lines of a `Source` on the monospace grid of mono.ts,
// with bands (a bar behind one line) and tints (some characters of one line in a colour, inside the same text
// element, so the grid still holds). It draws only a source that `sourceFromDisk` made, so a film cannot show
// code the pipeline did not read from the file; a band or a tint on a line the source lacks throws.
import type { ReactElement } from "react";
import { C } from "./palette";
import { Mono, MonoRun } from "./text";
import { cardHeight, colX, fitColumns, lineSpans, lineY, requireLine, ROW } from "./mono";
import type { Band, Card, Tint } from "./mono";
import { requireFromDisk } from "./source";
import type { Source } from "./source";

export type { Band, Card, Tint } from "./mono";
export { colX, lineY } from "./mono";

const FRAME_RADIUS = 8;
const FRAME_STROKE = 2;
const BAND_INSET = 8; // a band is narrower than the frame by this much on each side
const BAND_RADIUS = 4;

export function CodeCard(props: {
  card: Card;
  source: Source;
  bands?: Band[];
  tints?: Tint[];
  opacity?: number;
}): ReactElement {
  const { card, source, bands = [], tints = [], opacity = 1 } = props;
  requireFromDisk(source);
  for (const { line } of [...bands, ...tints]) requireLine(source, line);

  // The numbers end where the 4 columns of the gutter do: 2 columns (the gap) before the code.
  const numberRight = colX(card, -2);
  return (
    <g opacity={opacity}>
      <rect
        x={card.x}
        y={card.y}
        width={card.width}
        height={cardHeight(card, source.lines.length)}
        rx={FRAME_RADIUS}
        fill={C.panel}
        stroke={C.line}
        strokeWidth={FRAME_STROKE}
      />
      {bands.map((band, i) => (
        <rect
          key={`band${i}`}
          x={card.x + BAND_INSET}
          y={lineY(card, source, band.line) - card.size}
          width={card.width - 2 * BAND_INSET}
          height={ROW * card.size}
          rx={BAND_RADIUS}
          fill={band.color}
          opacity={band.opacity}
        />
      ))}
      {source.lines.flatMap((line, i) => {
        const n = source.from + i;
        const y = lineY(card, source, n);
        const spans = lineSpans(line, tints.filter((tint) => tint.line === n), fitColumns(card));
        return [
          <Mono
            key={`n${n}`}
            x={numberRight}
            y={y}
            size={card.size}
            text={String(n)}
            fill={C.muted}
            anchor="end"
          />,
          <MonoRun
            key={`c${n}`}
            x={colX(card, 0)}
            y={y}
            size={card.size}
            text={spans.map((span) => span.text).join("")}
          >
            {spans.map((span, j) =>
              span.color === undefined ? (
                span.text
              ) : (
                <tspan key={j} fill={span.color}>
                  {span.text}
                </tspan>
              ),
            )}
          </MonoRun>,
        ];
      })}
    </g>
  );
}
