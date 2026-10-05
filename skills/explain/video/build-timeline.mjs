#!/usr/bin/env node
// script.json contract for the explain video rung: one validator, one timeline builder.
//
//   build-timeline.mjs --check <script.json> --root <data-root>
//       validate; exit 0 silently, or one "FAIL <where>: <cause>" line per cause and exit 1
//   build-timeline.mjs <script.json> <durations.json> <engine> <out.json> [--root <data-root>]
//       write the timeline JSON for the Remotion app (engine: say | kokoro); it starts with the
//       format, canvas and length budgets, and its lead and tail frames come from the format
//
// Exit 2 on a usage error. FAIL lines go to stdout. Build mode does not re-run the
// budgets: render.sh runs --check first.
//
// script.json may carry "format": "explainer" (the default when absent), "brainrot" or "film".
// Every per-format limit lives in formats.json, next to this file.
//
// A film script has no components: its scenes carry id, narration, cites and an optional pause
// (frames of silence after the audio, an integer from 12 to 90), and the script may carry a
// top-level "sources" array. --check adds these FAIL lines for a film (prefix "FAIL scene <id>: ";
// the count, key, id, narration and cites lines are the explainer's, with the tag ", film" on a
// line that names a limit):
//   FAIL script: <n> scenes (needs 3 to 30, film)
//   a film scene has no component or props    one line, for either key or both
//   pause <v> must be an integer from 12 to 90    <v> as JSON text; 12.0 parses as the integer 12
// "sources" is an allowed top-level key of a film only; "pause" is a scene key of a film only.
// The lines of a film come in this order: the header, the scene count, then for each scene the
// duplicate id line and the scene's own lines (must be an object; missing id, narration; the
// component line; unexpected keys; the id rules; the narration rules; the cites rules; the pause line).
//
// A brainrot build also reads <id>.<engine>.words.json, next to durations.json, for every
// scene (engine is the one actually used, so a Kokoro run that fell back to say reads
// <id>.say.words.json). It holds the sentence and word times of the narration in seconds
// from the clip start; each cue frame is its sentence start. Each brainrot scene also gets
//   "captions": [{ "from", "to", "words": [{ "text", "from", "to" }] }]
// chunks of up to three words and up to captionChars characters (one word may be longer, alone)
// that tile the speech without gaps, in frames from the scene start (text is the narration token
// without its backticks). A brainrot build adds these FAIL lines
// (prefix "FAIL scene <id>: ", <file> is that words file):
//   cannot read <file>: <code>              file missing or unreadable
//   <file> is not valid JSON: <message>
//   <file> has a bad shape at <where>       <where> is e.g. words[3].to or sentences
//   <file> has <n> words, the narration has <m>
//   <file> word <i> is "<text>", the narration has "<token>"
//   <file> ends at <t> s, after the clip end <s> s
//   cue "<cue>" does not start a sentence in <file>
// An explainer build reads no words file.
import fs from "node:fs";
import path from "node:path";

const FPS = 30;
const MIN_CUE_GAP = 15;
// The range of a film scene's own pause, in frames.
const MIN_PAUSE = 12;
const MAX_PAUSE = 90;
const TAB_COLUMNS = 4;
// Limits per format. The brainrot and film values are the spec starting values; tune them in formats.json
// only. The film row holds no component limit: a film has no components.
// wordTimed: build mode reads words files, takes cue frames from them and writes captions.
// A file that is missing, unreadable, not JSON or without the three rows ends the run here: the FAIL line
// and exit 1 (the same as finish, which is not defined yet at load time).
const loadFormats = () => {
  let cause;
  try {
    const rows = JSON.parse(fs.readFileSync(new URL("./formats.json", import.meta.url), "utf8"));
    const isRow = (row) => typeof row === "object" && row !== null && !Array.isArray(row);
    if (isRow(rows?.explainer) && isRow(rows?.film) && isRow(rows?.brainrot)) return rows;
    cause = "expected an object with an explainer, a film and a brainrot row";
  } catch (err) {
    cause = err.code ?? err.message;
  }
  console.log(`FAIL script: cannot read formats.json: ${cause}`);
  process.exit(1);
};
const FORMATS = loadFormats();
const ENGINES = ["say", "kokoro"];
const KINDS = ["file", "directory", "topic", "conversation"];
const SCENE_ID = /^[a-z0-9][a-z0-9-]*$/; // the id names audio files and stills
const CELLS = ["a", "b", "c"].flatMap((col) => ["1", "2", "3"].map((row) => col + row));
const USAGE =
  "usage: build-timeline.mjs --check <script.json> --root <data-root>\n" +
  "       build-timeline.mjs <script.json> <durations.json> <engine: say|kokoro> <out.json> [--root <data-root>]\n";

