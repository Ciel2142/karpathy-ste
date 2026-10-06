"""Tests for templates/page.html (spec section 7) and its guard script.

The template is also a demo of itself: verify.sh must pass it as it stands. Each
broken state is derived from the template at test time by one string edit, so a
change to the template reaches every case. Each edit asserts that its anchor occurs
exactly once in the template: a template change cannot turn a case into the good
case without notice. verify.sh must report the one status that the guard writes
for that edit. verify.sh loads a page twice, 1440x900 and 500x844, both with
#verify in the URL; there is no plain dump, so the cases for the fragment read the
DOM state through a probe that wraps setAttribute on <html>. Twenty-four Chrome runs of
verify.sh (two dumps each): the good template, the 700 px block, the 13 px rule,
the 15-unit SVG text, the throwing script, the probe, the probe with the hash
test defeated; then four more for the clip rule: the hide rule deleted, a clip
without the button, a clip with the button, a clip with a hidden button; then one
for Play all: two clips and a probe that drives a run with synthetic events; then
seven for the Sources switch (spec 3, 4): a 12 px snippet, a 700 px span and a 12 px
snippet in a fold, each in a cite that the reading view hides; the switch deleted;
the switch moved from the nav into the header; a page with no cite and no switch; the
probe with the switch on at parse time; then
five for the answer box (spec 2, 4): the box deleted, its <p> blank, its <p> deleted,
the box outside <header>, and the box and the switch both deleted. The preset case
stops in verify.sh before Chrome starts. The other cases are static. The glossary case
(spec 2 rule 7) is static too: the run of the good template lints the prose of its dt and dd.
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
VIDEO = os.path.join(SKILL, "templates", "video.html")
THEME = os.path.join(SKILL, "video", "src", "theme.ts")
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
# The Sources switch: the last child of nav#toc (spec 3). The cites hide behind it.
SWITCH = '<label class="sources"><input type="checkbox" id="show-sources"> Sources</label>'
# The answer box of the header (spec 2 rule 2): one <p> that starts with the label, then its cites.
ANSWER = """  <div class="answer">
    <p><strong>Short answer.</strong> Copy the template file, and write your answer in this box. Give each part of the answer one section, with a question as its title. Write all prose in STE-80. Then run <code>verify.sh</code> on the page.</p>
    <div class="cites">
      <cite data-path="https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf" data-line="1" data-snippet="Simplified Technical English">ASD-STE100 <code>Simplified Technical English</code></cite>
    </div>
  </div>
"""
# The <p> of the answer box, cut from ANSWER.
ANSWER_P = ANSWER[ANSWER.index("<p>"):ANSWER.index("</p>") + len("</p>")]
# The last line of the first details.walk; a cite block for the fold case goes right after it.
FOLD_TEXT = "measures all the text.</p>\n"
# The cite block of the structure section: the 700 px span goes inside it. The answer box holds
# a cite block too, and comes first, so the anchor starts at the list item that holds this one.
CITES_OPEN = '<li>Write all prose in STE-80.\n      <div class="cites">\n'
# A parse-time script: a reader's browser restored the switch as on, before "load".
SWITCH_ON = '<script>document.getElementById("show-sources").checked = true;</script>\n'
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
      var sources = document.getElementById("show-sources");
      value += ";PROBE:" + (open ? "open" : "closed") + ":" + (stacked ? "stacked" : "single") +
        ";TITLE:" + (same ? "same" : "changed") +
        ";SOURCES:" + (sources && sources.checked ? "on" : "off");
    }
    return original.call(this, name, value);
  };
})();
</script>
"""

