// The box a scene lays out in. The composition gives every scene one SceneBox: the panel size,
// its margins and title band, and the type sizes the scenes use. Scenes read it with useBox()
// instead of module constants, so the same scene renders in the landscape frame or in a
// smaller panel.
//
// Placement contract: a scene draws inside its nearest positioned ancestor, which must be exactly
// box.width x box.height (Title fills it with AbsoluteFill; SceneTitle is placed with
// top/left/right: box.margin). A panel smaller than the frame needs a positioned wrapper of that size.
import { createContext, useContext } from "react";
import type { ReactElement, ReactNode } from "react";

export type Size = { width: number; height: number };

// The font and node sizes a scene draws with, all in px.
export type SceneType = {
  heroTitle: number; // Title scene: title font px
  heroSubtitle: number; // Title scene: subtitle font px
  bullet: number; // BulletsAppear text font px
  code: number; // CodeHighlights mono font px
  codeLine: number; // CodeHighlights line height px
  node: Size; // DiagramWalk node box
  nodeLabel: number;
  nodeSub: number;
  edgeLabel: number;
  panelHeading: number; // BeforeAfter heading font px
  panelLine: number; // BeforeAfter line font px
};

export type SceneBox = Size & {
  margin: number; // outer margin of the panel
  titleSize: number; // SceneTitle font px
  titleBand: number; // panel top margin -> top of the 2 px rule under the title
  type: SceneType;
};

// Today's explainer frame: 1280 x 720 at 30 fps, rendered exactly as before the box existed.
export const LANDSCAPE_BOX: SceneBox = {
  width: 1280,
  height: 720,
  margin: 48,
  titleSize: 44,
  titleBand: 60,
  type: {
    heroTitle: 64,
    heroSubtitle: 36,
    bullet: 32,
    code: 24,
    codeLine: 36,
    node: { width: 260, height: 96 },
    nodeLabel: 28,
    nodeSub: 20,
    edgeLabel: 22,
    panelHeading: 32,
    panelLine: 26,
  },
};

// No default value: a scene without a provider above it must fail, not draw at landscape size.
const SceneBoxContext = createContext<SceneBox | null>(null);

export function SceneBoxProvider({
  box,
  children,
}: {
  box: SceneBox;
  children: ReactNode;
}): ReactElement {
  return <SceneBoxContext.Provider value={box}>{children}</SceneBoxContext.Provider>;
}

export function useBox(): SceneBox {
  const box = useContext(SceneBoxContext);
  if (box === null) {
    throw new Error("useBox: no SceneBoxProvider above this scene");
  }
  return box;
}

// The body area under the title band: the box every scene body is laid out in.
export function contentRect(box: SceneBox): {
  left: number;
  top: number;
  width: number;
  height: number;
} {
  const top = box.margin + box.titleBand + 30;
  return {
    left: box.margin,
    top,
    width: box.width - 2 * box.margin,
    height: box.height - box.margin - top,
  };
}
