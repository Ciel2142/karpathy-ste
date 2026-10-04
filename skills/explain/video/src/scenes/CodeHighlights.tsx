// "code-with-line-highlights": source lines with their line numbers. At each highlight cue
// its line range gets a blue band and a left bar; earlier highlights dim to the fill colour.
import { useCurrentFrame } from "remotion";
import { Content, cueAt, ramp, SceneTitle } from "../layout";
import { useBox } from "../sceneBox";
import { theme } from "../theme";
import type { CodeProps, Cued } from "../types";

const MAX_LINES = 14;
const FADE_FRAMES = 10;
const BAR_WIDTH = 6;
const PAD = 16; // horizontal space inside a band, left of the line number

export function CodeHighlights({ title, source, lines, highlights, cueFrames }: Cued<CodeProps>) {
  const frame = useCurrentFrame();
  const { code, codeLine } = useBox().type;
  const shown = lines.slice(0, MAX_LINES);
  const gutter = String(source.from + shown.length - 1).length; // digits of the last number
  const starts = highlights.map((h) => cueAt(cueFrames, h.cue));
  // A highlight dims as the next one comes in.
  const bands = highlights.map((h, i) => {
    const on = ramp(frame, starts[i], FADE_FRAMES);
    const dim = i + 1 < starts.length ? ramp(frame, starts[i + 1], FADE_FRAMES) : 0;
    return { h, on, dim };
  });
  const top = (line: number) => (line - source.from) * codeLine;

  return (
    <>
      <SceneTitle text={title} />
      <Content style={{ fontFamily: theme.mono, fontSize: code }}>
        {bands.map(({ h, on, dim }) => (
          <div
            key={h.cue}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: top(h.from),
              height: (h.to - h.from + 1) * codeLine,
              opacity: on,
            }}
          >
            <div style={{ position: "absolute", inset: 0, background: theme.fill }} />
            <div style={{ position: "absolute", inset: 0, background: theme.blueTint, opacity: 1 - dim }} />
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                width: BAR_WIDTH,
                background: theme.blue,
                opacity: 1 - dim,
              }}
            />
          </div>
        ))}
        {shown.map((text, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: i * codeLine,
              height: codeLine,
              lineHeight: `${codeLine}px`,
              display: "flex",
              whiteSpace: "pre",
              overflow: "hidden",
            }}
          >
            <span style={{ flex: "none", width: `${gutter + 2}ch`, paddingLeft: PAD, color: theme.muted }}>
              {String(source.from + i).padStart(gutter, " ")}
            </span>
            <span style={{ tabSize: 4, color: theme.ink }}>{text}</span>
          </div>
        ))}
      </Content>
    </>
  );
}