// ---------- small helpers ----------

const isObject = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
const isInt = (v) => Number.isInteger(v);
const isUrl = (s) => /^https?:\/\//.test(s);
const charLength = (s) => [...s].length;
const wordCount = (s) => s.split(/\s+/).filter(Boolean).length;
const isWordChar = (c) => c !== undefined && /[\p{L}\p{N}_]/u.test(c);
const q = (s) => JSON.stringify(s);

const readJson = (file, label) => {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (err) {
    return { fail: `FAIL script: cannot read ${label} ${file}: ${err.code ?? err.message}` };
  }
  try {
    return { value: JSON.parse(text) };
  } catch (err) {
    return { fail: `FAIL script: ${label} ${file} is not valid JSON: ${err.message}` };
  }
};

// ---------- props shapes ----------
// A shape maps each prop to a spec: str {max, optional, empty}, int, cell, obj {shape},
// arr {item, min, max}. `optional`: the key may be absent; `empty`: "" is allowed.

const str = (max, optional = false, empty = optional) => ({ t: "str", max, optional, empty });
const int = { t: "int" };
const cue = str(Infinity);
const arr = (item, min = 0, max = Infinity) => ({ t: "arr", item, min, max });
const obj = (shape) => ({ t: "obj", shape });
const cell = { t: "cell" };

// The shapes of one format: every limit comes from its FORMATS row.
const shapesFor = (limits) => {
  const side = obj({
    heading: str(limits.beforeAfterHeading),
    lines: arr(str(limits.beforeAfterLineChars, true), 0, limits.beforeAfterLines),
  });
  return {
    title: { title: str(limits.titleTitle), subtitle: str(limits.titleSubtitle), cue },
    "bullets-appear": { title: str(Infinity), bullets: arr(obj({ text: str(limits.bulletText), cue }), 2, 4) },
    "diagram-with-highlight-walk": {
      title: str(Infinity),
      nodes: arr(
        obj({ id: str(Infinity), label: str(limits.diagramLabel), sub: str(limits.diagramSub, true), cell }),
        2,
        7,
      ),
      edges: arr(obj({ from: str(Infinity), to: str(Infinity), label: str(10, true) })),
      walk: arr(obj({ node: str(Infinity), cue })),
    },
    "code-with-line-highlights": {
      title: str(Infinity),
      source: obj({ path: str(Infinity), from: int, to: int }),
      highlights: arr(obj({ from: int, to: int, cue })),
    },
    "before-after": { title: str(Infinity), before: side, after: side, cue },
  };
};

// Cues of a component in the order its author listed them (defensive: props may be malformed).
const list = (v) => (Array.isArray(v) ? v : []);
const cuesOf = (component, props) => {
  const p = isObject(props) ? props : {};
  const pick = (items, key) => list(items).map((item) => item?.[key]);
  const raw =
    component === "title" || component === "before-after"
      ? [p.cue]
      : component === "bullets-appear"
        ? pick(p.bullets, "cue")
        : component === "diagram-with-highlight-walk"
          ? pick(p.walk, "cue")
          : component === "code-with-line-highlights"
            ? pick(p.highlights, "cue")
            : [];
  return raw.filter((c) => typeof c === "string" && c !== "");
};

// Own keys only: a JSON key such as "constructor" or "__proto__" must not match an inherited name.
const has = (object, key) => Object.hasOwn(object, key);

// The script's format: "explainer" when the key is absent, else the raw value (possibly invalid).
const formatOf = (script) => (has(script, "format") ? script.format : "explainer");
const knownFormat = (format) => typeof format === "string" && has(FORMATS, format);
// An invalid format validates against the explainer limits.
const limitsFor = (format) => (knownFormat(format) ? FORMATS[format] : FORMATS.explainer);
// Suffix of every FAIL line that names a limit: nothing for explainer, ", brainrot" for brainrot,
// ", film" for film.
const tagOf = (format) => (knownFormat(format) && format !== "explainer" ? `, ${format}` : "");

