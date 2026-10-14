#!/usr/bin/env python3
"""Discovery for `explain --as course` (rungs/course.md "Discover"): find the directories beside the sources
that the flow goes through.

Usage: course_discover.py <course-dir> <parent-dir>... [--source <path>]...

1. Read the section `Other systems` of each `<course-dir>/map/*.md`. From the fact part of each line (the text
   before the first " | ", so not the cite), collect each name in backticks: a handle. The system name of a
   line is its text before the first ":", and each name in parentheses there.
2. The candidates are the directories in each parent directory that are not sources and not hidden. The
   sources are the `--source` paths; with no `--source`, a directory whose slug is the id of a map.
3. Run one `grep` per candidate, with a list argv (no shell): the handles go in through `-f <file>`, and `-o -h`
   prints each match. A handle that is part of a longer handle that matched also matched. Only the text types
   of INCLUDES count; EXCLUDE_DIRS are skipped.
4. Drop each handle that matches more than DROP_OVER candidates: it is too general to find one system.
5. A candidate is kept when it holds a handle that remains, or when its name is a system name (lowercase,
   letters and digits only: `cryptoproservice` is `CryptoProService`). Rank the name matches first, then by
   the number of handles that remain, then by the name. Keep KEEP.

Stdout: one line per kept candidate, `candidate: <abs dir> <name-match|-> <n> handles: <h> <h> ...`; one line
per cut candidate, `cut: <abs dir> <reason>`; a `note:` line for a map with no `Other systems` section; then
`discover: <k> kept, <c> cut, <n> candidates, <h> handles, <d> dropped`. The same lines go to
`<course-dir>/discover/result.txt`, with `handles.txt` (the `-f` file), `candidates.txt` and `matches.tsv`
(`<candidate>\\t<handle>`, one line per match).

Exit 0 when the search ran (also with no candidate), 2 on a usage or read error. Standard library only.
"""

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

INCLUDES = ("java", "kt", "xml", "yml", "yaml", "properties", "json", "md", "proto", "sql", "xsl", "xslt", "go",
            "ts", "py", "cs", "conf")
EXCLUDE_DIRS = (".git", "node_modules", "target", "build")
DROP_OVER = 5
KEEP = 8
WORKERS = 4
SECTION = "## Other systems"
HANDLE = re.compile(r"`([^`\n]+)`")
USAGE = "usage: course_discover.py <course-dir> <parent-dir>... [--source <path>]...\n"


def squash(name):
    """A name in lowercase with letters and digits only: the form in which two names match."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def slug(name):
    """The slug rule of convention 5 of SKILL.md, for a directory name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower())[:40].strip("-") or "topic"


def _section(text):
    """The lines of the `Other systems` section of a map, or None when the map has no such section."""
    lines, inside, found = [], False, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == SECTION
            found = found or inside
            continue
        if inside:
            lines.append(line)
    return lines if found else None


def read_maps(course_dir):
    """(sorted handles, set of squashed system names, list of map file names with no section)."""
    handles, names, missing = set(), set(), []
    folder = os.path.join(course_dir, "map")
    for entry in sorted(os.listdir(folder)):
        if not entry.endswith(".md"):
            continue
        with open(os.path.join(folder, entry), encoding="utf-8") as handle:
            lines = _section(handle.read())
        if lines is None:
            missing.append(entry)
            continue
        for line in lines:
            fact = line.lstrip("-* ").split(" | ", 1)[0]
            handles.update(value.strip() for value in HANDLE.findall(fact) if value.strip())
            head = fact.split(":", 1)[0] if ":" in fact else ""
            head = HANDLE.sub("", head)
            for part in [re.sub(r"\(.*?\)", "", head)] + re.findall(r"\((.*?)\)", head):
                if squash(part):
                    names.add(squash(part))
    return sorted(handles), names, missing


def candidates(parents, sources, map_ids):
    """The absolute directories in `parents` that are not sources and not hidden, sorted, each once."""
    found = set()
    sources = {os.path.realpath(path) for path in sources}
    for parent in parents:
        for entry in os.listdir(parent):
            path = os.path.join(parent, entry)
            if entry.startswith(".") or not os.path.isdir(path):
                continue
            if os.path.realpath(path) in sources or (not sources and slug(entry) in map_ids):
                continue
            found.add(os.path.abspath(path))
    return sorted(found)


