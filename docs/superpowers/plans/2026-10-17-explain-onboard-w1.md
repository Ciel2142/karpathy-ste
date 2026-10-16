# explain onboard, wave 1 (mermaid-pattern) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mermaid text renders to inline SVG in an explain page: `mermaid_svg.py render` and `inline`, the three `figure.mermaid` CSS rules of the page template, and the Mermaid pattern of `rungs/page.md` section 4.

**Architecture:** One stdlib-only Python script, `scripts/mermaid_svg.py`, fetches the pinned `mermaid@12.2.0` bundle by hash, writes a one-page harness that calls `mermaid.render` for every diagram, runs headless Chrome once with the process-group handling of `verify.sh`, reads the harness result out of the DOM dump, and finishes each SVG (intrinsic size, `role="img"`, title, `data-ste`). `inline` applies that to every `figure.mermaid[data-src]` of a page. The template and the rung file teach the pattern; drift tests pin them.

**Tech Stack:** Python 3.14 stdlib (`urllib`, `hashlib`, `subprocess`, `tempfile`, `re`, `html`), headless Google Chrome, the `mermaid.min.js` bundle, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md` (sections 8, 9 and 13). Wave map: `docs/superpowers/waves/2026-10-16-explain-onboard.yaml`, wave `mermaid-pattern`. Coverage: waived.

Base: 098d2f12cdbc2683877bad6f46ff6d8fc8fd3a69
Test runs: scoped per task; full suite once, final task.

All paths below are relative to `skills/explain/` unless they start with `docs/`. Every test command runs from `skills/explain/`.

## Global Constraints

- The bundle is `mermaid@12.2.0`, file name `mermaid-12.2.0.min.js`, 5 494 801 bytes, sha256 `a8a6a6f805b074a8261a2825c86f99c8054acb3b35f50bb7e24a4f9f2c3c3b9f`; default path `$HOME/karpathy/video-workspace/mermaid/mermaid-12.2.0.min.js`, override `EXPLAIN_MERMAID_JS`. URLs, in order: `https://unpkg.com/mermaid@12.2.0/dist/mermaid.min.js`, then `https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.min.js`.
- Chrome is `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, run with `--headless=new --disable-gpu --dump-dom --hide-scrollbars --user-data-dir=<work>/profile`, in its own process group, polled for a last line ending in `</html>`, then killed and swept by the temp path (HANDOFF run rule 6: `os.killpg` may raise `PermissionError`; fall back to `Popen.kill()` plus `pkill -KILL -f <work>`).
- The Mermaid config is fixed in the script: `theme: "base"`, `securityLevel: "strict"`, `startOnLoad: false`, `htmlLabels: false` at the top level AND under `flowchart`, `fontSize: "14px"`, `themeVariables`: `fontFamily` = the `--sans` stack of `templates/page.html`, `primaryColor #f0eee6`, `primaryTextColor #1f1d1a`, `primaryBorderColor #1f1d1a`, `lineColor #1f1d1a`, `secondaryColor #faf9f5`, `tertiaryColor #faf9f5`, `background #faf9f5`, `edgeLabelBackground #faf9f5`.
- The finished SVG keeps `viewBox`; `width` and `height` are the `viewBox` size rounded UP to whole pixels; no root `max-width` style; `role="img"`; `data-ste="skip"`; `aria-labelledby="<id>-title"`; a `<title id="<id>-title">`; zero `foreignObject`.
- Output lines are `mermaid: ok <n> diagrams` (last line on success) or `mermaid: FAIL …`; exit 0 ok, 1 a render or a page fault, 2 usage, Chrome not found, or a bundle fault.
- No test of the normal suite touches the network. Chrome tests skip with `mermaid bundle missing: <path>` when the bundle is absent. The real download is tested only under `EXPLAIN_MERMAID_E2E=1`.
- Stdlib only (the suite runs under the system python3). Never commit `out/`. Never write under `~/karpathy/video-workspace/app` or `public/`.
- `rungs/page.md` lints clean: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/page.md` prints `0 errors, 0 warnings` (run from the repository root).
- Commit style of this repository: `feat: explain: …`, `test: explain: …`, `docs: explain: …`.

## Review Focus

1. A `figure.mermaid` with no `data-src` attribute: the author forgot it, the page shows an empty figure, `verify.sh` does not look. Expected: `mermaid: FAIL figure <n> no data-src`, exit 1, page untouched (Task 3).
2. Two figures on one page with the same diagram id (same `data-src`, or two `.mmd` files with one stem): Mermaid scopes its `<style>` by id, so the two SVGs would share rules and ids. Expected: `mermaid: FAIL <id> duplicate id`, exit 1 (Task 3).
3. The DOM dump arrives before the harness finished (no `data-mermaid` on `<html>`): a silent empty SVG would pass. Expected: `mermaid: FAIL harness incomplete`, exit 1 (Task 2).
4. A bundle file in place whose bytes are not the pinned ones (a cut download by another tool, a hand-copied file): rendering with it gives an unverified SVG. Expected: hashed on every run, `mermaid: FAIL sha256 <got>`, exit 2, the file left in place (Task 1).
5. A diagram id that is not a valid CSS id or HTML id (`1-flow`, `my flow.mmd`): Mermaid's scoped `#id` rules and `mermaid.render` break. Expected: `mermaid: FAIL <stem> bad id` before Chrome runs; exit 2 from `render`, exit 1 from `inline` (Tasks 2 and 3).

