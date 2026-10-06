"""Tests for the clip format of video/build-timeline.mjs: the formats.json row and the script check
(--check). A clip is a film with its own row (60 s, 12 source lines). Each test names the mutation
that turns it red."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_video_timeline import VideoCase
from test_video_timeline_film import FILM_ROW, FORMATS, film_script

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
