// "diagram-with-highlight-walk": nodes on a 3x3 grid joined by arrows. At each walk cue the
// next node takes the highlight and a token travels to it along an edge; visited nodes keep
// a light fill, and the token clears the label of the edge it is on.
import { Easing, interpolateColors, useCurrentFrame } from "remotion";
import { Content, cueAt, oneLine, ramp, SceneTitle } from "../layout";
import { contentRect, useBox } from "../sceneBox";
import { theme } from "../theme";
import type { Cued, DiagramEdge, DiagramProps, WalkStep } from "../types";
import { along, cellCentre, labelPlace, Point, segment } from "./diagramGeometry";

const TRAVEL_FRAMES = 15;
const TOKEN_RADIUS = 7; // 14 px disc
const ARROW = 14; // arrowhead length and width in px, whatever the stroke

type Token = { edge: number; reverse: boolean; at: Point };

// The edge the token takes into walk step j: the one joining it to the previous step (either
// direction), else one into it from any node visited before, else none.
const edgeInto = (edges: DiagramEdge[], walk: WalkStep[], j: number) => {
  const to = walk[j].node;
  const prev = walk[j - 1].node;
  const forward = edges.findIndex((e) => e.from === prev && e.to === to);
  if (forward >= 0) return { edge: forward, reverse: false };
  const backward = edges.findIndex((e) => e.from === to && e.to === prev);
  if (backward >= 0) return { edge: backward, reverse: true };
  const earlier = new Set(walk.slice(0, j).map((s) => s.node));
  const any = edges.findIndex((e) => e.to === to && earlier.has(e.from));
  return any >= 0 ? { edge: any, reverse: false } : null;
};

export function DiagramWalk({ title, nodes, edges, walk, cueFrames }: Cued<DiagramProps>) {
  const frame = useCurrentFrame();
  const box = useBox();
  const content = contentRect(box);
  const node = box.type.node;
  const centres = new Map<string, Point>(nodes.map((n) => [n.id, cellCentre(n.cell, content)]));
  const centre = (id: string): Point => {
    const found = centres.get(id);
    if (!found) throw new Error(`diagram-with-highlight-walk: unknown node ${JSON.stringify(id)}`);
    return found;
  };
  const lines = edges.map((e) => segment(centre(e.from), centre(e.to), node));

  // The walk step that holds the highlight (-1 before the first cue) and its progress.
  const starts = walk.map((step) => cueAt(cueFrames, step.cue));
  const current = starts.filter((start) => frame >= start).length - 1;
  const lit = current >= 0 ? ramp(frame, starts[current], TRAVEL_FRAMES) : 0;
  const visited = new Set(walk.slice(0, Math.max(current, 0)).map((s) => s.node));

  let token: Token | null = null;
  if (current >= 1 && frame > starts[current] && frame <= starts[current] + TRAVEL_FRAMES) {
    const route = edgeInto(edges, walk, current);
    if (route) {
      const t = Easing.inOut(Easing.cubic)(lit);
      token = { ...route, at: along(lines[route.edge], route.reverse ? 1 - t : t) };
    }
  }

  return (
    <>
      <SceneTitle text={title} />
      <Content>
        <svg
          width={content.width}
          height={content.height}
          style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="10"
              refY="5"
              markerUnits="userSpaceOnUse"
              markerWidth={ARROW}
              markerHeight={ARROW}
              orient="auto"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill={theme.muted} />
            </marker>
          </defs>
          {edges.map((e, i) => {
            const [p0, p1] = lines[i];
            const place = labelPlace(lines[i]);
            return (
              <g key={`${e.from}-${e.to}`}>
                <line
                  x1={p0.x}
                  y1={p0.y}
                  x2={p1.x}
                  y2={p1.y}
                  stroke={theme.muted}
                  strokeWidth={2.5}
                  markerEnd="url(#arrow)"
                />
                {e.label ? (
                  <text
                    x={place.x}
                    y={place.y}
                    textAnchor={place.anchor}
                    dominantBaseline={place.baseline}
                    fontFamily={theme.sans}
                    fontSize={box.type.edgeLabel}
                    fill={theme.muted}
                    opacity={token?.edge === i ? 0 : 1}
                  >
                    {e.label}
                  </text>
                ) : null}
              </g>
            );
          })}
          {token ? <circle cx={token.at.x} cy={token.at.y} r={TOKEN_RADIUS} fill={theme.blue} /> : null}
        </svg>
        {nodes.map((n) => {
          const c = centre(n.id);
          const rest = visited.has(n.id) ? theme.fill : theme.bg;
          const isCurrent = current >= 0 && walk[current].node === n.id;
          const p = isCurrent ? lit : 0;
          return (
            <div
              key={n.id}
              style={{
                position: "absolute",
                left: c.x - node.width / 2,
                top: c.y - node.height / 2,
                width: node.width,
                height: node.height,
                boxSizing: "border-box",
                padding: "0 10px",
                border: `3px solid ${interpolateColors(p, [0, 1], [theme.ink, theme.blue])}`,
                background: rest,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
              }}
            >
              <div style={{ position: "absolute", inset: 0, background: theme.blueTint, opacity: p }} />
              <div style={{ ...oneLine, position: "relative", maxWidth: "100%", fontSize: box.type.nodeLabel, fontWeight: 700, lineHeight: 1.2 }}>
                {n.label}
              </div>
              {n.sub ? (
                <div
                  style={{ ...oneLine, position: "relative", maxWidth: "100%", fontSize: box.type.nodeSub, lineHeight: 1.2, marginTop: 4, color: theme.muted }}
                >
                  {n.sub}
                </div>
              ) : null}
            </div>
          );
        })}
      </Content>
    </>
  );
}