## File structure

- `scripts/mermaid_svg.py` (new, one module, under 400 lines): constants, `MermaidError`, bundle (`bundle_path`, `sha256_of`, `ensure_bundle`), SVG finish (`finish_svg`), Chrome (`harness_html`, `render_many`), page (`Figure`, `page_figures`, `inline_page`), CLI (`cmd_render`, `cmd_inline`, `main`).
- `tests/test_mermaid_svg.py` (new): `FinishSvgCase`, `BundleCase`, `RenderCase`, `InlineCase`; in-process runs of `main`, as `tests/test_bpmn_svg.py` does for `bpmn.py`.
- `tests/mermaid_page.py` (new): `mermaid_page(out, section=None, mmd="flow.mmd")`, the Mermaid twin of `tests/bpmn_page.py`.
- `tests/fixtures/mermaid/` (new): `flow.mmd`, `state.mmd`, `bad.mmd`, `wide.mmd`, `section.html`.
- `templates/page.html`: three `figure.mermaid` rules after the BPMN rules (line 138). `tests/test_page_template.py`: their pins and two guard runs.
- `rungs/page.md` section 4: the Mermaid pattern bullet. `tests/test_rung_drift.py`: its phrases.

---

### Task 1: Bundle and the SVG finish

**Files:**
- Create: `scripts/mermaid_svg.py`
- Create: `tests/test_mermaid_svg.py`

**Interfaces:**
- Consumes: nothing of this wave.
- Produces (all in `scripts/mermaid_svg.py`):
  ```python
  CHROME: str; BUNDLE_NAME: str; BUNDLE_SIZE: str  # "5.5 MB"
  BUNDLE_SHA256: str; BUNDLE_URLS: tuple[str, str]; DEFAULT_TIMEOUT: int  # 60
  CONFIG: dict  # the fixed Mermaid config of Global Constraints
  ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
  class MermaidError(Exception):   # str(e) is the whole output line "mermaid: FAIL …"; e.code is 1 or 2
      def __init__(self, line: str, code: int = 1) -> None
  def bundle_path() -> Path
  def sha256_of(path: Path) -> str
  def ensure_bundle(path: Path) -> Path
  def finish_svg(svg: str, diagram_id: str, title: str) -> str
  def main(argv: list[str]) -> int
  ```

- [ ] **Step 1: Write the failing tests**

In `tests/test_mermaid_svg.py`: `sys.path.insert(0, <scripts dir>)`, `import mermaid_svg`; module constants `BUNDLE = mermaid_svg.bundle_path()`, `HAVE_BUNDLE = BUNDLE.is_file()`, `NO_BUNDLE = "mermaid bundle missing: %s" % BUNDLE`, `E2E = os.environ.get("EXPLAIN_MERMAID_E2E") == "1"`; a helper `run(argv, env=None) -> tuple[int, str, str]` that calls `mermaid_svg.main(argv)` under `contextlib.redirect_stdout` / `redirect_stderr` and `unittest.mock.patch.dict(os.environ, env or {})`. Each test case uses a `tempfile.TemporaryDirectory` with `tmp/` and `work/` inside it, as `tests/test_verify.py` does, and a cleanup that runs `pkill -KILL -f <tmp>`.

A Mermaid-shaped sample for `FinishSvgCase` (one string constant):

```
<svg id="flow" width="100%" style="max-width: 496.4px;" viewBox="0 0 496.4 311.5" role="graphics-document document" aria-roledescription="flowchart-v2" xmlns="http://www.w3.org/2000/svg"><style>#flow{font-size:14px}</style><g><text>a</text></g></svg>
```

`FinishSvgCase`, each on `finish_svg(SAMPLE, "flow", "The path & the reply")`:
- `test_size_is_the_viewbox_rounded_up`: root tag holds `width="497"` and `height="312"`, exactly once each, and `viewBox="0 0 496.4 311.5"` unchanged.
- `test_root_max_width_style_is_removed`: `max-width` not in the output; `xmlns` and `id="flow"` kept.
- `test_role_is_img`: `role="img"` once; `graphics-document` absent.
- `test_title_and_aria_are_added`: `data-ste="skip"` and `aria-labelledby="flow-title"` on the root; the first child after the root start tag is `<title id="flow-title">The path &amp; the reply</title>`.
- `test_no_viewbox_is_a_fault`: a sample without `viewBox` raises `MermaidError` whose line is `mermaid: FAIL flow no viewBox`.
- `test_foreign_object_is_a_fault`: a sample holding `<foreignObject>` raises `MermaidError` with line `mermaid: FAIL flow foreignObject in output`.

