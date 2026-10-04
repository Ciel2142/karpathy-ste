// Layout and timing helpers shared by every scene: the margins, the title band and the content
// box below it (all read from the SceneBox the composition provides), and cue-relative
// animation progress.
import type { CSSProperties, ReactNode } from "react";
import { interpolate } from "remotion";
import { contentRect, useBox } from "./sceneBox";
import { theme } from "./theme";
import type { CueFrames } from "./types";

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
  const box = useBox();
  return (
    <>
      <div
        style={{
          ...oneLine,
          position: "absolute",
          top: box.margin,
          left: box.margin,
          right: box.margin,
          fontFamily: theme.sans,
          fontSize: box.titleSize,
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
          top: box.margin + box.titleBand,
          left: box.margin,
          right: box.margin,
          height: 2,
          background: theme.ink,
        }}
      />
    </>
  );
}

// The content box, as an absolutely placed container for a scene body.
export function Content({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  const rect = contentRect(useBox());
  return (
    <div
      style={{
        position: "absolute",
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
        fontFamily: theme.sans,
        color: theme.ink,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
