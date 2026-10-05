"""Tests for the scene box values and the diagram geometry. They run the real .ts modules through
Node (which strips the types), so the numbers checked here are the numbers the scenes draw with.
Always on; skipped only when `node` is missing. Each test names the mutation that turns it red."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "video" / "src"
BOX_URL = (SRC / "box.ts").as_uri()
GEOMETRY_URL = (SRC / "scenes" / "diagramGeometry.ts").as_uri()

NODE = shutil.which("node")
NO_NODE_REASON = "node is not on PATH"

EPS = 1e-9


def run_node(script):
    """Run `script` (ES module source) in Node and return what it prints as parsed JSON."""
    done = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=60,
    )
    if done.returncode != 0:
        raise AssertionError("node exited %d: %s" % (done.returncode, done.stderr.strip()))
    return json.loads(done.stdout)


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestSceneBox(unittest.TestCase):
    def test_brainrot_content_rect(self):
        """Red: BRAINROT_BOX has another margin, titleBand or size, or contentRect changes."""
        got = run_node(
            'import { BRAINROT_BOX, contentRect } from "%s";'
            "console.log(JSON.stringify(contentRect(BRAINROT_BOX)));" % BOX_URL
        )
        self.assertEqual(got, {"left": 48, "top": 154, "width": 984, "height": 758})

    def test_brainrot_box_values(self):
        """Red: any brainrot size or type value drifts from the spec 4.2 table."""
        got = run_node(
            'import { BRAINROT_BOX } from "%s";'
            "console.log(JSON.stringify(BRAINROT_BOX));" % BOX_URL
        )
        self.assertEqual(got, {
            "width": 1080, "height": 960, "margin": 48, "titleSize": 56, "titleBand": 76,
            "stackPanels": True,
            "type": {
                "heroTitle": 72, "heroSubtitle": 44, "bullet": 44, "code": 34, "codeLine": 48,
                "node": {"width": 280, "height": 112}, "nodeLabel": 32, "nodeSub": 24,
                "edgeLabel": 26, "panelHeading": 38, "panelLine": 32,
            },
        })

    def test_brainrot_code_fits_forty_columns(self):
        """Red: the code font or line height grows so 40 columns or 14 lines overflow the box.
        A 3-digit gutter plus 40 columns is 45ch + 16 px at a 0.61 em advance."""
        got = run_node(
            'import { BRAINROT_BOX, contentRect } from "%s";'
            "const c = contentRect(BRAINROT_BOX);"
            "console.log(JSON.stringify({ code: BRAINROT_BOX.type.code,"
            " codeLine: BRAINROT_BOX.type.codeLine, width: c.width, height: c.height }));" % BOX_URL
        )
        self.assertLessEqual(45 * 0.61 * got["code"] + 16, got["width"])
        self.assertLessEqual(14 * got["codeLine"], got["height"])

    def test_box_exports_the_brainrot_box_only(self):
        """Red: a second box (any other SceneBox value) is left in box.ts, or BRAINROT_BOX,
        codeLineLimit or contentRect stops being exported."""
        got = run_node(
            'import * as box from "%s";'
            "console.log(JSON.stringify(Object.keys(box).sort()));" % BOX_URL
        )
        self.assertEqual(got, ["BRAINROT_BOX", "codeLineLimit", "contentRect"])

    def test_code_line_limit_of_the_brainrot_box(self):
        """Red: codeLineLimit (the number of code lines CodeHighlights slices to) is not 15 for
        BRAINROT_BOX (floor(758 / 48)). Guards the helper's value, not that CodeHighlights calls
        it."""
        got = run_node(
            'import { BRAINROT_BOX, codeLineLimit } from "%s";'
            "console.log(JSON.stringify(codeLineLimit(BRAINROT_BOX)));" % BOX_URL
        )
        self.assertEqual(got, 15)


@unittest.skipIf(NODE is None, NO_NODE_REASON)
class TestPortraitDiagramGeometry(unittest.TestCase):
    """The 3x3 diagram grid in the brainrot content box (984 x 758), with its 280 x 112 nodes.
    The content size and node size come from BRAINROT_BOX in the Node script; the expected
    numbers below are literals that pin the spec values."""

    def run_geometry(self, body):
        return run_node(
            'import { BRAINROT_BOX, contentRect } from "%s";'
            'import { cellCentre, segment, EDGE_GAP } from "%s";'
            "const { width, height } = contentRect(BRAINROT_BOX);"
            "const content = { width, height };"
            "const node = BRAINROT_BOX.type.node;"
            "%s" % (BOX_URL, GEOMETRY_URL, body)
        )

    def test_portrait_cell_centres(self):
        """Red: GRID or cellCentre changes, or a node box grows so neighbouring cells overlap."""
        got = self.run_geometry(
            "console.log(JSON.stringify({ a1: cellCentre('a1', content),"
            " c3: cellCentre('c3', content), b2: cellCentre('b2', content),"
            " node }));"
        )
        self.assertAlmostEqual(got["a1"]["x"], 164, delta=EPS)
        self.assertAlmostEqual(got["a1"]["y"], 126.33333333333333, delta=EPS)
        self.assertAlmostEqual(got["c3"]["x"], 820, delta=EPS)
        self.assertAlmostEqual(got["c3"]["y"], 631.6666666666666, delta=EPS)
        # Pairs in neighbouring cells keep at least a 48 px gap between their node boxes.
        gap_x = got["b2"]["x"] - got["a1"]["x"]
        self.assertGreaterEqual(gap_x, got["node"]["width"] + 48 - EPS)
        self.assertGreaterEqual(got["c3"]["x"] - got["b2"]["x"], got["node"]["width"] + 48 - EPS)

    def test_portrait_segment_ends_outside_nodes(self):
        """Red: borderPoint drops EDGE_GAP or uses the wrong half size, so a line end lies inside
        a node box or off the centre line."""
        got = self.run_geometry(
            "const a = cellCentre('a1', content), b = cellCentre('b2', content);"
            "const [p0, p1] = segment(a, b, node);"
            "console.log(JSON.stringify({ a, b, p0, p1, gap: EDGE_GAP, node }));"
        )
        a, b, p0, p1 = got["a"], got["b"], got["p0"], got["p1"]
        half_w = got["node"]["width"] / 2 + got["gap"]
        half_h = got["node"]["height"] / 2 + got["gap"]

        def outside(p, centre):
            """On or beyond the node box grown by EDGE_GAP."""
            return (abs(p["x"] - centre["x"]) >= half_w - EPS
                    or abs(p["y"] - centre["y"]) >= half_h - EPS)

        self.assertTrue(outside(p0, a), "start %r is inside the box of a1" % p0)
        self.assertTrue(outside(p1, b), "end %r is inside the box of b2" % p1)

        def on_centre_line(p):
            cross = (b["x"] - a["x"]) * (p["y"] - a["y"]) - (b["y"] - a["y"]) * (p["x"] - a["x"])
            return abs(cross) < 1e-6

        self.assertTrue(on_centre_line(p0), "start %r is off the centre line" % p0)
        self.assertTrue(on_centre_line(p1), "end %r is off the centre line" % p1)
        # The visible line runs from a towards b: start nearer a, end nearer b, and not crossed.
        self.assertLess(p0["x"], p1["x"])
        self.assertGreater(p0["x"], a["x"])
        self.assertLess(p1["x"], b["x"])


if __name__ == "__main__":
    unittest.main()
