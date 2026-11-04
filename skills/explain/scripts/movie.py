#!/usr/bin/env python3
"""Movie plan for `explain --as movie`: reads, writes and checks `movie.json`, writes the
bridges and stitches the movie.

Usage: see USAGE below (check, bridges, stitch, status). Exit 0 on all ok, 1 on a failure
found, 2 on a usage error, unreadable JSON or (for `stitch`) no Remotion CLI.

`<dir>` is the movie output directory; it holds `movie.json`. `provenance.root` is absolute,
or relative to `<dir>` (the test fixture uses `.`). Every write is atomic: a temporary file in
the same directory, then `os.replace` (`save` writes `movie.json` that way).

`check` prints one failure per line, then
`plan: ok (<q> questions, <c> chapters, <lo>..<hi> s with bridges)` or `plan: <n> failures`.
`<lo>` and `<hi>` are the sum of the chapter `seconds` plus a bridge of 8 s, then of 15 s, in
each gap (spec 4.4); `<lo>` must be at least 240 and `<hi>` at most 900, else
`schema: seconds sum <s>, <lo>..<hi> s with bridges (min 240, max 900)`.
Failure prefixes are fixed: `schema:`, `id:`, `question <id>:`,
`chapter <id>:`, `cite <question-id>#<n>:` (the rules of `cite_check`), `prose:` (an
`ste_lint.py --html` error line) and `state:`.

`bridges` refuses a plan that fails `check`: it prints the failures and the count line of
`check`, exits 1 and writes nothing. Otherwise it writes, for each gap `<n>` between chapter
`<n>` and chapter `<n+1>`, `bridges/<n>/script.json` (a clip, from BRIDGE_TEMPLATE_SCRIPT) and
`bridges/<n>/scene/Film.tsx` (from BRIDGE_TEMPLATE_SCENE), then prints `bridges: ok (<n>)`.
The values come from `movie.json` alone, so a second run writes the same bytes. A bridge's
subject is the movie's subject text with kind `topic`: a bridge cites nothing, and the
timeline check allows a scene without cites only for a topic.

`stitch` joins chapter 1, bridge 1, chapter 2, ..., chapter n into `video.mp4` and writes
`chapters.json` (`[{"id", "title", "start"}]`, the start being the float sum, unrounded, of
the durations in seconds of the parts before the chapter). It does not run `check`. It
prints one line per stage, in this order; the first FAIL stops it with exit 1:
  parts: ok (<n>) | FAIL chapter <id> is <status>, not built | FAIL <part> missing
         | FAIL <part> <what> differs | FAIL <part> <probe cause> | FAIL no chapters
  concat: ok (<s> s) | FAIL ffmpeg exit <n>
  container: ok (<s> s) | FAIL streams <types> (expected one video and one audio)
         | FAIL duration <d> s, expected <s> s | FAIL <probe cause>
  length: ok (<s> s) | FAIL <s> s (min 240, max 900)
Every chapter must be `built` before any part is looked at; then every part must have its
`video.mp4`, and each part's probe must match the first part's in `<what>`: video codec, audio
codec, width, height, frame rate, audio rate. `<part>` is the path under `<dir>`
(`bridges/1/video.mp4`); a `<probe cause>` is `ffprobe exit <n>` or `ffprobe output unreadable`.
`concat` writes `build/concat.txt` and runs ffmpeg with the concat demuxer and stream copy into
`build/video.part.mp4`; its seconds are the sum of the parts. `container` probes that file:
one video and one audio stream, a duration within 0.5 s of the sum; then it replaces
`video.mp4` with it and writes `chapters.json`, so a stitch that fails earlier leaves the old
`video.mp4`. `transcript` follows `container`: it reads each chapter's `chapters/<id>/index.html`
and finds the chapter's viewer still, the `-end` still of the last scene before `answer` other
than `ask`, as the render names it: `chapters/<id>/review/still-NN-<scene>-end.png`, NN the
1-based place of the scene. Its lines:
  transcript: ok (<n> chapters) | FAIL chapter <id>: no transcript
         | FAIL chapter <id>: transcript has no section <ask|answer>
         | FAIL chapter <id>: transcript has no section before answer
         | FAIL chapter <id>: no still <path>
`<path>` is the still's path under `<dir>`. Then it writes `build/hub-sections.html` (a section
per chapter, with narration, cites and a link to the chapter's transcript), copies chapter k's
still to `review/viewer-stills/<k>-<id>.png` (k from 1) and writes
`review/viewer-transcript.html` (the title, the question texts, a section per chapter without
`ask`, `answer`, cites and link that ends with the text `still: viewer-stills/<k>-<id>.png`
and that still as an image). The transcript markup is read with a section regex over the
text between `<main>` and `</main>`, not an HTML parser: the markup is the one
`video/transcript.py` writes (a `<section id>` holding `<h2>`, `<p>` and an optional
`div.cites`, none of them nested), and the regex keeps inline tags as written.
`hub` follows `transcript`: it fills `templates/movie.html` from `movie.json`, the chapter
starts and `build/hub-sections.html`, and writes `index.html` (`hub: ok index.html`).
`length` is last and only sets the exit code, on the container's duration.
Seconds print with one decimal. ffprobe (`-of json`) and ffmpeg are those of the Remotion CLI,
`<ws>/app/node_modules/.bin/remotion` with `<ws>` from `$EXPLAIN_VIDEO_WORKSPACE`, else
`~/karpathy/video-workspace`; they run with cwd `<ws>/app` and stdin from /dev/null, as
check_render.sh runs them, through `run`, the one subprocess seam of the stitch. Without the
CLI, `stitch` prints `no Remotion CLI at <path>` on stderr and exits 2.
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

from cite_check import fact_problems
from course import _find_ste_lint

USAGE = (
    "usage: movie.py check <dir>\n"
    "       movie.py bridges <dir>\n"
    "       movie.py stitch <dir>\n"
    "       movie.py status <dir>\n"
)
MOVIE_FILE = "movie.json"
VERSION = 1
MIN_QUESTIONS, MAX_QUESTIONS = 3, 5
MIN_CHAPTERS, MAX_CHAPTERS = 4, 10
MIN_SECONDS, MAX_SECONDS = 30, 150
MIN_TOTAL, MAX_TOTAL = 240, 900
MIN_BRIDGE, MAX_BRIDGE = 8, 15  # seconds of a bridge (spec 4.4)
MAX_ANSWERS = 2
STATES = ("planned", "building", "stitched")
STATUSES = ("pending", "built", "failed")
KINDS = ("topic", "file", "directory")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
STE_ERROR = re.compile(r"^\d+:\d+  (E .*)$")
PROVENANCE_KEYS = ("root", "commit", "dirty", "date", "source", "not_covered")
CHAPTER_TEXT = ("title", "question", "picture", "ends_with")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_TEMPLATE_SCENE = os.path.join(SKILL_DIR, "video", "src", "bridge")
BRIDGE_TEMPLATE_SCRIPT = os.path.join(SKILL_DIR, "templates", "movie-bridge-script.json")
SCRIPT_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")  # inside a string of the script template
SCENE_PLACEHOLDER = re.compile(r'"\{\{(done|sofar|next)\}\}"')  # a string literal of the scene
REMOTION_IN_APP = ("node_modules", ".bin", "remotion")  # the Remotion CLI under <workspace>/app
PROBE_ENTRIES = "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate:format=duration"
PART_FIELDS = (("vcodec", "video codec"), ("acodec", "audio codec"), ("width", "width"),
               ("height", "height"), ("fps", "frame rate"), ("rate", "audio rate"))
LENGTH_SLACK = 0.5  # seconds the concat may differ from the sum of its parts
BUILD_DIR, CONCAT_FILE, PART_FILE = "build", "concat.txt", "video.part.mp4"
VIDEO_FILE, CHAPTERS_FILE = "video.mp4", "chapters.json"


class ReadError(Exception):
    """`movie.json` is missing, not JSON, or not an object."""


def load(movie_dir):
    """Return the parsed `<movie_dir>/movie.json`; raise ReadError."""
    path = os.path.join(movie_dir, MOVIE_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise ReadError("cannot read %s: %s" % (path, " ".join(str(error).split()))) from error
    if not isinstance(data, dict):
        raise ReadError("cannot read %s: top level must be an object" % path)
    return data


def _write_atomic(path, text):
    """Write `text` to `path` through a temporary file in the same directory; on failure the old
    file stays and no temp is left."""
    fd, temp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp",
                                dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o644)  # mkstemp makes 0600; keep the file readable
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def save(movie_dir, movie):
    """Write `movie.json` atomically; on failure the old file stays and no temp is left."""
    _write_atomic(os.path.join(movie_dir, MOVIE_FILE),
                  json.dumps(movie, indent=2, ensure_ascii=False) + "\n")


def resolve_root(movie_dir, root):
    """The absolute directory of `root`: as given, or relative to the movie directory."""
    return os.path.normpath(os.path.join(os.path.abspath(movie_dir), root))


# --- helpers --------------------------------------------------------------------------


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _objects(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _label(item, index):
    ident = item.get("id")
    return ident if isinstance(ident, str) and ident else str(index)


def _str_list(value):
    return [name for name in value if isinstance(name, str)] if isinstance(value, list) else []


# --- checks ---------------------------------------------------------------------------


def _check_top(movie):
    failures = []
    if "version" not in movie:
        failures.append("schema: version is missing")
    elif not _is_int(movie["version"]) or movie["version"] != VERSION:
        failures.append("schema: version must be %d" % VERSION)
    for key in ("title", "question", "lang"):
        if key not in movie:
            failures.append("schema: %s is missing" % key)
        elif not isinstance(movie[key], str):
            failures.append("schema: %s must be a string" % key)
    for key, kind, name in (("pronounce", dict, "an object"), ("review", bool, "a boolean")):
        if key not in movie:
            failures.append("schema: %s is missing" % key)
        elif not isinstance(movie[key], kind):
            failures.append("schema: %s must be %s" % (key, name))
    failures += _check_subject(movie.get("subject", None), "subject" in movie)
    failures += _check_provenance(movie.get("provenance", None), "provenance" in movie)
    if "state" not in movie:
        failures.append("schema: state is missing")
    elif movie["state"] not in STATES:
        failures.append("state: must be one of %s" % ", ".join(STATES))
    return failures


def _check_subject(subject, present):
    if not present:
        return ["schema: subject is missing"]
    if not isinstance(subject, dict):
        return ["schema: subject must be an object"]
    failures = []
    if not isinstance(subject.get("text"), str):
        failures.append("schema: subject.text must be a string")
    if subject.get("kind") not in KINDS:
        failures.append("schema: subject.kind must be one of %s" % ", ".join(KINDS))
    return failures


def _check_provenance(provenance, present):
    if not present:
        return ["schema: provenance is missing"]
    if not isinstance(provenance, dict):
        return ["schema: provenance must be an object"]
    return ["schema: provenance.%s must be a string" % key
            for key in PROVENANCE_KEYS if not isinstance(provenance.get(key), str)]


def _count_failure(key, value, low, high):
    if not isinstance(value, list):
        return ["schema: %s must be a list" % key]
    if not low <= len(value) <= high:
        return ["schema: %s has %d entries (min %d, max %d)" % (key, len(value), low, high)]
    return []


def _check_questions(movie):
    questions = movie.get("questions")
    failures = _count_failure("questions", questions, MIN_QUESTIONS, MAX_QUESTIONS)
    kind = movie["subject"].get("kind") if isinstance(movie.get("subject"), dict) else None
    for index, question in enumerate(questions if isinstance(questions, list) else []):
        if not isinstance(question, dict):
            failures.append("schema: questions[%d] must be an object" % index)
            continue
        label = _label(question, index)
        failures += _check_id("question", question, label)
        for key in ("text", "answer"):
            if not isinstance(question.get(key), str):
                failures.append("question %s: %s must be a string" % (label, key))
        cites = question.get("cites")
        if not isinstance(cites, list):
            failures.append("question %s: cites must be a list" % label)
        else:
            failures += _check_cite_shapes(label, cites)
            if kind in ("file", "directory") and not cites:
                failures.append("question %s: a file or directory subject needs at least"
                                " one cite" % label)
    return failures


def _check_id(what, item, label):
    ident = item.get("id")
    if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident):
        return ["%s %s: id must match [a-z0-9][a-z0-9-]*" % (what, label)]
    return []


def _cite_shape_ok(cite):
    return (isinstance(cite, dict)
            and isinstance(cite.get("path"), str) and bool(cite["path"])
            and _is_int(cite.get("line")) and cite["line"] >= 1
            and isinstance(cite.get("snippet"), str) and bool(cite["snippet"].strip()))


def _check_cite_shapes(label, cites):
    failures = []
    for number, cite in enumerate(cites, start=1):
        if not _cite_shape_ok(cite):
            failures.append("question %s: cite %d needs path, line and snippet" % (label, number))
    return failures


def _check_chapters(movie):
    chapters = movie.get("chapters")
    failures = _count_failure("chapters", chapters, MIN_CHAPTERS, MAX_CHAPTERS)
    known = set(_ids(movie.get("questions")))
    seconds, all_valid = 0, isinstance(chapters, list)
    for index, chapter in enumerate(chapters if isinstance(chapters, list) else []):
        if not isinstance(chapter, dict):
            failures.append("schema: chapters[%d] must be an object" % index)
            all_valid = False
            continue
        label = _label(chapter, index)
        failures += _check_id("chapter", chapter, label)
        failures += _check_chapter_fields(chapter, label, known)
        value = chapter.get("seconds")
        if _is_int(value) and MIN_SECONDS <= value <= MAX_SECONDS:
            seconds += value
        else:
            failures.append("chapter %s: seconds must be an integer from %d to %d"
                            % (label, MIN_SECONDS, MAX_SECONDS))
            all_valid = False
    if all_valid:
        low, high = _with_bridges(seconds, len(chapters))
        if low < MIN_TOTAL or high > MAX_TOTAL:
            failures.append("schema: seconds sum %d, %d..%d s with bridges (min %d, max %d)"
                            % (seconds, low, high, MIN_TOTAL, MAX_TOTAL))
    return failures


def _with_bridges(seconds, chapters):
    """(low, high): the seconds of `chapters` chapters that sum to `seconds`, plus a bridge of
    MIN_BRIDGE, then of MAX_BRIDGE seconds in each gap between two chapters."""
    gaps = max(chapters - 1, 0)
    return seconds + gaps * MIN_BRIDGE, seconds + gaps * MAX_BRIDGE


def _check_chapter_fields(chapter, label, known):
    failures = ["chapter %s: %s must be a string" % (label, key)
                for key in CHAPTER_TEXT if not isinstance(chapter.get(key), str)]
    if chapter.get("status") not in STATUSES:
        failures.append("chapter %s: status must be one of %s" % (label, ", ".join(STATUSES)))
    if not isinstance(chapter.get("reason"), str):
        failures.append("chapter %s: reason must be a string" % label)
    answers = chapter.get("answers")
    if not isinstance(answers, list) or not all(isinstance(a, str) for a in answers):
        failures.append("chapter %s: answers must be a list of question ids" % label)
        return failures
    if len(answers) > MAX_ANSWERS:
        failures.append("chapter %s: answers has %d entries (max %d)"
                        % (label, len(answers), MAX_ANSWERS))
    elif not answers:
        failures.append("chapter %s: answers has 0 entries (min 1)" % label)
    failures += ["chapter %s: answers names %s, not a question" % (label, name)
                 for name in answers if name not in known]
    return failures


def _ids(items):
    return [item["id"] for item in _objects(items) if isinstance(item.get("id"), str)]


def _check_coverage(movie):
    named = {name for chapter in _objects(movie.get("chapters"))
             for name in _str_list(chapter.get("answers"))}
    return ["question %s: no chapter answers it" % ident
            for ident in dict.fromkeys(_ids(movie.get("questions"))) if ident not in named]


def _check_duplicates(movie):
    ids = _ids(movie.get("questions")) + _ids(movie.get("chapters"))
    return ["id: %s is used twice" % ident for ident in dict.fromkeys(ids) if ids.count(ident) > 1]


def _check_cites(movie_dir, movie):
    provenance = movie.get("provenance")
    root = provenance.get("root") if isinstance(provenance, dict) else None
    if not isinstance(root, str):
        return []
    root = resolve_root(movie_dir, root)
    failures = []
    for question in _objects(movie.get("questions")):
        ident = question.get("id")
        if not isinstance(ident, str):
            continue
        cites = question.get("cites")
        for number, cite in enumerate(cites if isinstance(cites, list) else [], start=1):
            if _cite_shape_ok(cite):
                failures += ["cite %s#%d: %s" % (ident, number, problem) for problem in
                             fact_problems(cite["path"], cite["line"], cite["snippet"], root)]
    return failures


def _check_state(movie):
    if movie.get("state") != "stitched":
        return []
    return ["state: stitched but chapter %s is not built" % _label(chapter, index)
            for index, chapter in enumerate(_objects(movie.get("chapters")))
            if chapter.get("status") != "built"]


def _prose_fields(movie):
    """`(field path, text)` of each prose field, in document order; empty fields are left out."""
    fields = [("title", movie.get("title")), ("question", movie.get("question"))]
    for index, question in enumerate(_objects(movie.get("questions"))):
        label = _label(question, index)
        fields += [("questions[%s].%s" % (label, key), question.get(key))
                   for key in ("text", "answer")]
    for index, chapter in enumerate(_objects(movie.get("chapters"))):
        label = _label(chapter, index)
        fields += [("chapters[%s].%s" % (label, key), chapter.get(key)) for key in CHAPTER_TEXT]
    provenance = movie.get("provenance")
    if isinstance(provenance, dict):
        fields.append(("provenance.not_covered", provenance.get("not_covered")))
    return [(path, " ".join(text.split())) for path, text in fields
            if isinstance(text, str) and text.strip()]


def _check_prose(movie):
    """`prose:` failures: the prose fields as one HTML document through `ste_lint.py --html`,
    one whitespace-collapsed `<p>` per line so the line of an error names the field."""
    fields = _prose_fields(movie)
    if not fields:
        return []
    linter = _find_ste_lint()
    if linter is None:
        return ["prose: ste_lint.py not found"]
    lang = movie.get("lang") if isinstance(movie.get("lang"), str) and movie["lang"] else "en"
    first = 2  # line 1 is the opening tag
    document = '<html lang="%s"><body>\n%s\n</body></html>\n' % (
        html.escape(lang), "\n".join("<p>%s</p>" % html.escape(text) for _, text in fields))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prose.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(document)
        try:
            result = subprocess.run([sys.executable, "-B", linter, "--html", path],
                                    capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            return ["prose: ste_lint.py failed: %s" % error]
    errors = []
    for line in result.stdout.splitlines():
        found = STE_ERROR.match(line)
        if found:
            number = int(line.split(":", 1)[0]) - first
            where = fields[number][0] if 0 <= number < len(fields) else "(unknown field)"
            errors.append("prose: %s: %s" % (where, found.group(1)))
    if result.returncode not in (0, 1) or (result.returncode == 1 and not errors):
        return ["prose: ste_lint.py failed: exit %d" % result.returncode]
    return errors


def check_chapter_script(movie_dir, chapter):
    """Failures of `chapters/<id>/script.json` against spec 4.3; empty when there is no script."""
    ident = chapter.get("id")
    if not isinstance(ident, str):
        return []
    path = os.path.join(movie_dir, "chapters", ident, "script.json")
    if not os.path.isfile(path):
        return []
    prefix = "chapter %s: " % ident
    try:
        with open(path, encoding="utf-8") as handle:
            script = json.load(handle)
    except (OSError, ValueError):
        return [prefix + "script.json cannot be read"]
    if not isinstance(script, dict):
        return [prefix + "script.json must be an object"]
    failures = []
    if script.get("format") != "film":
        failures.append(prefix + "format is %s, not film" % script.get("format"))
    title = chapter.get("title")
    if script.get("title") != title:
        failures.append(prefix + 'script title "%s" differs from "%s"' % (script.get("title"), title))
    scenes = _objects(script.get("scenes"))
    if not scenes:
        return failures + [prefix + "script has no scenes"]
    for position, name, scene in (("first", "ask", scenes[0]), ("last", "answer", scenes[-1])):
        if scene.get("id") != name:
            failures.append(prefix + "%s scene is %s, not %s" % (position, scene.get("id"), name))
    return failures


def check(movie_dir, movie):
    """Return the failures of `movie`, one per fault; empty means ok. Changes no state."""
    failures = _check_top(movie)
    failures += _check_questions(movie)
    failures += _check_chapters(movie)
    failures += _check_duplicates(movie)
    failures += _check_coverage(movie)
    failures += _check_cites(movie_dir, movie)
    failures += _check_prose(movie)
    failures += _check_state(movie)
    for chapter in _objects(movie.get("chapters")):
        failures += check_chapter_script(movie_dir, chapter)
    return failures


def status(movie_dir, movie):
    """The `status` lines: one per chapter, one per stray chapter directory, then the state."""
    chapters = _objects(movie.get("chapters"))
    lines = []
    for chapter in chapters:
        reason = chapter.get("reason")
        lines.append("chapter: %s %s%s" % (chapter.get("id"), chapter.get("status"),
                                           " " + reason if isinstance(reason, str) and reason else ""))
    known = set(_ids(chapters))
    root = os.path.join(movie_dir, "chapters")
    names = sorted(os.listdir(root)) if os.path.isdir(root) else []
    lines += ["stray: chapters/%s" % name for name in names
              if name not in known and os.path.isdir(os.path.join(root, name))]
    lines.append("state: %s" % movie.get("state"))
    return lines


# --- bridges --------------------------------------------------------------------------


def _ts_string(text):
    r"""`text` as a TypeScript string literal in which every UTF-16 code unit is a `\uXXXX`
    escape. The literal then holds only a backslash, `u` and hex digits, so it can hold no token
    and no import source of check_scene.py (each has a character outside that set), and the
    stage draws the same text. A lone surrogate passes as its own escape."""
    units = text.encode("utf-16-be", errors="surrogatepass")
    return '"%s"' % "".join("\\u%02x%02x" % (units[k], units[k + 1])
                            for k in range(0, len(units), 2))


def _fill(value, values):
    """A copy of `value` (parsed JSON) with each `{{name}}` of its strings replaced by
    `values[name]`, in one pass: a filled-in value is not read again for placeholders."""
    if isinstance(value, dict):
        return {key: _fill(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill(item, values) for item in value]
    if isinstance(value, str):
        return SCRIPT_PLACEHOLDER.sub(lambda found: values[found.group(1)], value)
    return value


def _with_pronounce(script, pronounce):
    """A copy of `script` with a copy of `pronounce` right after `lang`."""
    result = {}
    for key, value in script.items():
        result[key] = value
        if key == "lang":
            result["pronounce"] = dict(pronounce)
    return result


def _bridge_labels(movie, n):
    """The labels of bridge `n`: the question of chapter `n`, the answer of the first question it
    answers, and the question of chapter `n + 1` (chapters count from 1)."""
    before, after = movie["chapters"][n - 1], movie["chapters"][n]
    answers = {question["id"]: question["answer"] for question in movie["questions"]}
    return {"done": before["question"], "sofar": answers[before["answers"][0]],
            "next": after["question"]}


def bridges(movie_dir, movie):
    """Write `bridges/<n>/script.json` and `bridges/<n>/scene/Film.tsx` for each gap between two
    chapters of a plan that passes `check`; print `bridges: ok (<n>)` and return the ids written."""
    with open(BRIDGE_TEMPLATE_SCRIPT, encoding="utf-8") as handle:
        script_template = json.load(handle)
    with open(os.path.join(BRIDGE_TEMPLATE_SCENE, "Film.tsx"), encoding="utf-8") as handle:
        scene_template = handle.read()
    provenance = movie["provenance"]
    ids = []
    for n in range(1, len(movie["chapters"])):
        labels = _bridge_labels(movie, n)
        script = _fill(script_template, {
            "n": str(n), "lang": movie["lang"],
            "subject_text": movie["subject"]["text"],
            "root": resolve_root(movie_dir, provenance["root"]), "date": provenance["date"],
            "done_question": labels["done"], "answer": labels["sofar"],
            "next_question": labels["next"]})
        if movie["lang"] == "ru":
            script = _with_pronounce(script, movie["pronounce"])
        scene = SCENE_PLACEHOLDER.sub(lambda found: _ts_string(labels[found.group(1)]),
                                      scene_template)
        directory = os.path.join(movie_dir, "bridges", str(n))
        os.makedirs(os.path.join(directory, "scene"), exist_ok=True)
        _write_atomic(os.path.join(directory, "script.json"),
                      json.dumps(script, indent=2, ensure_ascii=False) + "\n")
        _write_atomic(os.path.join(directory, "scene", "Film.tsx"), scene)
        ids.append(str(n))
    sys.stdout.write("bridges: ok (%d)\n" % len(ids))
    return ids


# --- stitch ---------------------------------------------------------------------------


class StitchError(Exception):
    """A stage of `stitch` refuses; the message is the cause of its FAIL line."""


def video_workspace():
    """The video workspace root as check_render.sh finds it: `$EXPLAIN_VIDEO_WORKSPACE`, else
    `~/karpathy/video-workspace`."""
    return os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or os.path.join(
        os.path.expanduser("~"), "karpathy", "video-workspace")


def remotion_cli(workspace):
    """The argv prefix of the Remotion CLI of `workspace`; FileNotFoundError
    `no Remotion CLI at <path>` when it is not an executable file."""
    path = os.path.join(os.path.abspath(workspace), "app", *REMOTION_IN_APP)
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        raise FileNotFoundError("no Remotion CLI at %s" % path)
    return [path]


def run(argv, cwd):
    """Run `argv` in `cwd` with stdin from /dev/null (ffmpeg reads keys from stdin) and stderr
    passed through; return (exit code, stdout). The one subprocess seam of `stitch`."""
    done = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          encoding="utf-8", errors="replace", check=False)
    return done.returncode, done.stdout


def _remotion(cli, args):
    """`run` the Remotion CLI `cli` with `args` and cwd `<ws>/app`, the directory that holds
    its node_modules."""
    app = cli[0]
    for _ in REMOTION_IN_APP:
        app = os.path.dirname(app)
    return run(cli + args, app)


def _ffprobe(cli, mp4):
    """The parsed ffprobe JSON of `mp4` (an absolute path); StitchError on a non-zero exit or
    output that is not a JSON object."""
    code, out = _remotion(cli, ["ffprobe", "-v", "error", "-show_entries", PROBE_ENTRIES,
                                "-of", "json", mp4])
    if code != 0:
        raise StitchError("ffprobe exit %d" % code)
    try:
        data = json.loads(out)
    except ValueError as error:
        raise StitchError("ffprobe output unreadable") from error
    if not isinstance(data, dict):
        raise StitchError("ffprobe output unreadable")
    return data


def _probe_fields(data):
    """The `probe` dict of parsed ffprobe JSON, from its first video and first audio stream."""
    streams = _objects(data.get("streams"))
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    try:
        duration = float(data["format"]["duration"])
        rate = int(audio["sample_rate"]) if "sample_rate" in audio else None
    except (KeyError, TypeError, ValueError) as error:
        raise StitchError("ffprobe output unreadable") from error
    return {"vcodec": video.get("codec_name"), "acodec": audio.get("codec_name"),
            "width": video.get("width"), "height": video.get("height"),
            "fps": video.get("r_frame_rate"), "rate": rate, "duration": duration}


def probe(cli, mp4):
    """`mp4` through ffprobe: `vcodec` and `acodec` (codec names), `width` and `height` (ints),
    `fps` (the r_frame_rate string as ffprobe gives it, `30/1`), `rate` (the audio sample rate,
    an int) and `duration` (float seconds). A field of an absent stream is None. StitchError
    `ffprobe exit <n>` or `ffprobe output unreadable`."""
    return _probe_fields(_ffprobe(cli, mp4))


def parts(movie_dir, movie):
    """The parts of the movie in order, as paths under `movie_dir`: chapter 1, bridge 1,
    chapter 2, ..., chapter n. StitchError names the first chapter that is not `built`, else
    the first part without its `video.mp4`."""
    chapters = _objects(movie.get("chapters"))
    if not chapters:
        raise StitchError("no chapters")
    for index, chapter in enumerate(chapters):
        if chapter.get("status") != "built":
            raise StitchError("chapter %s is %s, not built"
                              % (_label(chapter, index), chapter.get("status")))
    names = []
    for index, chapter in enumerate(chapters):
        if index:
            names.append("bridges/%d/%s" % (index, VIDEO_FILE))
        names.append("chapters/%s/%s" % (_label(chapter, index), VIDEO_FILE))
    for name in names:
        if not os.path.isfile(os.path.join(movie_dir, name)):
            raise StitchError("%s missing" % name)
    return names


def concat_list(paths):
    r"""The text of `build/concat.txt` for the ffmpeg concat demuxer: one `file '<path>'` line
    per path, each `'` of a path written as `'\''` (close the quote, an escaped quote, reopen)."""
    return "".join("file '%s'\n" % path.replace("'", "'\\''") for path in paths)


def _starts(durations):
    """The start of each chapter: chapter k is part 2k, so its start is the float sum of the
    durations of parts 0 to 2k - 1, not rounded (0.0 for the first)."""
    return [float(sum(durations[:index])) for index in range(0, len(durations), 2)]


# Each stage takes the facts of the stages before it and returns (the text after `ok `, its own
# facts); a StitchError is its FAIL cause. The later stages print between `container` and
# `length`.


def _stage_parts(job):
    names = parts(job["dir"], job["movie"])
    probes = []
    for name in names:
        try:
            probes.append(probe(job["cli"], os.path.join(job["dir"], name)))
        except StitchError as error:
            raise StitchError("%s %s" % (name, error)) from error
    for name, found in zip(names[1:], probes[1:]):
        for key, what in PART_FIELDS:
            if found[key] != probes[0][key]:
                raise StitchError("%s %s differs" % (name, what))
    return "(%d)" % len(names), {"parts": names,
                                 "durations": [found["duration"] for found in probes]}


def _stage_concat(job):
    build = os.path.join(job["dir"], BUILD_DIR)
    os.makedirs(build, exist_ok=True)
    listing = os.path.join(build, CONCAT_FILE)
    _write_atomic(listing, concat_list([os.path.join(job["dir"], name) for name in job["parts"]]))
    code, _ = _remotion(job["cli"], ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                                     "-i", listing, "-c", "copy", os.path.join(build, PART_FILE)])
    if code != 0:
        raise StitchError("ffmpeg exit %d" % code)
    total = sum(job["durations"])
    return "(%.1f s)" % total, {"total": total}


def _stage_container(job):
    part = os.path.join(job["dir"], BUILD_DIR, PART_FILE)
    data = _ffprobe(job["cli"], part)
    kinds = sorted(str(stream.get("codec_type")) for stream in _objects(data.get("streams")))
    if kinds != ["audio", "video"]:
        raise StitchError("streams %s (expected one video and one audio)"
                          % (", ".join(kinds) or "none"))
    duration = _probe_fields(data)["duration"]
    if abs(duration - job["total"]) > LENGTH_SLACK:
        raise StitchError("duration %.1f s, expected %.1f s" % (duration, job["total"]))
    os.replace(part, os.path.join(job["dir"], VIDEO_FILE))
    starts = _starts(job["durations"])
    chapters = _objects(job["movie"].get("chapters"))
    _write_atomic(os.path.join(job["dir"], CHAPTERS_FILE), json.dumps(
        [{"id": chapter.get("id"), "title": chapter.get("title"), "start": start}
         for chapter, start in zip(chapters, starts)], indent=2, ensure_ascii=False) + "\n")
    return "(%.1f s)" % duration, {"duration": duration, "starts": starts}


TRANSCRIPT_FILE = "index.html"
VIEWER_FILE = os.path.join("review", "viewer-transcript.html")
VIEWER_STILLS = os.path.join("review", "viewer-stills")  # a still per chapter, `<k>-<id>.png`
HUB_FILE = os.path.join(BUILD_DIR, "hub-sections.html")
VIEWER_HIDDEN = ("ask", "answer")  # scenes the viewer must not see
MAIN_TEXT = re.compile(r"<main>(.*?)</main>", re.S)
SECTION_TEXT = re.compile(r'<section id="([^"]+)">\s*<h2>.*?</h2>\s*(.*?)\s*</section>', re.S)
CITES_TEXT = re.compile(r'\s*<div class="cites"[^>]*>.*?</div>', re.S)


def chapter_sections(movie_dir, chapter):
    """{scene id: the section's inner HTML without its `<h2>`} of the chapter's transcript, in
    document order. StitchError when it is missing or has no `ask` or `answer` section."""
    ident = chapter.get("id")
    path = os.path.join(movie_dir, "chapters", str(ident), TRANSCRIPT_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        raise StitchError("chapter %s: no transcript" % ident)
    found = MAIN_TEXT.search(text)
    sections = dict(SECTION_TEXT.findall(found.group(1) if found else ""))
    for scene in VIEWER_HIDDEN:
        if scene not in sections:
            raise StitchError("chapter %s: transcript has no section %s" % (ident, scene))
    return sections


def _chapter_html(chapter, bodies):
    return '<section id="ch-%s"><h2>%s</h2>\n%s\n</section>\n' % (
        chapter.get("id"), html.escape(str(chapter.get("title"))), "\n".join(bodies))


def hub_section(chapter, sections):
    """The chapter's section for the hub: every scene's narration and cites, in order, then the
    link to the chapter's own transcript."""
    link = '<a href="chapters/%s/index.html" data-ste="skip">transcript</a>' % html.escape(
        str(chapter.get("id")))
    return _chapter_html(chapter, list(sections.values()) + [link])


def viewer_section(chapter, sections, still=None):
    """The same without the `ask` and `answer` scenes and without any cites block; with `still`
    (the still's path relative to `review/`), the path as text and the still as an image."""
    bodies = [CITES_TEXT.sub("", body) for scene, body in sections.items()
              if scene not in VIEWER_HIDDEN]
    if still is not None:
        bodies.append('<p class="still">still: %s</p>\n<img src="%s" alt="">'
                      % (html.escape(still), html.escape(still)))
    return _chapter_html(chapter, bodies)


def still_source(chapter, sections):
    """The path under the movie directory of the chapter's viewer still: the `-end` still of the
    last scene before `answer` other than `ask`, as the render names it,
    `chapters/<id>/review/still-NN-<scene>-end.png` with NN the 1-based place of the scene (the
    transcript has one section per scene, in scene order). StitchError when no such scene comes
    before `answer`."""
    names = list(sections)
    before = [(place, name) for place, name in enumerate(names[:names.index("answer")], start=1)
              if name not in VIEWER_HIDDEN]
    if not before:
        raise StitchError("chapter %s: transcript has no section before answer" % chapter.get("id"))
    place, name = before[-1]
    return "chapters/%s/review/still-%02d-%s-end.png" % (chapter.get("id"), place, name)


def _copy_atomic(source, path):
    """Copy the file `source` to `path` through a temporary file in the same directory; on
    failure the old file stays and no temp is left."""
    fd, temp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp",
                                dir=os.path.dirname(path))
    os.close(fd)
    try:
        shutil.copyfile(source, temp)
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def _viewer_page(movie, chapter_html):
    questions = "".join("<li>%s</li>\n" % html.escape(str(q.get("text")))
                        for q in _objects(movie.get("questions")))
    title = html.escape(str(movie.get("title")))
    return ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n'
            "<title>%s</title>\n</head>\n<body>\n<h1>%s</h1>\n<ul>\n%s</ul>\n%s"
            "</body>\n</html>\n" % (html.escape(str(movie.get("lang"))), title, title,
                                      questions, "".join(chapter_html)))


