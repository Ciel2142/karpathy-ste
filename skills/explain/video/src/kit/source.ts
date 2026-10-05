// The source lines a film may show. The code card draws only a `Source`, and the only way to get one is
// `sourceFromDisk`, which the pipeline calls with lines it read from disk. `requireFromDisk` is the check
// at run time: it throws for an object that `sourceFromDisk` did not make (a copy, a JSON round trip, a
// literal with the same keys, a cast), which no type check can promise. The brand below gives the plain
// mistake a compile-time message.
//
// This file is plain TypeScript with no imports, so Node can run it directly: the Python tests
// import it without a bundler.

// A type-level mark that exists only in the type: a plain object literal has no such property, so
// TypeScript refuses it where a `Source` is wanted. Not exported, so a scene cannot name it.
declare const fromDisk: unique symbol;

// `lines` start at line number `from` of the file `path`.
export type Source = {
  readonly path: string;
  readonly from: number;
  readonly lines: readonly string[];
  readonly [fromDisk]: true;
};

// The objects `sourceFromDisk` made. Private: nothing else can add to it.
const made = new WeakSet<object>();

// The one maker of a `Source`. It copies `lines` (a later change of the array it was given does not
// reach the source), freezes the copy and the object, and records the object.
export const sourceFromDisk = (raw: { path: string; from: number; lines: readonly string[] }): Source => {
  const source = Object.freeze({
    path: raw.path,
    from: raw.from,
    lines: Object.freeze([...raw.lines]),
  }) as Source;
  made.add(source);
  return source;
};

// Throws for a source that was not made by `sourceFromDisk`, and names the fix.
export const requireFromDisk = (source: Source): void => {
  if (!made.has(source)) {
    throw new Error('CodeCard: the source was not read from disk; declare it in "sources" of script.json');
  }
};