// Only the formats made of components have shapes; the film row holds no component limit.
const COMPONENT_FORMATS = ["explainer", "brainrot"];
const SHAPES_BY_FORMAT = Object.fromEntries(COMPONENT_FORMATS.map((name) => [name, shapesFor(FORMATS[name])]));
// An invalid format validates against the explainer shapes.
const shapesOf = (format) => SHAPES_BY_FORMAT[COMPONENT_FORMATS.includes(format) ? format : "explainer"];

// Check a value against a spec; `fail(cause)` records one cause.
const checkSpec = (value, spec, where, fail, tag = "") => {
  if (spec.t === "str") {
    if (typeof value !== "string") return fail(`${where} must be a string`);
    if (value === "" && !spec.empty) return fail(`${where} is empty`);
    const n = charLength(value);
    if (n > spec.max) fail(`${where} is ${n} chars (max ${spec.max}${tag})`);
  } else if (spec.t === "int") {
    if (!isInt(value)) fail(`${where} must be an integer`);
  } else if (spec.t === "cell") {
    if (!CELLS.includes(value)) fail(`${where} ${q(value)} must be one of a1 to c3`);
  } else if (spec.t === "obj") {
    checkShape(value, spec.shape, where, fail, tag);
  } else if (spec.t === "arr") {
    if (!Array.isArray(value)) return fail(`${where} must be an array`);
    if (value.length < spec.min || value.length > spec.max) {
      const range = spec.max === Infinity ? `at least ${spec.min}` : `${spec.min} to ${spec.max}`;
      fail(`${where} has ${value.length} items (needs ${range}${tag})`);
    }
    value.forEach((item, i) => checkSpec(item, spec.item, `${where}[${i}]`, fail, tag));
  }
};

const checkShape = (value, shape, where, fail, tag = "") => {
  if (!isObject(value)) return fail(`${where || "props"} must be an object`);
  const at = (key) => (where ? `${where}.${key}` : key);
  for (const [key, spec] of Object.entries(shape)) {
    if (!has(value, key)) {
      if (!spec.optional) fail(`missing prop ${q(at(key))}`);
    } else {
      checkSpec(value[key], spec, at(key), fail, tag);
    }
  }
  for (const key of Object.keys(value)) if (!has(shape, key)) fail(`unexpected prop ${q(at(key))}`);
};

// ---------- cues ----------

// Positions where `cue` occurs in `narration` between word boundaries.
const cueMatches = (narration, cueText) => {
  const hits = [];
  for (let i = narration.indexOf(cueText); i >= 0; i = narration.indexOf(cueText, i + 1)) {
    if (!isWordChar(narration[i - 1]) && !isWordChar(narration[i + cueText.length])) hits.push(i);
  }
  return hits;
};

const atSentenceStart = (narration, offset) => offset === 0 || /[.!?]\s+$/.test(narration.slice(0, offset));

// Cue text rules: found, unique, at a sentence start, in narration order.
// The 15-frame distance needs the real clip length, so build mode checks it (see buildScenes).
const checkCues = (scene, fail) => {
  const { narration, component, props } = scene;
  if (typeof narration !== "string" || narration.trim() === "") return;
  let previous = -1;
  for (const cueText of cuesOf(component, props)) {
    const hits = cueMatches(narration, cueText);
    if (hits.length === 0) fail(`cue ${q(cueText)} is not in the narration`);
    else if (hits.length > 1) fail(`cue ${q(cueText)} is not unique in the narration`);
    else if (!atSentenceStart(narration, hits[0])) fail(`cue ${q(cueText)} is not at a sentence start`);
    else if (hits[0] <= previous) fail(`cue ${q(cueText)} is out of narration order`);
    if (hits.length === 1) previous = hits[0];
  }
};

// ---------- code source ----------

const columns = (line) => charLength(line) + (TAB_COLUMNS - 1) * (line.split("\t").length - 1);