`BundleCase` (no Chrome; `file://` URLs of files under `work/`; `EXPLAIN_MERMAID_JS` points under `work/m/`, a directory that does not exist yet):
- `test_bundle_path_reads_the_env_then_the_default`: with the env set, `bundle_path()` is that path; without it, `Path.home()/"karpathy"/"video-workspace"/"mermaid"/BUNDLE_NAME`.
- `test_wrong_bytes_fail_sha256_and_leave_no_part_file`: `BUNDLE_URLS` patched to one `file://` URL of a 20-byte file; `ensure_bundle` raises `MermaidError` with line `mermaid: FAIL sha256 <sha256 of that file>` and `code == 2`; stdout holds `mermaid: download mermaid-12.2.0.min.js (5.5 MB)`; no file at the bundle path; no `*.part` in its directory.
- `test_bundle_in_place_with_wrong_bytes_fails_and_stays`: a wrong file already at the bundle path; `ensure_bundle` raises the same `sha256` line; the file is still there; nothing printed.
- `test_second_url_is_tried_when_the_first_fails` (`skipUnless(HAVE_BUNDLE, NO_BUNDLE)`): URLs = a `file://` path that does not exist, then a `file://` copy of the real bundle; `ensure_bundle` returns the path, the file in place hashes to `BUNDLE_SHA256`, the parent directory was created, no `.part` left, stdout holds the download line and then `mermaid: downloaded mermaid-12.2.0.min.js`.
- `test_both_urls_failing_report_download`: two `file://` paths that do not exist; `MermaidError` line starts with `mermaid: FAIL download mermaid-12.2.0.min.js`, `code == 2`.
- `test_real_download_matches_the_hash` (`skipUnless(E2E, "EXPLAIN_MERMAID_E2E=1 only")`): real `BUNDLE_URLS` into `work/m/`; the file hashes to `BUNDLE_SHA256`.
- `test_usage_without_a_command_exits_2`: `run([])` returns 2, stderr starts with `usage: mermaid_svg.py`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -v`
Expected: `ModuleNotFoundError: No module named 'mermaid_svg'`.

- [ ] **Step 3: Implement the constants, `MermaidError`, the bundle functions and `finish_svg` in `scripts/mermaid_svg.py`**

Header comment in the style of `bpmn.py`: the two commands, the two env vars, the exit codes, the output lines (spec section 8).

- `bundle_path()`: `EXPLAIN_MERMAID_JS` read from `os.environ` at call time, else the default under `Path.home()`.
- `ensure_bundle(path)`: file present → hash it; mismatch → `MermaidError("mermaid: FAIL sha256 <got>", 2)`, file untouched. File absent → print `mermaid: download mermaid-12.2.0.min.js (5.5 MB)`, create the parent directory, fetch each URL of `BUNDLE_URLS` in order with `urllib.request.urlopen` into `<path>.<pid>.part` (a `file://` URL works unchanged); the first URL that opens is used; every URL failing → `MermaidError("mermaid: FAIL download mermaid-12.2.0.min.js: <last error>", 2)`. Hash the part file; mismatch → remove the part file, `MermaidError("mermaid: FAIL sha256 <got>", 2)`; match → `os.replace` into place, print `mermaid: downloaded mermaid-12.2.0.min.js`. A `try/finally` removes the part file on any exception.
- `finish_svg(svg, diagram_id, title)`: regex on the root start tag only (`<svg[^>]*>`, first match). Named behaviors: `viewBox` missing → `MermaidError("mermaid: FAIL <id> no viewBox")`; `width` and `height` set to `math.ceil` of the third and fourth `viewBox` numbers, any prior `width`/`height` attributes on the root replaced; the `max-width` declaration cut from the root `style`, the attribute dropped when empty; `role` set to `img` (replacing any value); `data-ste="skip"` and `aria-labelledby="<id>-title"` added; `<title id="<id>-title">` + `html.escape(title)` + `</title>` inserted right after the root start tag; `foreignObject` anywhere → `MermaidError("mermaid: FAIL <id> foreignObject in output")`. Everything else of the SVG text is kept byte for byte.
- `main(argv)`: dispatch on `argv[0]` to `cmd_render` / `cmd_inline` (both return 2 with the usage line until Tasks 2 and 3 land); no or unknown command → usage line on stderr, return 2. A `MermaidError` raised anywhere under a command is printed as its line on stdout (on stderr when the line starts with `usage:`) and its `code` returned. The `if __name__ == "__main__":` block installs handlers for `SIGHUP`, `SIGINT`, `SIGTERM` that raise `SystemExit(129 | 130 | 143)` so cleanup `finally` blocks run (Task 2), then `sys.exit(main(sys.argv[1:]))`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -v`
Expected: all `FinishSvgCase` and `BundleCase` tests `ok`; the E2E test `skipped`.

- [ ] **Step 5: Commit**

```bash
git add skills/explain/scripts/mermaid_svg.py skills/explain/tests/test_mermaid_svg.py
git commit -m "feat: explain: mermaid_svg.py fetches the pinned bundle by hash and finishes a Mermaid SVG for the page"
```

---

### Task 2: `render` through headless Chrome

**Files:**
- Modify: `scripts/mermaid_svg.py`
- Create: `tests/fixtures/mermaid/flow.mmd`, `tests/fixtures/mermaid/state.mmd`, `tests/fixtures/mermaid/bad.mmd`
- Modify: `tests/test_mermaid_svg.py`

**Interfaces:**
- Consumes: `ensure_bundle`, `finish_svg`, `MermaidError`, `CHROME`, `CONFIG`, `ID` (Task 1).
- Produces:
  ```python
  def read_timeout() -> int                       # MERMAID_TIMEOUT or DEFAULT_TIMEOUT
  def harness_html(bundle_js: str, diagrams: list[tuple[str, str]]) -> str   # (id, text)
  def render_many(diagrams: list[tuple[str, str]], bundle: Path, timeout: int) -> dict[str, str]  # id -> raw SVG
  def cmd_render(argv: list[str]) -> int
  ```

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/mermaid/flow.mmd` (six nodes, one decision, two edge labels):

