// The stage of a film (spec 5.1). The pipeline owns the stage and the author owns what is on it: FilmStage
// renders one <svg> of the film's size on the ground of the film palette, which holds the author's Film
// (src/film/Film.tsx), then the narration clip of each scene, placed as Explain.tsx places a clip: it
// starts leadFrames after the scene start, so the voice starts at the scene's first mark.
//
// `at` and the sources are made here, in the render, memoised on the timeline: Remotion passes the props
// (defaultProps, calculateMetadata, --props) through JSON, and a copy of a Source makes CodeCard throw.
// FilmStage handles no error: a mark error, or a source that the timeline lacks, throws in Film and ends
// the render.
import { useMemo } from "react";
import type { ReactElement } from "react";
import { Html5Audio, Sequence, staticFile } from "remotion";
import { C, STAGE } from "./kit";
import type { Source } from "./kit";
import { makeAt } from "./kit/marks";
import { sourceFromDisk } from "./kit/source";
import { Film } from "./film/Film";
import type { SceneId, SourceId } from "./film/script.gen";
import type { FilmTimeline } from "./types";

export function FilmStage(timeline: FilmTimeline): ReactElement {
  const { scenes, sources: declared } = timeline;
  const at = useMemo(() => makeAt<SceneId>(scenes), [scenes]);
  const sources = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(declared).map(([id, entry]): [string, Source] => [id, sourceFromDisk(entry)]),
      ) as Record<SourceId, Source>,
    [declared],
  );
  return (
    <>
      <svg
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