// Lines of <root>/<file>, one entry per line, no trailing newline.
const readSourceLines = (root, file) => {
  const text = fs.readFileSync(path.join(root, file), "utf8");
  const lines = text.split("\n").map((l) => l.replace(/\r$/, ""));
  if (lines.at(-1) === "") lines.pop();
  return lines;
};

// A data-root path must be relative and stay inside the root: no "..", no absolute path.
const outsideRoot = (file) => {
  if (path.isAbsolute(file)) return true;
  const n = path.normalize(file);
  return n === "." || n === ".." || n.startsWith(".." + path.sep);
};

const sourceOk = (props) =>
  isObject(props?.source) &&
  typeof props.source.path === "string" &&
  isInt(props.source.from) &&
  isInt(props.source.to);

const checkCode = (props, root, fail, limits, tag) => {
  if (!sourceOk(props)) return;
  const { path: file, from, to } = props.source;
  if (from < 1 || from > to) return fail(`source range ${from}-${to} is not a valid line range`);
  if (to - from + 1 > limits.codeLines) {
    fail(`source range ${from}-${to} is ${to - from + 1} lines (max ${limits.codeLines}${tag})`);
  }
  if (outsideRoot(file)) return fail(`source.path ${q(file)} must be a relative path inside the data root`);
  let lines;
  try {
    lines = readSourceLines(root, file);
  } catch {
    return fail(`source.path ${file} cannot be read under the data root`);
  }
  if (to > lines.length) {
    fail(`source.to ${to} is outside ${file} (${lines.length} lines)`);
  } else {
    for (let n = from; n <= to; n++) {
      const cols = columns(lines[n - 1]);
      if (cols > limits.codeColumns) fail(`line ${n} is ${cols} columns (max ${limits.codeColumns}${tag})`);
    }
  }
  list(props.highlights).forEach((h, i) => {
    if (isInt(h?.from) && isInt(h?.to) && (h.from > h.to || h.from < from || h.to > to)) {
      fail(`highlights[${i}] range ${h.from}-${h.to} is outside the source range ${from}-${to}`);
    }
  });
};

// ---------- diagram references and cells ----------

const checkDiagram = (props, fail) => {
  const nodes = list(props.nodes).filter(isObject);
  const ids = new Set(nodes.map((n) => n.id));
  const cellOwner = new Map();
  list(props.nodes).forEach((n, i) => {
    if (!isObject(n) || !CELLS.includes(n.cell)) return;
    if (cellOwner.has(n.cell)) fail(`nodes[${i}].cell ${q(n.cell)} is already used by nodes[${cellOwner.get(n.cell)}]`);
    else cellOwner.set(n.cell, i);
  });
  list(props.edges).forEach((e, i) => {
    for (const end of ["from", "to"]) {
      if (isObject(e) && typeof e[end] === "string" && !ids.has(e[end])) fail(`edges[${i}].${end} ${q(e[end])} is not a node id`);
    }
  });
  list(props.walk).forEach((w, i) => {
    if (isObject(w) && typeof w.node === "string" && !ids.has(w.node)) fail(`walk[${i}].node ${q(w.node)} is not a node id`);
  });
};

// ---------- scene and script checks ----------

const CITE_SHAPE = { path: str(Infinity), line: int, snippet: str(Infinity) };

const checkCites = (cites, subjectKind, fail) => {
  if (!Array.isArray(cites)) return fail("cites must be an array");
  if (cites.length === 0 && (subjectKind === "file" || subjectKind === "directory")) {
    fail(`no cites (subject kind ${subjectKind})`);
  }
  cites.forEach((c, i) => {
    const where = `cites[${i}]`;
    if (!isObject(c)) return fail(`${where} must be an object`);
    const url = typeof c.path === "string" && isUrl(c.path);
    const shape = { ...CITE_SHAPE, line: { ...int, optional: url } };
    checkShape(c, shape, where, fail);
    if (isInt(c.line) && c.line < 1) fail(`${where}.line must be 1 or more`);
    if (typeof c.path === "string" && !url && outsideRoot(c.path)) {
      fail(`${where}.path ${q(c.path)} must be a relative path inside the data root`);
    }
  });
};

const checkSceneId = (id, fail) => {
  if (typeof id !== "string" || id === "") fail("id must be a non-empty string");
  else if (!SCENE_ID.test(id)) fail(`id ${q(id)} must match [a-z0-9-]`);
};