def grep_argv(handles_file, candidate):
    return (["grep", "-r", "-o", "-h", "-s", "-I", "-F", "-f", handles_file]
            + ["--include=*.%s" % include for include in INCLUDES]
            + ["--exclude-dir=%s" % name for name in EXCLUDE_DIRS]
            + [candidate])


def search(handles_file, candidate, handles):
    """The set of handles that `candidate` holds: one grep; each printed match, and each handle inside it."""
    run = subprocess.run(grep_argv(handles_file, candidate), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, errors="replace", shell=False)
    if run.returncode > 1 and not run.stdout:
        sys.stderr.write("course_discover: grep exit %d in %s\n" % (run.returncode, candidate))
    printed = set(run.stdout.splitlines())
    return {handle for handle in handles if any(handle in match for match in printed)}


def rank(found, names):
    """(kept lines, cut lines) from {candidate: set of handles that remain or not}."""
    counts = {}
    for held in found.values():
        for handle in held:
            counts[handle] = counts.get(handle, 0) + 1
    dropped = {handle for handle, count in counts.items() if count > DROP_OVER}
    ranked, cut = [], []
    for path, held in found.items():
        kept = sorted(held - dropped)
        match = squash(os.path.basename(path)) in names
        if kept or match:
            ranked.append((not match, -len(kept), os.path.basename(path), path, match, kept))
        elif held:
            cut.append((path, "only handles of more than %d candidates" % DROP_OVER))
    ranked.sort()
    lines = ["candidate: %s %s %d handles:%s" % (path, "name-match" if match else "-", len(kept),
                                                "".join(" " + handle for handle in kept))
             for _, _, _, path, match, kept in ranked[:KEEP]]
    cut += [(path, "more than %d discovered sources" % KEEP) for _, _, _, path, _, _ in ranked[KEEP:]]
    return lines, ["cut: %s %s" % (path, reason) for path, reason in sorted(cut)], dropped


def _write(path, lines):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(line + "\n" for line in lines))


def _parse(argv):
    """(course dir, parents, sources) or None after a usage line."""
    positional, sources, index = [], [], 0
    while index < len(argv):
        if argv[index] == "--source":
            if index + 1 >= len(argv):
                return None
            sources.append(argv[index + 1])
            index += 2
            continue
        positional.append(argv[index])
        index += 1
    if len(positional) < 2:
        return None
    return positional[0], positional[1:], sources


def main(argv):
    parsed = _parse(argv)
    if parsed is None:
        sys.stderr.write(USAGE)
        return 2
    course_dir, parents, sources = parsed
    for folder in [os.path.join(course_dir, "map")] + parents:
        if not os.path.isdir(folder):
            sys.stderr.write("course_discover: not a directory: %s\n" % folder)
            return 2
    try:
        handles, names, missing = read_maps(course_dir)
        map_ids = {entry[:-3] for entry in os.listdir(os.path.join(course_dir, "map")) if entry.endswith(".md")}
        found_dirs = candidates(parents, sources, map_ids)
    except (OSError, UnicodeDecodeError) as error:
        sys.stderr.write("course_discover: %s\n" % error)
        return 2
    out = os.path.join(course_dir, "discover")
    os.makedirs(out, exist_ok=True)
    handles_file = os.path.join(out, "handles.txt")
    _write(handles_file, handles)
    _write(os.path.join(out, "candidates.txt"), found_dirs)
    found = {}
    if handles and found_dirs:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            held = pool.map(lambda path: search(handles_file, path, handles), found_dirs)
            found = dict(zip(found_dirs, held))
    _write(os.path.join(out, "matches.tsv"),
           ["%s\t%s" % (path, handle) for path in found_dirs for handle in sorted(found.get(path, ()))])
    kept, cut, dropped = rank(found, names)
    lines = kept + cut + ["note: map %s has no Other systems section" % name for name in missing]
    lines.append("discover: %d kept, %d cut, %d candidates, %d handles, %d dropped"
                 % (len(kept), len(cut), len(found_dirs), len(handles), len(dropped)))
    _write(os.path.join(out, "result.txt"), lines)
    sys.stdout.write("".join(line + "\n" for line in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
