// The box a scene lays out in. The composition gives every scene one SceneBox: the panel size,
// its margins and title band, and the type sizes the scenes use. Scenes read it with useBox()
// (sceneBox.tsx) instead of module constants, so the same scene renders in the landscape frame
// or in a smaller panel.
//
// This file is plain TypeScript with no imports, so Node can run it directly: the Python
// geometry tests import it without a bundler. sceneBox.tsx re-exports everything here.
//
// Placement contract: a scene draws inside its nearest positioned ancestor, which must be exactly
// box.width x box.height (Title fills it with AbsoluteFill; SceneTitle is placed with
// top/left/right: box.margin). A panel smaller than the frame needs a positioned wrapper of that size.

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
  stackPanels: boolean; // BeforeAfter: before above after, not side by side
  type: SceneType;
};

// Today's explainer frame: 1280 x 720 at 30 fps, rendered exactly as before the box existed.
export const LANDSCAPE_BOX: SceneBox = {
  width: 1280,
  height: 720,
  margin: 48,
  titleSize: 44,
  titleBand: 60,
  stackPanels: false,
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

// The scene panel of a brainrot short: the top 1080 x 960 of the 1080 x 1920 frame. Its content
// box (984 x 758) is wider than tall, so before-after stacks by an explicit flag, not by aspect.
// A code row of a 3-digit gutter plus 40 columns is 45ch + 16 px: 45 x 0.61 x 34 + 16 = 949 px,
// inside the 984 px content width; 14 lines x 48 px = 672 px, inside the 758 px height.
export const BRAINROT_BOX: SceneBox = {
  width: 1080,
  height: 960,
  margin: 48,
  titleSize: 56,
  titleBand: 76,
  stackPanels: true,
  type: {
    heroTitle: 72,
    heroSubtitle: 44,
    bullet: 44,
    code: 34,
    codeLine: 48,
    node: { width: 280, height: 112 },
    nodeLabel: 32,
    nodeSub: 24,
    edgeLabel: 26,
    panelHeading: 38,
    panelLine: 32,
  },
};

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
