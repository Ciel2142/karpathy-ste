"""Tests for scripts/video-workspace.sh: the Remotion workspace outside the repo. The real
cmp, cp, mv and shasum run on the real video/ package files; npm, curl and the remotion
binary that npm installs are fakes that log their arguments, so no registry, Chrome or
model download is needed. Each test names the mutation that turns it red."""

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
WORKSPACE_SH = EXPLAIN / "scripts" / "video-workspace.sh"
KOKORO_SHA = "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
VOICES_SHA = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
WRONG_BYTES = b"not a model\n"

# npm ci as the real one does it: remove node_modules, then install, which puts the remotion
# binary at node_modules/.bin/remotion. Each fake appends "<tool> <argv>" to FAKE_LOG and a
# "FAKE <tool> <argv>" marker to FAKE_STDOUT, the file that also holds the script's stdout.
FAKE_NPM = r"""#!/bin/sh
echo "npm $*" >> "$FAKE_LOG"
echo "FAKE npm $*" >> "$FAKE_STDOUT"
[ "$1" = ci ] || exit 0
rm -rf node_modules
mkdir -p node_modules/.bin
cat > node_modules/.bin/remotion <<'EOF'
#!/bin/sh
echo "remotion $* (cwd $(pwd -P))" >> "$FAKE_LOG"
echo "FAKE remotion $*" >> "$FAKE_STDOUT"
EOF
chmod +x node_modules/.bin/remotion
"""
# curl -fsSL -o <file> <url>: writes WRONG_BYTES to <file>.
FAKE_CURL = r"""#!/bin/sh
echo "curl $*" >> "$FAKE_LOG"
echo "FAKE curl $*" >> "$FAKE_STDOUT"
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'not a model\n' > "$out"
"""


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="video-ws-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.ws = self.tmp / "ws"
        self.app = self.ws / "app"
        self.log = self.tmp / "fake.log"
        self.out = self.tmp / "stdout.txt"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, body in (("npm", FAKE_NPM), ("curl", FAKE_CURL)):
            path = bin_dir / name
            path.write_text(body, encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.env = dict(
            os.environ,
            PATH=f"{bin_dir}:{os.environ['PATH']}",
            EXPLAIN_VIDEO_WORKSPACE=str(self.ws),
            FAKE_LOG=str(self.log),
            FAKE_STDOUT=str(self.out),
        )

    def run_ws(self, *args, script=WORKSPACE_SH):
        """Run the script; stdout and the fakes' markers share self.out, in write order."""
        self.out.write_bytes(b"")
        with open(self.out, "ab") as stdout:
            run = subprocess.run(
                ["/bin/bash", str(script), *args],
                stdout=stdout, stderr=subprocess.PIPE, text=True, env=self.env,
            )
        run.stdout = self.out.read_text(encoding="utf-8")
        return run

    def calls(self, tool):
        if not self.log.exists():
            return []
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return [line for line in lines if line.split(" ", 1)[0] == tool]

    def assert_ok(self, run):
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stdout.splitlines()[-1], f"workspace: ok {self.ws}")

    def copy_skill(self):
        """A copy of scripts/video-workspace.sh and video/ whose lock file a test may edit."""
        skill = self.tmp / "skill"
        (skill / "scripts").mkdir(parents=True)
        shutil.copy2(WORKSPACE_SH, skill / "scripts" / WORKSPACE_SH.name)
        shutil.copytree(
            EXPLAIN / "video", skill / "video",
            ignore=shutil.ignore_patterns("node_modules", "__pycache__", "public", "build"),
        )
        return skill


