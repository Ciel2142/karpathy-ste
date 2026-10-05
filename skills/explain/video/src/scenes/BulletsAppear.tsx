// "bullets-appear": each bullet slides in from the left and fades in at its cue; earlier
// bullets stay.
import { useCurrentFrame } from "remotion";
import { Content, cueAt, ramp, SceneTitle } from "../layout";
import { useBox } from "../sceneBox";
import { theme } from "../theme";
import type { BulletsProps, Cued } from "../types";

const FADE_FRAMES = 12;
const SLIDE_PX = 24;

export function BulletsAppear({ title, bullets, cueFrames }: Cued<BulletsProps>) {
  const frame = useCurrentFrame();
  const box = useBox();
  return (
    <>
      <SceneTitle text={title} />
      <Content style={{ display: "flex", flexDirection: "column", gap: 36, paddingTop: 24 }}>
        {bullets.map((bullet) => {
          const p = ramp(frame, cueAt(cueFrames, bullet.cue), FADE_FRAMES);
          return (
            <div
              key={bullet.cue}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 24,
                opacity: p,
                transform: `translateX(${(p - 1) * SLIDE_PX}px)`,
              }}
            >
              <div
                style={{
                  flex: "none",
                  width: 14,
                  height: 14,
                  background: theme.blue,
                }}
              />
              <div style={{ fontSize: box.type.bullet, lineHeight: 1.3 }}>{bullet.text}</div>
            </div>
          );
        })}
      </Content>
    </>
  );
}
