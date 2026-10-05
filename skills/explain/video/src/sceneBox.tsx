// The React side of the SceneBox: the provider the composition wraps each scene in and the hook
// the scenes read it with. The box type, the box values and contentRect live in box.ts (plain
// TypeScript, so Node can import them in tests) and are re-exported here.
import { createContext, useContext } from "react";
import type { ReactElement, ReactNode } from "react";
import type { SceneBox } from "./box";

export { BRAINROT_BOX, LANDSCAPE_BOX, codeLineLimit, contentRect } from "./box";
export type { SceneBox, SceneType, Size } from "./box";

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
