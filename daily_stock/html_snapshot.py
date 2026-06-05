"""Deterministic HTML structure fingerprints for layout regression tests."""

from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
import json
import re


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skeleton: list[tuple] = []
        self.tags: Counter[str] = Counter()
        self.classes: Counter[str] = Counter()
        self.in_style = False
        self.style_parts: list[str] = []
        self.heading: list[str] | None = None
        self.headings: list[list[str]] = []

    def handle_decl(self, decl: str) -> None:
        self.skeleton.append(("decl", decl.lower()))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        classes = tuple(sorted((attrs_by_name.get("class") or "").split()))
        self.tags[tag] += 1
        self.classes.update(classes)
        self.skeleton.append(("start", tag, classes, "id" in attrs_by_name))
        if tag == "style":
            self.in_style = True
        if tag in ("h1", "h2"):
            self.heading = [tag, ""]

    def handle_endtag(self, tag: str) -> None:
        self.skeleton.append(("end", tag))
        if tag == "style":
            self.in_style = False
        if self.heading and tag == self.heading[0]:
            self.headings.append(self.heading)
            self.heading = None

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.style_parts.append(data)
        if self.heading:
            self.heading[1] += data.strip()


def build_html_structure_snapshot(content: str) -> dict:
    """Return a stable snapshot of layout-relevant HTML structure and CSS."""
    parser = _StructureParser()
    parser.feed(content)
    skeleton_json = json.dumps(
        parser.skeleton,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    normalized_css = re.sub(r"\s+", " ", "".join(parser.style_parts)).strip()
    return {
        "page_count": parser.classes["page"],
        "headings": parser.headings,
        "tag_counts": dict(sorted(parser.tags.items())),
        "class_counts": dict(sorted(parser.classes.items())),
        "skeleton_sha256": sha256(skeleton_json.encode("utf-8")).hexdigest(),
        "css_sha256": sha256(normalized_css.encode("utf-8")).hexdigest(),
    }
