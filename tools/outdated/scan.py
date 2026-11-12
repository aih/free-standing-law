#!/usr/bin/env python3
"""List candidate outdated, inapplicable or wrong provisions in one title of the Code.

Reads OLRC's USLM 1.0 for the title at a release point and writes every signal it finds in
the statutory text of the sections in force (sections with no @status). Each signal is a
candidate for a reviewer to accept or reject in the title's curated table
(tools/outdated/README.md describes the method and the categories).

Signals:

  footnote      A Code footnote in the section text ("So in original", "See References in
                Text note", "Probably should be ...").
  dead-ref      A reference in the section text to a section of the Code that is repealed,
                omitted, transferred or reserved at the release point, or that does not exist.
  rit-note      A References in Text note that says the provision referred to was repealed,
                omitted, terminated, abolished, renamed, redesignated or transferred.
  status-note   A note under the section whose heading records a change the text does not
                show: Change of Name, Transfer of Functions, Abolition, Termination,
                Termination of Reporting Requirements, Expiration.
  term          A word or phrase from the title's term list (tools/outdated/terms.tsv) found in
                the section text: a body that no longer exists, an obsolete place name, an
                obsolete term.
  date          A year earlier than the release point's, in a phrase that fixes a time limit
                ("not later than", "before", "after", "until", "fiscal year", "expire",
                "terminate", "beginning").
  dup-num       Two sibling units of the section with the same designation.

Usage:
    python3 tools/outdated/scan.py 11 [--xml-dir data/uscode/xml] [--year 2026]
            [--out analysis/outdated/candidates/t11.json]

The Code-wide index of section identifiers and their status (for dead-ref) is built from every
usc*.xml file in --xml-dir and cached in --xml-dir/.section-status.json.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]  # the repository
HERE = ROOT / "analysis/outdated"
TOOL = Path(__file__).resolve().parent
NS = "{http://xml.house.gov/schemas/uslm/1.0}"
LEVELS = {"subsection", "paragraph", "subparagraph", "clause", "subclause", "item",
          "subitem", "subsubitem"}

RIT_WORDS = re.compile(
    r"\b(was|were|has been|have been|is)\s+(?:\w+\s+){0,3}?"
    r"(repealed|omitted|terminated|abolished|renamed|redesignated|transferred|"
    r"struck out|expired|eliminated)\b", re.I)
STATUS_HEADINGS = re.compile(
    r"change of name|transfer of functions|abolition|termination|expiration|"
    r"sunset|reorganization plan|savings provision", re.I)
DATE_PHRASE = re.compile(
    r"(?:not later than|no later than|before|after|until|prior to|ending|beginning|"
    r"through|fiscal years?|expires?|terminates?|on or before|on or after|"
    r"effective)\b[^.;]{0,80}?\b(1[89]\d\d|20[0-2]\d)\b", re.I)


def text_of(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def section_index(xml_dir: Path) -> dict[str, str]:
    cache = xml_dir / ".section-status.json"
    if cache.exists():
        return json.loads(cache.read_text())
    index: dict[str, str] = {}
    for path in sorted(xml_dir.glob("usc*.xml")):
        for _, el in ET.iterparse(path, events=("end",)):
            if el.tag == NS + "section":
                ident = el.get("identifier")
                # A <section> quoted by an amending Act has no identifier. A repealed range
                # is one element: "/us/usc/t24/s32 /us/usc/t24/s33" or "/us/usc/t24/s21a...25".
                for part in (ident or "").split():
                    first, _, last = part.partition("...")
                    status = el.get("status") or ""
                    index.setdefault(first, status)
                    if last:
                        index.setdefault(first.rsplit("/s", 1)[0] + "/s" + last, status)
                        index.setdefault("range:" + first, status + "|" + last)
                el.clear()
    cache.write_text(json.dumps(index))
    return index


def load_terms(path: Path) -> list[tuple[re.Pattern, str, str]]:
    out = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"):
            out.append((re.compile(row["pattern"], re.I), row["label"], row["reason"]))
    return out


def section_of(href: str) -> str | None:
    m = re.match(r"(/us/usc/t[0-9a-zA-Z]+/s[^/]+)", href)
    return m.group(1) if m else None


def strip_notes(sec):
    """A copy of the section without notes, source credit or quoted content."""
    import copy
    body = copy.deepcopy(sec)
    for parent in body.iter():
        for child in list(parent):
            if child.tag in (NS + "notes", NS + "sourceCredit"):
                parent.remove(child)
    return body


def unit_path(sec) -> dict:
    """Map each element of the section body to the identifier of its nearest level."""
    out = {}

    def walk(el, current):
        ident = el.get("identifier") if el.tag[len(NS):] in LEVELS or el.tag == NS + "section" else None
        cur = ident or current
        out[el] = cur
        for c in el:
            walk(c, cur)
    walk(sec, sec.get("identifier"))
    return out


def scan(title: str, xml_dir: Path, year: int, terms) -> dict:
    fname = xml_dir / f"usc{title.zfill(2) if title.isdigit() else title}.xml"
    index = section_index(xml_dir)
    tree = ET.parse(fname)
    root = tree.getroot()
    signals = []
    sections = 0
    for sec in root.iter(NS + "section"):
        ident = sec.get("identifier")
        if not ident or sec.get("status"):
            continue
        sections += 1
        heading = text_of(sec.find(NS + "heading")) if sec.find(NS + "heading") is not None else ""
        num = sec.find(NS + "num").get("value") if sec.find(NS + "num") is not None else ""
        body = strip_notes(sec)
        units = unit_path(body)

        def add(kind, unit, detail, **extra):
            signals.append({"section": ident, "num": num, "heading": heading, "kind": kind,
                            "unit": unit, "detail": detail, **extra})

        # footnotes, with the words before the footnote mark
        for parent in body.iter():
            for el in parent:
                if el.tag == NS + "note" and el.get("type") == "footnote":
                    add("footnote", units.get(el, ident), text_of(el),
                        context=before_footnote(parent, el))
        # references in the text
        for el in body.iter(NS + "ref"):
            href = el.get("href") or ""
            target = section_of(href)
            if not target or el.get("class") == "footnoteRef":
                continue
            status = index.get(target)
            if status is None:
                add("dead-ref", units.get(el, ident), f"{text_of(el)} -> {href}: no section with this identifier at the release point (it may lie inside a range of repealed sections)", target=target)
            elif status:
                add("dead-ref", units.get(el, ident), f"{text_of(el)} -> {href}: {status}", target=target, status=status)
        # terms and dates in the text
        for el in body.iter():
            if el.tag not in (NS + "p", NS + "content", NS + "chapeau", NS + "continuation", NS + "heading"):
                continue
            # A <content> holding <p> elements is read through them; otherwise read it whole.
            if el.tag == NS + "content" and el.find(NS + "p") is not None:
                own = (el.text or "").strip()
            else:
                own = text_of(el)
            if not own:
                continue
            for pat, label, reason in terms:
                for m in pat.finditer(own):
                    add("term", units.get(el, ident), f"{label}: “{context(own, m)}”", reason=reason)
            for m in DATE_PHRASE.finditer(own):
                if int(m.group(1)) < year:
                    add("date", units.get(el, ident), f"“{context(own, m)}”")
        # duplicate designations among siblings
        for parent in body.iter():
            nums = collections.Counter(
                (c.tag, c.find(NS + "num").get("value"))
                for c in parent if c.tag[len(NS):] in LEVELS and c.find(NS + "num") is not None)
            for (tag, value), n in nums.items():
                if n > 1 and value:
                    add("dup-num", parent.get("identifier") or ident, f"{n} {tag[len(NS):]}s numbered ({value})")
        # notes under the section
        notes = sec.find(NS + "notes")
        if notes is not None:
            for note in notes.findall(NS + "note"):
                h = note.find(NS + "heading")
                htext = text_of(h) if h is not None else ""
                body_text = text_of(note)
                if note.get("topic") == "referencesInText":
                    for p in note.findall(NS + "p"):
                        t = text_of(p)
                        if RIT_WORDS.search(t):
                            add("rit-note", ident, t)
                elif htext and STATUS_HEADINGS.search(htext) and note.get("role") != "crossHeading":
                    add("status-note", ident, f"{htext}: {body_text[len(htext):].strip()[:600]}")
    counts = collections.Counter(s["kind"] for s in signals)
    return {
        "title": title,
        "source": str(fname.relative_to(ROOT)) if fname.is_relative_to(ROOT) else str(fname),
        "year": year,
        "sections_in_force": sections,
        "sections_with_signals": len({s["section"] for s in signals}),
        "counts": dict(sorted(counts.items())),
        "signals": signals,
    }


def before_footnote(parent, note, width: int = 90) -> str:
    """The text of `parent` up to `note`, without footnote marks or other footnotes."""
    parts = []

    def walk(el):
        if el is note:
            raise StopIteration
        if el.tag == NS + "note" and el.get("type") == "footnote":
            parts.append(el.tail or "")
            return
        if el.get("class") == "footnoteRef":
            parts.append(el.tail or "")
            return
        parts.append(el.text or "")
        for c in el:
            walk(c)
        if el is not parent:
            parts.append(el.tail or "")
    try:
        walk(parent)
    except StopIteration:
        pass
    text = re.sub(r"\s+", " ", "".join(parts)).strip()
    return ("…" if len(text) > width else "") + text[-width:]


def context(text: str, m: re.Match, width: int = 70) -> str:
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("title")
    ap.add_argument("--xml-dir", default=str(ROOT / "data/uscode/xml"))
    ap.add_argument("--year", type=int, default=2026, help="the release point's year")
    ap.add_argument("--terms", default=str(TOOL / "terms.tsv"))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    result = scan(a.title, Path(a.xml_dir), a.year, load_terms(Path(a.terms)))
    out = Path(a.out) if a.out else HERE / f"candidates/t{a.title}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"title {a.title}: {result['sections_in_force']} sections in force, "
          f"{result['sections_with_signals']} with signals, {result['counts']} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
