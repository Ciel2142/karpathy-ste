"""Tests for templates/page.html (spec section 7) and its guard script.

The template is also a demo of itself: verify.sh must pass it as it stands. Each
broken state is derived from the template at test time by one string edit, so a
change to the template reaches every case. Each edit asserts that its anchor occurs
exactly once in the template: a template change cannot turn a case into the good
case without notice. verify.sh must report the one status that the guard writes
for that edit. verify.sh loads a page twice, 1440x900 and 500x844, both with
#verify in the URL; there is no plain dump, so the cases for the fragment read the
DOM state through a probe that wraps setAttribute on <html>. Twelve Chrome runs of
verify.sh (two dumps each): the good template, the 700 px block, the 13 px rule,
the 15-unit SVG text, the throwing script, the probe, the probe with the hash
test defeated; then four more for the clip rule: the hide rule deleted, a clip
without the button, a clip with the button, a clip with a hidden button; then one
for Play all: two clips and a probe that drives a run with synthetic events. The
preset case stops in verify.sh before Chrome starts. The other cases are static.
Each run gets a private TMPDIR, so every Chrome process carries that path and the
cleanup can kill a stray one.
"""

import json
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
VERIFY = os.path.join(SKILL, "scripts", "verify.sh")
TEMPLATE = os.path.join(SKILL, "templates", "page.html")
SHEET = os.path.join(SKILL, "templates", "sheet.html")
RENDER_OK = ["render 1440x900: ok", "render 500x844: ok"]
OTHER_OK = ["citations: ok", "prose: ok"]

# Guard part 1 closes the first <script>; the throwing script goes right after it.
AFTER_GUARD_1 = "window.onerror = function () { window.explainJsErrors += 1; };\n</script>\n"
# The comment line that introduces guard part 2, with the <script> that holds it.
GUARD_2 = "<script>\n/* Guard, part 2 of 2"
HASH_TEST = '"#verify"'
# The last text of the flow SVG (one occurrence); the 15-unit text goes right after it.
FLOW_LAST_TEXT = '<text x="526" y="56" text-anchor="middle" class="label">verify.sh</text>\n'
LOAD_OPEN = 'window.addEventListener("load", function () {\n'
LAST_SCRIPT_END = "</script>\n</body>"
SCRIPT_BUDGET = 200
# The lead paragraph of the first section; the clip figure goes right after it (spec 4.2).
FIRST_LEAD = ('  <p>The page is one HTML file. It has no remote parts, thus it opens offline '
              'from one file.</p>\n')
# The Play all button, one line in <header>, and the rule that hides it on a page without clips.
PLAY_ALL = '<button id="play-all" type="button">Play all</button>\n'
HIDE_RULE = "body:not(:has(figure.clip)) #play-all { display: none; }"
# The clip figure of spec 4.2, as in tests/fixtures/verify-lesson.html. Its paths are relative,
# so check 1 passes; content="page" runs no media check, so the missing files do not matter.
CLIP_FIGURE = """<figure class="clip">
  <video controls preload="none" src="clips/intro/video.mp4" poster="clips/intro/poster.png"></video>
  <figcaption><span class="part"></span>The parser reads one tag at a time.
    <a href="clips/intro/index.html" data-ste="skip">transcript</a></figcaption>
</figure>
"""
# The lead paragraph of the code section; the second clip of the Play all case goes after it.
CODE_LEAD = ('  <p>Put each code block in a <code>figure.code</code> element. The caption gives '
             'the source as <code>name:line</code>, and the <code>pre</code> element contains '
             'the lines.</p>\n')

