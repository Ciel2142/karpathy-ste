"""The onboard fixture page: templates/page.html with the sections of fixtures/onboard-page/section.html.

onboard_page(out) writes out/index.html and a copy of fixtures/onboard-page/order.mmd as out/diagrams/order.mmd,
as mermaid_page of mermaid_page.py does for a flow: the sections go before the provenance section, one nav link
for each section before the Provenance link, and the rung meta becomes "onboard"
(its anchor holds the <title> line after it, because a template comment quotes the same tag). data-root="." and
data-kind="topic" stay: the page cites the .mmd copy beside it. Each test writes the page that it checks, so the
page never drifts from the template."""

import shutil
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "onboard-page"
PAGE_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "page.html"
NAV = (("entry", "Entry"), ("flow-order", "Order"))  # (section id, nav text), in page order
MMD = "order.mmd"


def onboard_page(out: Path, section: str | None = None) -> Path:
    """Writes out/index.html and out/diagrams/order.mmd and returns the page path. `section` replaces the
    text of section.html. Each edit is on an anchor that occurs once in the template (AssertionError
    if it does not)."""
    if section is None:
        section = (FIXTURES / "section.html").read_text(encoding="utf-8")
    nav = "".join('<a href="#%s">%s</a>\n  ' % (ident, text) for ident, text in NAV)
    edits = [
        ('<section id="provenance-facet">', section.rstrip("\n") + '\n\n<section id="provenance-facet">'),
        ('<a href="#provenance-facet">Provenance</a>', nav + '<a href="#provenance-facet">Provenance</a>'),
        ('<meta name="explain-rung" content="page">\n<title>', '<meta name="explain-rung" content="onboard">\n<title>'),
    ]
    page = PAGE_TEMPLATE.read_text(encoding="utf-8")
    for anchor, text in edits:
        if page.count(anchor) != 1:
            raise AssertionError("%r occurs %d times in page.html, not once" % (anchor, page.count(anchor)))
        page = page.replace(anchor, text)
    out = Path(out)
    (out / "diagrams").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / MMD, out / "diagrams" / MMD)
    path = out / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
