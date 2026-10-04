// The motion of the generated background (RunnerLoop): which lane the block character runs in,
// its hop, the scrolling stripes and the obstacles coming down the road. Pure, with no imports,
// so Node can run this file directly and two renders draw the same frames.
//
// runnerState is a function of (frame, seed) alone; nothing is kept between calls. A beat is
// BEAT frames long, and everything random is drawn from a mulberry32 stream keyed by the seed and
// the beat index, never by the frame:
//   - the runner's lane for a beat, so the lane changes only on a beat boundary;
//   - whether the beat spawns an obstacle, and in which lane.
// An obstacle spawns at z = 0 on its beat's first frame and advances 1/60 per frame, so it is on
// screen for 60 frames, which is 3 beats. The obstacles of frame f are therefore the spawns of
// the 3 beats up to and including f's own beat. Beats before frame 0 take part too, so the road
// is already busy on the first frame.

export type Lane = 0 | 1 | 2;

export type RunnerState = {
  stripe: number; // scroll offset of the lane stripes in px, in [0, STRIPE_PERIOD)
  lane: Lane; // the lane the runner is in
  hop: number; // 0..1: the height of the hop, non-zero only in a beat that changes lane
  // On screen right now, far to near (z grows from the horizon at 0 towards the camera at 1).
  obstacles: { lane: Lane; z: number }[];
};

const BEAT = 20; // frames per beat
const OBSTACLE_FRAMES = 60; // z advances 1/60 per frame, from 0 up to (not including) 1
const BEATS_ALIVE = OBSTACLE_FRAMES / BEAT;
const SPAWN_CHANCE = 0.6;
const STRIPE_STEP = 24; // px per frame
const STRIPE_PERIOD = 120; // px; the dash pattern repeats every 120 px

// mulberry32: a small 32-bit PRNG. Each call to the returned function gives a number in [0, 1).
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), a | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function toLane(r: number): Lane {
  return r < 1 / 3 ? 0 : r < 2 / 3 ? 1 : 2;
}

function mod(n: number, m: number): number {
  return ((n % m) + m) % m;
}

// What a beat decides, from the seed and the beat index only.
function beatPlan(seed: number, beat: number): { lane: Lane; obstacleLane: Lane | null } {
  const rand = mulberry32((Math.imul(seed, 0x9e3779b1) + Math.imul(beat, 0x85ebca6b)) >>> 0);
  const lane = toLane(rand());
  const spawns = rand() < SPAWN_CHANCE;
  const obstacleLane = toLane(rand());
  return { lane, obstacleLane: spawns ? obstacleLane : null };
}

export function runnerState(frame: number, seed: number): RunnerState {
  const beat = Math.floor(frame / BEAT);
  const inBeat = mod(frame, BEAT);
  const plan = beatPlan(seed, beat);

  // The runner hops across the beat in which it changes lane, and only then.
  const changesLane = plan.lane !== beatPlan(seed, beat - 1).lane;
  const hop = changesLane ? Math.sin((Math.PI * inBeat) / BEAT) : 0;

  const obstacles: RunnerState["obstacles"] = [];
  for (let back = 0; back < BEATS_ALIVE; back++) {
    const { obstacleLane } = back === 0 ? plan : beatPlan(seed, beat - back);
    if (obstacleLane === null) continue;
    obstacles.push({ lane: obstacleLane, z: (inBeat + back * BEAT) / OBSTACLE_FRAMES });
  }

  return { stripe: mod(frame * STRIPE_STEP, STRIPE_PERIOD), lane: plan.lane, hop, obstacles };
}