const checkNarration = (narration, fail, limits, tag) => {
  if (typeof narration !== "string" || narration.trim() === "") fail("narration is empty");
  else if (wordCount(narration) > limits.maxNarrationWords) {
    fail(`narration is ${wordCount(narration)} words (max ${limits.maxNarrationWords}${tag})`);
  }
};

const SCENE_KEYS = ["id", "component", "props", "narration", "cites"];

const checkScene = (scene, where, root, subjectKind, report, limits, shapes, tag) => {
  const fail = (cause) => report(where, cause);
  if (!isObject(scene)) return fail("must be an object");
  for (const key of SCENE_KEYS) if (!(key in scene) && key !== "cites") fail(`missing ${q(key)}`);
  for (const key of Object.keys(scene)) if (!SCENE_KEYS.includes(key)) fail(`unexpected key ${q(key)}`);
  if ("id" in scene) checkSceneId(scene.id, fail);
  if ("narration" in scene) checkNarration(scene.narration, fail, limits, tag);
  checkCites(scene.cites ?? [], subjectKind, fail);

  if ("component" in scene) {
    const known = typeof scene.component === "string" && has(shapes, scene.component);
    const shape = known ? shapes[scene.component] : undefined;
    if (!shape) return fail(`unknown component ${q(scene.component)}`);
    if ("props" in scene) {
      checkShape(scene.props, shape, "", fail, tag);
      if (isObject(scene.props)) {
        checkCues(scene, fail);
        if (scene.component === "diagram-with-highlight-walk") checkDiagram(scene.props, fail);
        if (scene.component === "code-with-line-highlights") checkCode(scene.props, root, fail, limits, tag);
      }
    }
  }
};

// The cause of a film scene's pause when it is not an integer from MIN_PAUSE to MAX_PAUSE, or "" when it
// holds. JSON.parse reads the text 12.0 as the integer 12, so 12.0 holds. Build mode reports the same cause.
const pauseCause = (value) =>
  isInt(value) && value >= MIN_PAUSE && value <= MAX_PAUSE
    ? ""
    : `pause ${q(value)} must be an integer from ${MIN_PAUSE} to ${MAX_PAUSE}`;

const FILM_SCENE_KEYS = ["id", "narration", "cites", "pause", "component", "props"];

// A film scene: id, narration, cites and an optional pause. Own keys only (`has`): an inherited name
// is never a present key. `component` and `props` are not scene keys of a film: one line for either
// key or both, and no unexpected-key line for them.
const checkFilmScene = (scene, where, subjectKind, report, limits, tag) => {
  const fail = (cause) => report(where, cause);
  if (!isObject(scene)) return fail("must be an object");
  for (const key of ["id", "narration"]) if (!has(scene, key)) fail(`missing ${q(key)}`);
  if (has(scene, "component") || has(scene, "props")) fail("a film scene has no component or props");
  for (const key of Object.keys(scene)) if (!FILM_SCENE_KEYS.includes(key)) fail(`unexpected key ${q(key)}`);
  if (has(scene, "id")) checkSceneId(scene.id, fail);
  if (has(scene, "narration")) checkNarration(scene.narration, fail, limits, tag);
  checkCites(scene.cites ?? [], subjectKind, fail);
  if (has(scene, "pause")) {
    const cause = pauseCause(scene.pause);
    if (cause !== "") fail(cause);
  }
};

const sceneWhere = (scene, index) =>
  typeof scene?.id === "string" && SCENE_ID.test(scene.id) ? `scene ${scene.id}` : `scene #${index + 1}`;

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const validDate = (s) => {
  const d = new Date(s);
  return DATE.test(s) && !Number.isNaN(d.getTime()) && d.toISOString().startsWith(s);
};

