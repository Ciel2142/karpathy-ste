"""Tests for mermaid_svg.py: the pinned bundle by hash, the SVG finish and the command line
(spec section 8)."""

import contextlib
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import mermaid_svg  # noqa: E402

BUNDLE = mermaid_svg.bundle_path()
HAVE_BUNDLE = BUNDLE.is_file()
NO_BUNDLE = "mermaid bundle missing: %s" % BUNDLE
E2E = os.environ.get("EXPLAIN_MERMAID_E2E") == "1"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "mermaid"

SAMPLE = (
    '<svg id="flow" width="100%" style="max-width: 496.4px;" viewBox="0 0 496.4 311.5" '
    'role="graphics-document document" aria-roledescription="flowchart-v2" '
    'xmlns="http://www.w3.org/2000/svg"><style>#flow{font-size:14px}</style>'
    "<g><text>a</text></g></svg>"
)


def run(argv, env=None):
    """Run main with argv; return the exit code, stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, env or {}):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mermaid_svg.main(argv)
    return code, out.getvalue(), err.getvalue()


def root_tag(svg):
    """The root start tag of an svg text."""
    return re.match(r"<svg[^>]*>", svg).group(0)


def svg_text(svg):
    """The words of every <text> element of an svg, tags cut and white space squashed."""
    parts = re.findall(r"<text\b[^>]*>(.*?)</text>", svg, re.S)
    return " ".join(" ".join(re.sub(r"<[^>]*>", " ", part).split()) for part in parts)


class TempCase(unittest.TestCase):
    """A case with `tmp/` and `work/` in a temporary directory, as tests/test_verify.py has."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._dir.name)
        self.tmp = os.path.join(self.root, "tmp")
        self.work = os.path.join(self.root, "work")
        os.mkdir(self.tmp)
        os.mkdir(self.work)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(self._kill_strays)

    def _kill_strays(self):
        subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)


class FinishSvgCase(TempCase):

    def finish(self, svg=SAMPLE):
        return mermaid_svg.finish_svg(svg, "flow", "The path & the reply")

    def test_size_is_the_viewbox_rounded_up(self):
        tag = root_tag(self.finish())
        self.assertEqual(tag.count('width="497"'), 1, tag)
        self.assertEqual(tag.count('height="312"'), 1, tag)
        self.assertEqual(tag.count("width="), 1, tag)
        self.assertEqual(tag.count("height="), 1, tag)
        self.assertIn('viewBox="0 0 496.4 311.5"', tag)

    def test_other_attributes_that_end_in_width_are_kept(self):
        svg = SAMPLE.replace('id="flow"', 'id="flow" stroke-width="2" data-width="9"')
        tag = root_tag(self.finish(svg))
        self.assertIn('stroke-width="2"', tag)
        self.assertIn('data-width="9"', tag)

    def test_whole_viewbox_numbers_stay_whole(self):
        svg = SAMPLE.replace("0 0 496.4 311.5", "0 0 300.0 120")
        tag = root_tag(self.finish(svg))
        self.assertIn('width="300"', tag)
        self.assertIn('height="120"', tag)

    def test_root_max_width_style_is_removed(self):
        out = self.finish()
        self.assertNotIn("max-width", out)
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', root_tag(out))
        self.assertIn('id="flow"', root_tag(out))

    def test_other_style_declarations_are_kept(self):
        svg = SAMPLE.replace("max-width: 496.4px;", "max-width: 496.4px; background: red;")
        tag = root_tag(self.finish(svg))
        self.assertNotIn("max-width", tag)
        self.assertIn("background: red;", tag)

    def test_role_is_img(self):
        out = self.finish()
        self.assertEqual(out.count('role="img"'), 1)
        self.assertNotIn("graphics-document", out)

    def test_title_and_aria_are_added(self):
        out = self.finish()
        tag = root_tag(out)
        self.assertIn('data-ste="skip"', tag)
        self.assertIn('aria-labelledby="flow-title"', tag)
        self.assertEqual(
            out[len(tag):].split("</title>")[0] + "</title>",
            '<title id="flow-title">The path &amp; the reply</title>',
        )

    def test_the_rest_of_the_svg_is_kept_byte_for_byte(self):
        out = self.finish()
        self.assertTrue(
            out.endswith('<style>#flow{font-size:14px}</style><g><text>a</text></g></svg>')
        )

    def test_no_viewbox_is_a_fault(self):
        svg = SAMPLE.replace(' viewBox="0 0 496.4 311.5"', "")
        with self.assertRaises(mermaid_svg.MermaidError) as caught:
            self.finish(svg)
        self.assertEqual(str(caught.exception), "mermaid: FAIL flow no viewBox")
        self.assertEqual(caught.exception.code, 1)

    def test_foreign_object_is_a_fault(self):
        svg = SAMPLE.replace("<g>", "<g><foreignObject><div>a</div></foreignObject>")
        with self.assertRaises(mermaid_svg.MermaidError) as caught:
            self.finish(svg)
        self.assertEqual(str(caught.exception), "mermaid: FAIL flow foreignObject in output")
        self.assertEqual(caught.exception.code, 1)