def _stage_transcript(job):
    chapters = _objects(job["movie"].get("chapters"))
    all_sections = [(chapter, chapter_sections(job["dir"], chapter)) for chapter in chapters]
    sources = [still_source(chapter, sections) for chapter, sections in all_sections]
    for (chapter, _), source in zip(all_sections, sources):
        if not os.path.isfile(os.path.join(job["dir"], source)):
            raise StitchError("chapter %s: no still %s" % (chapter.get("id"), source))
    _write_atomic(os.path.join(job["dir"], HUB_FILE),
                  "".join(hub_section(c, s) for c, s in all_sections))
    os.makedirs(os.path.join(job["dir"], VIEWER_STILLS), exist_ok=True)
    stills = []
    for number, (chapter, source) in enumerate(zip(chapters, sources), start=1):
        name = "%d-%s.png" % (number, chapter.get("id"))
        _copy_atomic(os.path.join(job["dir"], source), os.path.join(job["dir"], VIEWER_STILLS, name))
        stills.append("%s/%s" % (os.path.basename(VIEWER_STILLS), name))
    _write_atomic(os.path.join(job["dir"], VIEWER_FILE), _viewer_page(
        job["movie"], [viewer_section(c, s, still)
                       for (c, s), still in zip(all_sections, stills)]))
    return "(%d chapters)" % len(chapters), {}