const checkHeader = (script, report) => {
  const fail = (cause) => report("script", cause);
  // `sources` belongs to a film only.
  const allowed = ["format", "title", "subject", "provenance", "scenes", ...(formatOf(script) === "film" ? ["sources"] : [])];
  for (const key of Object.keys(script)) if (!allowed.includes(key)) fail(`unexpected key ${q(key)}`);
  if (!knownFormat(formatOf(script))) fail("format must be explainer or brainrot");
  checkSpec(script.title, str(Infinity), "title", fail);
  checkShape(script.subject, { text: str(Infinity), kind: str(Infinity) }, "subject", fail);
  if (isObject(script.subject) && typeof script.subject.kind === "string" && !KINDS.includes(script.subject.kind)) {
    fail(`subject.kind ${q(script.subject.kind)} must be one of ${KINDS.join(", ")}`);
  }
  const prov = script.provenance;
  checkShape(
    prov,
    { root: str(Infinity), commit: str(Infinity), dirty: str(Infinity), date: str(Infinity), source: str(Infinity), not_covered: str(Infinity, false, true) },
    "provenance",
    fail,
  );
  if (isObject(prov)) {
    if (typeof prov.dirty === "string" && !["dirty", "no"].includes(prov.dirty)) fail(`provenance.dirty ${q(prov.dirty)} must be dirty or no`);
    if (typeof prov.date === "string" && prov.date !== "" && !validDate(prov.date)) fail(`provenance.date ${q(prov.date)} must be YYYY-MM-DD`);
  }
};

// Every cause, as FAIL lines, in document order.
const validate = (script, root) => {
  const lines = [];
  const report = (where, cause) => lines.push(`FAIL ${where}: ${cause}`);
  if (!isObject(script)) return ["FAIL script: top level must be an object"];
  checkHeader(script, report);
  const format = formatOf(script);
  const limits = limitsFor(format);
  const shapes = shapesOf(format);
  const tag = tagOf(format);
  const isFilm = format === "film";
  if (!Array.isArray(script.scenes)) {
    report("script", "scenes must be an array");
    return lines;
  }
  const count = script.scenes.length;
  if (count < limits.minScenes || count > limits.maxScenes) {
    report("script", `${count} scenes (needs ${limits.minScenes} to ${limits.maxScenes}${tag})`);
  }
  const kind = script.subject?.kind;
  const seen = new Set();
  script.scenes.forEach((scene, i) => {
    const id = scene?.id;
    if (typeof id === "string" && id !== "") {
      if (seen.has(id)) report("script", `duplicate scene id ${q(id)}`);
      seen.add(id);
    }
    const where = sceneWhere(scene, i);
    if (isFilm) checkFilmScene(scene, where, kind, report, limits, tag);
    else checkScene(scene, where, root, kind, report, limits, shapes, tag);
  });
  return lines;
};

// ---------- words ----------
// <id>.<engine>.words.json (spec 5.2): { sentences: [{from, to}], words: [{text, from, to}] },
// seconds from the clip start. words[i].text is the i-th narration token, verbatim.

// Seconds of slack for the producer's rounding: sentence-start matches and the clip end.
const WORDS_TOLERANCE = 0.001;
const tokensOf = (narration) => narration.split(/\s+/).filter(Boolean);
const isSeconds = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;

// Where the words object breaks the shape, or "" when it holds.
const wordsShapeError = (value) => {
  if (!isObject(value)) return "top level";
  for (const key of ["sentences", "words"]) {
    const items = value[key];
    if (!Array.isArray(items)) return key;
    for (let i = 0; i < items.length; i++) {
      const at = `${key}[${i}]`;
      const item = items[i];
      if (!isObject(item)) return at;
      if (key === "words" && typeof item.text !== "string") return `${at}.text`;
      if (!isSeconds(item.from)) return `${at}.from`;
      if (!isSeconds(item.to) || item.to < item.from) return `${at}.to`;
      if (key === "words" && i > 0 && items[i - 1].to > item.from) return `${at}.from`;
    }
  }
  return "";
};

