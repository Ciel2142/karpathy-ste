"""Shared end-to-end render for the video rung tests (EXPLAIN_VIDEO_E2E=1 only).

render_fixture() runs scripts/render.sh --engine say once per process on a three-scene
fixture (title, bullets-appear, before-after, copied from the template with an absolute
provenance.root) in a temp output dir, against the default workspace
~/karpathy/video-workspace (set up by video-workspace.sh; never deleted here). Both
test_render and test_check_render reuse the cached result. The temp dir is removed at exit.
"""

import atexit
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
RENDER_SH = EXPLAIN / "scripts" / "render.sh"
TEMPLATE = EXPLAIN / "templates" / "video-script.json"
E2E = os.environ.get("EXPLAIN_VIDEO_E2E") == "1"
E2E_REASON = "end-to-end render: set EXPLAIN_VIDEO_E2E=1"
FIXTURE_COMPONENTS = ("title", "bullets-appear", "before-after")
RENDER_TIMEOUT = 900

_cache = {}


def fixture_script():
    """The template, cut to one scene of each fixture component, rooted at the skill dir."""
    script = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    script["provenance"]["root"] = str(EXPLAIN)
    script["scenes"] = [s for s in script["scenes"] if s["component"] in FIXTURE_COMPONENTS]
    return script


def render_fixture():
    """(output dir, CompletedProcess) of the one fixture render of this process."""
    if "result" not in _cache:
        out = Path(tempfile.mkdtemp(prefix="explain-e2e-"))
        atexit.register(shutil.rmtree, out, ignore_errors=True)
        (out / "script.json").write_text(json.dumps(fixture_script(), indent=2), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "EXPLAIN_VIDEO_WORKSPACE"}
        run = subprocess.run(
            ["/bin/bash", str(RENDER_SH), str(out), "--engine", "say"],
            capture_output=True, text=True, env=env, timeout=RENDER_TIMEOUT,
        )
        _cache["result"] = (out, run)
    return _cache["result"]
