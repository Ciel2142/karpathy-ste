// "title": the video title centred, the subtitle fading in at its cue.
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { cueAt, MARGIN, ramp } from "../layout";
import { theme } from "../theme";
import type { Cued, TitleProps } from "../types";

const FADE_FRAMES = 12;

export function Title({ title, subtitle, cue, cueFrames }: Cued<TitleProps>) {
  const frame = useCurrentFrame();
  const shown = ramp(frame, cueAt(cueFrames, cue), FADE_FRAMES);
  return (
    <AbsoluteFill
      style={{
        padding: MARGIN,
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        fontFamily: theme.sans,
      }}
    >
      <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.15, color: theme.ink }}>
        {title}
      </div>
      <div style={{ width: 160, height: 2, background: theme.ink, margin: "28px 0" }} />
      <div style={{ fontSize: 36, lineHeight: 1.25, color: theme.muted, opacity: shown }}>
        {subtitle}
      </div>
    </AbsoluteFill>
  );
}