// The words file of scene `id` next to durations.json, checked against the narration and the clip.
// Reports one cause through `bad` and returns undefined on the first failure.
const readWords = (dir, id, engine, narration, clipSeconds, bad) => {
  const file = `${id}.${engine}.words.json`;
  const stop = (cause) => {
    bad(cause);
  };
  let text;
  try {
    text = fs.readFileSync(path.join(dir, file), "utf8");
  } catch (err) {
    return stop(`cannot read ${file}: ${err.code ?? err.message}`);
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch (err) {
    return stop(`${file} is not valid JSON: ${err.message}`);
  }
  const where = wordsShapeError(value);
  if (where) return stop(`${file} has a bad shape at ${where}`);
  const { sentences, words } = value;
  const tokens = tokensOf(narration);
  if (words.length !== tokens.length) return stop(`${file} has ${words.length} words, the narration has ${tokens.length}`);
  const i = words.findIndex((w, k) => w.text !== tokens[k]);
  if (i >= 0) return stop(`${file} word ${i} is ${q(words[i].text)}, the narration has ${q(tokens[i])}`);
  const end = words.at(-1)?.to;
  if (end > clipSeconds + WORDS_TOLERANCE) return stop(`${file} ends at ${end} s, after the clip end ${clipSeconds} s`);
  return { file, sentences, words };
};

// The frame (relative to the scene start) of the sentence that `cueText` starts, or undefined
// after reporting that no sentence starts at the cue's first word. `file` only names the cause.
const cueFrameFromWords = (words, sentences, narration, cueText, leadFrames, bad, file) => {
  const [offset] = cueMatches(narration, cueText);
  const start = words[tokensOf(narration.slice(0, offset)).length]?.from;
  const sentence = sentences.find((s) => Math.abs(s.from - start) <= WORDS_TOLERANCE);
  if (sentence === undefined) {
    bad(`cue ${q(cueText)} does not start a sentence in ${file}`);
    return undefined;
  }
  return leadFrames + Math.round(sentence.from * FPS);
};

// ---------- captions ----------
// Caption chunks of a brainrot scene (spec 5.4). A chunk closes after CAPTION_WORDS words or
// after a word whose text ends in a mark, and before a word that would take its text over the
// character cap of the format (captionChars: the band draws one line). A word longer than the cap
// is a chunk alone. Each chunk lasts until the next one starts.

const CAPTION_WORDS = 3;
const CAPTION_BREAK = /[.,;:?!]$/;

// `words`: the words of a words file (seconds from the clip start); frames are scene-relative.
// `captionChars`: the cap of a chunk's text, its words joined by one space, without backticks;
// null (the explainer row) is no cap.
const captionChunks = (words, leadFrames, captionChars) => {
  const cap = captionChars ?? Infinity;
  const frame = (seconds) => leadFrames + Math.round(seconds * FPS);
  const groups = [];
  let open = [];
  for (const word of words) {
    const text = word.text.replaceAll("`", "");
    if (open.length > 0 && charLength([...open.map((w) => w.text), text].join(" ")) > cap) {
      groups.push(open);
      open = [];
    }
    open.push({ text, from: frame(word.from), to: frame(word.to) });
    if (open.length === CAPTION_WORDS || CAPTION_BREAK.test(text)) {
      groups.push(open);
      open = [];
    }
  }
  if (open.length > 0) groups.push(open);
  return groups.map((group, i) => ({
    from: group[0].from,
    to: i + 1 < groups.length ? groups[i + 1][0].from : group.at(-1).to,
    words: group,
  }));
};

// ---------- build mode ----------

// `limits`: the FORMATS row of the script's format; its wordTimed flag decides, for cue frames and
// captions alike, whether a scene reads a words file. `wordsDir`: the directory of durations.json,
// where those files live.
const buildScenes = (script, durations, engine, root, fail, limits, wordsDir) => {
  const { leadFrames, tailFrames, wordTimed, captionChars } = limits;
  const clips = isObject(durations?.scenes) ? durations.scenes : {};
  let from = 0;
  const out = [];
  list(script?.scenes).forEach((scene, i) => {
    const where = sceneWhere(scene, i);
    const bad = (cause) => fail(`FAIL ${where}: ${cause}`);
    if (!isObject(scene) || typeof scene.id !== "string" || typeof scene.narration !== "string" || !isObject(scene.props)) {
      return bad("needs id, narration and props to build");
    }
    const seconds = has(clips, scene.id) ? clips[scene.id] : undefined;
    if (seconds === undefined) return bad("no duration in durations.json");
    if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0) {
      return bad(`duration ${q(seconds)} must be a positive number of seconds`);
    }
    const clipFrames = Math.ceil(seconds * FPS);
    const props = { ...scene.props };
    if (scene.component === "code-with-line-highlights") {
      if (!sourceOk(props) || root === undefined) return bad("cannot read source lines (needs source and --root)");
      try {
        props.lines = readSourceLines(root, props.source.path).slice(props.source.from - 1, props.source.to);
      } catch {
        return bad(`source.path ${props.source.path} cannot be read under the data root`);
      }
    }
    const timing = wordTimed ? readWords(wordsDir, scene.id, engine, scene.narration, seconds, bad) : undefined;
    if (wordTimed && timing === undefined) return;
    const cueFrames = {};
    let previous = null;
    for (const cueText of cuesOf(scene.component, scene.props)) {
      const hits = cueMatches(scene.narration, cueText);
      if (hits.length === 0) {
        bad(`cue ${q(cueText)} is not in the narration`);
        continue;
      }
      const frame = timing
        ? cueFrameFromWords(timing.words, timing.sentences, scene.narration, cueText, leadFrames, bad, timing.file)
        : leadFrames + Math.round((hits[0] / scene.narration.length) * clipFrames);
      if (frame === undefined) continue;
      // The 15-frame distance is checked here, not by --check: it needs the real clip length.
      if (previous !== null && frame - previous < MIN_CUE_GAP) {
        bad(`cue ${q(cueText)} is ${frame - previous} frames after the previous cue (minimum ${MIN_CUE_GAP})`);
      }
      cueFrames[cueText] = frame;
      previous = frame;
    }
    const durationInFrames = leadFrames + clipFrames + tailFrames;
    out.push({
      id: scene.id,
      component: scene.component,
      props,
      from,
      durationInFrames,
      leadFrames,
      audioFrames: clipFrames,
      audio: `audio/${scene.id}.${engine}.wav`,
      cueFrames,
      ...(timing && { captions: captionChunks(timing.words, leadFrames, captionChars) }),
    });
    from += durationInFrames;
  });
  return out;
};

