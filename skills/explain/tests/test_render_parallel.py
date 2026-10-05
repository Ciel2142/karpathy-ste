"""Two renders at the same time (spec 9.2, the run-directory case). ParallelRenderCase needs
EXPLAIN_VIDEO_E2E=1.

ParallelRenderCase brings the workspace up to date (scripts/video-workspace.sh --engine say),
takes tree_digest of <ws>/app, then starts two renders of scripts/render.sh --engine say, one
right after the other: the film, the worked example (template_script() of test_film_example.py,
with out/scene a copy of its scene FILM_DIR), and the brainrot template (an empty clip folder, so
the generated background, and SEED). Each runs in a session of its own, in a temp dir of its own
with its stdout and stderr in files. The two overlap in time, both print all their ok lines (the
film the ten of ORDER of test_render_film.py, brainrot its ten), <ws>/app is the same afterwards
(node_modules aside: the film's scene goes only into its run directory), and neither leaves its
run directory <ws>/runs/run.<pid>.<6 chars>. Two more renders show that no run directory is left
after a fail (a brainrot render with an invalid seed) and after SIGTERM to the process group of an
explainer render (the three-scene explainer fixture of video_e2e.py). <ws> is workspace() of
video_e2e.py and every render gets render_env(), so the renders follow $EXPLAIN_VIDEO_WORKSPACE.
Other sessions may render in the same workspace, so each check names the pids of its own renders.

TreeDigestCase checks tree_digest on a temp tree and always runs; a later wave imports
tree_digest for its own "the shared app is unchanged" check. Each test names the mutation that
turns it red."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_film_example import FILM_DIR, template_script
from test_render import default_signals, kill_group, names, stage_lines
from test_render_brainrot import BACKGROUND, BRAINROT_TEMPLATE, SEED, stage_patterns
from test_render_film import ORDER as FILM_ORDER
from video_e2e import (E2E, E2E_REASON, EXPLAIN, RENDER_SH, RENDER_TIMEOUT, fixture_script,
                       render_env, workspace)

WORKSPACE_SH = EXPLAIN / "scripts" / "video-workspace.sh"
BAD_SEED_LINE = "background: FAIL EXPLAIN_BRAINROT_SEED must be an integer, got 'abc'"


def raise_error(error):
    """onerror of os.walk: an unreadable directory fails the digest instead of dropping out."""
    raise error


def tree_digest(root: Path, skip: tuple = ("node_modules",)) -> str:
    """sha256 over every entry under `root` in sorted order of its relative path, without the
    top-level names in `skip` (and what lies under them): the path, its kind (file, directory,
    link), and the bytes of a file or the target of a link. A link is not followed."""
    root = Path(root)
    entries = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=raise_error):
        if Path(dirpath) == root:
            dirnames[:] = [name for name in dirnames if name not in skip]
            filenames = [name for name in filenames if name not in skip]
        entries += [Path(dirpath, name) for name in dirnames + filenames]
    digest = hashlib.sha256()
    for path in sorted(entries, key=lambda p: p.relative_to(root).as_posix()):
        if path.is_symlink():
            kind, data = "link", os.readlink(path).encode()
        elif path.is_dir():
            kind, data = "directory", b""
        else:
            kind, data = "file", path.read_bytes()
        # each field with its length first, so that no two trees give the same byte stream
        for field in (path.relative_to(root).as_posix().encode(), kind.encode(), data):
            digest.update(b"%d:" % len(field) + field)
    return digest.hexdigest()


class TreeDigestCase(unittest.TestCase):
    """tree_digest on a temp tree: no workspace, no render."""

    def make_tree(self):
        """A fresh temp tree: a.txt, src/b.txt, a link to a.txt, and a node_modules both at the
        top and in src/."""
        root = Path(tempfile.mkdtemp(prefix="tree-digest-test-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name, text in (("a.txt", "abc"), ("src/b.txt", "b"), ("node_modules/x", "x"),
                           ("src/node_modules/x", "x")):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")
        (root / "link").symlink_to("a.txt")
        return root

    def changed(self, change):
        """The digest of a fresh tree after `change(root)`."""
        root = self.make_tree()
        change(root)
        return tree_digest(root)

    # red: a digest of the names only (the changed byte and the changed link go unseen)
    def test_digest_sees_a_new_file_a_changed_byte_and_a_changed_link(self):
        base = tree_digest(self.make_tree())
        # the same tree at another path has the same digest
        self.assertEqual(self.changed(lambda root: None), base)

        def new_file(root):
            (root / "src" / "c.txt").write_text("", encoding="utf-8")

        def changed_byte(root):
            (root / "a.txt").write_text("abd", encoding="utf-8")

        def changed_link(root):
            (root / "link").unlink()
            (root / "link").symlink_to("src/b.txt")

        for change in (new_file, changed_byte, changed_link):
            with self.subTest(change=change.__name__):
                self.assertNotEqual(self.changed(change), base)

    # red: the skip matches at every depth (the change in src/node_modules goes unseen), or not
    # at all (the change in the top-level node_modules is seen)
    def test_digest_skips_top_level_node_modules_only(self):
        base = tree_digest(self.make_tree())

        def top(root):
            (root / "node_modules" / "x").write_text("y", encoding="utf-8")
            (root / "node_modules" / ".cache").mkdir()

        def nested(root):
            (root / "src" / "node_modules" / "x").write_text("y", encoding="utf-8")

        self.assertEqual(self.changed(top), base)
        self.assertNotEqual(self.changed(nested), base)


class Render:
    """A render.sh --engine say run of `script` (a dict), started at once: in a temp dir of its
    own (the output dir out/, stdout and stderr in files, an empty clip folder, so that a brainrot
    render picks the generated background), in a session of its own with HUP, INT and TERM at
    their default action. With `scene` (a directory), out/scene is a copy of it. Its environment
    is render_env(EXPLAIN_BRAINROT_BACKGROUNDS=<clips>, **env). `add_cleanup` (addCleanup or
    addClassCleanup) gets the kill of the process group and the removal of the temp dir. `start`
    and `end` are time.monotonic() values; poll() sets `end`. The pid is that of render.sh itself,
    so its run directory is run.<pid>.<6 chars>."""

    def __init__(self, add_cleanup, script, scene=None, **env):
        self.tmp = Path(tempfile.mkdtemp(prefix="explain-parallel-"))
        add_cleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        self.out.mkdir()
        (self.tmp / "clips").mkdir()
        (self.out / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")
        if scene is not None:
            shutil.copytree(scene, self.out / "scene")
        run_env = render_env(EXPLAIN_BRAINROT_BACKGROUNDS=str(self.tmp / "clips"), **env)
        with open(self.tmp / "stdout", "w") as stdout, open(self.tmp / "stderr", "w") as stderr:
            self.proc = subprocess.Popen(
                ["/bin/bash", str(RENDER_SH), str(self.out), "--engine", "say"],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, env=run_env, cwd=self.tmp,
                start_new_session=True, preexec_fn=default_signals)
        self.start, self.end = time.monotonic(), None
        self.pid = self.proc.pid
        add_cleanup(kill_group, self.proc)

    def output(self):
        """(stdout, stderr), as far as they are written."""
        return tuple((self.tmp / name).read_text(encoding="utf-8") for name in ("stdout", "stderr"))

    def result(self):
        """The CompletedProcess of the run; call it once render.sh has exited."""
        return subprocess.CompletedProcess(self.proc.args, self.proc.returncode, *self.output())

    def poll(self):
        """True once render.sh has exited; the first True sets `end`."""
        if self.end is None and self.proc.poll() is not None:
            self.end = time.monotonic()
        return self.end is not None


def wait_all(renders, timeout):
    """Wait until every render has exited, noting the end of each as it comes. After `timeout` s
    the process groups still running are killed: their exit code then shows it."""
    deadline = time.monotonic() + timeout
    while not all([render.poll() for render in renders]):
        if time.monotonic() > deadline:
            for render in renders:
                if not render.poll():
                    kill_group(render.proc)
                    render.poll()
            return
        time.sleep(0.2)


def brainrot_script():
    """The brainrot template, rooted at the skill dir."""
    script = json.loads(BRAINROT_TEMPLATE.read_text(encoding="utf-8"))
    script["provenance"]["root"] = str(EXPLAIN)
    return script


def run_dirs(pid):
    """The names in <ws>/runs that are run directories of render.sh `pid`: run.<pid>.<6 chars>."""
    return [name for name in names(workspace() / "runs") or [] if name.startswith("run.%d." % pid)]


@unittest.skipUnless(E2E, E2E_REASON)
class ParallelRenderCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ready = subprocess.run(["/bin/bash", str(WORKSPACE_SH), "--engine", "say"],
                               capture_output=True, text=True, env=render_env(),
                               stdin=subprocess.DEVNULL, timeout=RENDER_TIMEOUT)
        if ready.returncode != 0:
            raise unittest.SkipTest("video-workspace.sh --engine say exit %d:\n%s%s"
                                    % (ready.returncode, ready.stdout, ready.stderr))
        cls.before = tree_digest(workspace() / "app")
        brainrot = brainrot_script()
        cls.film = Render(cls.addClassCleanup, template_script(), scene=FILM_DIR)
        cls.brainrot = Render(cls.addClassCleanup, brainrot, EXPLAIN_BRAINROT_SEED=SEED)
        wait_all((cls.film, cls.brainrot), RENDER_TIMEOUT)
        cls.after = tree_digest(workspace() / "app")

    def finish(self, render, timeout):
        """The CompletedProcess of `render` once it has exited; the test fails after `timeout` s."""
        try:
            render.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail("render.sh still runs after %s s:\n%s" % (timeout, "".join(render.output())))
        return render.result()

    # red: the renders ran one after the other, so the class shows nothing
    def test_the_two_renders_ran_at_the_same_time(self):
        starts = (self.film.start, self.brainrot.start)
        ends = (self.film.end, self.brainrot.end)
        self.assertLess(max(starts), min(ends), "starts %s, ends %s" % (starts, ends))

    # red: a shared public/audio or a shared project, where one render takes the other's files
    def test_both_renders_print_all_their_ok_lines(self):
        brainrot = [pattern or BACKGROUND["generated"] for pattern in stage_patterns(4)]
        for name, render, patterns in (("film", self.film, FILM_ORDER),
                                       ("brainrot", self.brainrot, brainrot)):
            with self.subTest(render=name):
                run = render.result()
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                lines = stage_lines(run.stdout)
                self.assertEqual(len(lines), len(patterns), run.stdout)
                for line, pattern in zip(lines, patterns):
                    self.assertRegex(line, "^%s$" % pattern)

    # red: a render writes audio or sources under <ws>/app, or the film's scene is copied there.
    # Not run red (decision 12 of the wave plan): SceneRunCase of test_render_film.py is its red-first
    # proof, in a temporary workspace
    def test_the_app_is_unchanged(self):
        # the digest is of the workspace that both renders used
        for render in (self.film, self.brainrot):
            stdout = render.output()[0]
            self.assertIn("workspace: ok %s" % workspace(), stage_lines(stdout), stdout)
        self.assertEqual(self.after, self.before)

    # red: no removal on exit
    def test_no_run_directory_is_left_after_a_pass(self):
        for name, render in (("film", self.film), ("brainrot", self.brainrot)):
            with self.subTest(render=name):
                self.assertEqual(render.proc.returncode, 0, "".join(render.output()))
                self.assertEqual(run_dirs(render.pid), [])

    # red: removal only on success
    def test_no_run_directory_is_left_after_a_fail(self):
        render = Render(self.addCleanup, brainrot_script(), EXPLAIN_BRAINROT_SEED="abc")
        run = self.finish(render, RENDER_TIMEOUT)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        lines = stage_lines(run.stdout)
        # the run directory was made: the workspace stage passed, and the timeline was built in it
        self.assertIn("workspace: ok %s" % workspace(), lines, run.stdout)
        self.assertTrue([line for line in lines if line.startswith("timeline (")], run.stdout)
        self.assertEqual(lines[-1], BAD_SEED_LINE, run.stdout)
        self.assertEqual(run_dirs(render.pid), [])

    # red: no trap, a removal through the node_modules link, or a render.sh that exits before the
    # Remotion CLI (which outlives TERM), so that the CLI makes the removed run directory again
    def test_no_run_directory_is_left_after_sigterm(self):
        render = Render(self.addCleanup, fixture_script())
        deadline = time.monotonic() + RENDER_TIMEOUT

        def timeline_lines():
            lines = stage_lines(render.output()[0])
            return [line for line in lines if line.startswith("timeline (")]

        while not timeline_lines():
            if render.proc.poll() is not None or time.monotonic() > deadline:
                self.fail("render.sh printed no timeline line while it ran:\n"
                          + "".join(render.output()))
            time.sleep(0.2)
        self.assertEqual(len(run_dirs(render.pid)), 1, names(workspace() / "runs"))
        time.sleep(2)
        os.killpg(render.pid, signal.SIGTERM)
        run = self.finish(render, 60)
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(run_dirs(render.pid), [])
        self.assertTrue((workspace() / "app" / "node_modules" / ".explain-lock-sha").exists())


if __name__ == "__main__":
    unittest.main()