HUB_TEMPLATE = os.path.join(SKILL_DIR, "templates", "movie.html")
HUB_PAGE = "index.html"
HUB_MARKER = re.compile(r"\{\{([a-z_]+)\}\}")


def _hub_cite(cite):
    """One `<cite>` of a viewer question, as `page.html` writes it: `<name>:<line>` and the
    snippet as code; a URL cite shows its host and has no line."""
    path, snippet = str(cite.get("path")), str(cite.get("snippet"))
    if path.startswith(("http://", "https://")):
        return '<cite data-path="%s" data-snippet="%s">%s <code>%s</code></cite>' % (
            html.escape(path), html.escape(snippet),
            html.escape(urllib.parse.urlsplit(path).netloc or path), html.escape(snippet))
    line = html.escape(str(cite.get("line")))
    return '<cite data-path="%s" data-line="%s" data-snippet="%s">%s:%s <code>%s</code></cite>' % (
        html.escape(path), line, html.escape(snippet), html.escape(os.path.basename(path)), line,
        html.escape(snippet))


def _hub_questions(movie):
    """The `<dl>` of the viewer questions: each text, then its answer, the answer's cites block
    as its last child (none for a question without cites)."""
    items = []
    for question in _objects(movie.get("questions")):
        cites = "".join(_hub_cite(cite) for cite in _objects(question.get("cites")))
        block = '<div class="cites" data-ste="skip">%s</div>' % cites if cites else ""
        items.append("<dt>%s</dt>\n<dd>%s%s</dd>\n" % (html.escape(str(question.get("text"))),
                                                       html.escape(str(question.get("answer"))),
                                                       block))
    return '<dl class="questions">\n%s</dl>' % "".join(items)