```
flowchart TD
  recv[receive the message] --> kind{type?}
  kind -->|send| route[route by place]
  kind -->|cancel| cancel[cancel the request]
  route --> deliver[deliver to the partner]
  cancel --> reply[reply to the sender]
  deliver --> reply
```

`tests/fixtures/mermaid/state.mmd`:

```
stateDiagram-v2
  [*] --> New
  New --> Sent: deliver
  Sent --> Done: ack
  Sent --> Failed: timeout
  Done --> [*]
```

`tests/fixtures/mermaid/bad.mmd`:

```
flowchart TD
  a --> --> b
```

- [ ] **Step 2: Write the failing tests**

`RenderCase` in `tests/test_mermaid_svg.py`, `@unittest.skipUnless(HAVE_BUNDLE, NO_BUNDLE)` on the class except where noted; every test runs with `TMPDIR=<tmp>/` in the env and ends with the `assert_no_chrome_left` check of `tests/test_verify.py` (no process matching `<tmp>` and `<tmp>` empty). Each assertion reads the root tag with a regex, not an XML parser.
- `test_render_flow_to_a_file`: `run(["render", flow.mmd, out.svg])` → 0; stdout == `mermaid: ok 1 diagrams\n`; the file: no `foreignObject`, `role="img"`, `data-ste="skip"`, `aria-labelledby="flow-title"`, `<title id="flow-title">flow</title>`, integer `width` and `height` each not below the `viewBox` width and height, no `max-width`, the words `receive the message` and `cancel` present as SVG text.
- `test_render_to_stdout_keeps_the_svg_clean`: `run(["render", flow.mmd])` → 0; stdout starts with `<svg` and holds no `mermaid:` line; stderr == `mermaid: ok 1 diagrams\n`.
- `test_title_option_sets_the_title`: `--title "One message"` → `<title id="flow-title">One message</title>`.
- `test_state_diagram_renders`: `state.mmd` → 0, no `foreignObject`, the words `Sent` and `Failed` present.
- `test_parse_error_names_the_id_and_exits_1`: `bad.mmd` with an out path → 1; stdout starts with `mermaid: FAIL bad Parse error`; no out file written.
- `test_chrome_not_found_exits_2` (no skip): `mermaid_svg.CHROME` patched to `<work>/no-chrome` → 2; stdout == `mermaid: FAIL Chrome not found <work>/no-chrome\n`.
- `test_timeout_kills_the_group_and_removes_the_temp_dir`: `CHROME` patched to a script `#!/bin/sh` + `while :; do sleep 1; done` (mode 755), `MERMAID_TIMEOUT=1` → 1; stdout == `mermaid: FAIL timeout\n`; run took under 5 s; no process left; `<tmp>` empty.
- `test_dump_without_a_result_is_harness_incomplete`: `CHROME` patched to a script that prints `<html><body></body></html>` and then loops as above → 1; stdout == `mermaid: FAIL harness incomplete\n`; no process left.
- `test_bad_id_fails_before_chrome` (no skip): a copy of `flow.mmd` named `1 flow.mmd`, `CHROME` patched to a missing path → 2; stdout == `mermaid: FAIL 1 flow bad id\n`.
- `test_unreadable_input_is_usage` (no skip): a missing `.mmd` → 2; stderr starts with `usage:`.
- `test_bad_timeout_is_usage` (no skip): `MERMAID_TIMEOUT=abc` → 2; stderr names `MERMAID_TIMEOUT`.
- `test_render_with_a_wrong_bundle_prints_the_sha_line_and_exits_2` (no skip): `CHROME` patched to `sys.executable`, `EXPLAIN_MERMAID_JS` at a wrong 20-byte file → 2; stdout == `mermaid: FAIL sha256 <got>\n`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -k RenderCase -v`
Expected: every test fails on exit 2 with the usage line (`cmd_render` is the Task 1 stub).

- [ ] **Step 4: Implement `read_timeout`, `harness_html`, `render_many` and `cmd_render`**

- `read_timeout()`: `MERMAID_TIMEOUT` must be a positive decimal integer without a leading zero (the `is_count` rule of `verify.sh`); otherwise `MermaidError("usage: MERMAID_TIMEOUT must be a positive integer: <value>", 2)` whose line goes to stderr.
- `harness_html(bundle_js, diagrams)`: one HTML document, `<meta charset="utf-8">`, the bundle in a `<script>`, the diagrams as JSON in a second `<script>` (`</` written as `<\/`), one `<div id="out-<n>">` per diagram holding a `<textarea id="svg-<n>">`. The harness script: `mermaid.initialize(CONFIG)`, then for each diagram in order `await mermaid.render(id, text)`; on success set the textarea's `textContent` to the SVG string and `data-status="ok"` on its div; on error `data-status="fail"` and `data-message` = the first line of `String(error.message || error)`; after the loop set `data-mermaid` on `<html>` to `OK` when every diagram passed, else `FAIL`. The textarea is what makes the dump round-trip exact: Chrome serializes its text with `&lt;`, `&amp;` escapes, and `html.unescape` returns the SVG string byte for byte.
- `render_many(diagrams, bundle, timeout)`: ids checked against `ID.fullmatch` first (`MermaidError("mermaid: FAIL <id> bad id", 2)`); `CHROME` not executable → `MermaidError("mermaid: FAIL Chrome not found <CHROME>", 2)`; `ensure_bundle(bundle)`; work dir from `tempfile.mkdtemp(prefix="mermaid.", dir=os.environ.get("TMPDIR") or None)`; harness written to `<work>/harness.html`, Chrome started with `subprocess.Popen(..., stdout=<work>/dump.html, stderr=DEVNULL, start_new_session=True)` and the `file://` URL from `Path.as_uri()`; poll every 0.2 s until the dump's last line ends with `</html>` or `timeout` seconds pass (`MermaidError("mermaid: FAIL timeout")`). Then stop Chrome: `os.killpg(pid, SIGKILL)` with `PermissionError` falling back to `proc.kill()`, `wait()`, then `pkill -KILL -f <work>` until `pgrep -f <work>` is clear three polls in a row (0.2 s apart, at most 25 tries; a survivor prints `mermaid_svg.py: Chrome processes survived the kill: <work>` on stderr); `shutil.rmtree(work, ignore_errors=True)` in a `finally`. Read the dump: no `data-mermaid` on the first `<html` tag → `MermaidError("mermaid: FAIL harness incomplete")`; each `data-status="fail"` div → one line `mermaid: FAIL <id> <message>`, all of them printed, then `MermaidError` with the first line (code 1); otherwise return `{id: html.unescape(textarea text)}`.
- `cmd_render(argv)`: `argparse` with `in`, optional `out`, `--title`; `in` unreadable → usage, 2; id = the stem of `in`; title default the id; `render_many` with one diagram, `finish_svg`; write `out` when given and print `mermaid: ok 1 diagrams` on stdout, else write the SVG to stdout and the ok line to stderr.

