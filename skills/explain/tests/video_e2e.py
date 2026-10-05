"""Shared helpers of the gated end-to-end renders of the video rung tests (EXPLAIN_VIDEO_E2E=1 only).

Every render of scripts/render.sh --engine say in these tests uses the workspace
$EXPLAIN_VIDEO_WORKSPACE, else the default workspace ~/karpathy/video-workspace (set up by
video-workspace.sh; never deleted here), and compiles in a run directory of its own there
(<ws>/runs/run.<pid>.<6 chars>, which render.sh removes). This module holds what they share:
E2E and E2E_REASON (the gate), the paths EXPLAIN and RENDER_SH, RENDER_TIMEOUT, workspace() (the
workspace of a test render) and render_env() (the environment of every gated render: it keeps the
caller's workspace and drops the caller's BACKGROUND_SETTINGS). The renders themselves live with
their tests: render_brainrot() of test_render_brainrot (cached for each process, and shared by
test_check_render), and the film renders of test_render_film and test_render_parallel.
"""

import os
from pathlib import Path

EXPLAIN = Path(__file__).resolve().parent.parent
RENDER_SH = EXPLAIN / "scripts" / "render.sh"
TEMPLATE = EXPLAIN / "templates" / "video-script.json"
E2E = os.environ.get("EXPLAIN_VIDEO_E2E") == "1"
E2E_REASON = "end-to-end render: set EXPLAIN_VIDEO_E2E=1"
RENDER_TIMEOUT = 900
# The caller's background settings: a test render sets its own or none.
BACKGROUND_SETTINGS = ("EXPLAIN_BRAINROT_BACKGROUNDS", "EXPLAIN_BRAINROT_SEED")


def workspace() -> Path:
    """The workspace of a test render: $EXPLAIN_VIDEO_WORKSPACE, else ~/karpathy/video-workspace.
    An empty value counts as unset, as in render.sh."""
    return Path(os.environ.get("EXPLAIN_VIDEO_WORKSPACE") or Path.home() / "karpathy" / "video-workspace")


def render_env(**extra: str) -> dict:
    """os.environ without the caller's BACKGROUND_SETTINGS, then `extra`. EXPLAIN_VIDEO_WORKSPACE
    is kept, so the render uses workspace()."""
    env = {k: v for k, v in os.environ.items() if k not in BACKGROUND_SETTINGS}
    env.update(extra)
    return env
