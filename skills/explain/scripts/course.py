#!/usr/bin/env python3
"""Course plan for `explain --as course`: reads, writes and checks `course.json`.

Usage: see USAGE below (check, summary, approve, next, mark, reopen, hub).
Exit 0 on success, 1 on failures found or a refused change, 2 on a usage or read error or a
version 1 course.

`<dir>` is the course output directory; it holds `course.json`, `lessons/<id>/` and
`map/<source-id>.md`. `root` in `course.json` is absolute, or relative to `<dir>` (the test
fixture uses the second form so that it works in any checkout). Every write goes through
`save`, which is atomic: a temporary file in the same directory, then `os.replace`.

`course.json` is version 2: a hop carries `flow`, null or `<source-id>/<flow-id>` (a flow of
`map/<source-id>.md`), and `nodes`, the node ids of that flow on the hop (empty for a null
flow). Every command refuses a version 1 file before it does anything else: it writes the one
line `course: version 1 is older than this skill; start a new course` to stderr, changes no
file and exits 2. Nothing migrates a version 1 course.

`check` prints one failure per line, then `course: ok` or `course: <n> failures`.
Failure prefixes are fixed (plan section 4): `schema:`, `id:`, `lesson <id>:`, `hop <id>:`,
`flow <source>/<flow>:`, `node <source>/<flow>/<id>:`, `source <id>:`, `cite <hop>#<n>:`,
`prose:` (an `ste_lint.py --html` error line) and `state:`.
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
import textwrap

import cite_check
import onboard

USAGE = (
    "usage: course.py check <dir>\n"
    "       course.py summary <dir>\n"
    "       course.py approve <dir>\n"
    "       course.py next <dir> [--limit N]\n"
    "       course.py mark <dir> <lesson-id> pending|building|done|failed|dropped"
    " [--reason TEXT]\n"
    "       course.py reopen <dir>\n"
    "       course.py hub <dir>\n"
)
STATE_CHANGED = "state: plan changed after approval; run summary and approve again"
STE_ERROR = re.compile(r"^\d+:\d+  (E .*)$")
COURSE_FILE = "course.json"
VERSION = 2
OLD_VERSION = "course: version 1 is older than this skill; start a new course"
HUB_FILE = "index.html"
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "page.html")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
FLOW_REF = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z][a-z0-9_-]*")
# a name in a `not_covered` sentence: a whole token, so `esb/request-retry` does not name
# `esb/request`, and a backtick or a period after the name does not break it
NAME_TOKEN = re.compile(r"[a-z0-9][a-z0-9_/-]*")
STATES = ("planned", "approved", "done")
SOURCE_KINDS = ("code", "docs")
FOUND = ("named", "discovered")
EVIDENCE = ("code", "docs", "inferred")
STATUSES = ("pending", "building", "done", "failed", "dropped")
NEEDS_REASON = ("failed", "dropped")
# lesson status changes that `mark` allows (spec 5.1); any status may go to `dropped`, the
# user's word. `done -> pending` is allowed only when lessons/<id>/index.html is missing.
TRANSITIONS = {
    ("pending", "building"),
    ("building", "done"),
    ("building", "failed"),
    ("building", "pending"),
    ("failed", "pending"),
    ("dropped", "pending"),
}
OPEN = ("pending", "building")
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
        os.chmod(temp, 0o644)  # mkstemp makes 0600; keep course.json readable, as the hub
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
    if schema.get(course, "version", "", int) is not None and course["version"] != VERSION:
        schema.fail("version", "must be %d" % VERSION)
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
    if "flow" not in hop:
        schema.fail("%s.flow" % path, "missing")
    elif hop["flow"] is not None and not isinstance(hop["flow"], str):
        schema.fail("%s.flow" % path, "must be null or a string")
    elif hop["flow"] is not None and not FLOW_REF.fullmatch(hop["flow"]):
        schema.fail("%s.flow" % path, "must be <source-id>/<flow-id>")
    nodes = schema.get(hop, "nodes", path, list)
    for index, name in enumerate(nodes or []):
        if not isinstance(name, str):
            schema.fail("%s.nodes[%d]" % (path, index), "must be a string")
    if nodes and "flow" in hop and hop["flow"] is None:
        schema.fail("%s.nodes" % path, "must be empty when flow is null")
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


def _map_flows(course_dir, source_id):
    """Each flow of `map/<source_id>.md` with its node ids in diagram order (`onboard.flow_nodes`).

    A missing or unreadable map has no flows; it gives no line here, the orchestrator's
    `onboard.py check` reports it."""
    path = os.path.join(course_dir, "map", source_id + ".md")
    try:
        return onboard.flow_nodes(onboard.read_map(path))
    except (onboard.OnboardError, OSError):
        return {}


def _named(not_covered, name):
    """True when one string of `not_covered` holds `name` as a whole `NAME_TOKEN` token."""
    return any(name in NAME_TOKEN.findall(text) for text in _names(not_covered))


def _flow_hops(course):
    """The hops with a string `id`, a `flow` that is null or a `FLOW_REF`, and `nodes` a list of
    strings. Every other hop has a `schema:` line already, so `_check_flows` skips it."""
    def bound(hop):
        flow, nodes = hop.get("flow", ""), hop.get("nodes")  # "": a missing flow fails FLOW_REF
        return (
            isinstance(hop.get("id"), str)
            and (flow is None or (isinstance(flow, str) and FLOW_REF.fullmatch(flow) is not None))
            and isinstance(nodes, list)
            and all(isinstance(name, str) for name in nodes)
        )

    return [hop for hop in _objects(course.get("hops")) if bound(hop)]


def _hop_flow_lines(hop, maps):
    """The `hop <id>:` lines of one hop of `_flow_hops`; `maps` holds the flows of each source."""
    ident, flow, nodes = hop["id"], hop["flow"], hop["nodes"]
    if flow is None:
        return ["hop %s: flow missing" % ident] if hop.get("evidence") == "code" else []
    source, name = flow.split("/", 1)
    known = maps[source].get(name)  # None: the map has no such flow
    lines = []
    if known is None:
        lines.append("hop %s: flow %s not in map/%s.md" % (ident, flow, source))
    if not nodes:
        lines.append("hop %s: nodes empty" % ident)
    if known is not None:
        lines += ["hop %s: node %s not in flow %s" % (ident, node, flow)
                  for node in nodes if node not in known]
    return lines


def _check_flows(course_dir, course):
    """Each hop against its flow, then the flow floor (every flow of every map of a source is on
    a hop or named in `not_covered`), then the node floor (the same for every node of a flow
    that some hop names)."""
    hops = _flow_hops(course)
    sources = list(dict.fromkeys(_ids(_objects(course.get("sources")))))
    named = [hop["flow"].split("/", 1)[0] for hop in hops if hop["flow"] is not None]
    maps = {ident: _map_flows(course_dir, ident) for ident in dict.fromkeys(sources + named)}
    failures = [line for hop in hops for line in _hop_flow_lines(hop, maps)]
    on_hops = {}  # each flow that a hop names -> the nodes of those hops
    for hop in hops:
        if hop["flow"] is not None:
            on_hops.setdefault(hop["flow"], set()).update(hop["nodes"])
    not_covered = course.get("not_covered")
    for source in sources:
        for flow in maps[source]:
            ref = "%s/%s" % (source, flow)
            if ref not in on_hops and not _named(not_covered, ref):
                failures.append("flow %s: in no hop and not in not_covered" % ref)
    for source, flows in maps.items():
        for flow, nodes in flows.items():
            ref = "%s/%s" % (source, flow)
            if ref not in on_hops:
                continue  # no hop follows this flow: the flow floor covers it
            for node in nodes:
                if node not in on_hops[ref] and not _named(not_covered, "%s/%s" % (ref, node)):
                    failures.append("node %s/%s: in no hop and not in not_covered" % (ref, node))
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


def _shape_changed(course):
    """True for an `approved` or `done` course whose shape is not the approved one."""
    return (course.get("state") in ("approved", "done")
            and course.get("approved_shape") != shape(course))


def _check_state(course):
    return [STATE_CHANGED] if _shape_changed(course) else []


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
    failures += _check_flows(course_dir, course)
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


# --- summary --------------------------------------------------------------------------

WIDTH = 100
SLOTS = 3  # lessons built at once
MINUTES_PER_LESSON = 30


def source_dir(course_dir, course, source):
    """The absolute directory to run git in for `source`: its path under the course `root`,
    or the parent directory when that path is a file."""
    root = resolve_root(course_dir, course.get("root") if isinstance(course.get("root"), str)
                        else "")
    path = os.path.normpath(os.path.join(root, source.get("path") or ""))
    return os.path.dirname(path) if os.path.isfile(path) else path


def git_state(directory):
    """`(short commit, dirty)` of the repository that holds `directory`.

    Outside git, or when git is missing or `directory` does not exist, it is `("none", False)`.
    Dirty means `git status --porcelain` printed something (SKILL.md, convention 2)."""
    def run(*args):
        return subprocess.run(
            ["git", "-C", directory, *args], capture_output=True, text=True, timeout=30
        )

    try:
        head = run("rev-parse", "--short", "HEAD")
        if head.returncode != 0 or not head.stdout.strip():
            return "none", False
        status = run("status", "--porcelain")
    except (OSError, subprocess.SubprocessError):
        return "none", False
    return head.stdout.strip(), status.returncode == 0 and bool(status.stdout.strip())


def moved(recorded_commit, recorded_dirty, state):
    """`moved:` text when the current `(commit, dirty)` differs from the record, else None."""
    commit, dirty = state
    if commit != recorded_commit:
        return "moved: %s -> %s" % (recorded_commit, commit)
    if dirty != bool(recorded_dirty):
        return "moved: dirty"
    return None


def build_estimate(remaining):
    """Hours to build `remaining` lessons `SLOTS` at once, rounded up to a half hour."""
    half_hours = -(-remaining * MINUTES_PER_LESSON // (SLOTS * 30))
    return "%g" % (half_hours / 2)


def _wrap(text, indent, hang=None):
    return textwrap.wrap(
        text, width=WIDTH, initial_indent=" " * indent,
        subsequent_indent=" " * (indent + 4 if hang is None else hang),
        break_long_words=False, break_on_hyphens=False,
    ) or [" " * indent]


def _summary_sources(course_dir, course):
    lines = ["Sources"]
    for source in _objects(course.get("sources")):
        head = "%s  %s  %s" % (source.get("id"), source.get("kind"), source.get("found"))
        lines += _wrap(head, 2)
        if source.get("why"):
            lines += _wrap(source["why"], 4, 4)
        note = moved(source.get("commit"), source.get("dirty"),
                     git_state(source_dir(course_dir, course, source)))
        if note:
            lines += _wrap(note, 4, 4)
    return lines


def _summary_hops(course):
    hops = _objects(course.get("hops"))
    ids = {hop.get("id") for hop in hops}
    children = {}
    for hop in hops:
        if isinstance(hop.get("branch"), str) and hop["branch"] in ids:
            children.setdefault(hop["branch"], []).append(hop)
    lines, seen = ["Main path"], set()

    def show(hop, depth):
        if id(hop) in seen:
            return
        seen.add(id(hop))
        evidence = hop.get("evidence")
        if isinstance(hop.get("flow"), str):
            evidence = "%s, flow %s, %d nodes" % (
                evidence, hop["flow"], len(_names(hop.get("nodes")))
            )
        if depth:
            evidence = "%s, fails at %s" % (evidence, hop.get("branch"))
        text = "%s  %s \u2192 %s  (%s)" % (hop.get("id"), hop.get("from"), hop.get("to"), evidence)
        lines.extend(_wrap(text, 2 + 4 * depth))
        for child in children.get(hop.get("id"), []):
            show(child, depth + 1)

    for hop in hops:
        if not (isinstance(hop.get("branch"), str) and hop["branch"] in ids):
            show(hop, 0)
    for hop in hops:  # a branch loop that no main-path hop reaches: still listed
        show(hop, 1)
    return lines


def _summary_blocks(course):
    lines = ["Blocks and lessons"]
    for block in _objects(course.get("blocks")):
        lines += _wrap("%s: %s" % (block.get("id"), block.get("title")), 2)
        for lesson in _objects(block.get("lessons")):
            text = "%s  %s  [%s]  %s" % (
                lesson.get("id"), lesson.get("question"), ", ".join(_names(lesson.get("hops"))),
                lesson.get("status"),
            )
            if lesson.get("reason"):
                text += " (%s)" % lesson["reason"]
            lines += _wrap(text, 4)
    return lines


def summary(course_dir, course):
    """The plan as plain text lines for the approval stop. Changes no state."""
    lessons = _lessons(course)
    remaining = sum(1 for lesson in lessons if lesson.get("status") not in ("done", "dropped"))
    lines = _wrap(str(course.get("title")), 0, 2) + _wrap(str(course.get("question")), 0, 2)
    for part in (
        _summary_sources(course_dir, course),
        _summary_hops(course),
        _summary_blocks(course),
    ):
        lines += [""] + part
    lines += ["", "lessons: %d (%d to build), about %s h at %d at once"
              % (len(lessons), remaining, build_estimate(remaining), SLOTS)]
    for text in course.get("not_covered") if isinstance(course.get("not_covered"), list) else []:
        lines += _wrap("not covered: %s" % text, 0, 4)
    return lines


# --- hub ------------------------------------------------------------------------------


def render_hub(course_dir, course, template):
    """The hub HTML (spec section 7) in the chrome of `template`, the text of page.html.

    The rendering lives in course_hub.py; it raises ValueError on a template without its
    anchors. The import is here, not at the top: course_hub imports this module."""
    import course_hub

    return course_hub.render_hub(course_dir, course, template)


def _write_atomic(path, text):
    """Write `text` to `path` through a temporary file in the same directory."""
    fd, temp = tempfile.mkstemp(prefix=".hub.", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o644)  # mkstemp makes 0600; the hub is a page to read and share
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


# --- command line ---------------------------------------------------------------------


def _load_or_report(course_dir):
    """The course of `course_dir`, or None after one stderr line: unreadable, or version 1."""
    try:
        course = load(course_dir)
    except (OSError, ValueError) as error:
        sys.stderr.write(
            "course: cannot read %s: %s\n" % (os.path.join(course_dir, COURSE_FILE), error)
        )
        return None
    version = course.get("version")
    if version == 1 and not isinstance(version, bool):  # true == 1: a schema fault, not version 1
        sys.stderr.write(OLD_VERSION + "\n")
        return None
    return course


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


def _command_summary(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    sys.stdout.write("\n".join(summary(args[0], course)) + "\n")
    return 0


def _command_approve(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    if _shape_changed(course):
        # a new approval goes through `planned`, as `check` would set it
        course["state"] = "planned"
        save(args[0], course)
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
    if reason and len(reason.splitlines()) > 1:
        return _refuse("mark: --reason must be one line")
    page = os.path.isfile(os.path.join(course_dir, "lessons", ident, "index.html"))
    start = lesson.get("status")
    if not _transition_allowed(start, status, page):
        return _refuse("mark: %s: %s -> %s not allowed" % (ident, start, status))
    if status == "done" and not page:
        return _refuse("mark: done needs lessons/%s/index.html" % ident)
    lesson["status"] = status
    lesson["reason"] = reason if status in NEEDS_REASON else ""
    if status in OPEN and course.get("state") == "done":
        course["state"] = "approved"  # an open lesson: the course is not done
    save(course_dir, course)
    return 0


def _transition_allowed(start, end, page):
    """Spec 5.1: the build moves a lesson pending -> building -> done or failed (or back to
    pending); a retry moves failed or dropped to pending; the user may drop any lesson. A
    `done` lesson whose page is missing may go back to pending (the fix of that check line)."""
    if end == "dropped" or (start, end) in TRANSITIONS:
        return True
    return start == "done" and end == "pending" and not page


def _command_reopen(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    # no lesson subagent runs at a resume, so a `building` lesson is one the last run left
    reset = [lesson for lesson in _lessons(course)
             if lesson.get("status") in ("failed", "building")]
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


def _command_hub(args):
    if len(args) != 1:
        sys.stderr.write(USAGE)
        return 2
    course = _load_or_report(args[0])
    if course is None:
        return 2
    # the hub draws only a plan that checks clean (a schema fault, a shape changed after
    # approval, a done lesson without its page): print the failures and write nothing
    failures = check(args[0], course)
    if failures:
        return _report(failures)
    path = os.path.join(args[0], HUB_FILE)
    try:
        with open(TEMPLATE, encoding="utf-8") as handle:
            template = handle.read()
        _write_atomic(path, render_hub(args[0], course, template))
    except (OSError, ValueError) as error:
        sys.stderr.write("course: hub: %s\n" % " ".join(str(error).split()))
        return 2
    # approved -> done only when no lesson is open (spec 5.1), and a done course with an
    # open lesson goes back to approved; a planned course stays planned
    open_lessons = bool(next_lessons(course, None))
    if course.get("state") in ("approved", "done"):
        state = "approved" if open_lessons else "done"
        if course["state"] != state:
            course["state"] = state
            save(args[0], course)
    sys.stdout.write("hub: wrote %s\n" % path)
    return 0


COMMANDS = {
    "check": _command_check,
    "summary": _command_summary,
    "approve": _command_approve,
    "next": _command_next,
    "mark": _command_mark,
    "reopen": _command_reopen,
    "hub": _command_hub,
}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(USAGE)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
