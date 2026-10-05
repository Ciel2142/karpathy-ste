// The marks of a film scene. A scene times every motion from a mark: the frame where a scene, a
// sentence or a word of its narration starts. `makeAt` turns the film scenes of the timeline
// (build-timeline.mjs) into the `at` function a scene calls, so the picture follows the voice.
//
// This file is plain TypeScript with no runtime imports, so Node can run it directly: the Python
// tests import it without a bundler.

// Where in a scene a mark falls: the start of its Nth sentence (from 1), or the start of a word of
// its narration. A word is found by its text; `nth` picks which time the scene says it (from 1). A mark
// is a sentence or a word, never both: `at` throws for an object with `sentence` and also `word` or
// `nth`, which the type itself does not refuse.
export type Where = { sentence: number } | { word: string; nth?: number };

// `at(scene)` is the start of the scene's first sentence, `at(scene, where)` a place inside it,
// `at.said(scene)` the end of the narration and `at.end(scene)` the end of the scene. All of them
// are film frames.
export type At<S extends string> = {
  (scene: S, where?: Where): number;
  said(scene: S): number;
  end(scene: S): number;
};

// A film scene of the timeline: `from` and `durationInFrames` are film frames, `leadFrames` and
// `audioFrames` lengths, `sentences` and `words` frames relative to the scene's `from`.
export type MarkScene = {
  id: string;
  from: number;
  durationInFrames: number;
  leadFrames: number;
  audioFrames: number;
  sentences: readonly number[];
  words: readonly { text: string; from: number; to: number }[];
};

const markError = (scene: string, why: string): Error => new Error(`MARK scene ${scene}: ${why}`);

const isCount = (n: number): boolean => Number.isInteger(n) && n >= 1;

// What a word and a token are compared by: lower case, with every character that is not a Unicode
// letter or digit removed. `Verify.sh` and the token `` `verify.sh` `` agree; `self` and `self-contained` do not.
const key = (text: string): string => text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

// The scene-relative frame of sentence `n` (from 1).
const sentenceFrame = (scene: MarkScene, n: number): number => {
  if (!isCount(n)) throw markError(scene.id, `sentence ${n} is not a positive integer`);
  if (n > scene.sentences.length) {
    throw markError(scene.id, `sentence ${n} is past the last one (${scene.sentences.length})`);
  }
  return scene.sentences[n - 1];
};

// The scene-relative frame of the start of the `nth` token (from 1) that matches `word`.
const wordFrame = (scene: MarkScene, word: string, nth: number): number => {
  const wanted = key(word);
  if (wanted === "") throw markError(scene.id, `word "${word}" has no letter or digit`);
  if (!isCount(nth)) throw markError(scene.id, `nth ${nth} is not a positive integer`);
  const found = scene.words.filter((w) => key(w.text) === wanted);
  if (found.length === 0) throw markError(scene.id, `word "${word}" is not in the narration`);
  if (nth > found.length) {
    throw markError(scene.id, `nth ${nth} is past the last "${word}" (${found.length})`);
  }
  return found[nth - 1].from;
};

// A scene is looked up in a Map, so an id like `constructor` is a missing scene, not an inherited member.
export const makeAt = <S extends string>(scenes: readonly MarkScene[]): At<S> => {
  const byId = new Map<string, MarkScene>(scenes.map((s): [string, MarkScene] => [s.id, s]));
  const find = (id: string): MarkScene => {
    const scene = byId.get(id);
    if (scene === undefined) throw markError(id, "no such scene");
    return scene;
  };

  const at = (id: S, where: Where = { sentence: 1 }): number => {
    const scene = find(id);
    let relative: number;
    if ("sentence" in where) {
      // tsc accepts a Where with both a sentence and a word (an excess-property check on a union only
      // refuses keys that no member has), so this is where that mistake is refused.
      if ("word" in where || "nth" in where) {
        throw markError(id, "a mark is a sentence or a word, not both");
      }
      relative = sentenceFrame(scene, where.sentence);
    } else {
      relative = wordFrame(scene, where.word, where.nth ?? 1);
    }
    return scene.from + relative;
  };
  at.said = (id: S): number => {
    const scene = find(id);
    return scene.from + scene.leadFrames + scene.audioFrames;
  };
  at.end = (id: S): number => {
    const scene = find(id);
    return scene.from + scene.durationInFrames;
  };
  return at;
};
