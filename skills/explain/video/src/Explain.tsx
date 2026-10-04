// The whole video: the scenes of the timeline one after another, each fading in over its
// first 8 frames, with its narration clip starting after leadFrames.
import type { ReactNode } from "react";
import {
  AbsoluteFill,
  Html5Audio,
  interpolate,
  Sequence,
  Series,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { BeforeAfter } from "./scenes/BeforeAfter";
import { BulletsAppear } from "./scenes/BulletsAppear";
import { CodeHighlights } from "./scenes/CodeHighlights";
import { DiagramWalk } from "./scenes/DiagramWalk";
import { Title } from "./scenes/Title";
import { LANDSCAPE_BOX, SceneBoxProvider } from "./sceneBox";
import { theme } from "./theme";
import type { Timeline, TimelineScene } from "./types";

function SceneBody({ scene }: { scene: TimelineScene }) {
  const { cueFrames } = scene;
  switch (scene.component) {
    case "title":
      return <Title {...scene.props} cueFrames={cueFrames} />;
    case "bullets-appear":
      return <BulletsAppear {...scene.props} cueFrames={cueFrames} />;
    case "diagram-with-highlight-walk":
      return <DiagramWalk {...scene.props} cueFrames={cueFrames} />;
    case "code-with-line-highlights":
      return <CodeHighlights {...scene.props} cueFrames={cueFrames} />;
    case "before-after":
      return <BeforeAfter {...scene.props} cueFrames={cueFrames} />;
    default:
      throw new Error(`unknown scene component in ${JSON.stringify(scene)}`);
  }
}

function FadeIn({ children }: { children: ReactNode }) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
}

export function Explain({ scenes }: Timeline) {
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
