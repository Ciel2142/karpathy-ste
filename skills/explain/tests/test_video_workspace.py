"""Tests for scripts/video-workspace.sh: the Remotion workspace outside the repo. The real
cmp, cp, mv and shasum run on the real video/ package files (cp through a wrapper that logs
its arguments to FAKE_CP_LOG first); npm, curl and the remotion binary that npm installs are
fakes that log their arguments, so no registry, Chrome or model download is needed. Each
test names the mutation that turns it red."""

import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
WORKSPACE_SH = EXPLAIN / "scripts" / "video-workspace.sh"
KOKORO_SHA = "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"
VOICES_SHA = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
SILERO_SHA = "f036d3da1584899e5e24bdf2d5bd3bcf896e2d62505de39a02caca76014d7a1c"
SILERO_URL = "https://models.silero.ai/models/tts/ru/v5_3_ru.pt"
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
# curl for the two-fetch test: writes half of WRONG_BYTES to <file>, marks that it has started
# in the FAKE_BARRIER directory, waits (10 s at most) until a second curl has marked too, then
# writes the rest. Two fetches that share one part file mix the halves; one part file each
# gives both the whole bytes.
FAKE_CURL_BARRIER = r"""#!/bin/sh
echo "curl $*" >> "$FAKE_LOG"
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'not a ' > "$out"
: > "$FAKE_BARRIER/started.$$"
tries=0
while :; do
  set -- "$FAKE_BARRIER"/started.*
  [ $# -ge 2 ] && break
  tries=$((tries + 1))
  [ "$tries" -le 200 ] || exit 1
  sleep 0.05
done
printf 'model\n' >> "$out"
"""
# curl for the stop test: writes half of WRONG_BYTES to <file>, then hangs.
FAKE_CURL_STALL = r"""#!/bin/sh
echo "curl $*" >> "$FAKE_LOG"
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'not a ' > "$out"
sleep 30
"""
# cp: appends its arguments to FAKE_CP_LOG, one call a line, tab-separated, then runs the
# real /bin/cp with them. Its own log, so FAKE_LOG keeps only npm, curl and remotion.
CP_WRAPPER = r"""#!/bin/sh
(IFS=$(printf '\t'); printf '%s\n' "$*") >> "$FAKE_CP_LOG"
exec /bin/cp "$@"
"""


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="video-ws-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.ws = self.tmp / "ws"
        self.app = self.ws / "app"
        self.log = self.tmp / "fake.log"
        self.cp_log = self.tmp / "cp.log"
        self.out = self.tmp / "stdout.txt"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        for name, body in (("npm", FAKE_NPM), ("curl", FAKE_CURL), ("cp", CP_WRAPPER)):
            path = bin_dir / name
            path.write_text(body, encoding="utf-8")
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
        self.env = dict(
            os.environ,
            PATH=f"{bin_dir}:{os.environ['PATH']}",
            EXPLAIN_VIDEO_WORKSPACE=str(self.ws),
            FAKE_LOG=str(self.log),
            FAKE_STDOUT=str(self.out),
            FAKE_CP_LOG=str(self.cp_log),
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

    def pinned_script(self, *shas):
        """A copy of the script with each pinned sha256 replaced by the sha of WRONG_BYTES, so
        the fake curl's file is a match."""
        skill = self.copy_skill()
        script = skill / "scripts" / WORKSPACE_SH.name
        text = script.read_text(encoding="utf-8")
        for sha in shas:
            self.assertEqual(text.count(sha), 1)
            text = text.replace(sha, hashlib.sha256(WRONG_BYTES).hexdigest())
        script.write_text(text, encoding="utf-8")
        return script

    def install_curl(self, body):
        """Put another fake curl in front of the default one."""
        path = self.tmp / "bin" / "curl"
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)


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
        left behind in the app, or the old file is removed and the new one copied onto its
        final name (a new inode too, but a reader can see a half-written file)."""
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
        # every copy into the app (both runs) goes to another name than the final one
        finals = {str(self.app / name) for name in ("package.json", "package-lock.json")}
        copies = self.cp_log.read_text(encoding="utf-8").splitlines()
        self.assertTrue(copies, "the cp wrapper logged no call")
        self.assertEqual([call for call in copies if call.split("\t")[-1] in finals], [])

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

    def test_silero_cost_line_url_and_part_file(self):
        """Mutation: no cost line for the Silero file, the Kokoro base is kept for its URL,
        or the download goes to the shared <name>.part."""
        run = self.run_ws("--engine", "silero")

        curls = self.calls("curl")
        self.assertEqual(len(curls), 1, run.stdout + run.stderr)
        lines = run.stdout.splitlines()
        cost = "workspace: download v5_3_ru.pt (145 MB)"
        self.assertEqual(lines.count(cost), 1, run.stdout)
        marker = next(line for line in lines if line.startswith("FAKE curl"))
        self.assertLess(lines.index(cost), lines.index(marker), run.stdout)
        argv = curls[0].split()[1:]
        self.assertEqual(argv[-1], SILERO_URL)
        self.assertRegex(
            argv[argv.index("-o") + 1],
            "^" + re.escape(f"{self.ws}/models/v5_3_ru.pt.") + r"\d+\.part$",
        )

    def test_silero_checksum_mismatch_deletes_part_and_fails(self):
        """Mutation: the Silero file is moved into place without the check, or the .part file
        is kept after the mismatch."""
        run = self.run_ws("--engine", "silero")

        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        got = hashlib.sha256(WRONG_BYTES).hexdigest()
        self.assertEqual(
            run.stdout.splitlines()[-1],
            f"workspace: FAIL checksum v5_3_ru.pt expected {SILERO_SHA} got {got}",
        )
        self.assertNotIn("workspace: downloaded", run.stdout)
        self.assertEqual(sorted(p.name for p in (self.ws / "models").iterdir()), [])

    def test_silero_downloaded_line(self):
        """Mutation: no "workspace: downloaded v5_3_ru.pt" line once the file is in place, or
        it comes before the check."""
        script = self.pinned_script(SILERO_SHA)

        run = self.run_ws("--engine", "silero", script=script)

        self.assert_ok(run)
        lines = run.stdout.splitlines()
        curl = next(i for i, line in enumerate(lines) if line.startswith("FAKE curl"))
        done = "workspace: downloaded v5_3_ru.pt"
        self.assertEqual(lines.count(done), 1, run.stdout)
        self.assertEqual(lines.index(done), curl + 1, run.stdout)
        self.assertEqual((self.ws / "models" / "v5_3_ru.pt").read_bytes(), WRONG_BYTES)

    def test_silero_in_place_mismatch_is_fetched_again(self):
        """Mutation: a Silero file in place is left alone whatever its bytes (every Russian
        run then falls back), or the old bytes are kept after the fetch."""
        script = self.pinned_script(SILERO_SHA)
        (self.ws / "models").mkdir(parents=True)
        (self.ws / "models" / "v5_3_ru.pt").write_bytes(b"a bad file\n")

        run = self.run_ws("--engine", "silero", script=script)

        self.assert_ok(run)
        self.assertEqual(len(self.calls("curl")), 1)
        self.assertEqual((self.ws / "models" / "v5_3_ru.pt").read_bytes(), WRONG_BYTES)

    def test_silero_in_place_match_is_not_fetched(self):
        """Mutation: a Silero file in place is fetched again on every run (no hash check)."""
        script = self.pinned_script(SILERO_SHA)
        (self.ws / "models").mkdir(parents=True)
        (self.ws / "models" / "v5_3_ru.pt").write_bytes(WRONG_BYTES)

        run = self.run_ws("--engine", "silero", script=script)

        self.assert_ok(run)
        self.assertEqual(self.calls("curl"), [])
        self.assertNotIn("workspace: download", run.stdout)

    def test_kokoro_in_place_is_left_alone(self):
        """Mutation: the Kokoro file in place is hashed and fetched again too (recheck for
        every engine)."""
        (self.ws / "models").mkdir(parents=True)
        (self.ws / "models" / "kokoro-v1.0.onnx").write_bytes(b"any bytes\n")

        run = self.run_ws("--engine", "kokoro")

        self.assertEqual(
            [call.split()[-1].rsplit("/", 1)[-1] for call in self.calls("curl")],
            ["voices-v1.0.bin"], run.stdout + run.stderr,
        )
        self.assertNotIn("workspace: download kokoro-v1.0.onnx", run.stdout)
        self.assertEqual(
            (self.ws / "models" / "kokoro-v1.0.onnx").read_bytes(), b"any bytes\n"
        )

    def test_kokoro_fetch_has_its_own_part_file(self):
        """Mutation: the Kokoro download goes to the shared <name>.part."""
        self.run_ws("--engine", "kokoro")

        argv = self.calls("curl")[0].split()[1:]
        self.assertRegex(
            argv[argv.index("-o") + 1],
            "^" + re.escape(f"{self.ws}/models/kokoro-v1.0.onnx.") + r"\d+\.part$",
        )
        self.assertTrue(argv[-1].endswith("/model-files-v1.1/kokoro-v1.0.onnx"), argv)

    def test_say_engine_skips_models(self):
        """Mutation: models are fetched whatever the engine."""
        self.assert_ok(self.run_ws("--engine", "say"))
        self.assertEqual(self.calls("curl"), [])
        self.assertEqual(list((self.ws / "models").iterdir()), [])


class ConcurrentFetches(WorkspaceCase):
    def kill_group(self, proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass

    def test_two_fetches_at_once_both_succeed(self):
        """Mutation: both fetches write the shared <name>.part (the halves mix, or the first
        mv takes the file from under the second)."""
        script = self.pinned_script(SILERO_SHA)
        self.assert_ok(self.run_ws("--engine", "say", script=script))
        barrier = self.tmp / "barrier"
        barrier.mkdir()
        self.install_curl(FAKE_CURL_BARRIER)
        env = dict(self.env, FAKE_BARRIER=str(barrier))
        outs = [self.tmp / "run-a.txt", self.tmp / "run-b.txt"]
        procs = []
        for out in outs:
            with open(out, "wb") as stdout:
                procs.append(subprocess.Popen(
                    ["/bin/bash", str(script), "--engine", "silero"],
                    stdout=stdout, stderr=subprocess.STDOUT, env=env, start_new_session=True,
                ))
            self.addCleanup(self.kill_group, procs[-1])
        codes = [proc.wait(timeout=60) for proc in procs]

        shown = "\n".join(out.read_text(encoding="utf-8") for out in outs)
        self.assertEqual(codes, [0, 0], shown)
        for out in outs:
            self.assertEqual(
                out.read_text(encoding="utf-8").splitlines()[-1], f"workspace: ok {self.ws}"
            )
        self.assertEqual(len(self.calls("curl")), 2, "the fetches did not overlap")
        self.assertEqual([p.name for p in (self.ws / "models").iterdir()], ["v5_3_ru.pt"])
        self.assertEqual((self.ws / "models" / "v5_3_ru.pt").read_bytes(), WRONG_BYTES)

    def test_a_stopped_fetch_leaves_no_part(self):
        """Mutation: no trap removes the part file (a TERM to the process group leaves it), or
        only EXIT is trapped, so the TERM ends the shell before it can clean up."""
        self.install_curl(FAKE_CURL_STALL)
        models = self.ws / "models"
        with open(self.out, "wb") as stdout:
            proc = subprocess.Popen(
                ["/bin/bash", str(WORKSPACE_SH), "--engine", "silero"],
                stdout=stdout, stderr=subprocess.STDOUT, env=self.env, start_new_session=True,
            )
        self.addCleanup(self.kill_group, proc)
        deadline = time.monotonic() + 20
        while not any(part.stat().st_size > 0 for part in models.glob("*.part")):
            self.assertIsNone(proc.poll(), self.out.read_text(encoding="utf-8"))
            self.assertLess(time.monotonic(), deadline, "the fake curl wrote no part")
            time.sleep(0.05)

        os.killpg(proc.pid, signal.SIGTERM)
        code = proc.wait(timeout=20)

        self.assertEqual(code, 1, self.out.read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in models.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
