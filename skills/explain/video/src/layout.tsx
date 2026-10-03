// Layout and timing helpers shared by every scene: the 48 px margins, the title band, the
// content box below it, and cue-relative animation progress.
import type { CSSProperties, ReactNode } from "react";
import { interpolate } from "remotion";
import { theme } from "./theme";
import type { CueFrames } from "./types";

export const FRAME = { width: 1280, height: 720 };
export const MARGIN = 48;
const TITLE_SIZE = 44;
const RULE_TOP = MARGIN + 60; // the 2 px ink rule under the title
// The box every scene body is laid out in (title band above it).
export const CONTENT = {
  left: MARGIN,
  top: RULE_TOP + 30,
  width: FRAME.width - 2 * MARGIN,
  height: FRAME.height - MARGIN - (RULE_TOP + 30),
};

// The frame of a cue, relative to the scene start. build-timeline.mjs writes one entry per
// cue string in the props, so a miss means the timeline and the props disagree.
export const cueAt = (cueFrames: CueFrames, cue: string): number => {
  const frame = cueFrames[cue];
  if (frame === undefined) {
    throw new Error(`no cue frame for ${JSON.stringify(cue)} in the timeline`);
  }
  return frame;
};

// 0 up to `start`, then linear to 1 over `length` frames, then 1. A motion that starts at a
// cue frame is therefore still at its start state on the cue frame itself.
export const ramp = (frame: number, start: number, length: number): number =>
  interpolate(frame, [start, start + length], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

// One line, never wider than the frame: an over-long title ends in an ellipsis.
export const oneLine: CSSProperties = {
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
};

export function SceneTitle({ text }: { text: string }) {
  return (
    <>
      <div
        style={{
          ...oneLine,
          position: "absolute",
          top: MARGIN,
          left: MARGIN,
          right: MARGIN,
          fontFamily: theme.sans,
          fontSize: TITLE_SIZE,
          fontWeight: 700,
          lineHeight: 1.2,
          color: theme.ink,
        }}
      >
        {text}
      </div>
      <div
        style={{
          position: "absolute",
          top: RULE_TOP,
          left: MARGIN,
          right: MARGIN,
          height: 2,
          background: theme.ink,
        }}
      />
    </>
  );
}

// The content box, as an absolutely placed container for a scene body.
export function Content({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div
      style={{
        position: "absolute",
        left: CONTENT.left,
        top: CONTENT.top,
        width: CONTENT.width,
        height: CONTENT.height,
        fontFamily: theme.sans,
        color: theme.ink,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
