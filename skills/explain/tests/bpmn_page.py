"""The BPMN fixture page: templates/page.html with the section of fixtures/bpmn-section.html.

bpmn_page(out) writes out/index.html and a copy of fixtures/two_planes.bpmn beside it, as lesson_page of
test_lesson_e2e.py does: the section goes before the provenance section, its nav link before the
Provenance link, and data-root="." stays (the page cites the .bpmn copy beside it). Each test writes the
page that it checks, so the page never drifts from the template."""

import shutil
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PAGE_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "page.html"
SECTION_ID = "stage-a"
NAV_TEXT = "Первичная проверка"


def bpmn_page(out: Path, section: str | None = None) -> Path:
    """Writes out/index.html and out/two_planes.bpmn and returns the page path. `section` replaces the
    text of bpmn-section.html. Each edit is on an anchor that occurs once in the template (AssertionError
    if it does not)."""
    if section is None:
        section = (FIXTURES / "bpmn-section.html").read_text(encoding="utf-8")
    edits = [
        ('<section id="provenance-facet">', section.rstrip("\n") + '\n\n<section id="provenance-facet">'),
        ('<a href="#provenance-facet">Provenance</a>',
         '<a href="#%s">%s</a>\n  <a href="#provenance-facet">Provenance</a>' % (SECTION_ID, NAV_TEXT)),
        ('data-root="."', 'data-root="."'),
    ]
    page = PAGE_TEMPLATE.read_text(encoding="utf-8")
    for anchor, text in edits:
        if page.count(anchor) != 1:
            raise AssertionError("%r occurs %d times in page.html, not once" % (anchor, page.count(anchor)))
        page = page.replace(anchor, text)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "two_planes.bpmn", out / "two_planes.bpmn")
    path = out / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
