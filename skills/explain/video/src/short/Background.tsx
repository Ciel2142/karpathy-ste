// The bottom half of a brainrot short, chosen by pick_background.py and written into the timeline:
// the user's clip, muted and cropped to cover its half of the frame, or the generated RunnerLoop.
// Short puts it outside the Series, so it runs without a break across scene boundaries.
import { Loop, OffthreadVideo, staticFile, useVideoConfig } from "remotion";
import { BRAINROT_BOX } from "../sceneBox";
import type { Background as BackgroundChoice } from "../types";
import { RunnerLoop } from "./RunnerLoop";

// The fixed seed of the generated loop: two renders of one timeline draw the same frames.
const RUNNER_SEED = 7;

// The background fills the lower half of the frame: as wide and as tall as the scene panel.
const { width: WIDTH, height: HEIGHT } = BRAINROT_BOX;

export function Background({ background }: { background: BackgroundChoice | undefined }) {
  const { fps } = useVideoConfig();
  if (background === undefined) {
    throw new Error("Short: timeline has no background; run render.sh");
  }
  if (background.kind === "generated") {
    return <RunnerLoop seed={RUNNER_SEED} />;
  }
  const style = { width: WIDTH, height: HEIGHT, objectFit: "cover" } as const;
  if (background.loop) {
    // The clip is shorter than the video: it plays from its start and repeats.
    return (
      <Loop durationInFrames={Math.max(1, Math.floor(background.seconds * fps))}>
        <OffthreadVideo src={staticFile(background.src)} muted trimBefore={0} style={style} />
      </Loop>
    );
  }
  return (
    <OffthreadVideo
      src={staticFile(background.src)}
      muted
      trimBefore={Math.round(background.start * fps)}
      style={style}
    />
  );
}
