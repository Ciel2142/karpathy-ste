// Shapes of build/timeline.json, written by ../build-timeline.mjs (build mode) from the
// script and the measured clip lengths. Every frame number here is computed; none is
// hand-written. Cue frames are relative to the scene start.

export type CueFrames = Record<string, number>;

export type TitleProps = { title: string; subtitle: string; cue: string };

export type Bullet = { text: string; cue: string };
export type BulletsProps = { title: string; bullets: Bullet[] };

export type Cell = "a1" | "a2" | "a3" | "b1" | "b2" | "b3" | "c1" | "c2" | "c3";
export type DiagramNode = { id: string; label: string; sub?: string; cell: Cell };
export type DiagramEdge = { from: string; to: string; label?: string };
export type WalkStep = { node: string; cue: string };
export type DiagramProps = {
  title: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  walk: WalkStep[];
};

export type Highlight = { from: number; to: number; cue: string };
export type CodeProps = {
  title: string;
  source: { path: string; from: number; to: number };
  lines: string[]; // source lines from..to, added by build mode
  highlights: Highlight[];
};

export type Panel = { heading: string; lines: string[] };
export type BeforeAfterProps = {
  title: string;
  before: Panel;
  after: Panel;
  cue: string;
};

// One spoken word of a caption chunk; frames are relative to the scene start.
export type CaptionWord = { text: string; from: number; to: number };
// 1 to 3 words shown together from `from` up to (not including) `to`. A chunk can be
// zero-length (from == to) for a word under about 17 ms.
export type CaptionChunk = { from: number; to: number; words: CaptionWord[] };

// The brainrot background, chosen by pick_background.py and written into the timeline.
export type Background =
  | { kind: "clip"; file: string; src: string; start: number; seconds: number; loop: boolean }
  | { kind: "generated" };

// What every scene component receives: its own props plus its cue frames.
export type Cued<P> = P & { cueFrames: CueFrames };

type SceneTiming = {
  id: string;
  from: number; // first frame of the scene in the whole video
  durationInFrames: number; // leadFrames + audioFrames + tail
  leadFrames: number; // picture before the voice starts
  audioFrames: number; // ceil(clip seconds * fps)
  audio: string; // path under public/, e.g. audio/intro.say.wav
  cueFrames: CueFrames;
  captions?: CaptionChunk[]; // the captions of a brainrot scene
};

export type TimelineScene = SceneTiming &
  (
    | { component: "title"; props: TitleProps }
    | { component: "bullets-appear"; props: BulletsProps }
    | { component: "diagram-with-highlight-walk"; props: DiagramProps }
    | { component: "code-with-line-highlights"; props: CodeProps }
    | { component: "before-after"; props: BeforeAfterProps }
  );

// The timeline of a brainrot short: what build/timeline.json holds when its format is brainrot.
export type Timeline = {
  format: "brainrot";
  engine: string;
  fps: number;
  width: number;
  height: number;
  totalFrames: number;
  maxSceneSeconds: number;
  maxTotalSeconds: number;
  background?: Background; // the brainrot background, added by pick_background.py
  scenes: TimelineScene[];
};

// A film scene: no component and no cues. `sentences` (the start of each sentence) and `words` are
// frames relative to the scene start; the kit's makeAt turns them into marks.
export type FilmScene = {
  id: string;
  from: number;
  durationInFrames: number; // leadFrames + audioFrames + pause
  leadFrames: number;
  audioFrames: number;
  audio: string;
  sentences: number[];
  words: { text: string; from: number; to: number }[];
};

// A frame that the stills stage cuts (and the guard will measure): the middle of each sentence
// ("s<k>") and the last frame ("end") of each scene.
export type CheckFrame = { frame: number; scene: string; still: string };

// The declared lines of one source of the script, read from disk at build time (tabs as 4 spaces).
export type FilmSource = { path: string; from: number; lines: string[] };

// build/timeline.json of a film or a clip: the composition Film renders it.
export type FilmTimeline = {
  format: "film" | "clip";
  engine: string;
  fps: number;
  width: number;
  height: number;
  totalFrames: number;
  maxSceneSeconds: number;
  maxTotalSeconds: number;
  // The guard's text floor in px, from the format row.
  minText: number;
  sources: Record<string, FilmSource>;
  checkFrames: CheckFrame[];
  scenes: FilmScene[];
};
