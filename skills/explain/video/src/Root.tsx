import { CalculateMetadataFunction, Composition } from "remotion";
import { Explain } from "./Explain";
import { FilmStage } from "./FilmStage";
import type { FilmTimeline, Timeline } from "./types";

// Real props always come from build/timeline.json via --props.
const EMPTY: Timeline = {
  format: "brainrot",
  engine: "none",
  fps: 30,
  width: 1080,
  height: 1920,
  totalFrames: 30,
  maxSceneSeconds: 30,
  maxTotalSeconds: 90,
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

// The film of a film script. Its props hold no Source: FilmStage makes the sources in its render.
const EMPTY_FILM: FilmTimeline = {
  format: "film",
  engine: "none",
  fps: 30,
  width: 1280,
  height: 720,
  totalFrames: 30,
  maxSceneSeconds: 30,
  maxTotalSeconds: 150,
  sources: {},
  checkFrames: [],
  scenes: [],
};

const calculateFilmMetadata: CalculateMetadataFunction<FilmTimeline> = ({ props }) => {
  if (props.scenes.length === 0) {
    throw new Error("Film: no scenes; render with --props <path to build/timeline.json>");
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
    <>
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
      <Composition
        id="Film"
        component={FilmStage}
        defaultProps={EMPTY_FILM}
        calculateMetadata={calculateFilmMetadata}
        durationInFrames={EMPTY_FILM.totalFrames}
        fps={EMPTY_FILM.fps}
        width={EMPTY_FILM.width}
        height={EMPTY_FILM.height}
      />
    </>
  );
}