# Play all, two clips: one row per step that PLAY_PROBE drives, in order. A row holds the
# step; then clip 1 and clip 2, each "+" (it plays) or "-" (it does not), the text of its
# .part, and "@t" when its currentTime is t, not 0; then the id of the section that the
# step scrolled into view, or "".
PLAY_ALL_TRACE = [
    ("click", "+Part 1 of 2", "-", "structure"),    # a run starts from clip 1
    ("end 1", "-", "+Part 2 of 2", "code"),         # "pause" (ended true), "ended": next clip
    ("end 2", "-", "-", ""),                        # after the last clip the run ends
    ("click", "+Part 1 of 2", "-", "structure"),
    ("reject 1", "-", "+Part 2 of 2", "code"),      # a rejected play() skips to the next
    ("error 2", "-", "-", ""),                      # an error mid-clip skips; no clip is next
    ("click", "+Part 1 of 2", "-", "structure"),
    ("block 1", "-", "-", ""),                      # a blocked play() ends the run: no skip
    ("click", "+Part 1 of 2", "-", "structure"),
    ("pause 1", "-", "-", ""),                      # the reader's pause ends the run
    ("click", "+Part 1 of 2", "-", "structure"),
    ("play 2", "-", "+", ""),                       # play on another clip ends the run
    ("click", "+Part 1 of 2", "-", "structure"),    # the run pauses the reader's clip 2
    ("end 1", "-", "+Part 2 of 2", "code"),
    ("click", "+Part 1 of 2", "-", "structure"),    # a click restarts the run from clip 1
    ("late 2", "+Part 1 of 2", "-", ""),            # clip 2 ran out as the reader clicked
    ("seek 1", "+Part 1 of 2@7", "-", ""),
    ("click", "+Part 1 of 2", "-", "structure"),    # a restart on clip 1: rewind, no pause
    ("missing 1", "-", "+Part 2 of 2", "code"),     # error, then the rejection: one skip
    ("click", "-", "+Part 2 of 2", "code"),         # clip 1 is now broken: play() rejects at
    ("click", "-", "+Part 2 of 2", "code"),         # once; stale events of clip 2: no effect
]

