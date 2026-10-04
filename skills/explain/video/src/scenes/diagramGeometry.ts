// Geometry of a "diagram-with-highlight-walk" scene, in content-box coordinates: the 3x3
// grid, where an edge leaves and enters a node box, and where its label sits. The content size
// and the node size come from the SceneBox the caller reads.
import type { Size } from "../sceneBox";
import type { Cell } from "../types";

const GRID = [1 / 6, 1 / 2, 5 / 6];
export const EDGE_GAP = 6; // space between a box border and the line end
const LABEL_OFFSET = 14; // distance of the label's near side from the line

export type Point = { x: number; y: number };

// "a1".."c3": the letter is the column (left to right), the digit the row (top to bottom).
export const cellCentre = (cell: Cell, content: Size): Point => ({
  x: content.width * GRID["abc".indexOf(cell[0])],
  y: content.height * GRID[Number(cell[1]) - 1],
});

// Where the segment from a box centre towards `toward` leaves the box, plus EDGE_GAP.
const borderPoint = (centre: Point, toward: Point, node: Size): Point => {
  const dx = toward.x - centre.x;
  const dy = toward.y - centre.y;
  const tx = dx === 0 ? Infinity : (node.width / 2 + EDGE_GAP) / Math.abs(dx);
  const ty = dy === 0 ? Infinity : (node.height / 2 + EDGE_GAP) / Math.abs(dy);
  const t = Math.min(tx, ty);
  return { x: centre.x + dx * t, y: centre.y + dy * t };
};

// The visible line of an edge: from the border of `a` to the border of `b`.
export const segment = (a: Point, b: Point, node: Size): [Point, Point] => [
  borderPoint(a, b, node),
  borderPoint(b, a, node),
];

export const along = ([p0, p1]: [Point, Point], t: number): Point => ({
  x: p0.x + (p1.x - p0.x) * t,
  y: p0.y + (p1.y - p0.y) * t,
});

export type LabelPlace = {
  x: number;
  y: number;
  anchor: "start" | "middle" | "end";
  baseline: "text-before-edge" | "central" | "text-after-edge";
};

// The label sits beside the midpoint, on the right-hand normal of the line, and grows away
// from the line: its anchor and baseline follow the sign of each normal component, so no
// corner of the text box lies on the line's side.
export const labelPlace = ([p0, p1]: [Point, Point]): LabelPlace => {
  const len = Math.hypot(p1.x - p0.x, p1.y - p0.y) || 1;
  const normal = { x: -(p1.y - p0.y) / len, y: (p1.x - p0.x) / len };
  return {
    x: (p0.x + p1.x) / 2 + normal.x * LABEL_OFFSET,
    y: (p0.y + p1.y) / 2 + normal.y * LABEL_OFFSET,
    anchor: normal.x > 0.2 ? "start" : normal.x < -0.2 ? "end" : "middle",
    baseline: normal.y > 0.2 ? "text-before-edge" : normal.y < -0.2 ? "text-after-edge" : "central",
  };
};