# Wraps setAttribute on <html>: when the guard writes data-verify, the probe appends
# the DOM state at that moment, then calls the original. The title is captured when
# the probe runs (parse time, before "load"), so a later write to document.title
# shows as TITLE:changed; comparing with the <title> element would not, because the
# document.title setter rewrites that element.
PROBE = """<script>
(function () {
  var doc = document.documentElement, original = doc.setAttribute;
  var initialTitle = document.title;
  doc.setAttribute = function (name, value) {
    if (name === "data-verify") {
      var details = document.getElementsByTagName("details"), open = true, i;
      for (i = 0; i < details.length; i++) if (!details[i].open) open = false;
      var steps = document.querySelectorAll(".step"), stacked = true;
      for (i = 0; i < steps.length; i++) if (steps[i].hasAttribute("hidden")) stacked = false;
      var same = document.title === initialTitle;
      value += ";PROBE:" + (open ? "open" : "closed") + ":" + (stacked ? "stacked" : "single") +
        ";TITLE:" + (same ? "same" : "changed");
    }
    return original.call(this, name, value);
  };
})();
</script>
"""

# Play all, two clips: one row per step that PLAY_PROBE drives, in order. A row holds the
# step; then clip 1 and clip 2, each "+" (it plays) or "-" (it does not), the text of its
# .part, and "@t" when its currentTime is t, not 0; then the id of the section that the
# step scrolled into view, or "". The probe's play() fires "play" at once and its pause()
# delivers "pause" after the step, so a run that pauses the clip it plays ends at once.
PLAY_ALL_TRACE = [
    ("click", "+Part 1 of 2", "-", "structure"),    # a run starts from clip 1
    ("end 1", "-", "+Part 2 of 2", "code"),         # "pause" (ended true), "ended": next clip
    ("end 2", "-", "-", ""),                        # after the last clip the run ends
    ("click", "+Part 1 of 2", "-", "structure"),
    ("reject 1", "-", "+Part 2 of 2", "code"),      # a rejected play() skips to the next
    ("error 2", "-", "-", ""),                      # an error mid-clip skips; no clip is next
    ("click", "+Part 1 of 2", "-", "structure"),
    ("pause 1", "-", "-", ""),                      # the reader's pause ends the run
    ("click", "+Part 1 of 2", "-", "structure"),
    ("play 2", "-", "+", ""),                       # play on another clip ends the run
    ("reject 1", "-", "+", ""),                     # a late rejection after the run: no effect
    ("click", "+Part 1 of 2", "-", "structure"),    # the run pauses the reader's clip 2
    ("end 1", "-", "+Part 2 of 2", "code"),
    ("click", "+Part 1 of 2", "-", "structure"),    # a click restarts the run from clip 1
    ("seek 1", "+Part 1 of 2@7", "-", ""),
    ("click", "+Part 1 of 2", "-", "structure"),    # a restart on clip 1: rewind, no pause
    ("missing 1", "-", "+Part 2 of 2", "code"),     # error, then the rejection: one skip
]

