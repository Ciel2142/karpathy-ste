// The generated background of a brainrot short: three lanes in perspective, scrolling lane
// stripes, a block character that hops between lanes, and obstacles coming down the road. It draws
// runnerState(frame, seed) and nothing else, so two renders are the same frames.
//
// Projection: z runs from the horizon (0) to the camera (1). A point at depth z is at
// y = HORIZON + (HEIGHT - HORIZON) * z, and its offset from the centre line is its near offset
// times z; sizes scale by z. The lane stripes use the same projection from a world distance t
// ahead of the camera: z = NEAR_T / t, so a stripe of a fixed world length shrinks towards the
// horizon.
import type { ReactElement } from "react";
import { useCurrentFrame } from "remotion";
import { BRAINROT_BOX } from "../sceneBox";
import { runnerState, type Lane } from "./runner";

// The background is the lower half of the frame: as wide and as tall as the scene panel.
const { width: WIDTH, height: HEIGHT } = BRAINROT_BOX;
const CENTRE = WIDTH / 2;
const HORIZON = 220; // y of the horizon inside the background
const LANE_WIDTH = WIDTH / 3; // a lane at z = 1
const BLOCK = 120; // the runner's block, and an obstacle at z = 1
const RUNNER_Z = 0.82; // the depth the runner stands at
const HOP_LIFT = 140; // px of lift at hop = 1
const NEAR_T = 120; // world distance of z = 1; also the stripe period
const FAR_T = 1320; // stripes farther than this are not drawn (z = 0.09)
const DASH = 60; // world length of one stripe; the gap is NEAR_T - DASH
const CLIP_T = 100; // stripes nearer than this are past the bottom edge (z = 1.2)

const INK = {
  skyTop: "#1b0f3a",
  skyHorizon: "#6a2a8c",
  sun: "#ff5a9d",
  ground: "#0b0912",
  road: "#1c1a2e",
  edge: "#ff3d9a",
  stripe: "#d8dcff",
  runner: "#22d6ff",
  runnerEdge: "#0a3d4d",
  obstacle: "#ff4d4d",
  obstacleEdge: "#4a0d0d",
} as const;

const yAt = (z: number): number => HORIZON + (HEIGHT - HORIZON) * z;
// x of the lane's centre line at depth z; lane 1 is the middle lane.
const laneX = (lane: Lane, z: number): number => CENTRE + (lane - 1) * LANE_WIDTH * z;

function stripes(offset: number): ReactElement[] {
  const out: ReactElement[] = [];
  for (const boundary of [-0.5, 0.5]) {
    for (let k = -1; NEAR_T + k * NEAR_T - offset < FAR_T; k++) {
      const start = Math.max(NEAR_T + k * NEAR_T - offset, CLIP_T);
      const end = NEAR_T + k * NEAR_T - offset + DASH;
      if (end <= CLIP_T) continue;
      const zNear = NEAR_T / start;
      const zFar = NEAR_T / end;
      const half = (z: number): number => 5 * z; // half width of the stripe at depth z
      const x = (z: number): number => CENTRE + boundary * LANE_WIDTH * z;
      const points = [
        [x(zNear) - half(zNear), yAt(zNear)],
        [x(zNear) + half(zNear), yAt(zNear)],
        [x(zFar) + half(zFar), yAt(zFar)],
        [x(zFar) - half(zFar), yAt(zFar)],
      ]
        .map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`)
        .join(" ");
      out.push(<polygon key={`${boundary}:${k}`} points={points} fill={INK.stripe} />);
    }
  }
  return out;
}

function Obstacle({ lane, z }: { lane: Lane; z: number }): ReactElement {
  const size = BLOCK * z;
  return (
    <rect
      x={laneX(lane, z) - size / 2}
      y={yAt(z) - size}
      width={size}
      height={size}
      rx={size * 0.2}
      fill={INK.obstacle}
      stroke={INK.obstacleEdge}
      strokeWidth={Math.max(1, 6 * z)}
    />
  );
}

export function RunnerLoop({ seed }: { seed: number }): ReactElement {
  const frame = useCurrentFrame();
  const state = runnerState(frame, seed);
  const ground = yAt(RUNNER_Z);
  const lift = state.hop * HOP_LIFT;
  const x = laneX(state.lane, RUNNER_Z);
  // The obstacles come far to near; the ones nearer than the runner are drawn over it.
  const behind = state.obstacles.filter((o) => o.z < RUNNER_Z);
  const front = state.obstacles.filter((o) => o.z >= RUNNER_Z);
  return (
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ display: "block" }}>
      <defs>
        <linearGradient id="runner-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={INK.skyTop} />
          <stop offset="1" stopColor={INK.skyHorizon} />
        </linearGradient>
      </defs>
      <rect x={0} y={0} width={WIDTH} height={HORIZON} fill="url(#runner-sky)" />
      <circle cx={CENTRE} cy={HORIZON} r={170} fill={INK.sun} />
      <rect x={0} y={HORIZON} width={WIDTH} height={HEIGHT - HORIZON} fill={INK.ground} />
      <polygon points={`${CENTRE},${HORIZON} ${WIDTH},${HEIGHT} 0,${HEIGHT}`} fill={INK.road} />
      <line x1={CENTRE} y1={HORIZON} x2={0} y2={HEIGHT} stroke={INK.edge} strokeWidth={8} />
      <line x1={CENTRE} y1={HORIZON} x2={WIDTH} y2={HEIGHT} stroke={INK.edge} strokeWidth={8} />
      {stripes(state.stripe)}
      {behind.map((o, i) => (
        <Obstacle key={`b${i}`} lane={o.lane} z={o.z} />
      ))}
      <ellipse cx={x} cy={ground} rx={BLOCK / 2} ry={14} fill="#000000" opacity={0.4} />
      <rect
        x={x - BLOCK / 2}
        y={ground - BLOCK - lift}
        width={BLOCK}
        height={BLOCK}
        rx={28}
        fill={INK.runner}
        stroke={INK.runnerEdge}
        strokeWidth={6}
      />
      {front.map((o, i) => (
        <Obstacle key={`f${i}`} lane={o.lane} z={o.z} />
      ))}
    </svg>
  );
}