# Stubs play(), pause(), paused and scrollIntoView() so that no media loads, then, when
# the guard writes data-verify, runs the steps (STEPS: the step column of PLAY_ALL_TRACE)
# and appends ";TRACE:" and one entry per step, read from the DOM and from the stubs,
# never from the Play all code. The stubs model a browser. play() on a clip that does
# not play fires "play" at once (a browser fires it later) and returns an object whose
# catch() keeps the handler, so a step can reject the promise: "reject" with a plain error,
# "block" with a NotAllowedError (the browser blocks a play() that no click started;
# nothing played, so no "pause" follows). On a broken clip (after "missing") catch()
# calls the handler at once and nothing plays. pause() on a playing clip queues "pause",
# then the stale rejection of its pending play(); the probe delivers them after the step,
# as a browser does later. paused is true when the clip does not play. A script error in
# a step appends ";THROWN".
PLAY_PROBE = """<script>
(function () {
  var doc = document.documentElement, original = doc.setAttribute;
  var queued = [], scrolled = "", media = HTMLMediaElement.prototype;
  function fire(el, type) { el.dispatchEvent(new Event(type)); }
  media.play = function () {
    var el = this;
    el.probeReject = null;   /* a new promise */
    if (el.probeBroken) {   /* a browser rejects it at once: error code 4 */
      return { catch: function (handler) { handler(new Error("NotSupportedError")); } };
    }
    if (!el.probePlays) { el.probePlays = true; fire(el, "play"); }
    return { catch: function (handler) { el.probeReject = handler; } };
  };
  media.pause = function () {
    var el = this, handler = el.probeReject;
    if (!el.probePlays) return;
    el.probePlays = false; el.probeReject = null;
    queued.push(function () { fire(el, "pause"); if (handler) handler(new Error("AbortError")); });
  };
  Object.defineProperty(media, "paused", { get: function () { return !this.probePlays; } });
  Element.prototype.scrollIntoView = function () { scrolled = this.id; };
  doc.setAttribute = function (name, value) {
    if (name === "data-verify") {
      var clips = document.querySelectorAll("figure.clip video");
      var button = document.getElementById("play-all"), errors = window.explainJsErrors;
      var steps = STEPS, trace = [], s, c;
      function reject(i, error) {   /* the promise of the last play() rejects */
        var handler = clips[i].probeReject;
        clips[i].probePlays = false; clips[i].probeReject = null;
        if (handler) handler(error || new Error("rejected"));
      }
      var actions = {
        click: function () { button.click(); },
        end: function (i) {   /* a browser fires "pause" (ended true), then "ended" */
          Object.defineProperty(clips[i], "ended", { value: true, configurable: true });
          clips[i].probePlays = false;
          fire(clips[i], "pause"); fire(clips[i], "ended");
          delete clips[i].ended;
        },
        reject: function (i) { reject(i); },
        block: function (i) { reject(i, new DOMException("blocked", "NotAllowedError")); },
        late: function (i) { fire(clips[i], "ended"); },   /* an "ended" queued earlier */
        error: function (i) {   /* mid-clip: play() resolved before, thus only "error" */
          clips[i].probePlays = false; clips[i].probeReject = null; fire(clips[i], "error");
        },
        missing: function (i) {   /* no file: "error", the rejection; then broken */
          fire(clips[i], "error"); reject(i); clips[i].probeBroken = true;
        },
        pause: function (i) { clips[i].pause(); },   /* the reader pauses */
        play: function (i) { clips[i].play(); },     /* the reader plays */
        seek: function (i) { clips[i].currentTime = 7; }   /* the clip is at 7 s */
      };
      for (s = 0; s < steps.length; s++) {
        var word = steps[s].split(" "), row = [];
        scrolled = "";
        actions[word[0]](word[1] - 1);
        while (queued.length) queued.shift()();
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


def style_rules(html):
    """(selector list, declarations) of each rule in <style>, comments cut. A rule inside an
    @media block comes out with the block header as its selector."""
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", css)]


def font_size_floor_names(html):
    """The last word of each selector in a font-size rule of 14 px or more."""
    names = set()
    for selectors, body in style_rules(html):
        match = re.search(r"font-size:\s*(\d+(?:\.\d+)?)px", body)
        if match and float(match.group(1)) >= 14:
            names.update(sel.split()[-1] for sel in selectors.split(",") if sel.strip())
    return names


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

    def cite_block(self):
        """The cite block of the structure section, as it is written there (its comments cut).
        The answer box holds one too, and comes first in the file, so the search starts below it."""
        markup = re.sub(r"<!--.*?-->", "", self.template, flags=re.S)
        section = re.search(r'<section id="structure">.*?</section>', markup, re.S).group(0)
        return re.search(r'<div class="cites">.*?</div>\n', section, re.S).group(0)

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
                         ".answer p { font-size: 13px; }\n</style>")
        self.assert_both_fail(html, "SMALLTEXT:13")

    def test_hidden_cite_with_12px_snippet_reports_smalltext_12(self):
        # red: the guard measures the reading view only. The cites are hidden there, so the
        # 12 px snippet escapes (no layout box); the second measure, with Sources on, finds it.
        html = self.edit(self.template, "</style>", ".cites code { font-size: 12px; }\n</style>")
        self.assert_both_fail(html, "SMALLTEXT:12")

    def test_hidden_cite_700px_wide_reports_hscroll_at_500_only(self):
        # red: the guard measures the reading view only. With Sources on, the span makes the
        # page wider than 500 px; at 1440 px it fits.
        html = self.edit(self.template, CITES_OPEN, CITES_OPEN +
                         '<span style="display:inline-block;width:700px;height:1px"></span>\n')
        self.assert_renders(html, [
            "render 1440x900: ok",
            'render 500x844: FAIL data-verify="HSCROLL"',
        ], 1)

    def test_hidden_cite_in_a_fold_is_measured(self):
        # red: the second measure runs before the guard opens the details, or skips closed ones:
        # a cite block in a fold stays hidden, and its 12 px snippet escapes.
        html = self.edit(self.template, FOLD_TEXT, FOLD_TEXT + self.cite_block())
        html = self.edit(html, "</style>", "details.walk .cites code { font-size: 12px; }\n</style>")
        self.assert_both_fail(html, "SMALLTEXT:12")

    def test_switch_removed_reports_nosources(self):
        # red: the guard does not look for the switch: the cites hide for good, and no code says so.
        html = self.edit(self.template, "  " + SWITCH + "\n", "")
        self.assert_both_fail(html, "NOSOURCES")

    def test_switch_outside_the_nav_reports_nosources(self):
        # red: the guard finds the switch by id anywhere. A switch in <header> scrolls away with the
        # header, so the reader has no Sources switch in the sticky nav (spec 3).
        html = self.edit(self.template, "  " + SWITCH + "\n", "")
        html = self.edit(html, "</header>\n", "  " + SWITCH + "\n</header>\n")
        self.assert_both_fail(html, "NOSOURCES")

    def test_page_without_cites_needs_no_switch(self):
        # red: NOSOURCES fires on a page with no cite block (a topic from model knowledge).
        html, removed = re.subn(r'\s*<div class="cites">.*?</div>', "", self.template, flags=re.S)
        self.assertGreaterEqual(removed, 1)
        html = self.edit(html, "  " + SWITCH + "\n", "")
        self.assert_renders(html, RENDER_OK, 0)

    def test_guard_restores_a_checked_switch(self):
        # red: the guard sets the switch back to off. A reader's browser restores it as on at
        # "load", so the probe must see it on when the guard writes data-verify.
        html = self.edit(self.with_probe(self.template), PROBE, SWITCH_ON + PROBE)
        self.assert_both_fail(html, "OK;PROBE:open:stacked;TITLE:same;SOURCES:on")

    def test_answer_box_removed_reports_noanswer(self):
        # red: the guard does not look for the answer box: a page with no answer passes.
        html = self.edit(self.template, ANSWER, "")
        self.assert_both_fail(html, "NOANSWER")

    def test_blank_answer_box_reports_noanswer(self):
        # red: the guard checks that the box exists, not that it holds text: an empty box passes.
        html = self.edit(self.template, ANSWER, ANSWER.replace(ANSWER_P, "<p> \n </p>"))
        self.assert_both_fail(html, "NOANSWER")

    def test_answer_box_with_only_cites_reports_noanswer(self):
        # red: the guard reads all the text of the box, its cites too: a box of cites passes.
        html = self.edit(self.template, ANSWER, ANSWER.replace(ANSWER_P + "\n", ""))
        self.assert_both_fail(html, "NOANSWER")

    def test_answer_box_outside_header_reports_noanswer(self):
        # red: the guard looks for .answer in the whole page, not in <header>: a box that
        # sits in the first section passes.
        html = self.edit(self.template, ANSWER, "")
        end = html.index("</h2>\n", html.index("<main>")) + len("</h2>\n")
        html = html[:end] + ANSWER + html[end:]
        self.assert_both_fail(html, "NOANSWER")

    def test_missing_box_and_switch_report_in_order(self):
        # red: NOANSWER is pushed after NOSOURCES, or one code hides the other.
        html = self.edit(self.template, ANSWER, "")
        html = self.edit(html, "  " + SWITCH + "\n", "")
        self.assert_both_fail(html, "NOANSWER;NOSOURCES")

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
        self.assert_both_fail(html, "OK;PROBE:open:stacked;TITLE:same;SOURCES:off")

    def test_without_verify_fragment_details_stay_closed_and_one_step_shows(self):
        # Defeating the hash test makes the guard take the normal-view branch. The same
        # run carries the title broken state (no extra Chrome run): a guard that writes
        # document.title must show as TITLE:changed, which proves the probe can fail.
        html = self.edit(self.template, HASH_TEST, '"#never"')
        html = self.edit(html, LOAD_OPEN, LOAD_OPEN + '  document.title = "x";\n')
        html = self.with_probe(html)
        self.assert_both_fail(html, "OK;PROBE:closed:single;TITLE:changed;SOURCES:off")

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
        self.assertTrue(page_block.startswith(":root {\n  --bg:"), page_block)
        self.assertEqual(page_block, root_block(read(SHEET)))
        broken = self.edit(self.template, "--blue: #1d5fc2;", "--blue: #1d5fc3;")
        self.assertNotEqual(root_block(broken), root_block(read(SHEET)))

    def test_palette_is_the_warm_paper_in_all_four_copies(self):
        """Red: one of page.html, sheet.html, video.html or video/src/theme.ts holds another value
        for a colour token, or lacks the accent or the ground."""
        expected = {"bg": "#faf9f5", "fill": "#f0eee6", "ink": "#1f1d1a", "muted": "#6b6a64",
                    "line": "#d4d0c6", "accent": "#c2613f", "blue": "#1d5fc2", "red": "#c42f2a"}
        for path in (TEMPLATE, SHEET, VIDEO):
            css = dict(re.findall(r"--([a-z]+): (#[0-9a-f]{6});", root_block(read(path))))
            self.assertEqual(css, expected, path)
        ts = dict(re.findall(r'^  ([a-z]+): "(#[0-9a-f]{6})",', read(THEME), re.M))
        self.assertEqual(ts, expected, THEME)
        for path in (TEMPLATE, SHEET, VIDEO):
            self.assertNotIn("#fff", read(path), path)

    def test_cites_collect_in_a_block_under_the_prose(self):
        """Red: a template lacks the .cites rules, shows a cite inline in the prose, or quotes the
        snippet instead of setting it in <code>."""
        for rule in (".cites {", ".cites cite {", ".cites cite + cite {", ".cites code {"):
            self.assertIn(rule, self.template, rule)
        markup = re.sub(r"<!--.*?-->", "", self.template, flags=re.S)
        cites = re.findall(r"<cite\b[^>]*>(.*?)</cite>", markup, re.S)
        self.assertTrue(cites)
        for text in cites:
            self.assertRegex(text, r"^[^<\"]+ <code>[^<]+</code>$")
        blocks = re.findall(r'<div class="cites">(.*?)</div>', markup, re.S)
        self.assertEqual(sum(block.count("<cite") for block in blocks), len(cites))

    def test_switch_is_in_the_nav_and_cites_hide_by_default(self):
        """Red: the switch is missing, sits before a link, or is not in nav#toc; or the style lacks
        the hide rule, the :has rule, or the print rule that shows the cites."""
        self.assertEqual(self.template.count(SWITCH), 1)
        nav = re.search(r'<nav id="toc">(.*?)</nav>', self.template, re.S).group(1)
        self.assertIn(SWITCH, nav)
        self.assertGreater(nav.index(SWITCH), nav.rindex("</a>"))
        self.assertEqual(nav[nav.index(SWITCH) + len(SWITCH):].strip(), "")   # the last child
        rules = dict(style_rules(self.template))
        self.assertIn("display: none", rules[".cites"])
        self.assertEqual(rules["body:has(#show-sources:checked) .cites"].strip(), "display: block;")
        self.assertEqual(rules["@media print"].replace("\n", " ").split("{")[0].strip(), ".cites")
        self.assertIn("display: block", rules["@media print"])

    def test_label_and_input_have_explicit_font_sizes(self):
        """Red: label or input is in no font-size rule of 14 px or more; Chrome would size an
        input at 13.33 px, and a label in the nav would only inherit."""
        names = font_size_floor_names(self.template)
        self.assertIn("label", names)
        self.assertIn("input", names)

    def test_status_table_lists_nosources(self):
        """Red: the status table of the template has no row for NOSOURCES."""
        self.assertRegex(self.template, r"<tr><td><code>NOSOURCES</code></td><td>[^<]+</td></tr>")

    def test_header_asks_and_answers(self):
        """Red: the <h1> is not a question, or the <title> differs from it; the template still has
        p.lead; the answer box is missing, twice, or outside <header>; its <p> lacks the label, is
        not followed by its cites, has fewer than two sentences or more than four, or has more
        than 70 words."""
        markup = re.sub(r"<!--.*?-->", "", self.template, flags=re.S)   # a comment names <h1>
        header = re.search(r"<header>(.*?)</header>", markup, re.S).group(1)
        h1 = re.search(r"<h1>(.*?)</h1>", header, re.S).group(1)
        self.assertTrue(h1.endswith("?"), h1)
        self.assertEqual(re.search(r"<title>(.*?)</title>", markup, re.S).group(1), h1)
        self.assertNotIn('class="lead"', markup)
        self.assertEqual(self.template.count(ANSWER), 1)
        self.assertIn(ANSWER, header)
        self.assertTrue(ANSWER_P.startswith("<p><strong>Short answer.</strong>"), ANSWER_P)
        self.assertRegex(ANSWER, r'</p>\s*<div class="cites">')
        said = re.sub(r"<[^>]+>", "", ANSWER_P.replace("<strong>Short answer.</strong>", ""))
        self.assertIn(len(re.findall(r"[.?!](?:\s|$)", said.strip())), (2, 3, 4), said)
        self.assertLessEqual(len(re.sub(r"<[^>]+>", "", ANSWER_P).split()), 70)

    def test_status_table_lists_noanswer(self):
        """Red: the status table of the template has no row for NOANSWER, or the row comes after the
        NOSOURCES row."""
        row = r"<tr><td><code>%s</code></td><td>[^<]+</td></tr>"
        found = re.search(row % "NOANSWER", self.template)
        self.assertTrue(found)
        self.assertLess(found.start(), re.search(row % "NOSOURCES", self.template).start())

    def test_template_has_a_glossary_section(self):
        """Red: section#terms is missing, twice, or after section#provenance-facet; it has no <h2>
        question, no dl.terms, or fewer than two dt/dd pairs; a dd holds a cite block; no comment
        above the dl names div.cites; the nav link to #terms is missing or after the provenance
        link; the style has no .terms grid of max-content 1fr, no explicit 16 px bold .terms dt,
        or no max-width media rule that sets one column."""
        self.assertEqual(self.template.count('<section id="terms">'), 1)
        # The comment above the dl gives the markup of a dd that has cites; read it before the cut.
        comment = re.search(r'<section id="terms">(?:(?!</section>).)*?<!--((?:(?!-->).)*)-->\s*<dl class="terms">',
                            self.template, re.S)
        self.assertTrue(comment, "a comment must come right above the dl")
        self.assertIn("div.cites", comment.group(1))
        markup = re.sub(r"<!--.*?-->", "", self.template, flags=re.S)
        section = re.search(r'<section id="terms">(.*?)</section>', markup, re.S).group(1)
        self.assertLess(markup.index('<section id="terms">'),
                        markup.index('<section id="provenance-facet">'))
        self.assertRegex(section, r"<h2>What do the terms mean\?</h2>")
        glossary = re.search(r'<dl class="terms">(.*?)</dl>', section, re.S).group(1)
        pairs = re.findall(r"<dt>[^<]+</dt>\s*<dd>.*?</dd>", glossary, re.S)
        self.assertGreaterEqual(len(pairs), 2)
        self.assertEqual(glossary.count("<dt>"), len(pairs))
        self.assertNotIn('class="cites"', section)   # the template holds no file cite
        nav = re.search(r'<nav id="toc">(.*?)</nav>', self.template, re.S).group(1)
        self.assertIn('<a href="#terms">Terms</a>', nav)
        self.assertLess(nav.index('<a href="#terms">'), nav.index('<a href="#provenance-facet">'))
        rules = dict(style_rules(self.template))
        self.assertIn("display: grid", rules[".terms"])
        self.assertIn("grid-template-columns: max-content 1fr", rules[".terms"])
        dt = rules[".terms dt"]
        self.assertRegex(dt, r"font-size:\s*16px")
        self.assertRegex(dt, r"font-weight:\s*(700|bold)")
        narrow = [body for sel, body in rules.items() if re.fullmatch(r"@media \(max-width: \d+px\)", sel)]
        self.assertTrue(any(".terms" in body and "grid-template-columns: 1fr" in body
                            for body in narrow), narrow)

    def test_script_budget_at_most_200_lines(self):
        self.assertLessEqual(script_lines(self.template), SCRIPT_BUDGET)
        broken = self.edit(self.template, LAST_SCRIPT_END,
                           "\n" * SCRIPT_BUDGET + LAST_SCRIPT_END)
        self.assertGreater(script_lines(broken), SCRIPT_BUDGET)


if __name__ == "__main__":
    unittest.main()