# Stubs play(), pause() and scrollIntoView() so that no media loads, then, when the guard
# writes data-verify, runs the steps (STEPS: the step column of PLAY_ALL_TRACE) and
# appends ";TRACE:" and one entry per step, read from the DOM and from the stubs, never
# from the Play all code. play() on a clip that does not play fires "play" at once (a
# browser fires it later) and returns an object whose catch() keeps the handler, so a
# step can reject the promise. pause() on a playing clip queues "pause", delivered after
# the step, as a browser fires it later. A script error in a step appends ";THROWN".
PLAY_PROBE = """<script>
(function () {
  var doc = document.documentElement, original = doc.setAttribute;
  var queued = [], scrolled = "";
  function fire(el, type) { el.dispatchEvent(new Event(type)); }
  HTMLMediaElement.prototype.play = function () {
    var el = this;
    if (!el.probePlays) { el.probePlays = true; fire(el, "play"); }
    return { catch: function (handler) { el.probeReject = handler; } };
  };
  HTMLMediaElement.prototype.pause = function () {
    if (this.probePlays) { this.probePlays = false; queued.push(this); }
  };
  Element.prototype.scrollIntoView = function () { scrolled = this.id; };
  doc.setAttribute = function (name, value) {
    if (name === "data-verify") {
      var clips = document.querySelectorAll("figure.clip video");
      var button = document.getElementById("play-all"), errors = window.explainJsErrors;
      var steps = STEPS, trace = [], s, c;
      function reject(i) {   /* the promise of the last play() rejects */
        var handler = clips[i].probeReject;
        clips[i].probePlays = false; clips[i].probeReject = null;
        if (handler) handler(new Error("rejected"));
      }
      var actions = {
        click: function () { button.click(); },
        end: function (i) {   /* a browser fires "pause" (ended true), then "ended" */
          Object.defineProperty(clips[i], "ended", { value: true, configurable: true });
          clips[i].probePlays = false;
          fire(clips[i], "pause"); fire(clips[i], "ended");
          delete clips[i].ended;
        },
        reject: reject,
        error: function (i) {   /* mid-clip: play() resolved before, thus only "error" */
          clips[i].probePlays = false; clips[i].probeReject = null; fire(clips[i], "error");
        },
        missing: function (i) { fire(clips[i], "error"); reject(i); },   /* no file */
        pause: function (i) { clips[i].pause(); },   /* the reader pauses */
        play: function (i) { clips[i].play(); },     /* the reader plays */
        seek: function (i) { clips[i].currentTime = 7; }   /* the clip is at 7 s */
      };
      for (s = 0; s < steps.length; s++) {
        var word = steps[s].split(" "), row = [];
        scrolled = "";
        actions[word[0]](word[1] - 1);
        while (queued.length) fire(queued.shift(), "pause");
        for (c = 0; c < clips.length; c++) {
          var time = clips[c].currentTime;
          row.push((clips[c].probePlays ? "+" : "-") +
            clips[c].closest("figure.clip").querySelector(".part").textContent +
            (time ? "@" + time : ""));
        }
        trace.push(steps[s] + ":" + row.join("|") + ":" + scrolled);
      }
      value += ";TRACE:" + trace.join(",");
      if (window.explainJsErrors !== errors) value += ";THROWN";
    }
    return original.call(this, name, value);
  };
})();
</script>
"""


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def root_block(html):
    match = re.search(r":root \{[^}]*\}", html)
    assert match, "no :root block"
    return match.group(0)


def html_start_tag(html):
    match = re.search(r"<html\b[^>]*>", html)
    assert match, "no <html start tag"
    return match.group(0)


def script_lines(html):
    """Lines between <script> and </script> over all blocks (the tag lines excluded)."""
    total = 0
    for body in re.findall(r"<script>(.*?)</script>", html, re.S):
        total += max(len(body.split("\n")) - 2, 0)
    return total


def script_blocks(html):
    """The body of each <script> block, in document order (the regex of script_lines)."""
    return re.findall(r"<script>(.*?)</script>", html, re.S)