def _hub_chapters(movie, starts):
    """The `<ol id="chapters">`: one link per chapter to its section, with its start second."""
    items = ['<li><a href="#ch-%s" data-start="%.1f">%s</a></li>\n' % (
        html.escape(str(chapter.get("id"))), start, html.escape(str(chapter.get("title"))))
        for chapter, start in zip(_objects(movie.get("chapters")), starts)]
    return '<ol id="chapters">\n%s</ol>' % "".join(items)


def hub(movie_dir: str, movie: dict, starts: list[float]) -> str:
    """The text of the hub `index.html` (spec 4.6): `templates/movie.html` with each marker
    filled in one pass, so a filled-in value is not read again for markers. Every value is
    escaped except the prebuilt `questions`, `chapters` and `sections`; `sections` is the text of
    `build/hub-sections.html`, which the transcript stage writes. OSError when either file
    cannot be read."""
    with open(HUB_TEMPLATE, encoding="utf-8") as handle:
        template = handle.read()
    with open(os.path.join(movie_dir, HUB_FILE), encoding="utf-8") as handle:
        sections = handle.read()
    subject = movie.get("subject") if isinstance(movie.get("subject"), dict) else {}
    provenance = movie.get("provenance") if isinstance(movie.get("provenance"), dict) else {}
    values = {key: html.escape(str(value)) for key, value in (
        ("lang", movie.get("lang")), ("title", movie.get("title")),
        ("question", movie.get("question")),
        ("root", resolve_root(movie_dir, str(provenance.get("root")))),
        ("kind", subject.get("kind")),
        ("subject", "%s (%s)" % (subject.get("text"), subject.get("kind"))),
        ("source", provenance.get("source")), ("date", provenance.get("date")),
        ("commit", provenance.get("commit")), ("dirty", provenance.get("dirty")),
        ("not_covered", provenance.get("not_covered")))}
    values.update(questions=_hub_questions(movie), chapters=_hub_chapters(movie, starts),
                  sections=sections.rstrip("\n"))
    return HUB_MARKER.sub(lambda found: values[found.group(1)], template)


