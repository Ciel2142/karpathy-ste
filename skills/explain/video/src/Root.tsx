import { CalculateMetadataFunction, Composition } from "remotion";
import { Explain } from "./Explain";
import type { Timeline } from "./types";

// Real props always come from build/timeline.json via --props.
const EMPTY: Timeline = {
  engine: "none",
  fps: 30,
  width: 1280,
  height: 720,
  totalFrames: 30,
  scenes: [],
};

const calculateMetadata: CalculateMetadataFunction<Timeline> = ({ props }) => {
  if (props.scenes.length === 0) {
    throw new Error("Explain: no scenes; render with --props <path to build/timeline.json>");
  }
  return {
    durationInFrames: props.totalFrames,
    fps: props.fps,
    width: props.width,
    height: props.height,
  };
};

export function RemotionRoot() {
  return (
    <Composition
      id="Explain"
      component={Explain}
      defaultProps={EMPTY}
      calculateMetadata={calculateMetadata}
      durationInFrames={EMPTY.totalFrames}
      fps={EMPTY.fps}
      width={EMPTY.width}
      height={EMPTY.height}
    />
  );
}