class PageGuardTest(unittest.TestCase):

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        root = os.path.realpath(self._dir.name)
        self.tmp = os.path.join(root, "tmp")
        self.work = os.path.join(root, "work")
        os.mkdir(self.tmp)
        os.mkdir(self.work)
        self.template = read(TEMPLATE)
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(
            lambda: subprocess.run(["pkill", "-KILL", "-f", self.tmp], capture_output=True)
        )

    def edit(self, html, anchor, replacement):
        self.assertEqual(html.count(anchor), 1, "anchor %r must occur once" % anchor)
        return html.replace(anchor, replacement)

    def verify(self, path):
        env = dict(os.environ, TMPDIR=self.tmp + "/")
        env.pop("VERIFY_TIMEOUT", None)
        return subprocess.run(
            [VERIFY, path], capture_output=True, text=True, env=env, timeout=240,
        )

    def run_derived(self, html):
        path = os.path.join(self.work, "index.html")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(html)
        return self.verify(path)

    def assert_renders(self, html, renders, code):
        """verify.sh prints self-contained, the two render lines, citations, prose."""
        proc = self.run_derived(html)
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok"] + renders + OTHER_OK, proc.stdout)

    def assert_both_fail(self, html, status):
        self.assert_renders(html, [
            'render 1440x900: FAIL data-verify="%s"' % status,
            'render 500x844: FAIL data-verify="%s"' % status,
        ], 1)

    def with_probe(self, html):
        return self.edit(html, GUARD_2, PROBE + GUARD_2)

    def test_template_passes_all_five_checks(self):
        proc = self.verify(TEMPLATE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["self-contained: ok"] + RENDER_OK + OTHER_OK)

    def with_clip(self, html):
        return self.edit(html, FIRST_LEAD, FIRST_LEAD + CLIP_FIGURE)

    def test_template_hides_play_all_without_clips(self):
        # The pass itself is test_template_passes_all_five_checks; this pins its two parts.
        self.assertEqual(self.template.count(HIDE_RULE), 1)
        self.assertEqual(self.template.count('id="play-all"'), 1)
        self.assertNotIn('<figure class="clip"', self.template)   # no demo clip (spec 4.4)

    def test_deleting_the_hide_rule_reports_playall(self):
        # No clip, and the button shows: the guard reports PLAYALL.
        html = self.edit(self.template, HIDE_RULE + "\n", "")
        self.assert_both_fail(html, "PLAYALL")

    def test_clip_without_button_reports_playall(self):
        # A clip, and the author deleted the button: the control is gone, the guard says so.
        html = self.edit(self.with_clip(self.template), PLAY_ALL, "")
        self.assert_both_fail(html, "PLAYALL")

    def test_clip_with_hidden_button_reports_playall(self):
        # A clip, and the button is hidden: same status as a button that is gone.
        html = self.edit(self.with_clip(self.template), PLAY_ALL,
                         PLAY_ALL.replace('type="button"', 'type="button" style="display:none"'))
        self.assert_both_fail(html, "PLAYALL")

    def test_clip_with_button_passes(self):
        # The two ok lines also mean: the clip text is 14 px or more, and the breakout
        # width adds no horizontal overflow at 500 px.
        self.assert_renders(self.with_clip(self.template), RENDER_OK, 0)

    def test_play_all_block_is_in_block_2_within_budget(self):
        blocks = script_blocks(self.template)
        self.assertEqual(len(blocks), 3)
        guard_1, player, guard_2 = blocks
        self.assertIn("/* Play all */", player)
        self.assertIn("function explainPlayAll(", player)
        self.assertTrue(player.rstrip().endswith("\nexplainPlayAll();"), player[-60:])
        # The block alone, counted by the rule of script_lines.
        self.assertLessEqual(script_lines("<script>%s</script>" % player), SCRIPT_BUDGET)
        self.assertNotIn("explainPlayAll", guard_1 + guard_2)
        play_all = player[player.index("/* Play all */"):]
        for timer in ("setTimeout", "setInterval", "requestAnimationFrame"):
            self.assertNotIn(timer, play_all)

    def test_play_all_handles_a_rejected_play_promise(self):
        # window.onerror does not see a rejected promise: without catch() a run stalls.
        player = script_blocks(self.template)[1]
        self.assertRegex(player, r"\.play\(\)\s*\.catch\(")
        self.assertNotIn("autoplay", self.template.lower())

    def test_play_all_runs_clips_in_order(self):
        # Two clips in two sections. The probe drives the run after the guard measured;
        # the "OK" prefix means no guard status, thus no JSERROR with two clips present.
        html = self.edit(self.with_clip(self.template), CODE_LEAD, CODE_LEAD + CLIP_FIGURE)
        probe = self.edit(PLAY_PROBE, "STEPS", json.dumps([row[0] for row in PLAY_ALL_TRACE]))
        html = self.edit(html, GUARD_2, probe + GUARD_2)
        trace = ",".join("%s:%s|%s:%s" % row for row in PLAY_ALL_TRACE)
        self.assert_both_fail(html, "OK;TRACE:" + trace)

    def test_700px_block_reports_hscroll_at_500_only(self):
        html = self.edit(self.template, "<main>\n",
                         '<main>\n<div style="width:700px;height:1px"></div>\n')
        self.assert_renders(html, [
            "render 1440x900: ok",
            'render 500x844: FAIL data-verify="HSCROLL"',
        ], 1)

    def test_13px_rule_reports_smalltext_13(self):
        html = self.edit(self.template, "</style>",
                         "p.lead { font-size: 13px; }\n</style>")
        self.assert_both_fail(html, "SMALLTEXT:13")

    def test_15unit_svg_text_reports_smalltext_at_500_only(self):
        # SVG text is in viewBox units; the guard scales it by rendered width / viewBox width.
        # 1440: the SVG renders at its 600 px cap, so 15 units = 15 px >= 14: ok.
        # 500: content width = 500 - 2 * 16 (body padding) = 468 px,
        # so 15 * 468 / 600 = 11.7 px (the 18-unit text: 14.04 px, still ok).
        html = self.edit(self.template, FLOW_LAST_TEXT,
                         FLOW_LAST_TEXT + '<text x="300" y="78" style="font-size:15px">tiny</text>\n')
        self.assert_renders(html, [
            "render 1440x900: ok",
            'render 500x844: FAIL data-verify="SMALLTEXT:11.7"',
        ], 1)

    def test_throwing_inline_script_reports_jserror(self):
        html = self.edit(self.template, AFTER_GUARD_1,
                         AFTER_GUARD_1 + '<script>throw new Error("boom");</script>\n')
        self.assert_both_fail(html, "JSERROR")

    def test_verify_fragment_opens_details_and_stacks_steps(self):
        # The runtime title half of case 7: TITLE:same here, TITLE:changed in the next case.
        html = self.with_probe(self.template)
        self.assert_both_fail(html, "OK;PROBE:open:stacked;TITLE:same")

    def test_without_verify_fragment_details_stay_closed_and_one_step_shows(self):
        # Defeating the hash test makes the guard take the normal-view branch. The same
        # run carries the title broken state (no extra Chrome run): a guard that writes
        # document.title must show as TITLE:changed, which proves the probe can fail.
        html = self.edit(self.template, HASH_TEST, '"#never"')
        html = self.edit(html, LOAD_OPEN, LOAD_OPEN + '  document.title = "x";\n')
        html = self.with_probe(html)
        self.assert_both_fail(html, "OK;PROBE:closed:single;TITLE:changed")

    def test_data_verify_absent_in_source(self):
        # The static check reads the <html start tag only, the one place where a preset
        # status lives; the script and the demo prose may name data-verify freely.
        self.assertNotIn("data-verify=", html_start_tag(self.template))
        html = self.edit(self.template, '<html lang="en">',
                         '<html lang="en" data-verify="OK">')
        self.assertIn("data-verify=", html_start_tag(html))
        # verify.sh bails on the preset before it starts Chrome.
        self.assert_renders(html, [
            "render 1440x900: FAIL data-verify preset in source",
            "render 500x844: FAIL data-verify preset in source",
        ], 1)

    def test_title_is_never_touched(self):
        self.assertNotIn("document.title", self.template)
        broken = self.edit(self.template, LOAD_OPEN,
                           LOAD_OPEN + '  document.title = "x";\n')
        self.assertIn("document.title", broken)

    def test_palette_block_identical_to_sheet(self):
        page_block = root_block(self.template)
        self.assertTrue(page_block.startswith(":root {\n  --ink:"), page_block)
        self.assertEqual(page_block, root_block(read(SHEET)))
        broken = self.edit(self.template, "--blue: #1d5fc2;", "--blue: #1d5fc3;")
        self.assertNotEqual(root_block(broken), root_block(read(SHEET)))

    def test_script_budget_at_most_200_lines(self):
        self.assertLessEqual(script_lines(self.template), SCRIPT_BUDGET)
        broken = self.edit(self.template, LAST_SCRIPT_END,
                           "\n" * SCRIPT_BUDGET + LAST_SCRIPT_END)
        self.assertGreater(script_lines(broken), SCRIPT_BUDGET)


if __name__ == "__main__":
    unittest.main()
