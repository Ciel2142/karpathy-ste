#!/usr/bin/env python3
"""Movie plan for `explain --as movie`: reads, writes and checks `movie.json`.

Usage: see USAGE below (check, bridges, stitch, status). `check` and `status` are implemented here.
Exit 0 on all ok, 1 on a failure found, 2 on a usage error or unreadable JSON.

`<dir>` is the movie output directory; it holds `movie.json`. `provenance.root` is absolute,
or relative to `<dir>` (the test fixture uses `.`). Every write goes through `save`, which is
atomic: a temporary file in the same directory, then `os.replace`.

`check` prints one failure per line, then `plan: ok (<q> questions, <c> chapters, <s> s target)`
or `plan: <n> failures`. Failure prefixes are fixed: `schema:`, `id:`, `question <id>:`,
`chapter <id>:`, `cite <question-id>#<n>:` (the rules of `cite_check`), `prose:` (an
`ste_lint.py --html` error line) and `state:`.
"""

import html
import json
import os
import re
import subprocess
import sys
import tempfile

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
MAX_ANSWERS = 2
STATES = ("planned", "building", "stitched")
STATUSES = ("pending", "built", "failed")
KINDS = ("topic", "file", "directory")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
STE_ERROR = re.compile(r"^\d+:\d+  (E .*)$")
PROVENANCE_KEYS = ("root", "commit", "dirty", "date", "source", "not_covered")
CHAPTER_TEXT = ("title", "question", "picture", "ends_with")


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


def save(movie_dir, movie):
    """Write `movie.json` atomically; on failure the old file stays and no temp is left."""
    fd, temp = tempfile.mkstemp(prefix=".movie.", suffix=".tmp", dir=movie_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(movie, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o644)  # mkstemp makes 0600; keep movie.json readable
        os.replace(temp, os.path.join(movie_dir, MOVIE_FILE))
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


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
    if all_valid and not MIN_TOTAL <= seconds <= MAX_TOTAL:
        failures.append("schema: seconds sum %d (min %d, max %d)" % (seconds, MIN_TOTAL, MAX_TOTAL))
    return failures


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


# --- command line ---------------------------------------------------------------------


def _command_check(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    try:
        movie = load(args[0])
    except ReadError as error:
        sys.stderr.write("movie: %s\n" % error)
        return 2
    failures = check(args[0], movie)
    for failure in failures:
        sys.stdout.write(failure + "\n")
    if failures:
        sys.stdout.write("plan: %d failures\n" % len(failures))
        return 1
    sys.stdout.write("plan: ok (%d questions, %d chapters, %d s target)\n" % (
        len(movie["questions"]), len(movie["chapters"]),
        sum(chapter["seconds"] for chapter in movie["chapters"])))
    return 0


def _command_status(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    try:
        movie = load(args[0])
    except ReadError as error:
        sys.stderr.write("movie: %s\n" % error)
        return 2
    for line in status(args[0], movie):
        sys.stdout.write(line + "\n")
    return 0


def _not_implemented(args):
    sys.stderr.write("movie: not implemented yet\n")
    return 2


COMMANDS = {
    "check": _command_check,
    "bridges": _not_implemented,
    "stitch": _not_implemented,
    "status": _command_status,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(USAGE)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
