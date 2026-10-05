"""Tests for video/check_scene.py: the static check that render.sh runs on <output-dir>/scene/ before it
copies the scene into the run directory (spec 4.3 and 7.2). The file holds one failing scene for each rule
and each token of spec 7.2, each built as the clean fixture (tests/fixtures/scene-clean/, never compiled)
with one edit and asserted by its line, and the clean scene. A failing case asserts the exit code 1, an
empty stderr and the exact list of stdout lines, unless it says otherwise. <n> in a comment is the number
of the planted line, which each test computes. Each test names the mutation that turns it red."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
CHECK_SCENE = TESTS.parent / "video" / "check_scene.py"
SCENE_CLEAN = TESTS / "fixtures" / "scene-clean"

USAGE = "usage: check_scene.py <scene-dir>\n"

# The two token lists of spec 7.2, in the spec's order (written out here, not imported from the tool): the
# tokens that count wherever they stand, and the tokens that count only when the next character is not a
# letter or a digit (`<mask` refuses <mask> but not <maskUnits).
PLAIN_TOKENS = [
    "require(", "import(", "fetch(", "foreignObject", "dangerouslySetInnerHTML", "clipPath", "href",
    "http://", "https://", "@ts-nocheck", "@ts-ignore", "@ts-expect-error", "as unknown", "<any>",
]
WORD_TOKENS = ["<mask", "<use", "<image", "as any", ": any"]


def run_check(*arguments):
    """check_scene.py with `arguments`, as a CompletedProcess of text."""
    return subprocess.run(
        [sys.executable, "-B", str(CHECK_SCENE)] + [str(a) for a in arguments],
        capture_output=True, text=True, timeout=60,
    )


def check_scene(directory):
    """check_scene.py on the scene directory `directory`."""
    return run_check(directory)


def scene_copy(test, edit=None):
    """A temporary copy of SCENE_CLEAN, removed when `test` is cleaned up; `edit(copy)` runs on it first.
    Returns the copy (a Path)."""
    tmp = tempfile.TemporaryDirectory(prefix="check-scene-")
    test.addCleanup(tmp.cleanup)
    copy = Path(tmp.name) / "scene"
    shutil.copytree(SCENE_CLEAN, copy)
    if edit is not None:
        edit(copy)
    return copy


def append(directory, name, text):
    """Add `text` (a str, or bytes) and a line break to the end of the file `name` of `directory`, which
    ends with a line break. Returns the number of the first line added."""
    path = Path(directory) / name
    data = path.read_bytes()
    assert data.endswith(b"\n"), name
    payload = text if isinstance(text, bytes) else text.encode("utf-8")
    path.write_bytes(data + payload + b"\n")
    return data.count(b"\n") + 1


def prepend(directory, name, text):
    """Add `text` and a line break before the first line of the file `name` of `directory`."""
    path = Path(directory) / name
    path.write_text(text + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")


class SceneCase(unittest.TestCase):
    def assertVerdict(self, done, code, causes):
        """`done` exited with `code`, wrote nothing to stderr, and wrote exactly the lines `causes`."""
        self.assertEqual((done.returncode, done.stderr, done.stdout.splitlines()), (code, "", causes))

    def assertFails(self, done, causes):
        """`done` failed with exactly the cause lines `causes` (each is the text after "FAIL ")."""
        self.assertVerdict(done, 1, ["FAIL " + cause for cause in causes])


class CleanSceneCase(SceneCase):
    """A scene that passes."""

    # red: the clause of a remotion import starts at the first `import` or `export` word before it (the
    # two comment lines above the import of remotion give a fault), `./script.gen` is refused without its
    # file, a near miss is matched (<masks, <useful, <images, as anyone, : anything), or the re-export
    # of an allowed name (Part.tsx) is refused
    def test_the_clean_fixture_passes(self):
        """The fixture itself: Film.tsx and Part.tsx, an import of ./script.gen with no such file."""
        self.assertVerdict(check_scene(SCENE_CLEAN), 0, [])

    # red: a name of the five is missing from the tool's list (Easing, spring or interpolateColors; the
    # fixture brings in the other two), so the re-export fails by its line
    def test_every_allowed_name_of_remotion_passes(self):
        """The clean copy with a re-export of Easing, spring and interpolateColors from remotion appended to
        Part.tsx."""
        copy = scene_copy(self)
        append(copy, "Part.tsx", 'export { Easing, spring, interpolateColors } from "remotion";')
        self.assertVerdict(check_scene(copy), 0, [])

    # red: a hidden entry is a fault (.DS_Store, a hidden directory), or script.gen.ts is read (its
    # @ts-nocheck and its import of fs would be faults)
    def test_hidden_entries_and_script_gen_are_ignored(self):
        """The clean copy plus .DS_Store, a directory .cache/ with x.tsx in it, and a script.gen.ts that
        holds @ts-nocheck and an import of fs."""
        def edit(copy):
            (copy / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")
            (copy / ".cache").mkdir()
            (copy / ".cache" / "x.tsx").write_text('import fs from "fs";\n', encoding="utf-8")
            (copy / "script.gen.ts").write_text('// @ts-nocheck\nimport fs from "fs";\n', encoding="utf-8")

        self.assertVerdict(check_scene(scene_copy(self, edit)), 0, [])


class DirectoryRuleCase(SceneCase):
    """The rules of spec 4.3."""

    # red: a path that is not a directory is read (a traceback, exit 2), or its cause names another path
    # than the one given
    def test_no_scene_directory(self):
        """A path that does not exist, and the path of a file."""
        copy = scene_copy(self)
        for path in (copy / "absent", copy / "Film.tsx"):
            with self.subTest(path=path.name):
                self.assertFails(check_scene(path), ["no scene directory: %s" % path])

    # red: Film.tsx is not required, or the cause has another text
    def test_no_film_tsx(self):
        """The clean copy with Film.tsx removed."""
        copy = scene_copy(self, lambda d: (d / "Film.tsx").unlink())
        self.assertFails(check_scene(copy), ["no Film.tsx"])

    # red: a sub-directory passes, or the check reads the files inside it (Deep.tsx holds a fault)
    def test_a_directory_fails(self):
        """The clean copy plus a directory parts/ with Deep.tsx in it, which imports Sequence."""
        def edit(copy):
            (copy / "parts").mkdir()
            deep = copy / "parts" / "Deep.tsx"
            deep.write_text('import { Sequence } from "remotion";\n', encoding="utf-8")

        self.assertFails(check_scene(scene_copy(self, edit)), ["parts is a directory"])

    # red: a file that is not *.ts or *.tsx passes (notes.md, data.json), or the cause names it wrongly
    def test_another_file_fails(self):
        """The clean copy plus one other file, alone in its copy: notes.md, then data.json."""
        for name in ("notes.md", "data.json"):
            with self.subTest(name=name):
                copy = scene_copy(self, lambda d: (d / name).write_text("{}\n", encoding="utf-8"))
                self.assertFails(check_scene(copy), ["%s is not a .ts or .tsx file" % name])

    # red: Film.tsx is not read for its function, or `export const Film = (` counts as the function
    def test_film_without_the_exported_function(self):
        """The clean copy with `export function Film(` written as `export const Film = (`."""
        def edit(copy):
            film = copy / "Film.tsx"
            text = film.read_text(encoding="utf-8")
            self.assertIn("export function Film(", text)
            film.write_text(text.replace("export function Film(", "export const Film = ("), encoding="utf-8")

        self.assertFails(check_scene(scene_copy(self, edit)), ['Film.tsx has no "export function Film("'])


# Each row: the text appended to Film.tsx, the cause of its line, and the index (from 0) of the appended
# line that holds the quoted source, where the line of the cause is.
IMPORT_FAULTS = [
    ('import { getLength } from "@remotion/paths";', 'import from "@remotion/paths"', 0),
    ('import { makeAt } from "../kit/marks";', 'import from "../kit/marks"', 0),
    ('import "./side";', 'import from "./side"', 0),
    ('export { p } from "../other/motion";', 'import from "../other/motion"', 0),
    ("import { Part } from './Part.tsx';", 'import from "./Part.tsx"', 0),
    ('import { Sequence } from "remotion";', '"Sequence" from remotion', 0),
    ('import { useCurrentFrame, AbsoluteFill as Fill } from "remotion";', '"AbsoluteFill" from remotion', 0),
    ('import type { SpringConfig } from "remotion";', '"SpringConfig" from remotion', 0),
    ('import { type SpringConfig, spring } from "remotion";', '"SpringConfig" from remotion', 0),
    ('import * as R from "remotion";', '"* as R" from remotion', 0),
    ('import Remotion from "remotion";', '"Remotion" from remotion', 0),
    ('export { Sequence } from "remotion";', '"Sequence" from remotion', 0),
    ('export * from "remotion";', '"*" from remotion', 0),
    ('import {\n  spring, Img,\n} from "remotion";', '"Img" from remotion', 2),
]


class ImportRuleCase(SceneCase):
    """The import rule of spec 7.2: the sources, and the names of remotion."""

    # red: a source list that allows any ../kit/... or any ./..., a re-export that is not read, `type`
    # taken as the name (after `import`, or before a name in the braces), the clause of a namespace or a
    # default import not quoted, the line of a cause that is not the line of the quoted source (the first
    # line of a three-line import)
    def test_each_import_fault_fails_by_its_line(self):
        """The clean copy with one of the 14 faults appended to Film.tsx."""
        for text, cause, offset in IMPORT_FAULTS:
            with self.subTest(text=text):
                copy = scene_copy(self)
                first = append(copy, "Film.tsx", text)
                self.assertFails(check_scene(copy), ["Film.tsx:%d: %s" % (first + offset, cause)])

    # red: only Film.tsx is read, or the cause names Film.tsx
    def test_a_fault_in_another_file_names_that_file(self):
        """The clean copy with an import of Sequence from remotion appended to Part.tsx."""
        copy = scene_copy(self)
        first = append(copy, "Part.tsx", 'import { Sequence } from "remotion";')
        self.assertFails(check_scene(copy), ['Part.tsx:%d: "Sequence" from remotion' % first])

    # red: the clause is the text after the nearest `import` or `export` word, wherever it stands (the
    # first sub-test then gives exit 0: the `export {` of the comment hides Sequence), a clause with a
    # comment mark (`/*`, `*/`, `//`) is read around instead of quoted and refused (each of the next three
    # sub-tests then gives exit 0: the block comment holds a line that starts with `export {` or
    # `import {`, the clause starts after it, and the name before the comment is never read), or a list
    # is read by the first word of each item when an item is not `[type ]name[ as alias]` (the last
    # sub-test then gives exit 0: a quoted alias with a line continuation holds a line that starts with
    # `export {`, the clause starts after it, and its last item is `interpolate "`)
    def test_a_comment_inside_the_clause_never_hides_a_name(self):
        """Six copies, each with two lines appended to one file: a list that starts with Sequence and holds
        the words `export {` in a line comment; one that holds them in a block comment that closes before
        the name `useCurrentFrame`; three lists whose block comment opens after a refused name, holds a
        line that starts with `import {` or `export {`, and closes after an allowed name, in Film.tsx, in
        Part.tsx, and as a re-export in Part.tsx; and a re-export in Part.tsx of Sequence and of
        interpolate as a quoted alias that a backslash carries to the next line, which starts with
        `export {`."""
        planted = [
            ("Film.tsx", 'import { Sequence, // export {\n  useCurrentFrame } from "remotion";'),
            ("Film.tsx", 'import { Sequence, /*\nexport { */ useCurrentFrame } from "remotion";'),
            ("Film.tsx", 'import { Sequence, /*\nexport { spring */ } from "remotion";'),
            ("Part.tsx", 'import { Sequence /*\nimport { useCurrentFrame, Easing */ } from "remotion";'),
            ("Part.tsx", 'export { Sequence, AbsoluteFill /*\nexport { interpolate */ } from "remotion";'),
            ("Part.tsx", 'export { Sequence, interpolate as "a\\\n'
                         'export { useCurrentFrame, interpolate " } from "remotion";'),
        ]
        for name, text in planted:
            with self.subTest(name=name, text=text):
                copy = scene_copy(self)
                append(copy, name, text)
                done = check_scene(copy)
                self.assertEqual((done.returncode, done.stderr), (1, ""))
                self.assertRegex(done.stdout, r'(?m)^FAIL %s:\d+: ".*" from remotion$' % re.escape(name))

    # red: a quoted source is printed raw (the source after the string "import" runs to the next quote,
    # over four lines, so its cause takes five lines; the source of 62 characters is printed whole), or the
    # cut source is not stripped (the first cause then ends in a space before its closing quote)
    def test_a_quoted_source_is_one_line_of_at_most_40_characters(self):
        """Two copies, each with text appended to Part.tsx: the string "import", three lines of constants
        and a line with the string "film"; then one import of x from "./" and 60 letters."""
        keyword = ('export const KEYWORD = "import";\nexport const WIDE = 640;\nexport const TALL = 360;\n'
                   'export const RATE = 30;\nexport const NAME = "film";')
        long_source = "./" + "abcdefghij" * 6
        # The source of `keyword` runs from the quote that closes "import" to the quote that opens "film".
        # Collapsed, its 40th character is a space, which the strip removes.
        planted = [
            (keyword, keyword.split('"')[2]),
            ('import x from "%s";' % long_source, long_source),
        ]
        for text, source in planted:
            with self.subTest(text=text):
                copy = scene_copy(self)
                first = append(copy, "Part.tsx", text)
                cut = " ".join(source.split())[:40].strip()
                self.assertFails(check_scene(copy), ['Part.tsx:%d: import from "%s"' % (first, cut)])

    # red: the clause is one braced list even when it holds another import (the second import of a line is
    # then read as the names of the first, `spring`, and Sequence passes with exit 0)
    def test_two_imports_on_one_line_never_hide_a_name(self):
        """The clean copy with one line appended to Film.tsx: an import of spring from remotion, then an
        import of Sequence from remotion."""
        copy = scene_copy(self)
        append(copy, "Film.tsx", 'import { spring } from "remotion"; import { Sequence } from "remotion";')
        done = check_scene(copy)
        self.assertEqual((done.returncode, done.stderr), (1, ""))
        self.assertRegex(done.stdout, r'(?m)^FAIL Film\.tsx:\d+: ".*" from remotion$')


class TokenRuleCase(SceneCase):
    """The token rule of spec 7.2, with its two lists written out above."""

    # red: a token is missing from the tool's list (one sub-test per token of the 19), or a comment is
    # skipped (each line planted is a comment)
    def test_each_token_fails_by_its_line(self):
        """The clean copy with the line `// <token>` appended to Film.tsx, for each of the 19 tokens."""
        tokens = PLAIN_TOKENS + WORD_TOKENS
        self.assertEqual(len(tokens), 19)
        for token in tokens:
            with self.subTest(token=token):
                copy = scene_copy(self)
                line = append(copy, "Film.tsx", "// " + token)
                self.assertFails(check_scene(copy), ['Film.tsx:%d: token "%s"' % (line, token)])

    # red: a plain substring match (<maskx passes through as <mask), or a boundary that takes `_` as a
    # letter (<mask_ passes), or a `>` or a space or the end of the line as a letter
    def test_word_tokens_need_a_boundary(self):
        """The clean copy with `// <token>` and one more character appended to Film.tsx, for the five
        tokens with a boundary: a letter and a digit pass; `_`, `>` and a space fail by the line."""
        for token in WORD_TOKENS:
            for follower in ("x", "9"):
                with self.subTest(token=token, follower=follower):
                    copy = scene_copy(self)
                    append(copy, "Film.tsx", "// " + token + follower)
                    self.assertVerdict(check_scene(copy), 0, [])
            for follower in ("_", ">", " "):
                with self.subTest(token=token, follower=follower):
                    copy = scene_copy(self)
                    line = append(copy, "Film.tsx", "// " + token + follower)
                    self.assertFails(check_scene(copy), ['Film.tsx:%d: token "%s"' % (line, token)])

    # red: the match ignores case for every token (HREF, Fetch(, <Mask>, AS ANY, @TS-IGNORE and
    # @TS-EXPECT-ERROR are faults), @ts-nocheck is matched with its case (// @TS-NOCHECK and
    # // @Ts-NoCheck pass with exit 0; TypeScript reads that pragma in any case), or its cause names the
    # token in the case of the file
    def test_tokens_keep_their_case_but_ts_nocheck_counts_in_any_case(self):
        """The clean copy with a line of each of six tokens in other case appended to Film.tsx, which
        passes; then two copies, each with one line appended to Film.tsx: `// @TS-NOCHECK`, then
        `// @Ts-NoCheck`, which fail by the line as the token "@ts-nocheck"."""
        with self.subTest(text="other tokens in other case"):
            copy = scene_copy(self)
            others = ("HREF", "Fetch(", "<Mask>", "AS ANY", "@TS-IGNORE", "@TS-EXPECT-ERROR")
            append(copy, "Film.tsx", "\n".join("// " + other for other in others))
            self.assertVerdict(check_scene(copy), 0, [])
        for pragma in ("@TS-NOCHECK", "@Ts-NoCheck"):
            with self.subTest(text=pragma):
                copy = scene_copy(self)
                line = append(copy, "Film.tsx", "// " + pragma)
                self.assertFails(check_scene(copy), ['Film.tsx:%d: token "@ts-nocheck"' % line])

    # red: a token gives one cause for the file (not for each line), or one for each place on a line
    def test_a_token_counts_once_for_each_line(self):
        """The clean copy with a line that holds `href` twice and a later line that holds it once."""
        copy = scene_copy(self)
        first = append(copy, "Film.tsx", "// href href\n// href")
        self.assertFails(
            check_scene(copy),
            ['Film.tsx:%d: token "href"' % first, 'Film.tsx:%d: token "href"' % (first + 1)],
        )

    # red: a strict decode of the file (a traceback and no FAIL line)
    def test_bytes_that_are_not_utf8_do_not_stop_the_check(self):
        """The clean copy with the bytes `// \\xff @ts-nocheck` appended to Film.tsx."""
        copy = scene_copy(self)
        line = append(copy, "Film.tsx", b"// \xff @ts-nocheck")
        self.assertFails(check_scene(copy), ['Film.tsx:%d: token "@ts-nocheck"' % line])


class OutputCase(SceneCase):
    # red: the check stops at the first cause, or the order follows the file system (or the names of the
    # files), or the causes of one line come in another order than imports, then plain tokens in the list's
    # order
    def test_causes_come_in_a_fixed_order(self):
        """A copy with a directory zz/, a file notes.md, `// @ts-ignore` as the new line 1 of Part.tsx, the
        exported function of Film.tsx written as a constant, and one line appended to Film.tsx that holds
        an import of Sequence from remotion, `fetch(` and `href`."""
        def edit(copy):
            (copy / "zz").mkdir()
            (copy / "notes.md").write_text("notes\n", encoding="utf-8")
            prepend(copy, "Part.tsx", "// @ts-ignore")
            film = copy / "Film.tsx"
            text = film.read_text(encoding="utf-8")
            film.write_text(text.replace("export function Film(", "export const Film = ("), encoding="utf-8")

        copy = scene_copy(self, edit)
        line = append(copy, "Film.tsx", 'import { Sequence } from "remotion"; // fetch( href')
        self.assertFails(check_scene(copy), [
            "notes.md is not a .ts or .tsx file",
            "zz is a directory",
            'Film.tsx has no "export function Film("',
            'Film.tsx:%d: "Sequence" from remotion' % line,
            'Film.tsx:%d: token "fetch("' % line,
            'Film.tsx:%d: token "href"' % line,
            'Part.tsx:1: token "@ts-ignore"',
        ])

    # red: the usage goes to stdout, the exit code is not 2, or a second argument is taken for the scene
    def test_usage(self):
        """No argument, and two arguments."""
        scene = scene_copy(self)
        for arguments in ((), (scene, scene)):
            with self.subTest(arguments=len(arguments)):
                done = run_check(*arguments)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (2, "", USAGE))


if __name__ == "__main__":
    unittest.main()
