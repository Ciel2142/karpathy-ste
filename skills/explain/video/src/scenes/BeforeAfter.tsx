// "before-after": two columns. Before the cue only the left (before) column shows; at the cue
// a vertical wipe edge sweeps left to right across the right column and reveals it, and the
// left column dims.
import { interpolate, useCurrentFrame } from "remotion";
import { CONTENT, Content, cueAt, ramp, SceneTitle } from "../layout";
import { theme } from "../theme";
import type { BeforeAfterProps, Cued, Panel } from "../types";

const WIPE_FRAMES = 15;
const GAP = 48;
const COLUMN = (CONTENT.width - GAP) / 2;
const DIMMED = 0.45; // left column opacity once the wipe is done

function Column({ panel, accent, left }: { panel: Panel; accent: string; left: number }) {
  return (
    <div style={{ position: "absolute", top: 0, left, width: COLUMN }}>
      <div
        style={{
          fontSize: 32,
          fontWeight: 700,
          lineHeight: 1.2,
          color: accent,
          paddingBottom: 12,
          borderBottom: `2px solid ${accent}`,
          marginBottom: 20,
        }}
      >
        {panel.heading}
      </div>
      {panel.lines.map((line, i) => (
        <div
          key={i}
          style={{
            fontFamily: theme.mono,
            fontSize: 26,
            lineHeight: 1.4,
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
            color: theme.ink,
          }}
        >
          {line}
        </div>
      ))}
    </div>
  );
}

export function BeforeAfter({ title, before, after, cue, cueFrames }: Cued<BeforeAfterProps>) {
  const frame = useCurrentFrame();
  const wipe = ramp(frame, cueAt(cueFrames, cue), WIPE_FRAMES);
  const hidden = (1 - wipe) * 100; // % of the right column still covered, from its right side
  return (
    <>
      <SceneTitle text={title} />
      <Content>
        <div style={{ opacity: interpolate(wipe, [0, 1], [1, DIMMED]) }}>
          <Column panel={before} accent={theme.red} left={0} />
        </div>
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: COLUMN + GAP,
            width: COLUMN,
            clipPath: `inset(0 ${hidden}% 0 0)`,
          }}
        >
          <Column panel={after} accent={theme.blue} left={0} />
        </div>
      </Content>
    </>
  );
}
