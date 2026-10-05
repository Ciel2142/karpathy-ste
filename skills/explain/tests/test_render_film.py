"""Film cases of scripts/render.sh. FilmFunctionCase runs single functions of the script
(stage_render, clear_stale) in a temporary directory, through render_functions of test_render.py,
with a fake remotion CLI and no workspace: the composition each format renders, and the files a
new run removes. Each test names the mutation that turns it red."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_render import render_functions


def run_functions(tmp: Path, names: list, setup: str) -> subprocess.CompletedProcess:
    """Run the named functions of render.sh in /bin/bash with cwd `tmp`: `set -eu`, the text of
    the functions (render_functions), then the shell text `setup`."""
    script = "set -eu\n" + render_functions(names) + setup
    return subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True,
                          cwd=tmp, timeout=60)


class FilmFunctionCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="render-film-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.out = self.tmp / "out"
        (self.out / "build").mkdir(parents=True)

    def fake_remotion(self, calls):
        """An executable that appends its arguments to `calls` as one JSON list per line."""
        remotion = self.tmp / "remotion"
        remotion.write_text(
            "#!/bin/bash\n"
            "exec python3 -c 'import json, sys\n"
            "with open(sys.argv[1], \"a\") as log:\n"
            "    log.write(json.dumps(sys.argv[2:]) + \"\\n\")' %s \"$@\"\n" % calls,
            encoding="utf-8")
        remotion.chmod(0o755)
        return remotion

    # red: the composition is the literal Explain (the film case), or Film for every format
    # (the explainer and brainrot cases)
    def test_a_film_renders_composition_film(self):
        (self.out / "audio").mkdir()
        (self.out / "audio" / "s1.say.wav").write_bytes(b"clip")
        (self.out / "build" / "timeline.json").write_text(
            json.dumps({"scenes": [{"audio": "audio/s1.say.wav"}]}), encoding="utf-8")
        calls = self.tmp / "calls.json"
        remotion = self.fake_remotion(calls)
        for fmt, composition in (("film", "Film"), ("explainer", "Explain"),
                                 ("brainrot", "Explain")):
            with self.subTest(fmt=fmt):
                calls.unlink(missing_ok=True)
                run = run_functions(
                    self.tmp, ["fail", "now", "stage_render"],
                    "RATIO_LIMIT=2.0 video_s=3.000 out=%s run=%s/run remotion=%s fmt=%s\n"
                    "stage_render\n" % (self.out, self.tmp, remotion, fmt))
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                lines = [line for line in run.stdout.splitlines() if line.startswith("render (")]
                self.assertEqual(len(lines), 1, run.stdout)
                self.assertTrue(lines[0].endswith(": ok"), lines)
                self.assertEqual(
                    [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()],
                    [["render", composition, "%s/video.mp4" % self.out, "--props",
                      "%s/build/timeline.json" % self.out]])

    # red: guard.mp4 is left (the base), or all of build/ goes (timeline.json with it), or
    # review/ itself goes
    def test_stale_guard_video_is_removed(self):
        (self.out / "video.mp4").write_bytes(b"old video")
        (self.out / "review").mkdir()
        (self.out / "review" / "still-01-intro.png").write_bytes(b"old still")
        (self.out / "build" / "guard.mp4").write_bytes(b"old guard video")
        (self.out / "build" / "timeline.json").write_text("{}", encoding="utf-8")
        run = run_functions(self.tmp, ["clear_stale"], "out=%s\nclear_stale\n" % self.out)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse((self.out / "video.mp4").exists())
        self.assertFalse((self.out / "build" / "guard.mp4").exists())
        self.assertTrue((self.out / "review").is_dir())
        self.assertEqual(list((self.out / "review").iterdir()), [])
        self.assertTrue((self.out / "build" / "timeline.json").exists())


if __name__ == "__main__":
    unittest.main()
