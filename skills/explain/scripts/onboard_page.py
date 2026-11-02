#!/usr/bin/env python3
"""The `diagrams` command of onboard.py (spec section 9): writes the PlantUML fence of each place of a
map to its own `.puml` file.

Usage: onboard.py diagrams <map.md> --out <dir>
Writes `architecture.puml`, `flow-<flow-id>.puml` and `state.puml`, each the fence lines wrapped in
`@startuml` / `@enduml`; a place with `none found` or no diagram writes nothing. Prints
`diagrams: stale <file>` for each `.puml` of the directory no place produced (deleting nothing), then
`diagrams: ok <n> files`.
Exit 0 on success, 1 when a place holds a Mermaid diagram (`diagrams: <where>: not plantuml`, stdout),
2 on a usage error (stderr), an unreadable map (`map: cannot read ...`, stdout) or an unwritable directory
(`diagrams: cannot write <dir>: <reason>`, stderr).
"""

import argparse
import os
import sys
from typing import NoReturn

import onboard


def diagram_files(doc: onboard.MapDoc) -> dict[str, str]:
    """Each place with a diagram mapped from its file id to the file body: the first fence wrapped."""
    files = {}
    for where, scope, _ in onboard._places(doc):
        if not scope.diagrams:
            continue
        diagram = scope.diagrams[0]
        if diagram.notation != onboard.PLANTUML:
            raise onboard.OnboardError("diagrams: %s: not plantuml" % where, 1)
        ident = where
        if isinstance(scope, onboard.Flow):
            ident = "flow-" + where
            if ident in files:
                raise onboard.OnboardError("diagrams: flow %s twice" % where, 1)
        files[ident] = "@startuml\n" + diagram.text + "\n@enduml\n"
    return files


class _Parser(argparse.ArgumentParser):
    """The arguments of `diagrams`: the map and `--out`; any error is the usage and exit 2."""

    def __init__(self) -> None:
        super().__init__(add_help=False)
        self.add_argument("map")
        self.add_argument("--out", required=True)

    def error(self, message: str) -> NoReturn:
        raise onboard.OnboardError(onboard.USAGE, 2)


def _write(out: str, files: dict[str, str]) -> None:
    try:
        os.makedirs(out, exist_ok=True)
        for ident, body in files.items():
            with open(os.path.join(out, ident + ".puml"), "w", encoding="utf-8") as handle:
                handle.write(body)
    except OSError as error:
        raise onboard.OnboardError("diagrams: cannot write %s: %s" % (out, error.strerror or error), 2) from error


def cmd_diagrams(argv: list[str]) -> int:
    args = _Parser().parse_args(argv)
    doc = onboard.read_map(args.map)
    files = diagram_files(doc)
    _write(args.out, files)
    produced = {ident + ".puml" for ident in files}
    stale = sorted(name for name in os.listdir(args.out) if name.endswith(".puml") and name not in produced)
    sys.stdout.write("".join("diagrams: stale %s\n" % name for name in stale))
    sys.stdout.write("diagrams: ok %d files\n" % len(files))
    return 0