class BundleCase(TempCase):

    def setUp(self):
        super().setUp()
        self.bundle = Path(self.work) / "m" / mermaid_svg.BUNDLE_NAME

    def make_file(self, name, data):
        path = Path(self.work) / name
        path.write_bytes(data)
        return path

    def ensure(self, urls):
        """ensure_bundle on self.bundle with BUNDLE_URLS patched; return (path, stdout)."""
        out = io.StringIO()
        with mock.patch.object(mermaid_svg, "BUNDLE_URLS", tuple(urls)):
            with contextlib.redirect_stdout(out):
                path = mermaid_svg.ensure_bundle(self.bundle)
        return path, out.getvalue()

    def assert_no_part_file(self):
        parts = list(self.bundle.parent.glob("*.part")) if self.bundle.parent.is_dir() else []
        self.assertEqual(parts, [])

    def test_bundle_path_reads_the_env_then_the_default(self):
        with mock.patch.dict(os.environ, {"EXPLAIN_MERMAID_JS": str(self.bundle)}):
            self.assertEqual(mermaid_svg.bundle_path(), self.bundle)
        with mock.patch.dict(os.environ):
            os.environ.pop("EXPLAIN_MERMAID_JS", None)
            self.assertEqual(
                mermaid_svg.bundle_path(),
                Path.home() / "karpathy" / "video-workspace" / "mermaid" / mermaid_svg.BUNDLE_NAME,
            )

    def test_wrong_bytes_fail_sha256_and_leave_no_part_file(self):
        wrong = self.make_file("wrong.js", b"twenty bytes exactly")
        self.assertEqual(wrong.stat().st_size, 20)
        got = hashlib.sha256(wrong.read_bytes()).hexdigest()
        out = io.StringIO()
        with mock.patch.object(mermaid_svg, "BUNDLE_URLS", (wrong.as_uri(),)):
            with contextlib.redirect_stdout(out):
                with self.assertRaises(mermaid_svg.MermaidError) as caught:
                    mermaid_svg.ensure_bundle(self.bundle)
        self.assertEqual(str(caught.exception), "mermaid: FAIL sha256 " + got)
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(out.getvalue(), "mermaid: download mermaid-12.2.0.min.js (5.5 MB)\n")
        self.assertFalse(self.bundle.exists())
        self.assert_no_part_file()

    def test_bundle_in_place_with_wrong_bytes_fails_and_stays(self):
        self.bundle.parent.mkdir()
        self.bundle.write_bytes(b"twenty bytes exactly")
        got = hashlib.sha256(b"twenty bytes exactly").hexdigest()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(mermaid_svg.MermaidError) as caught:
                mermaid_svg.ensure_bundle(self.bundle)
        self.assertEqual(str(caught.exception), "mermaid: FAIL sha256 " + got)
        self.assertEqual(caught.exception.code, 2)
        self.assertTrue(self.bundle.is_file())
        self.assertEqual(self.bundle.read_bytes(), b"twenty bytes exactly")
        self.assertEqual(out.getvalue(), "")

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_second_url_is_tried_when_the_first_fails(self):
        missing = Path(self.work) / "no-such-file.js"
        copy = Path(self.work) / "copy.js"
        copy.write_bytes(BUNDLE.read_bytes())
        self.assertFalse(self.bundle.parent.exists())
        path, stdout = self.ensure([missing.as_uri(), copy.as_uri()])
        self.assertEqual(path, self.bundle)
        self.assertEqual(mermaid_svg.sha256_of(self.bundle), mermaid_svg.BUNDLE_SHA256)
        self.assertTrue(self.bundle.parent.is_dir())
        self.assert_no_part_file()
        self.assertEqual(
            stdout,
            "mermaid: download mermaid-12.2.0.min.js (5.5 MB)\n"
            "mermaid: downloaded mermaid-12.2.0.min.js\n",
        )

    def test_both_urls_failing_report_download(self):
        urls = [(Path(self.work) / name).as_uri() for name in ("none-1.js", "none-2.js")]
        with self.assertRaises(mermaid_svg.MermaidError) as caught:
            self.ensure(urls)
        self.assertTrue(
            str(caught.exception).startswith("mermaid: FAIL download mermaid-12.2.0.min.js"),
            str(caught.exception),
        )
        self.assertNotIn("\n", str(caught.exception))
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.bundle.exists())
        self.assert_no_part_file()

    def test_bundle_path_under_a_regular_file_is_a_download_fault(self):
        afile = Path(self.work) / "afile"
        afile.write_bytes(b"x")
        self.bundle = afile / mermaid_svg.BUNDLE_NAME
        with self.assertRaises(mermaid_svg.MermaidError) as caught:
            self.ensure([(Path(self.work) / "none.js").as_uri()])
        self.assertTrue(
            str(caught.exception).startswith("mermaid: FAIL download mermaid-12.2.0.min.js"),
            str(caught.exception),
        )
        self.assertNotIn("\n", str(caught.exception))
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(afile.read_bytes(), b"x")
        self.assertEqual(list(Path(self.work).rglob("*.part")), [])

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode 0 file")
    def test_unreadable_bundle_in_place_is_a_bundle_fault(self):
        self.bundle.parent.mkdir()
        self.bundle.write_bytes(b"twenty bytes exactly")
        self.bundle.chmod(0)
        self.addCleanup(self.bundle.chmod, 0o644)
        with self.assertRaises(mermaid_svg.MermaidError) as caught:
            mermaid_svg.ensure_bundle(self.bundle)
        self.assertTrue(
            str(caught.exception).startswith("mermaid: FAIL bundle %s: " % self.bundle),
            str(caught.exception),
        )
        self.assertNotIn("\n", str(caught.exception))
        self.assertEqual(caught.exception.code, 2)

    @unittest.skipUnless(E2E, "EXPLAIN_MERMAID_E2E=1 only")
    def test_real_download_matches_the_hash(self):
        path, _ = self.ensure(mermaid_svg.BUNDLE_URLS)
        self.assertEqual(mermaid_svg.sha256_of(path), mermaid_svg.BUNDLE_SHA256)

    def test_usage_without_a_command_exits_2(self):
        code, out, err = run([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("usage: mermaid_svg.py"), err)

    def test_unknown_command_exits_2_with_usage(self):
        code, out, err = run(["frobnicate"])
        self.assertEqual(code, 2)
        self.assertTrue(err.startswith("usage: mermaid_svg.py"), err)


class RenderCase(TempCase):
    """render through headless Chrome; every run has TMPDIR=<tmp>/ and leaves no process."""

    def env(self, extra=None):
        return {"TMPDIR": self.tmp + "/", **(extra or {})}

    def render(self, *args, env=None):
        """Run `render` with TMPDIR=<tmp>/, then check that nothing is left behind."""
        result = run(["render", *map(str, args)], self.env(env))
        self.assert_no_chrome_left()
        return result

    def assert_no_chrome_left(self):
        """No process matches <tmp> and <tmp> is empty, as tests/test_verify.py checks."""
        found = subprocess.run(
            ["pgrep", "-f", self.tmp], capture_output=True, text=True,
        ).stdout.split()
        if found:
            listing = subprocess.run(
                ["ps", "-o", "pid,ppid,pgid,etime,command", "-p", ",".join(found)],
                capture_output=True, text=True,
            ).stdout
            self.fail("processes left matching %s:\n%s" % (self.tmp, listing))
        self.assertEqual(os.listdir(self.tmp), [], "temp dir not removed")

    def fake_chrome(self, first=""):
        """A Chrome stand-in that, like headless Chrome after --dump-dom, never exits."""
        path = Path(self.work) / "chrome"
        path.write_text(
            "#!/bin/sh\necho $$ > %s.pid\n%swhile :; do sleep 1; done\n" % (path, first)
        )
        path.chmod(0o755)
        return str(path)

    def assert_group_gone(self, chrome):
        """No process is left in the process group of the stand-in."""
        pgid = Path(chrome + ".pid").read_text().strip()
        found = subprocess.run(["pgrep", "-g", pgid], capture_output=True, text=True).stdout
        self.assertEqual(found, "", "process group %s still has members" % pgid)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_render_flow_to_a_file(self):
        out = Path(self.work) / "flow.svg"
        code, stdout, stderr = self.render(FIXTURES / "flow.mmd", out)
        self.assertEqual(code, 0, stdout + stderr)
        self.assertEqual(stdout, "mermaid: ok 1 diagrams\n")
        svg = out.read_text(encoding="utf-8")
        tag = root_tag(svg)
        self.assertNotIn("foreignObject", svg)
        self.assertIn('role="img"', tag)
        self.assertIn('data-ste="skip"', tag)
        self.assertIn('aria-labelledby="flow-title"', tag)
        self.assertIn('<title id="flow-title">flow</title>', svg)
        box = re.search(r'\sviewBox="([^"]*)"', tag).group(1).split()
        width = re.search(r'\swidth="([^"]*)"', tag).group(1)
        height = re.search(r'\sheight="([^"]*)"', tag).group(1)
        self.assertRegex(width, r"^[0-9]+$")
        self.assertRegex(height, r"^[0-9]+$")
        self.assertGreaterEqual(int(width), float(box[2]))
        self.assertGreaterEqual(int(height), float(box[3]))
        self.assertNotIn("max-width", tag)
        words = svg_text(svg)
        self.assertIn("receive the message", words)
        self.assertIn("cancel", words)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_render_to_stdout_keeps_the_svg_clean(self):
        code, stdout, stderr = self.render(FIXTURES / "flow.mmd")
        self.assertEqual(code, 0, stdout + stderr)
        self.assertTrue(stdout.startswith("<svg"), stdout[:200])
        self.assertEqual([l for l in stdout.splitlines() if l.startswith("mermaid:")], [])
        self.assertNotIn("foreignObject", stdout)
        self.assertEqual(stderr, "mermaid: ok 1 diagrams\n")

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_title_option_sets_the_title(self):
        code, stdout, stderr = self.render(FIXTURES / "flow.mmd", "--title", "One message")
        self.assertEqual(code, 0, stdout + stderr)
        self.assertIn('<title id="flow-title">One message</title>', stdout)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_state_diagram_renders(self):
        out = Path(self.work) / "state.svg"
        code, stdout, stderr = self.render(FIXTURES / "state.mmd", out)
        self.assertEqual(code, 0, stdout + stderr)
        svg = out.read_text(encoding="utf-8")
        self.assertNotIn("foreignObject", svg)
        self.assertIn('<title id="state-title">state</title>', svg)
        words = svg_text(svg)
        self.assertIn("Sent", words)
        self.assertIn("Failed", words)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_parse_error_names_the_id_and_exits_1(self):
        out = Path(self.work) / "bad.svg"
        code, stdout, stderr = self.render(FIXTURES / "bad.mmd", out)
        self.assertEqual(code, 1, stdout + stderr)
        self.assertTrue(stdout.startswith("mermaid: FAIL bad Parse error"), stdout)
        self.assertEqual(len(stdout.splitlines()), 1, stdout)
        self.assertFalse(out.exists())

    def test_chrome_not_found_exits_2(self):
        missing = os.path.join(self.work, "no-chrome")
        with mock.patch.object(mermaid_svg, "CHROME", missing):
            code, stdout, stderr = self.render(FIXTURES / "flow.mmd")
        self.assertEqual(code, 2, stdout + stderr)
        self.assertEqual(stdout, "mermaid: FAIL Chrome not found %s\n" % missing)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_timeout_kills_the_group_and_removes_the_temp_dir(self):
        chrome = self.fake_chrome()
        start = time.monotonic()
        with mock.patch.object(mermaid_svg, "CHROME", chrome):
            code, stdout, stderr = self.render(
                FIXTURES / "flow.mmd", env={"MERMAID_TIMEOUT": "1"}
            )
        self.assertLess(time.monotonic() - start, 5)
        self.assertEqual(code, 1, stdout + stderr)
        self.assertEqual(stdout, "mermaid: FAIL timeout\n")
        self.assert_group_gone(chrome)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_dump_without_a_result_is_harness_incomplete(self):
        chrome = self.fake_chrome("printf '<html><body></body></html>\\n'\n")
        with mock.patch.object(mermaid_svg, "CHROME", chrome):
            code, stdout, stderr = self.render(FIXTURES / "flow.mmd")
        self.assertEqual(code, 1, stdout + stderr)
        self.assertEqual(stdout, "mermaid: FAIL harness incomplete\n")
        self.assert_group_gone(chrome)

    def test_bad_id_fails_before_chrome(self):
        copy = Path(self.work) / "1 flow.mmd"
        copy.write_bytes((FIXTURES / "flow.mmd").read_bytes())
        with mock.patch.object(mermaid_svg, "CHROME", os.path.join(self.work, "no-chrome")):
            code, stdout, stderr = self.render(copy)
        self.assertEqual(code, 2, stdout + stderr)
        self.assertEqual(stdout, "mermaid: FAIL 1 flow bad id\n")

    def test_unreadable_input_is_usage(self):
        code, stdout, stderr = self.render(Path(self.work) / "missing.mmd")
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("usage:"), stderr)

    def test_bad_timeout_is_usage(self):
        code, stdout, stderr = self.render(FIXTURES / "flow.mmd", env={"MERMAID_TIMEOUT": "abc"})
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertTrue(stderr.startswith("usage:"), stderr)
        self.assertIn("MERMAID_TIMEOUT", stderr)

    def test_render_with_a_wrong_bundle_prints_the_sha_line_and_exits_2(self):
        wrong = Path(self.work) / "wrong.js"
        wrong.write_bytes(b"twenty bytes exactly")
        got = hashlib.sha256(b"twenty bytes exactly").hexdigest()
        with mock.patch.object(mermaid_svg, "CHROME", sys.executable):
            code, stdout, stderr = self.render(
                FIXTURES / "flow.mmd", env={"EXPLAIN_MERMAID_JS": str(wrong)}
            )
        self.assertEqual(code, 2, stdout + stderr)
        self.assertEqual(stdout, "mermaid: FAIL sha256 %s\n" % got)

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_render_many_returns_every_raw_svg_of_one_run(self):
        diagrams = [
            ("flow", (FIXTURES / "flow.mmd").read_text()),
            ("state", (FIXTURES / "state.mmd").read_text()),
            ("amp", 'flowchart LR\n  a["fish & chips"] --> b\n'),
        ]
        with mock.patch.dict(os.environ, self.env()):
            svgs = mermaid_svg.render_many(diagrams, BUNDLE, 60)
        self.assert_no_chrome_left()
        self.assertEqual(list(svgs), ["flow", "state", "amp"])
        for diagram_id, svg in svgs.items():
            self.assertIn(' id="%s"' % diagram_id, root_tag(svg))
            self.assertTrue(svg.endswith("</svg>"), svg[-200:])
        # Mermaid splits a label into one tspan per word, so the words are read as text.
        self.assertIn("fish &amp; chips", svg_text(svgs["amp"]))
        self.assertNotIn("&amp;amp;", svgs["amp"])

    @unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)
    def test_render_many_reports_every_fault_once_in_order(self):
        bad = (FIXTURES / "bad.mmd").read_text()
        diagrams = [("flow", (FIXTURES / "flow.mmd").read_text()), ("bad", bad), ("worse", bad)]
        out = io.StringIO()
        with mock.patch.dict(os.environ, self.env()), contextlib.redirect_stdout(out):
            with self.assertRaises(mermaid_svg.MermaidError) as caught:
                mermaid_svg.render_many(diagrams, BUNDLE, 60)
        self.assert_no_chrome_left()
        self.assertEqual(caught.exception.code, 1)
        # main prints the raised line last, so the run shows each fault once, in order.
        lines = out.getvalue().splitlines() + [str(caught.exception)]
        self.assertEqual(
            [line.split(" Parse error")[0] for line in lines],
            ["mermaid: FAIL bad", "mermaid: FAIL worse"],
            lines,
        )


if __name__ == "__main__":
    unittest.main()
