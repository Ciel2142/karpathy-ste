"""Tests for the clip format of video/build-timeline.mjs: the formats.json row, the script check
(--check), build mode and --types. A clip is a film with its own row (60 s, 12 source lines, a text
floor of 19 px). Each test names the mutation that turns it red."""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import VideoCase
from test_video_timeline_film import FILM_ROW, FORMATS, FilmBuildCase, film_script, tool_with_formats, types_text

FORMAT_LINE = "FAIL script: format must be film, brainrot or clip"
CLIP_ROW = dict(FILM_ROW, maxTotalSeconds=60, sourceLines=12, minText=19)


def clip_script():
    """A valid three-scene clip script: film_script() with the format "clip"."""
    return dict(film_script(), format="clip")


class TestClipCheck(VideoCase):
    def test_clip_fixture_passes(self):
        """Red: `clip` is not a known format (the check prints the format line), or the clip check
        is stricter than its own fixture."""
        result = self.check(clip_script())
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_clip_row_values(self):
        """Red: a value of the clip row of formats.json changed, or the row is missing."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        self.assertEqual(rows["clip"], CLIP_ROW)

    def test_clip_source_lines(self):
        """Red: --check reads the film row for a clip (sourceLines 20: 13 lines pass), or the line
        loses the clip tag, or the range is exclusive at 12 lines."""
        script = clip_script()
        script["sources"][0].update({"from": 3, "to": 14})
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        script["sources"][0]["to"] = 15
        self.assertFails(self.check(script), "FAIL source app: range 3-15 is 13 lines (max 12, clip)")

    def test_clip_scene_count(self):
        """Red: the count line of a clip carries the film tag (`tagOf` gives ", film" for a clip),
        or the range is exclusive at an end (30 scenes fail), or a clip has no scene range."""
        script = clip_script()
        first = script["scenes"][0]
        script["scenes"] = script["scenes"][:2]
        self.assertFails(self.check(script), "FAIL script: 2 scenes (needs 3 to 30, clip)")
        script["scenes"] = [dict(first, id="s%d" % n) for n in range(1, 31)]
        result = self.check(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        script["scenes"] = [dict(first, id="s%d" % n) for n in range(1, 32)]
        self.assertFails(self.check(script), "FAIL script: 31 scenes (needs 3 to 30, clip)")

    def test_another_format_names_three_formats(self):
        """Red: the format line still names two formats (the clip is left out of it), or an unknown
        format is accepted."""
        script = clip_script()
        script["format"] = "other"
        self.assertFails(self.check(script), FORMAT_LINE)


class TestClipBuild(FilmBuildCase):
    FILM_KEYS = [
        "format", "fps", "width", "height", "totalFrames", "maxSceneSeconds", "maxTotalSeconds",
        "engine", "sources", "checkFrames", "scenes",
    ]

    def built(self, script):
        """The timeline of a build that must succeed."""
        result, timeline = self.build_film(script)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        return timeline

    def test_clip_top_level_values(self):
        """Red: build mode builds a clip as brainrot (the canvas and keys of that row), keeps the
        film's total of 150 s for a clip, writes another format name, or leaves `minText` out of
        the timeline or gives it another value than 19."""
        timeline = self.built(clip_script())
        self.assertEqual(
            (timeline["format"], timeline["width"], timeline["height"]), ("clip", 1280, 720)
        )
        self.assertEqual(
            (timeline["maxSceneSeconds"], timeline["maxTotalSeconds"], timeline["minText"]), (30, 60, 19)
        )
        self.assertEqual(sorted(timeline), sorted(self.FILM_KEYS + ["minText"]))

    def test_clip_builds_the_film_scenes(self):
        """Red: a clip is built by another path than a film's (its scenes lack sources or
        checkFrames, or its lead and pause frames come from another row), so the scenes, the
        sources, the check frames or the total differ from the same script built as a film."""
        clip = self.built(clip_script())
        film = self.built(film_script())
        for timeline in (clip, film):
            for key in ("format", "maxTotalSeconds", "minText"):
                del timeline[key]
        self.assertEqual(clip, film)

    def test_film_timeline_carries_min_text_14(self):
        """Red: only a clip carries `minText`, or a film gets the clip value."""
        self.assertEqual(self.built(film_script())["minText"], 14)

    def test_min_text_comes_from_the_row(self):
        """Red: build mode writes a fixed `minText` per format and not the value of the row (a copy
        of the tool beside a formats.json whose clip row has 21 writes 19)."""
        rows = json.loads(FORMATS.read_text(encoding="utf-8"))
        rows["clip"]["minText"] = 21
        tool = tool_with_formats(self.dir, rows)
        script = clip_script()
        clips = self.write_film_words(script)
        script_path = self.write_json("script.json", script)
        durations = self.write_json("durations.json", {"engine": "say", "fallback": None, "scenes": clips})
        out = os.path.join(self.dir, "out", "timeline.json")
        result = subprocess.run(
            ["node", str(tool), script_path, durations, "say", out, "--root", self.dir],
            capture_output=True,
            text=True,
            cwd=self.dir,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        with open(out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["minText"], 21)


class TestClipTypes(VideoCase):
    def test_types_takes_a_clip_script(self):
        """Red: --types refuses a clip (`--types needs a film script`), or writes other names for
        it than for a film script."""
        path = self.write_json("script.json", clip_script())
        out = os.path.join(self.dir, "out", "script.gen.ts")
        result = self.node("--types", path, out)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        with open(out, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), types_text('"type" | "forms" | "ends"', '"app"'))
