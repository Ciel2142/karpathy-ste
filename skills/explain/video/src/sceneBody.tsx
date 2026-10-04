// The body of one scene and its fade-in, shared by both layouts: Explain (landscape) and Short
// (brainrot) lay the same scene components out, each under its own SceneBox.
import type { ReactNode } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { BeforeAfter } from "./scenes/BeforeAfter";
import { BulletsAppear } from "./scenes/BulletsAppear";
import { CodeHighlights } from "./scenes/CodeHighlights";
import { DiagramWalk } from "./scenes/DiagramWalk";
import { Title } from "./scenes/Title";
import type { TimelineScene } from "./types";

export function SceneBody({ scene }: { scene: TimelineScene }) {
  const { cueFrames } = scene;
  switch (scene.component) {
    case "title":
      return <Title {...scene.props} cueFrames={cueFrames} />;
    case "bullets-appear":
      return <BulletsAppear {...scene.props} cueFrames={cueFrames} />;
    case "diagram-with-highlight-walk":
      return <DiagramWalk {...scene.props} cueFrames={cueFrames} />;
    case "code-with-line-highlights":
      return <CodeHighlights {...scene.props} cueFrames={cueFrames} />;
    case "before-after":
      return <BeforeAfter {...scene.props} cueFrames={cueFrames} />;
    default:
      throw new Error(`unknown scene component in ${JSON.stringify(scene)}`);
  }
}

export function FadeIn({ children }: { children: ReactNode }) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
}
