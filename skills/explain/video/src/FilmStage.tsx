// The stage of a film (spec 5.1). The pipeline owns the stage and the author owns what is on it: FilmStage
// renders one <svg> of the film's size on the ground of the film palette, which holds the author's Film
// (src/film/Film.tsx), then the narration clip of each scene, placed as Explain.tsx places a clip: it
// starts leadFrames after the scene start, so the voice starts at the scene's first mark.
//
// `at` and the sources are made here, in the render, memoised on the timeline: Remotion passes the props
// (defaultProps, calculateMetadata, --props) through JSON, and a copy of a Source makes CodeCard throw.
// FilmStage handles no error: a mark error, or a source that the timeline lacks, throws in Film and ends
// the render.
//
// The stage also measures the text of the film (spec 7.3): at each frame of the timeline's checkFrames it
// measures every <text> of the stage and hands the measures to kit/guard.ts. A frame with a fault ends the
// render through cancelRender, with the guard's stage line as the message, which render.sh reads from the
// log of the guard pass. It measures in a layout effect, which runs in the commit that draws the frame and
// before the frame is captured: the measured tree is the tree that ships. It measures in every render of
// composition Film; in the render stage the checked frames have passed the guard already.
import { useLayoutEffect, useMemo, useRef } from "react";
import type { ReactElement } from "react";
import { Html5Audio, Sequence, cancelRender, staticFile, useCurrentFrame } from "remotion";
import { C, MIN_TEXT, STAGE } from "./kit";
import type { Source } from "./kit";
import { faultsOf, guardLine } from "./kit/guard";
import type { Measured } from "./kit/guard";
import { makeAt } from "./kit/marks";
import { sourceFromDisk } from "./kit/source";
import { Film } from "./film/Film";
import type { SceneId, SourceId } from "./film/script.gen";
import type { FilmTimeline } from "./types";

// The product of the computed opacity of `element` and of each of its ancestors up to and including `stage`.
const opacityOf = (element: Element, stage: SVGSVGElement): number => {
  const own = parseFloat(getComputedStyle(element).opacity);
  return element === stage || element.parentElement === null
    ? own
    : own * opacityOf(element.parentElement, stage);
};

// The smallest computed font-size of `text` and of its <tspan> descendants, in its own user units.
const fontSizeOf = (text: SVGTextElement): number =>
  Math.min(
    ...[text, ...Array.from(text.querySelectorAll("tspan"))].map((e) => parseFloat(getComputedStyle(e).fontSize)),
  );

// Every <text> of the stage, in document order, as the guard reads it: its content, its opacity, its size on
// the canvas (the font size times the scale of its screen matrix) and its box in canvas pixels (moved by the
// place of the stage). A text with no screen matrix is not drawn, and is not measured.
const measure = (stage: SVGSVGElement): Measured[] => {
  const origin = stage.getBoundingClientRect();
  return Array.from(stage.querySelectorAll("text")).flatMap((text): Measured[] => {
    const matrix = text.getScreenCTM();
    if (matrix === null) return [];
    const rect = text.getBoundingClientRect();
    return [
      {
        text: text.textContent ?? "",
        opacity: opacityOf(text, stage),
        px: fontSizeOf(text) * Math.hypot(matrix.c, matrix.d),
        box: {
          left: rect.left - origin.left,
          top: rect.top - origin.top,
          right: rect.right - origin.left,
          bottom: rect.bottom - origin.top,
        },
      },
    ];
  });
};

export function FilmStage(timeline: FilmTimeline): ReactElement {
  const { scenes, sources: declared, checkFrames } = timeline;
  const frame = useCurrentFrame();
  const stage = useRef<SVGSVGElement>(null);
  const at = useMemo(() => makeAt<SceneId>(scenes), [scenes]);
  const sources = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(declared).map(([id, entry]): [string, Source] => [id, sourceFromDisk(entry)]),
      ) as Record<SourceId, Source>,
    [declared],
  );
  useLayoutEffect(() => {
    const entry = checkFrames.find((check) => check.frame === frame);
    if (entry === undefined || stage.current === null) return;
    const faults = faultsOf(measure(stage.current), STAGE, MIN_TEXT);
    if (faults.length > 0) cancelRender(new Error(guardLine(frame, entry.scene, faults)));
  }, [frame, checkFrames]);
  return (
    <>
      <svg
        ref={stage}
        viewBox={`0 0 ${STAGE.width} ${STAGE.height}`}
        width={timeline.width}
        height={timeline.height}
        style={{ display: "block", backgroundColor: C.bg }}
      >
        <Film at={at} sources={sources} />
      </svg>
      {scenes.map((scene) => (
        <Sequence
          key={scene.id}
          name={`${scene.id} voice`}
          from={scene.from + scene.leadFrames}
          durationInFrames={scene.audioFrames}
          layout="none"
        >
          <Html5Audio src={staticFile(scene.audio)} />
        </Sequence>
      ))}
    </>
  );
}