// ---------- command line ----------

const usageError = (msg) => {
  process.stderr.write(`build-timeline.mjs: ${msg}\n${USAGE}`);
  process.exit(2);
};

const parseArgs = (argv) => {
  const positional = [];
  let check = false;
  let root;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--check") check = true;
    else if (argv[i] === "--root") {
      root = argv[++i];
      if (root === undefined) usageError("--root needs a value");
    } else if (argv[i].startsWith("--")) usageError(`unknown option ${argv[i]}`);
    else positional.push(argv[i]);
  }
  return { check, root, positional };
};

const finish = (failures) => {
  for (const line of failures) console.log(line);
  process.exit(failures.length === 0 ? 0 : 1);
};

const main = () => {
  const { check, root, positional } = parseArgs(process.argv.slice(2));
  if (check) {
    if (positional.length !== 1 || root === undefined) usageError("--check needs <script.json> and --root <data-root>");
    const script = readJson(positional[0], "script");
    if (script.fail) finish([script.fail]);
    finish(validate(script.value, root));
  }
  if (positional.length !== 4) usageError("build mode needs <script.json> <durations.json> <engine> <out.json>");
  const [scriptFile, durationsFile, engine, outFile] = positional;
  if (!ENGINES.includes(engine)) usageError(`engine must be say or kokoro, got ${q(engine)}`);
  const script = readJson(scriptFile, "script");
  const durations = readJson(durationsFile, "durations");
  const failures = [script.fail, durations.fail].filter(Boolean);
  if (failures.length > 0) finish(failures);
  const format = isObject(script.value) ? formatOf(script.value) : "explainer";
  if (!knownFormat(format)) finish(["FAIL script: format must be explainer or brainrot"]);
  const limits = FORMATS[format];
  const wordsDir = path.dirname(durationsFile);
  const scenes = buildScenes(script.value, durations.value, engine, root, (line) => failures.push(line), limits, wordsDir);
  if (failures.length > 0) finish(failures);
  const totalFrames = scenes.reduce((sum, s) => sum + s.durationInFrames, 0);
  const { width, height, maxSceneSeconds, maxTotalSeconds } = limits;
  const timeline = { format, fps: FPS, width, height, totalFrames, maxSceneSeconds, maxTotalSeconds, engine, scenes };
  try {
    fs.mkdirSync(path.dirname(path.resolve(outFile)), { recursive: true });
    fs.writeFileSync(outFile, JSON.stringify(timeline, null, 2) + "\n");
  } catch (err) {
    finish([`FAIL script: cannot write ${outFile}: ${err.code ?? err.message}`]);
  }
};

main();
