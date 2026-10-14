#!/usr/bin/env python3
"""Course plan for `explain --as course`: reads, writes and checks `course.json`.

Usage: see USAGE below (check, approve, next, mark, reopen).
Exit 0 on success, 1 on failures found or a refused change, 2 on a usage or read error.

`<dir>` is the course output directory; it holds `course.json` and `lessons/<id>/`.
`root` in `course.json` is absolute, or relative to `<dir>` (the test fixture uses the
second form so that it works in any checkout). Every write goes through `save`, which is
atomic: a temporary file in the same directory, then `os.replace`.

`check` prints one failure per line, then `course: ok` or `course: <n> failures`.
Failure prefixes are fixed (plan section 4): `schema:`, `id:`, `lesson <id>:`, `hop <id>:`,
`source <id>:`, `cite <hop>#<n>:`, `prose:` (an `ste_lint.py --html` error line) and `state:`.
The cite rules (snippet of at most 12 words, verbatim on that line) come from `cite_check`.
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile

import cite_check

USAGE = (
    "usage: course.py check <dir>\n"
    "       course.py approve <dir>\n"
    "       course.py next <dir> [--limit N]\n"
    "       course.py mark <dir> <lesson-id> pending|building|done|failed|dropped"
    " [--reason TEXT]\n"
    "       course.py reopen <dir>\n"
)
STATE_CHANGED = "state: plan changed after approval; run summary and approve again"
STE_ERROR = re.compile(r"^\d+:\d+  (E .*)$")
COURSE_FILE = "course.json"
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
STATES = ("planned", "approved", "done")
SOURCE_KINDS = ("code", "docs")
FOUND = ("named", "discovered")
EVIDENCE = ("code", "docs", "inferred")
STATUSES = ("pending", "building", "done", "failed", "dropped")
NEEDS_REASON = ("failed", "dropped")
TYPE_NAMES = {
    str: "a string",
    bool: "a boolean",
    list: "a list",
    dict: "an object",
    int: "a positive integer",
}


def load(course_dir):
    """Return the parsed `<course_dir>/course.json`; raise OSError or ValueError."""
    with open(os.path.join(course_dir, COURSE_FILE), encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("top level must be an object")
    return data


def save(course_dir, course):
    """Write `course.json` atomically; on failure the old file stays and no temp is left."""
    fd, temp = tempfile.mkstemp(prefix=".course.", suffix=".tmp", dir=course_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(course, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, os.path.join(course_dir, COURSE_FILE))
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def resolve_root(course_dir, root):
    """The absolute directory of `root`: as given, or relative to the course directory."""
    return os.path.normpath(os.path.join(os.path.abspath(course_dir), root))


# --- schema ---------------------------------------------------------------------------


class _Schema:
    """Collects `schema:` failures and returns only the values that have the right type."""

    def __init__(self):
        self.failures = []

    def fail(self, path, problem):
        self.failures.append("schema: %s: %s" % (path, problem))

    def get(self, obj, key, path, kind, nonempty=False):
        """Return `obj[key]` if present and of `kind`, else None after a failure."""
        field = "%s.%s" % (path, key) if path else key
        if key not in obj:
            self.fail(field, "missing")
            return None
        value = obj[key]
        if kind is int:
            ok = isinstance(value, int) and not isinstance(value, bool) and value >= 1
        else:
            ok = isinstance(value, kind)
        if not ok:
            self.fail(field, "must be %s" % TYPE_NAMES[kind])
            return None
        if nonempty and not value:
            self.fail(field, "must not be empty")
            return None
        return value

    def enum(self, obj, key, path, choices):
        value = self.get(obj, key, path, str)
        if value is not None and value not in choices:
            self.fail("%s.%s" % (path, key) if path else key,
                      "must be one of %s" % ", ".join(choices))
            return None
        return value

    def ident(self, obj, path):
        value = self.get(obj, "id", path, str)
        if value is not None and not ID_PATTERN.fullmatch(value):
            self.fail("%s.id" % path, "must match [a-z0-9][a-z0-9-]*")
            return None
        return value

    def items(self, obj, key, path):
        """Yield `(path, item)` for the objects of the list `obj[key]`."""
        values = self.get(obj, key, path, list)
        for index, item in enumerate(values or []):
            where = "%s[%d]" % (key if not path else "%s.%s" % (path, key), index)
            if isinstance(item, dict):
                yield where, item
            else:
                self.fail(where, "must be an object")


def _check_schema(course):
    schema = _Schema()
    if schema.get(course, "version", "", int) is not None and course["version"] != 1:
        schema.fail("version", "must be 1")
    for key in ("title", "question", "lang", "root"):
        schema.get(course, key, "", str)
    schema.get(course, "review", "", bool)
    schema.enum(course, "state", "", STATES)
    if "approved_shape" in course:
        schema.get(course, "approved_shape", "", str)
    for path, source in schema.items(course, "sources", ""):
        _check_source(schema, source, path)
    for path, hop in schema.items(course, "hops", ""):
        _check_hop(schema, hop, path)
    for path, block in schema.items(course, "blocks", ""):
        _check_block(schema, block, path)
    for index, text in enumerate(schema.get(course, "not_covered", "", list) or []):
        if not isinstance(text, str):
            schema.fail("not_covered[%d]" % index, "must be a string")
    return schema.failures


def _check_source(schema, source, path):
    schema.ident(source, path)
    schema.get(source, "path", path, str, nonempty=True)
    schema.enum(source, "kind", path, SOURCE_KINDS)
    schema.enum(source, "found", path, FOUND)
    for key in ("why", "commit"):
        schema.get(source, key, path, str)
    schema.get(source, "dirty", path, bool)


def _check_hop(schema, hop, path):
    schema.ident(hop, path)
    for key in ("from", "to", "what"):
        schema.get(hop, key, path, str)
    schema.enum(hop, "evidence", path, EVIDENCE)
    if "branch" not in hop:
        schema.fail("%s.branch" % path, "missing")
    elif hop["branch"] is not None and not isinstance(hop["branch"], str):
        schema.fail("%s.branch" % path, "must be null or a string")
    for cite_path, cite in schema.items(hop, "cites", path):
        schema.get(cite, "path", cite_path, str, nonempty=True)
        schema.get(cite, "line", cite_path, int)
        schema.get(cite, "snippet", cite_path, str, nonempty=True)


def _check_block(schema, block, path):
    schema.ident(block, path)
    schema.get(block, "title", path, str)
    lessons = list(schema.items(block, "lessons", path))
    if isinstance(block.get("lessons"), list) and not block["lessons"]:
        schema.fail("%s.lessons" % path, "must not be empty")
    for lesson_path, lesson in lessons:
        _check_lesson(schema, lesson, lesson_path)


def _check_lesson(schema, lesson, path):
    schema.ident(lesson, path)
    for key in ("question", "brief"):
        schema.get(lesson, key, path, str)
    for key in ("hops", "sources"):
        for index, name in enumerate(schema.get(lesson, key, path, list) or []):
            if not isinstance(name, str):
                schema.fail("%s.%s[%d]" % (path, key, index), "must be a string")
    status = schema.enum(lesson, "status", path, STATUSES)
    reason = schema.get(lesson, "reason", path, str)
    if status is None or reason is None:
        return
    if status in NEEDS_REASON and not reason:
        schema.fail("%s.reason" % path, "needed for %s" % status)
    elif status not in NEEDS_REASON and reason:
        schema.fail("%s.reason" % path, "must be empty for %s" % status)


# --- cross-checks ---------------------------------------------------------------------


def _objects(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _ids(items):
    return [item["id"] for item in items if isinstance(item.get("id"), str)]


def _lessons(course):
    return [
        lesson
        for block in _objects(course.get("blocks"))
        for lesson in _objects(block.get("lessons"))
    ]


def _names(value):
    return [name for name in value if isinstance(name, str)] if isinstance(value, list) else []


def _duplicates(course):
    groups = (
        _objects(course.get("sources")),
        _objects(course.get("hops")),
        _objects(course.get("blocks")),
        _lessons(course),
    )
    failures = []
    for group in groups:
        ids = _ids(group)
        for ident in dict.fromkeys(ids):
            if ids.count(ident) > 1:
                failures.append("id: duplicate %s" % ident)
    return failures


def _check_references(course):
    hops = set(_ids(_objects(course.get("hops"))))
    sources = set(_ids(_objects(course.get("sources"))))
    failures = []
    for lesson in _lessons(course):
        ident = lesson.get("id")
        for hop in _names(lesson.get("hops")):
            if hop not in hops:
                failures.append("lesson %s: unknown hop %s" % (ident, hop))
        for source in _names(lesson.get("sources")):
            if source not in sources:
                failures.append("lesson %s: unknown source %s" % (ident, source))
    return failures


def _cite_problems(hop, root):
    """The `cite <hop>#<n>:` failures of one hop, by the rules of `cite_check`."""
    failures = []
    for number, cite in enumerate(_objects(hop.get("cites")), start=1):
        path, line, snippet = cite.get("path"), cite.get("line"), cite.get("snippet")
        if not (isinstance(path, str) and path and isinstance(snippet, str) and snippet.strip()):
            continue
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            continue
        values = {"data-path": path, "data-line": str(line), "data-snippet": snippet}
        shown = "%s:%d" % (os.path.basename(path), line)
        label = "cite %d (%s:%d): " % (number, path, line)
        for problem in cite_check._check_cite(number, values, root, shown):
            failures.append(
                "cite %s#%d: %s" % (hop["id"], number, problem[len(label):])
                if problem.startswith(label)
                else "cite %s#%d: %s" % (hop["id"], number, problem)
            )
    return failures


def _check_hops(course, root):
    hops = [hop for hop in _objects(course.get("hops")) if isinstance(hop.get("id"), str)]
    in_lessons = {
        name for lesson in _lessons(course) for name in _names(lesson.get("hops"))
    }
    failures = []
    for index, hop in enumerate(hops):
        ident, branch = hop["id"], hop.get("branch")
        if ident not in in_lessons:
            failures.append("hop %s: in no lesson" % ident)
        if isinstance(branch, str) and branch not in _ids(hops[:index]):
            failures.append("hop %s: branch %s is not an earlier hop" % (ident, branch))
        evidence = hop.get("evidence")
        has_cite = bool(_objects(hop.get("cites")))
        if evidence in ("code", "docs") and not has_cite:
            failures.append("hop %s: %s hop needs a cite" % (ident, evidence))
        elif evidence == "inferred" and has_cite:
            failures.append("hop %s: inferred hop has a cite" % ident)
        elif evidence in ("code", "docs") and root is not None:
            failures.extend(_cite_problems(hop, root))
    return failures


def _check_sources(course, root):
    if root is None:
        return []
    failures = []
    for source in _objects(course.get("sources")):
        ident, path = source.get("id"), source.get("path")
        if isinstance(ident, str) and isinstance(path, str) and path:
            full = os.path.normpath(os.path.join(root, path))
            if not os.path.exists(full):
                failures.append("source %s: path missing: %s" % (ident, full))
    return failures


def _check_done(course_dir, course):
    failures = []
    for lesson in _lessons(course):
        ident = lesson.get("id")
        if lesson.get("status") == "done" and isinstance(ident, str):
            if not os.path.isfile(os.path.join(course_dir, "lessons", ident, "index.html")):
                failures.append(
                    "lesson %s: done but lessons/%s/index.html missing" % (ident, ident)
                )
    return failures


def shape(course):
    """SHA-256 hex of the plan shape: hop ids and branches, block ids, lesson ids with their
    hops and sources, all in order. Prose, cites, statuses and source commits are not in it."""
    hops = [[hop.get("id"), hop.get("branch")] for hop in _objects(course.get("hops"))]
    blocks = [
        [
            block.get("id"),
            [
                [lesson.get("id"), _names(lesson.get("hops")), _names(lesson.get("sources"))]
                for lesson in _objects(block.get("lessons"))
            ],
        ]
        for block in _objects(course.get("blocks"))
    ]
    canonical = json.dumps({"hops": hops, "blocks": blocks}, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _check_state(course):
    if course.get("state") == "approved" and course.get("approved_shape") != shape(course):
        return [STATE_CHANGED]
    return []


def _prose_fields(course):
    """`(field path, text)` of each prose field, in document order; empty fields are left out."""
    fields = [("title", course.get("title")), ("question", course.get("question"))]
    for index, hop in enumerate(_objects(course.get("hops"))):
        fields.append(("hops[%s].what" % _label(hop, index), hop.get("what")))
    for index, block in enumerate(_objects(course.get("blocks"))):
        fields.append(("blocks[%s].title" % _label(block, index), block.get("title")))
        for number, lesson in enumerate(_objects(block.get("lessons"))):
            label = _label(lesson, number)
            fields.append(("lessons[%s].question" % label, lesson.get("question")))
            fields.append(("lessons[%s].brief" % label, lesson.get("brief")))
    if isinstance(course.get("not_covered"), list):
        fields += [("not_covered[%d]" % i, text) for i, text in enumerate(course["not_covered"])]
    return [
        (path, " ".join(text.split()))
        for path, text in fields
        if isinstance(text, str) and text.strip()
    ]


def _label(item, index):
    ident = item.get("id")
    return ident if isinstance(ident, str) and ident else str(index)


def _find_ste_lint():
    """Same lookup as scripts/verify.sh: the sibling skill, then the installed one."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (
        os.path.join(here, "..", "..", "ste", "scripts", "ste_lint.py"),
        os.path.expanduser("~/.claude/skills/ste/scripts/ste_lint.py"),
    ):
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def _check_prose(course):
    """`prose:` failures: the prose fields as one HTML document through `ste_lint.py --html`.

    Each field is one whitespace-collapsed `<p>` on its own line, so the line of a lint error
    names the field; the failure reads `prose: <field path>: <rule code and message>`."""
    fields = _prose_fields(course)
    if not fields:
        return []
    linter = _find_ste_lint()
    if linter is None:
        return ["prose: ste_lint.py not found"]
    lang = course.get("lang") if isinstance(course.get("lang"), str) and course["lang"] else "en"
    first = 2  # line 1 is the opening tag
    document = '<html lang="%s"><body>\n%s\n</body></html>\n' % (
        html.escape(lang), "\n".join("<p>%s</p>" % html.escape(text) for _, text in fields)
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prose.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(document)
        try:
            result = subprocess.run(
                [sys.executable, "-B", linter, "--html", path],
                capture_output=True, text=True, timeout=60,
            )
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


def check(course_dir, course):
    """Return the failures of `course`, one per fault; empty means ok.

    Changes no state. For an approved course whose shape moved it reports the `state:`
    failure; the command line `check` is what then sets `state` to `planned`."""
    root = course.get("root")
    root = resolve_root(course_dir, root) if isinstance(root, str) else None
    failures = _check_schema(course)
    failures += _duplicates(course)
    failures += _check_references(course)
    failures += _check_hops(course, root)
    failures += _check_sources(course, root)
    failures += _check_done(course_dir, course)
    failures += _check_prose(course)
    failures += _check_state(course)
    return failures


# --- state machine --------------------------------------------------------------------


def next_lessons(course, limit):
    """Ids of the `pending` and `building` lessons in plan order, at most `limit` of them."""
    ids = [
        lesson["id"]
        for lesson in _lessons(course)
        if lesson.get("status") in ("pending", "building") and isinstance(lesson.get("id"), str)
    ]
    return ids if limit is None else ids[:limit]


def _find_lesson(course, ident):
    return next((lesson for lesson in _lessons(course) if lesson.get("id") == ident), None)


# --- command line ---------------------------------------------------------------------


def _load_or_report(course_dir):
    try:
        return load(course_dir)
    except (OSError, ValueError) as error:
        sys.stderr.write(
            "course: cannot read %s: %s\n" % (os.path.join(course_dir, COURSE_FILE), error)
        )
        return None


def _report(failures):
    for failure in failures:
        sys.stdout.write(failure + "\n")
    if failures:
        sys.stdout.write("course: %d failures\n" % len(failures))
        return 1
    sys.stdout.write("course: ok\n")
    return 0


def _refuse(message):
    sys.stderr.write(message + "\n")
    return 1


def _command_check(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    failures = check(args[0], course)
    if STATE_CHANGED in failures:
        course["state"] = "planned"
        save(args[0], course)
    return _report(failures)


def _command_approve(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    if course.get("state") == "done":
        return _refuse("approve: course already done")
    # a moved shape is what a new approval is for, so the state rule does not apply here
    failures = check(args[0], dict(course, state="planned"))
    if failures:
        return _report(failures)
    course["state"] = "approved"
    course["approved_shape"] = shape(course)
    save(args[0], course)
    return 0


def _command_next(args):
    limit = None
    if len(args) == 3 and args[1] == "--limit":
        if not (args[2].isdigit() and int(args[2]) >= 1):
            sys.stderr.write(USAGE)
            return 2
        limit = int(args[2])
    elif len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    if course.get("state") == "planned":
        return _refuse("next: course not approved")
    for ident in next_lessons(course, limit):
        sys.stdout.write(ident + "\n")
    return 0


def _command_mark(args):
    reason = None
    if len(args) == 5 and args[3] == "--reason":
        reason = args[4]
    elif len(args) != 3:
        sys.stderr.write(USAGE)
        return 2
    course_dir, ident, status = args[0], args[1], args[2]
    if status not in STATUSES:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(course_dir)
    if course is None:
        return 2
    lesson = _find_lesson(course, ident)
    if lesson is None:
        return _refuse("mark: unknown lesson %s" % ident)
    if status in NEEDS_REASON and not reason:
        return _refuse("mark: %s needs --reason" % status)
    if status not in NEEDS_REASON and reason is not None:
        return _refuse("mark: --reason only for failed or dropped")
    if status == "done" and not os.path.isfile(
        os.path.join(course_dir, "lessons", ident, "index.html")
    ):
        return _refuse("mark: done needs lessons/%s/index.html" % ident)
    lesson["status"] = status
    lesson["reason"] = reason if status in NEEDS_REASON else ""
    save(course_dir, course)
    return 0


def _command_reopen(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    reset = [lesson for lesson in _lessons(course) if lesson.get("status") == "failed"]
    if not reset:
        return 0
    for lesson in reset:
        lesson["status"] = "pending"
        lesson["reason"] = ""
    if course.get("state") == "done":
        course["state"] = "approved"
    save(args[0], course)
    for lesson in reset:
        sys.stdout.write("%s\n" % lesson.get("id"))
    return 0


COMMANDS = {
    "check": _command_check,
    "approve": _command_approve,
    "next": _command_next,
    "mark": _command_mark,
    "reopen": _command_reopen,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(USAGE)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