If the Chrome tests pass on this machine the harness completes before the dump (the spike of 2026-10-16 did). If `test_render_flow_to_a_file` reports `harness incomplete` instead, add `--virtual-time-budget=<timeout * 1000>` to the Chrome arguments and note it in the header comment.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -v`
Expected: every `RenderCase` test `ok`; `pgrep -f mermaid.` afterwards prints nothing.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/mermaid_svg.py skills/explain/tests/test_mermaid_svg.py skills/explain/tests/fixtures/mermaid/flow.mmd skills/explain/tests/fixtures/mermaid/state.mmd skills/explain/tests/fixtures/mermaid/bad.mmd
git commit -m "feat: explain: mermaid_svg.py render draws one diagram through headless Chrome with the fixed page config"
```

---

### Task 3: `inline` fills every `figure.mermaid` of a page

**Files:**
- Modify: `scripts/mermaid_svg.py`
- Create: `tests/mermaid_page.py`, `tests/fixtures/mermaid/section.html`
- Modify: `tests/test_mermaid_svg.py`

**Interfaces:**
- Consumes: `render_many`, `finish_svg`, `read_timeout`, `bundle_path`, `MermaidError`, `ID` (Tasks 1 and 2).
- Produces:
  ```python
  class Figure(NamedTuple):   # one figure.mermaid of the page
      n: int; start: int; end: int; attrs: str; inner: str; src: str | None; caption: str | None
  def page_figures(html: str) -> list[Figure]
  def inline_page(page: Path, bundle: Path, timeout: int) -> int    # the number of diagrams
  def cmd_inline(argv: list[str]) -> int
  # tests/mermaid_page.py
  def mermaid_page(out: Path, section: str | None = None, mmd: str = "flow.mmd") -> Path
  ```