def _stage_hub(job):
    _write_atomic(os.path.join(job["dir"], HUB_PAGE), hub(job["dir"], job["movie"], job["starts"]))
    return HUB_PAGE, {}


STITCH_STAGES = (("parts", _stage_parts), ("concat", _stage_concat),
                 ("container", _stage_container), ("transcript", _stage_transcript),
                 ("hub", _stage_hub))


def _print_length(duration):
    """The `length:` line, on the shown (one-decimal) seconds; return its exit code."""
    seconds = "%.1f" % duration
    if MIN_TOTAL <= float(seconds) <= MAX_TOTAL:
        sys.stdout.write("length: ok (%s s)\n" % seconds)
        return 0
    sys.stdout.write("length: FAIL %s s (min %d, max %d)\n" % (seconds, MIN_TOTAL, MAX_TOTAL))
    return 1


def stitch(movie_dir, movie, workspace):
    """Print the stage lines of `stitch` (module docstring) and return the exit code: 0 all ok,
    1 on a FAIL, 2 when `workspace` has no Remotion CLI."""
    try:
        cli = remotion_cli(workspace)
    except FileNotFoundError as error:
        sys.stderr.write("%s\n" % error)
        return 2
    job = {"dir": os.path.abspath(movie_dir), "movie": movie, "cli": cli}
    for name, stage in STITCH_STAGES:
        try:
            detail, facts = stage(job)
        except StitchError as error:
            sys.stdout.write("%s: FAIL %s\n" % (name, error))
            return 1
        sys.stdout.write("%s: ok %s\n" % (name, detail))
        job = dict(job, **facts)
    return _print_length(job["duration"])


