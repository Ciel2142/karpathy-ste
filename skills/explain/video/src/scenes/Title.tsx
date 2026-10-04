// "title": the video title centred, the subtitle fading in at its cue.
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { cueAt, ramp } from "../layout";
import { useBox } from "../sceneBox";
import { theme } from "../theme";
import type { Cued, TitleProps } from "../types";

const FADE_FRAMES = 12;

export function Title({ title, subtitle, cue, cueFrames }: Cued<TitleProps>) {
  const frame = useCurrentFrame();
  const box = useBox();
  const shown = ramp(frame, cueAt(cueFrames, cue), FADE_FRAMES);
  return (
    <AbsoluteFill
      style={{
        padding: box.margin,
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        fontFamily: theme.sans,
      }}
    >
      <div style={{ fontSize: box.type.heroTitle, fontWeight: 700, lineHeight: 1.15, color: theme.ink }}>
        {title}
      </div>
      <div style={{ width: 160, height: 2, background: theme.ink, margin: "28px 0" }} />
      <div style={{ fontSize: box.type.heroSubtitle, lineHeight: 1.25, color: theme.muted, opacity: shown }}>
        {subtitle}
      </div>
    </AbsoluteFill>
  );
}
