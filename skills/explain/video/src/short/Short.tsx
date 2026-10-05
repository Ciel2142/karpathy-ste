// The brainrot layout, 1080 x 1920: the scene panel on top (white, 1080 x 960, laid out under
// BRAINROT_BOX), the background below it, and the word-by-word caption on the seam between them.
// Explain hands a timeline with format "brainrot" to this component.
import type { CSSProperties } from "react";
import { AbsoluteFill, Html5Audio, Sequence, Series, staticFile } from "remotion";
import { BRAINROT_BOX, SceneBoxProvider } from "../sceneBox";
import { FadeIn, SceneBody } from "../sceneBody";
import { theme } from "../theme";
import type { Timeline } from "../types";
import { Background } from "./Background";
import { CaptionBand } from "./CaptionBand";

const { width: PANEL_WIDTH, height: PANEL_HEIGHT } = BRAINROT_BOX;

// A scene draws inside its nearest positioned ancestor, which must be the box's size.
const panel: CSSProperties = {
  position: "absolute",
  left: 0,
  top: 0,
  width: PANEL_WIDTH,
  height: PANEL_HEIGHT,
  overflow: "hidden",
  backgroundColor: theme.bg,
};

const lower: CSSProperties = {
  position: "absolute",
  left: 0,
  top: PANEL_HEIGHT,
  width: PANEL_WIDTH,
  height: PANEL_HEIGHT,
  overflow: "hidden",
};

export function Short({ scenes, background }: Timeline) {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <div style={lower}>
        <Background background={background} />
      </div>
      <Series>
        {scenes.map((scene) => (
          <Series.Sequence key={scene.id} name={scene.id} durationInFrames={scene.durationInFrames}>
            <div style={panel}>
              <SceneBoxProvider box={BRAINROT_BOX}>
                <FadeIn>
                  <SceneBody scene={scene} />
                </FadeIn>
              </SceneBoxProvider>
            </div>
            <CaptionBand captions={scene.captions ?? []} />
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
    </AbsoluteFill>
  );
}