# --- command line ---------------------------------------------------------------------


def _load_arg(args):
    """The movie of the one argument, or None after a usage or read error on stderr (exit 2)."""
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return None
    try:
        return load(args[0])
    except ReadError as error:
        sys.stderr.write("movie: %s\n" % error)
        return None


def _print_failures(failures):
    """Print each failure, then the count line of `check`; return 1."""
    for failure in failures:
        sys.stdout.write(failure + "\n")
    sys.stdout.write("plan: %d failures\n" % len(failures))
    return 1


def _command_check(args):
    movie = _load_arg(args)
    if movie is None:
        return 2
    failures = check(args[0], movie)
    if failures:
        return _print_failures(failures)
    low, high = _with_bridges(sum(chapter["seconds"] for chapter in movie["chapters"]),
                              len(movie["chapters"]))
    sys.stdout.write("plan: ok (%d questions, %d chapters, %d..%d s with bridges)\n" % (
        len(movie["questions"]), len(movie["chapters"]), low, high))
    return 0


def _command_bridges(args):
    movie = _load_arg(args)
    if movie is None:
        return 2
    # the bridges are drawn only from a plan that checks clean: print the failures, write nothing
    failures = check(args[0], movie)
    if failures:
        return _print_failures(failures)
    try:
        bridges(args[0], movie)
    except (OSError, ValueError) as error:
        sys.stderr.write("movie: bridges: %s\n" % " ".join(str(error).split()))
        return 2
    return 0


def _command_status(args):
    movie = _load_arg(args)
    if movie is None:
        return 2
    for line in status(args[0], movie):
        sys.stdout.write(line + "\n")
    return 0


def _command_stitch(args):
    movie = _load_arg(args)
    if movie is None:
        return 2
    try:
        return stitch(args[0], movie, video_workspace())
    except OSError as error:
        sys.stderr.write("movie: stitch: %s\n" % " ".join(str(error).split()))
        return 2


COMMANDS = {
    "check": _command_check,
    "bridges": _command_bridges,
    "stitch": _command_stitch,
    "status": _command_status,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(USAGE)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
