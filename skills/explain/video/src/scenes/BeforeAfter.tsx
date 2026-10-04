// "before-after": two panels. Before the cue only the first (before) panel shows; at the cue
// a vertical wipe edge sweeps left to right across the second (after) panel and reveals it, and
// the before panel dims. Side by side the panels are two columns; when the box sets stackPanels
// they are two full-width halves, before above after.
import { interpolate, useCurrentFrame } from "remotion";
import { Content, cueAt, ramp, SceneTitle } from "../layout";
import { contentRect, useBox } from "../sceneBox";
import { theme } from "../theme";
import type { BeforeAfterProps, Cued, Panel } from "../types";

const WIPE_FRAMES = 15;
const GAP = 48;
const DIMMED = 0.45; // before panel opacity once the wipe is done

function Column({
  panel,
  accent,
  left,
  width,
}: {
  panel: Panel;
  accent: string;
  left: number;
  width: number;
}) {
  const { panelHeading, panelLine } = useBox().type;
  return (
    <div style={{ position: "absolute", top: 0, left, width }}>
      <div
        style={{
          fontSize: panelHeading,
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
            fontSize: panelLine,
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
  const box = useBox();
  const rect = contentRect(box);
  const column = box.stackPanels ? rect.width : (rect.width - GAP) / 2;
  const half = (rect.height - GAP) / 2; // stacked: the height of each panel
  const wipe = ramp(frame, cueAt(cueFrames, cue), WIPE_FRAMES);
  const hidden = (1 - wipe) * 100; // % of the after panel still covered, from its right side
  // Where the after panel sits: beside the before column, or in the bottom half of the content box.
  const afterPlace = box.stackPanels
    ? { top: half + GAP, height: half, left: 0 }
    : { top: 0, bottom: 0, left: column + GAP };
  return (
    <>
      <SceneTitle text={title} />
      <Content>
        <div style={{ opacity: interpolate(wipe, [0, 1], [1, DIMMED]) }}>
          <Column panel={before} accent={theme.red} left={0} width={column} />
        </div>
        <div
          style={{
            position: "absolute",
            ...afterPlace,
            width: column,
            clipPath: `inset(0 ${hidden}% 0 0)`,
          }}
        >
          <Column panel={after} accent={theme.blue} left={0} width={column} />
        </div>
      </Content>
    </>
  );
}
