// A small film scene, written the way a film author writes one: it imports the whole import surface of the
// kit from "../kit" and uses every name of it, so that tsc, run on a copy of the app that holds this file as
// src/kitcheck/Scene.tsx (test_film_kit.py, TestKitCompiles), proves that a scene needs nothing else.
import { useCurrentFrame } from "remotion";
import {
  C, MONO, SANS, STAGE, MIN_TEXT, p, lin, lerp, mix, mixColor, Mono, Sans, Draw, Mark, colX, lineY, CodeCard,
} from "../kit";
import type { At, Band, Card, FilmProps, Pt, Source, Tint, Where } from "../kit";

export function Scene(props: FilmProps<"type" | "checks", "app">) {
  const frame = useCurrentFrame();
  const at: At<"type" | "checks"> = props.at;
  const source: Source = props.sources.app;

  // Marks of all three kinds, and the two ends of a scene.
  const second: Where = { sentence: 2 };
  const word: Where = { word: "handler", nth: 2 };
  const typed = at("type");
  const checked = at("checks", second);
  const crossed = at("checks", word);
  const said = at.said("type");
  const end = at.end("checks");

  const card: Card = { x: 80, y: 140, width: 560, size: MIN_TEXT + 6 };
  const glow = lin(frame, typed, said - typed) * 0.2;
  const bands: Band[] = [{ line: source.from, color: C.yellow, opacity: glow }];
  const tints: Tint[] = [{ line: source.from, from: 0, to: 3, color: C.blue }];

  const start: Pt = { x: colX(card, 0), y: lineY(card, source, source.from) };
  const stop: Pt = { x: STAGE.width - 120, y: STAGE.height / 2 };
  const pen = mix(start, stop, p(frame, typed, said - typed));
  const ink = mixColor(C.muted, C.green, p(frame, checked, crossed - checked));

  return (
    <g>
      <rect x={0} y={0} width={STAGE.width} height={STAGE.height} fill={C.bg} />
      <Sans x={80} y={80} size={32} text="How a check runs" weight={600} />
      <CodeCard
        card={card}
        source={source}
        bands={bands}
        tints={tints}
        opacity={lerp(0, 1, p(frame, typed, 15))}
      />
      <Draw
        d={`M ${start.x} ${start.y} L ${pen.x} ${pen.y}`}
        t={lin(frame, said, end - said)}
        stroke={ink}
        width={3}
        opacity={0.9}
      />
      <Mark kind="check" x={stop.x} y={stop.y} t={p(frame, checked, 12)} scale={2} />
      <Mark kind="cross" x={stop.x} y={stop.y + 60} t={p(frame, crossed, 12)} opacity={0.8} />
      <Mono x={80} y={STAGE.height - 40} size={MIN_TEXT} text="verify.sh" fill={C.muted} />
      <text x={400} y={STAGE.height - 40} fontSize={MIN_TEXT} fontFamily={SANS} fill={C.muted}>
        <tspan fontFamily={MONO}>{source.path}</tspan>
      </text>
    </g>
  );
}