class PackageFiles(WorkspaceCase):
    def app_names(self):
        return sorted(p.name for p in self.app.iterdir())

    def test_app_gets_the_two_package_files_and_nothing_else(self):
        """Mutation: the source sync is back (src and the tools of video/ are listed)."""
        self.assert_ok(self.run_ws("--engine", "say"))

        self.assertEqual(
            self.app_names(),
            ["browser-ensure.log", "node_modules", "npm-ci.log", "package-lock.json",
             "package.json"],
        )
        for name in ("package.json", "package-lock.json"):
            self.assertEqual(
                (self.app / name).read_bytes(), (EXPLAIN / "video" / name).read_bytes(), name
            )

    def test_what_is_already_in_the_app_stays(self):
        """Mutation: the sync keeps --delete, or the dangling public/bg link is still removed."""
        self.assert_ok(self.run_ws("--engine", "say"))
        planted = {
            "stale.txt": b"old\n",
            "src/Old.tsx": b"export {};\n",
            "public/audio/keep.wav": b"RIFF",
            "bg-stage/clip.mp4": b"old staged clip",
        }
        for name, data in planted.items():
            (self.app / name).parent.mkdir(parents=True, exist_ok=True)
            (self.app / name).write_bytes(data)
        link = self.app / "public" / "bg"
        target = str(self.tmp / "gone")
        link.symlink_to(target)

        self.assert_ok(self.run_ws("--engine", "say"))

        for name, data in planted.items():
            self.assertEqual((self.app / name).read_bytes(), data, name)
        self.assertTrue(link.is_symlink(), "the dangling link was removed")
        self.assertEqual(os.readlink(link), target)
        self.assertFalse(link.exists(), "the link no longer dangles")

    def test_unchanged_package_files_are_not_touched(self):
        """Mutation: a copy on every run (cp, cp -p, or rsync, which sets the times again)."""
        self.assert_ok(self.run_ws("--engine", "say"))

        def marks():
            found = {}
            for name in ("package.json", "package-lock.json"):
                info = (self.app / name).stat()
                found[name] = (info.st_ino, info.st_mtime_ns, info.st_ctime_ns)
            return found

        before = marks()

        self.assert_ok(self.run_ws("--engine", "say"))

        self.assertEqual(marks(), before)

    def test_changed_package_file_arrives_by_a_rename(self):
        """Mutation: the file is overwritten in place (same inode), or the temporary file is
        left behind in the app."""
        skill = self.copy_skill()
        script = skill / "scripts" / WORKSPACE_SH.name
        self.assert_ok(self.run_ws("--engine", "say", script=script))
        names = self.app_names()
        inode = (self.app / "package.json").stat().st_ino
        source = skill / "video" / "package.json"
        source.write_bytes(source.read_bytes() + b"\n")

        self.assert_ok(self.run_ws("--engine", "say", script=script))

        self.assertEqual((self.app / "package.json").read_bytes(), source.read_bytes())
        self.assertNotEqual((self.app / "package.json").stat().st_ino, inode)
        self.assertEqual(self.app_names(), names)

    def test_backgrounds_made_and_the_old_stage_left_alone(self):
        """Mutation: backgrounds is not made, or the stage is made (a fresh workspace) or
        emptied (one that has it)."""
        self.assert_ok(self.run_ws("--engine", "say"))
        self.assertTrue((self.ws / "backgrounds").is_dir())
        self.assertFalse((self.ws / "bg-stage").exists())
        (self.ws / "bg-stage").mkdir()
        (self.ws / "bg-stage" / "clip.mp4").write_bytes(b"staged clip")

        self.assert_ok(self.run_ws("--engine", "say"))

        self.assertEqual((self.ws / "bg-stage" / "clip.mp4").read_bytes(), b"staged clip")
        self.assertTrue((self.ws / "backgrounds").is_dir())

    def test_resolving_bg_link_and_real_dir_kept(self):
        """Mutation: every public/bg is removed (a link that resolves, or a real directory), or
        the check follows the link and empties its target."""
        self.assert_ok(self.run_ws("--engine", "say"))
        link = self.app / "public" / "bg"
        link.parent.mkdir(parents=True, exist_ok=True)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "keep.mp4").write_bytes(b"keep")
        for label, target in (("the relative link to the stage", "../../bg-stage"),
                              ("an absolute link elsewhere", str(elsewhere))):
            with self.subTest(label):
                link.unlink(missing_ok=True)
                link.symlink_to(target)

                self.assert_ok(self.run_ws("--engine", "say"))

                self.assertTrue(link.is_symlink(), label)
                self.assertEqual(os.readlink(link), target)
        self.assertEqual((elsewhere / "keep.mp4").read_bytes(), b"keep")
        link.unlink()
        link.mkdir()
        (link / "inside.txt").write_text("x\n", encoding="utf-8")
        self.assert_ok(self.run_ws("--engine", "say"))
        self.assertTrue(link.is_dir() and not link.is_symlink())
        self.assertEqual((link / "inside.txt").read_text(encoding="utf-8"), "x\n")