- [ ] **Step 1: Write the fixture section and the page helper**

`tests/fixtures/mermaid/section.html`: one `<section id="flow-send">` with an `<h2>` question, one `<p>` of two STE sentences, its `div.cites` holding one cite of `diagrams/flow.mmd` line 1 with the snippet `flowchart` (visible text `flow.mmd:1 <code>flowchart</code>`), then the figure of spec section 9 verbatim:

```html
<figure class="mermaid" data-src="diagrams/flow.mmd">
  <figcaption>The path of one message from the listener to the reply.</figcaption>
</figure>
```

`tests/mermaid_page.py`: `mermaid_page(out, section, mmd)` does what `tests/bpmn_page.py` does with the same three single-anchor edits of `templates/page.html` (the section before `<section id="provenance-facet">`, a nav link `<a href="#flow-send">Flow</a>` before the Provenance link, `data-root="."` kept), copies `tests/fixtures/mermaid/<mmd>` to `out/diagrams/<mmd>`, writes `out/index.html` and returns its path.

- [ ] **Step 2: Write the failing tests**

`InlineCase` (`TMPDIR` and the no-Chrome-left check as in Task 2; the page from `mermaid_page(<work>/page)`; Chrome tests marked `skipUnless(HAVE_BUNDLE, NO_BUNDLE)` one by one):
- `test_inline_writes_the_svg_before_the_figcaption_and_the_svg_file` (Chrome): → 0; stdout == `mermaid: ok 1 diagrams\n`; the figure holds exactly one `<svg` and it comes before `<figcaption>`; `diagrams/flow.svg` exists and its text equals the inline SVG; `<title id="flow-title">The path of one message from the listener to the reply.</title>`; the rest of the page is unchanged (compare with the figure cut out).
- `test_second_run_replaces_the_svg` (Chrome): two runs → one `<svg` in the figure, the page equal after both runs.
- `test_filled_page_passes_verify_at_both_viewports` (Chrome): after `inline`, `scripts/verify.sh index.html` run as a subprocess with `TMPDIR` set, `VERIFY_TIMEOUT` unset → exit 0, stdout == `self-contained: ok`, `render 1440x900: ok`, `render 500x844: ok`, `citations: ok`, `prose: ok`, `bpmn: none`, one per line.
- `test_parse_error_names_the_id_and_writes_nothing` (Chrome): section edited to `diagrams/bad.mmd`, `mmd="bad.mmd"` → 1; stdout starts with `mermaid: FAIL bad Parse error`; no `diagrams/bad.svg`; page unchanged.
- `test_missing_data_src_file_fails_with_the_id`: `diagrams/flow.mmd` removed → 1; stdout == `mermaid: FAIL flow cannot read diagrams/flow.mmd\n`; page unchanged.
- `test_figure_without_data_src_fails`: `data-src="diagrams/flow.mmd"` cut from the section → 1; stdout == `mermaid: FAIL figure 1 no data-src\n`.
- `test_duplicate_id_fails`: the figure doubled in the section → 1; stdout == `mermaid: FAIL flow duplicate id\n`.
- `test_bad_data_src_stem_fails`: `data-src="diagrams/1 flow.mmd"` (file present) → 1; stdout == `mermaid: FAIL 1 flow bad id\n`.
- `test_every_figure_fault_is_listed_before_exit`: one figure without `data-src` and one with a missing file → 1; stdout holds both lines, in page order.
- `test_page_without_figures_prints_ok_0`: `templates/page.html` copied as the page → 0; stdout == `mermaid: ok 0 diagrams\n`; the file unchanged.
- `test_unreadable_page_is_usage`: a missing path → 2; stderr starts with `usage:`.
- `test_figure_without_figcaption_takes_the_id_as_title` (Chrome): `<figcaption>…</figcaption>` cut → `<title id="flow-title">flow</title>`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -k InlineCase -v`
Expected: every test fails on exit 2 with the usage line, or on `ImportError` of `mermaid_page` until Step 1 is in place.

- [ ] **Step 4: Implement `Figure`, `page_figures`, `inline_page` and `cmd_inline`**

- `page_figures(html)`: one `re.finditer` of `<figure class="[^"]*\bmermaid\b[^"]*"[^>]*>(.*?)</figure>` with `re.S`; `n` counts from 1 in page order; `src` is the `data-src` value or `None`; `caption` is the inner text of the first `<figcaption>…</figcaption>` with tags stripped and white space squashed, or `None`.
- `inline_page(page, bundle, timeout)`: read the page (unreadable → usage, 2); figures checked in order and every fault line printed before `MermaidError` with the first (code 1): no `data-src` → `mermaid: FAIL figure <n> no data-src`; the stem of `data-src` (its suffix must be `.mmd`) fails `ID` → `mermaid: FAIL <stem> bad id`; the file (relative to the page directory) unreadable → `mermaid: FAIL <id> cannot read <data-src>`; a stem seen before → `mermaid: FAIL <id> duplicate id`. No figures → print `mermaid: ok 0 diagrams`, return 0 without Chrome. Else `render_many` once for all diagrams, `finish_svg` each with the caption or the id; write `<src dir>/<id>.svg`; rebuild the page from the end backwards: the figure's inner text with any existing `<svg …>…</svg>` (first match, `re.S`) cut, then the new SVG and a newline put right after the figure's start tag; write the page once; print `mermaid: ok <n> diagrams`. On any `MermaidError` nothing is written.
- `cmd_inline(argv)`: exactly one argument, the page path; `inline_page(Path(arg), bundle_path(), read_timeout())`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_mermaid_svg.py" -v`
Expected: all `InlineCase` tests `ok` (the Chrome ones `skipped` only when the bundle is absent).

- [ ] **Step 6: Commit**

```bash
git add skills/explain/scripts/mermaid_svg.py skills/explain/tests/test_mermaid_svg.py skills/explain/tests/mermaid_page.py skills/explain/tests/fixtures/mermaid/section.html
git commit -m "feat: explain: mermaid_svg.py inline fills every figure.mermaid of a page in one Chrome run"
```

---

### Task 4: The three `figure.mermaid` rules of the page template

**Files:**
- Modify: `templates/page.html` (the BPMN CSS block, lines 117-138; the pattern list in the header comment near line 18)
- Create: `tests/fixtures/mermaid/wide.mmd`
- Modify: `tests/test_page_template.py`

**Interfaces:**
- Consumes: `mermaid_page` (Task 3), `mermaid_svg.main(["inline", …])` (Task 3), `style_rules`, `RENDER_OK`, `PageGuardTest.verify` (existing).
- Produces: the three rules, verbatim:
  ```css
  figure.mermaid { --bpmn-w: max(100%, min(1040px, 100vw - 64px)); width: var(--bpmn-w); margin: 16px 0 16px calc((100% - var(--bpmn-w)) / 2); overflow-x: auto; }
  figure.mermaid svg { display: block; max-width: none; }
  figure.mermaid svg text { font-size: 14px; }
  ```

- [ ] **Step 1: Write the wide fixture**

`tests/fixtures/mermaid/wide.mmd`: `flowchart LR` with eight nodes in one chain, `n1[listener] --> n2[parse] --> … --> n8[reply]`, each label two words, so the render is wider than 700 px.

- [ ] **Step 2: Write the failing tests**

In `tests/test_page_template.py` (import `mermaid_page` from `tests.mermaid_page`, `mermaid_svg` from the scripts directory, and the `HAVE_BUNDLE` / `NO_BUNDLE` pair computed as in Task 1):
- `test_mermaid_rules_exist_and_keep_the_floor`: `rules["figure.mermaid"] == rules["figure.bpmn"]`; `rules["figure.mermaid svg"] == "display: block; max-width: none;"`; `rules["figure.mermaid svg text"] == "font-size: 14px;"`; every selector holding `mermaid` has no `font-size` under 14 px.
- `test_mermaid_fixture_page_passes_the_guard` (`skipUnless(HAVE_BUNDLE, NO_BUNDLE)`): `mermaid_page(<work>)`, `mermaid_svg.main(["inline", page])` returns 0, `self.verify(page)` prints both `RENDER_OK` lines.
- `test_wide_mermaid_figure_scrolls_without_page_hscroll` (`skipUnless`): the section with `flow.mmd` replaced by `wide.mmd` (both occurrences) and `mmd="wide.mmd"`; after `inline`, the root `width` of the SVG in the page is over 700; `verify` prints both `RENDER_OK` lines. Red when `overflow-x: auto` leaves `figure.mermaid` (`HSCROLL` at 500 px).

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_page_template.py" -k mermaid -v`
Expected: `KeyError: 'figure.mermaid'` in the rules test; the wide test fails on `render 500x844: FAIL data-verify="HSCROLL…"`.

- [ ] **Step 4: Add the rules and the comment**

After `cite:has(.bpmn-label) > code` (line 138) add a short comment and the three rules of the Interfaces block, verbatim. The comment says: a `figure.mermaid` takes the figure rules of BPMN; the SVG keeps its intrinsic size (the script sets width and height from the `viewBox`, rounded up, because a width rounded down fails the font guard with `SMALLTEXT:14`); `figure.mermaid svg text` is 14 px because the template's `svg text` rule of 18 px wins over the size that Mermaid's labels inherit. In the header comment list of patterns add one line: `Mermaid: <figure class="mermaid" data-src="diagrams/<id>.mmd"> filled by scripts/mermaid_svg.py inline (rungs/page.md section 4).`

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -B -m unittest discover -s tests -p "test_page_template.py" -v`
Expected: every test `ok` (the whole file, so the palette, floor and budget pins still hold).

- [ ] **Step 6: Commit**

```bash
git add skills/explain/templates/page.html skills/explain/tests/test_page_template.py skills/explain/tests/fixtures/mermaid/wide.mmd
git commit -m "feat: explain: page template holds a figure.mermaid at its intrinsic size with 14 px labels"
```

---

### Task 5: The Mermaid pattern of `rungs/page.md`, its drift pins, the full suite

**Files:**
- Modify: `rungs/page.md` (section "4. Diagram patterns", after the BPMN plane bullet)
- Modify: `tests/test_rung_drift.py` (a new `MermaidRungCase` after `BpmnRungCase`)

**Interfaces:**
- Consumes: the `section` and `lint` helpers and `PAGE_MD` of `tests/test_rung_drift.py`; the `words` method pattern of `BpmnRungCase`.
- Produces: the pattern text that `rungs/onboard.md` (wave 3) will point at.

- [ ] **Step 1: Write the failing tests**

`MermaidRungCase` in `tests/test_rung_drift.py`:
- `test_page_md_has_the_mermaid_pattern`: in the words of "Diagram patterns", with a `subTest` per phrase: `<figure class="mermaid" data-src="diagrams/<id>.mmd">`, `mermaid_svg.py inline index.html`, `diagrams/<id>.svg`, `before the <figcaption>`, `A second run replaces the SVG`, `Never paste an SVG by hand`, `any flow with a branch, and any state machine`, `at most six boxes`, `flowchart`, `stateDiagram-v2`.
- `test_mermaid_pattern_follows_the_bpmn_plane`: in those words, the index of `<figure class="mermaid"` is greater than the index of `<figure class="bpmn">`.
- `test_page_md_lints_clean_with_the_mermaid_pattern`: `lint(PAGE_MD)` returns `(0, "0 errors, 0 warnings\n")`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -B -m unittest discover -s tests -p "test_rung_drift.py" -k MermaidRungCase -v`
Expected: the two phrase tests fail with `AssertionError`; the lint test passes already.

- [ ] **Step 3: Write the pattern bullet in `rungs/page.md` section 4**

One bullet `- Mermaid: …` after the BPMN plane bullet, in STE (sentences under 26 words, one idea each), carrying these facts and the figure block of spec section 9 verbatim inside the bullet, as the BPMN bullet carries its block:
1. Use it for any flow with a branch, and any state machine. The hand-drawn flow pattern stays for a straight pipeline of at most six boxes. The sequence and layers patterns stay. A BPMN plane keeps its own pattern.
2. Two types: `flowchart` (`TD` or `LR`) and `stateDiagram-v2`. A branch in the code is a decision node with one labelled edge per outcome. At most 25 nodes in one diagram.
3. Write the diagram text to `diagrams/<id>.mmd` in the output directory. The id is the file stem; it starts with a letter. Then the figure block.
4. Run `python3 <skill-dir>/scripts/mermaid_svg.py inline index.html`. It renders each `.mmd` to `diagrams/<id>.svg` and writes the SVG into its figure before the `<figcaption>`. A second run replaces the SVG. Never paste an SVG by hand. The script fetches the Mermaid bundle on its first run.
5. The style is fixed: the page palette, 14 px text, no HTML labels. Write no style in the diagram. The rules above for the units, the `viewBox` and the marker ids do not apply. The SVG keeps its intrinsic size; a wide diagram scrolls inside its figure.
6. The cites of the section go in the `div.cites` after the lead paragraph or the figcaption.
7. The `media` check of `verify.sh` does not read `data-src`. `inline` reports an empty figure and exits with code 1 when a `data-src` file is missing. The tiles show it too.

- [ ] **Step 4: Lint and run the drift tests**

Run (from the repository root): `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/page.md`
Expected: `0 errors, 0 warnings`. Rewrite the sentences the lint names until it is.

Run: `python3 -B -m unittest discover -s tests -p "test_rung_drift.py" -v`
Expected: every test `ok`, `MermaidRungCase` and `BpmnRungCase` included.

- [ ] **Step 5: Run the full suite**

Run: `python3 -B -m unittest discover -s tests`
Expected: the last line is `OK` or `OK (skipped=<n>)`, no `FAILED`; then `pgrep -f "mermaid\."` and `pgrep -f "verify\."` print nothing.

- [ ] **Step 6: Commit**

```bash
git add skills/explain/rungs/page.md skills/explain/tests/test_rung_drift.py
git commit -m "docs: explain: page.md teaches the Mermaid pattern of a page and the drift test pins it"
```
