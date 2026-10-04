// The whole video: the scenes of the timeline one after another, each fading in over its
// first 8 frames, with its narration clip starting after leadFrames. A brainrot timeline is laid
// out by Short instead; the landscape stack below is the explainer and never reads `background`,
// `captions` or BRAINROT_BOX.
import { AbsoluteFill, Html5Audio, Sequence, Series, staticFile } from "remotion";
import { LANDSCAPE_BOX, SceneBoxProvider } from "./sceneBox";
import { FadeIn, SceneBody } from "./sceneBody";
import { Short } from "./short/Short";
import { theme } from "./theme";
import type { Timeline } from "./types";

export function Explain(timeline: Timeline) {
  if (timeline.format === "brainrot") {
    return <Short {...timeline} />;
  }
  const { scenes } = timeline;
  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg }}>
      <SceneBoxProvider box={LANDSCAPE_BOX}>
        <Series>
          {scenes.map((scene) => (
            <Series.Sequence key={scene.id} name={scene.id} durationInFrames={scene.durationInFrames}>
              <FadeIn>
                <SceneBody scene={scene} />
              </FadeIn>
              <Sequence
                name={`${scene.id} voice`}
                from={scene.leadFrames}
                durationInFrames={scene.audioFrames}
                layout="none"
              >
                <Html5Audio src={staticFile(scene.audio)} />
              </Sequence>
            </Series.Sequence>
          ))}
        </Series>
      </SceneBoxProvider>
    </AbsoluteFill>
  );
}