class NpmCi(WorkspaceCase):
    def test_npm_ci_runs_when_stamp_missing_then_not_again(self):
        """Mutation: npm ci runs only when a stamp exists and differs (lock change only)."""
        self.assert_ok(self.run_ws("--engine", "say"))
        second = self.run_ws("--engine", "say")
        self.assert_ok(second)
        self.assertEqual(self.calls("npm"), ["npm ci"])
        self.assertEqual(len(self.calls("remotion")), 1)
        self.assertNotIn("workspace: npm ci", second.stdout)
        lock = (self.app / "package-lock.json").read_bytes()
        stamp = (self.app / "node_modules" / ".explain-lock-sha").read_text(encoding="utf-8")
        self.assertEqual(stamp.strip(), hashlib.sha256(lock).hexdigest())

    def test_npm_ci_runs_again_when_lock_changes(self):
        """Mutation: the stamp is tested for existence only, not compared with the lock."""
        skill = self.copy_skill()
        script = skill / "scripts" / WORKSPACE_SH.name
        self.assert_ok(self.run_ws("--engine", "say", script=script))
        lock = skill / "video" / "package-lock.json"
        lock.write_text(lock.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        self.assert_ok(self.run_ws("--engine", "say", script=script))

        self.assertEqual(self.calls("npm"), ["npm ci", "npm ci"])

    def test_browser_ensure_after_npm_ci(self):
        """Mutation: the browser ensure step is dropped."""
        self.assert_ok(self.run_ws("--engine", "say"))
        lines = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            lines, ["npm ci", f"remotion browser ensure (cwd {self.app.resolve()})"]
        )

    def test_costs_printed_before_each_step(self):
        """Mutation: the npm ci cost line is printed after npm ci."""
        run = self.run_ws()
        lines = run.stdout.splitlines()

        def before(cost, marker):
            self.assertIn(cost, lines)
            self.assertIn(marker, lines)
            self.assertLess(lines.index(cost), lines.index(marker), run.stdout)

        before("workspace: npm ci (about 55 s, 503 MB)", "FAKE npm ci")
        before("workspace: browser (Chrome Headless Shell, 193 MB)", "FAKE remotion browser ensure")
        marker = next(line for line in lines if line.startswith("FAKE curl"))
        before("workspace: download kokoro-v1.0.onnx (325 MB)", marker)


class Models(WorkspaceCase):
    def test_checksum_mismatch_deletes_part_and_fails(self):
        """Mutation: the .part file is kept after a checksum mismatch."""
        run = self.run_ws("--engine", "kokoro")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        got = hashlib.sha256(WRONG_BYTES).hexdigest()
        self.assertEqual(
            run.stdout.splitlines()[-1],
            f"workspace: FAIL checksum kokoro-v1.0.onnx expected {KOKORO_SHA} got {got}",
        )
        models = self.ws / "models"
        self.assertEqual(sorted(p.name for p in models.iterdir()), [])
        self.assertEqual(len(self.calls("curl")), 1)
        self.assertIn("/model-files-v1.1/kokoro-v1.0.onnx", self.calls("curl")[0])

    def test_curl_runs_without_progress_meter(self):
        """Mutation: curl without -s (the progress meter floods the render log)."""
        self.run_ws("--engine", "kokoro")
        argv = self.calls("curl")[0].split()[1:]
        flags = "".join(a[1:] for a in argv if a.startswith("-") and not a.startswith("--"))
        for flag in "fsSL":
            self.assertIn(flag, flags, argv)

    def test_downloaded_line_after_each_model(self):
        """Mutation: no "workspace: downloaded <name>" line once a model is in place."""
        skill = self.copy_skill()
        script = skill / "scripts" / WORKSPACE_SH.name
        text = script.read_text(encoding="utf-8")
        fake_sha = hashlib.sha256(WRONG_BYTES).hexdigest()
        for sha in (KOKORO_SHA, VOICES_SHA):
            self.assertEqual(text.count(sha), 1)
            text = text.replace(sha, fake_sha)
        script.write_text(text, encoding="utf-8")

        run = self.run_ws("--engine", "kokoro", script=script)

        self.assert_ok(run)
        lines = run.stdout.splitlines()
        curls = [i for i, line in enumerate(lines) if line.startswith("FAKE curl")]
        self.assertEqual(len(curls), 2, run.stdout)
        for name, curl in zip(("kokoro-v1.0.onnx", "voices-v1.0.bin"), curls):
            done = "workspace: downloaded " + name
            self.assertEqual(lines.count(done), 1, run.stdout)
            self.assertEqual(lines.index(done), curl + 1, run.stdout)

    def test_say_engine_skips_models(self):
        """Mutation: models are fetched whatever the engine."""
        self.assert_ok(self.run_ws("--engine", "say"))
        self.assertEqual(self.calls("curl"), [])
        self.assertEqual(list((self.ws / "models").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
