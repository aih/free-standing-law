"""One pass over every title of the Code at a release point: where each provision of law is.

- `credits[(law, div, sec)]`: the Code sections whose source credit names the provision (the
  provision's text, or its amendment, is in that section);
- `notes`: every statutory note that sets out a provision of law ("… provided that:"), with
  the provisions it sets out, where it sits, its heading and OLRC's `topic`.

Read from `data/uscode/xml/usc*.xml` (`python3 -m tools.uncodified fetch-code`). Sections inside `quotedContent`
are quoted amending text and are skipped (gotcha 6).
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from lxml import etree

from .citations import key_of, parse_credit, parse_note_citation, squash

U = "{http://xml.house.gov/schemas/uslm/1.0}"
ROOT = Path(__file__).resolve().parents[2]
XML = ROOT / "data/uscode/xml"
PROVIDED = re.compile(r"\bprovided(?: that)?:")
WHICH = re.compile(r"(?:, (?:which|that) |(?:\d|\)), )(?:provided(?! that:|:)|required|directed|authorized|established|created|related|prohibited|made|amended|enacted|was)\b")
CITES = re.compile(r"(?:(?:Section|Sections|Subsection|Subsections|Title|Subtitle|Part|Chapter) .{0,60}? of )?(?:Pub\. L\. \d|(?:Act )?[A-Z][a-z]+\.? \d{1,2}, \d{4}, ch\. \d|R\.S\.)")


def local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def text(el) -> str:
    return squash("".join(el.itertext()))


def in_quoted(el) -> bool:
    p = el.getparent()
    while p is not None:
        if local(p) == "quotedContent":
            return True
        p = p.getparent()
    return False


def title_files(xml_dir: Path = XML) -> list[Path]:
    files = sorted(xml_dir.glob("usc*.xml"))
    if not files:
        raise FileNotFoundError(f"no usc*.xml under {xml_dir}: unzip the release point (python3 -m tools.uncodified fetch-code)")
    return files


EDITORIAL = {"amendments", "codification", "referencesInText", "priorProvisions", "historicalAndRevision",
             "editorialNotes", "statutoryNotes", "dispositionOfSections", "constitutionality"}


def statutory_notes(notes_el):
    """The `note` children of a `notes` element that can set out law: all but the cross
    headings and the editorial kinds. (OLRC files some statutory notes under the
    "Editorial Notes" cross heading, so the cross headings are not used.)"""
    return [n for n in notes_el if local(n) == "note" and n.get("role") != "crossHeading"
            and n.get("topic") not in EDITORIAL]


def note_records(notes_el, where: str) -> list[dict]:
    out = []
    for note in statutory_notes(notes_el):
        heading_el = note.find(U + "heading")
        heading = text(heading_el) if heading_el is not None else ""
        for p in note.iter(U + "p"):
            if in_quoted(p):
                continue
            t = text(p)
            m = PROVIDED.search(t)
            w = WHICH.search(t)
            if m and m.start() < 2500 and not (w and w.start() < m.start()):
                mode, cut, body = "set out", m.start(), t[m.end():]
            elif w and w.start() < 2500:
                mode, cut, body = "described", w.start(), t[w.start() + 2:]
            else:
                continue
            cite = t[:cut]
            if not CITES.match(cite):
                continue  # Executive orders, proclamations, reorganization plans, prose
            keys = parse_note_citation(cite + " provided:")
            qc = p.find(".//" + U + "quotedContent")
            if qc is None and mode == "set out":
                nxt = p.getnext()
                qc = nxt.find(".//" + U + "quotedContent") if nxt is not None else None
            origin = qc.get("origin") if qc is not None else None
            # the citation before "as amended" names the provision set out; `origin` names the
            # last amending provision when the note is set out as amended, so it is a fallback
            ok = key_of(origin) if origin else None
            if ok and (not keys or keys[0][2] is None) and (not keys or ok[0] == keys[0][0]):
                keys = [ok]
            ended = None
            if mode == "described":
                e = re.search(r"\b(was|were) (repealed|omitted|terminated|superseded)\b|\b(expired|terminated) (on|at|upon|after)\b", body)
                ended = (e[2] or e[3]) if e else None
            out.append({
                "where": where,
                "heading": heading,
                "topic": note.get("topic"),
                "mode": mode,
                "ended": ended,
                "citation": cite.strip(" ,"),
                "origin": origin,
                "keys": [list(k) for k in keys],
                "amended": bool(re.search(r"\bas (?:amended|added)\b", cite)),
                "words": len(t.split()),
                "text": body[:4000].strip(),
            })
    return out


def build(xml_dir: Path = XML, files: list[Path] | None = None) -> dict:
    credits: dict[tuple, set[str]] = defaultdict(set)
    not_effective: dict[tuple, set[str]] = defaultdict(set)
    notes: list[dict] = []
    for f in files or title_files(xml_dir):
        for _, el in etree.iterparse(str(f), events=("end",), tag=(U + "section", U + "notes"), huge_tree=True):
            tag = local(el)
            if in_quoted(el):
                continue
            if tag == "notes":
                parent = el.getparent()
                if parent is not None and local(parent) != "section":
                    where = parent.get("identifier") or ""
                    notes.extend(note_records(el, where))
                continue
            ident = el.get("identifier") or ""
            sc = el.find(U + "sourceCredit")
            if sc is not None:
                void = laws_not_effective(el)
                for k in parse_credit(text(sc)):
                    (not_effective if k[0] in void else credits)[k].add(ident)
            for n in el.findall(U + "notes"):
                notes.extend(note_records(n, ident))
            if el.getparent() is not None and local(el.getparent()) != "section":
                el.clear(keep_tail=True)
    return {"credits": credits, "not_effective": not_effective, "notes": notes}


NOT_EFFECTIVE = re.compile(r"(?:did not|never) (?:become|take|became|took) effect")


def laws_not_effective(section) -> set[str]:
    """The laws whose amendment of this section the Amendments note says did not take effect
    ("… which amendment did not become effective pursuant to section 402(b) of Pub. L.
    95–598"). The source credit still names them."""
    out = set()
    for notes_el in section.findall(U + "notes"):
        for n in notes_el.findall(U + "note"):
            if n.get("topic") != "amendments":
                continue
            for p in n.iter(U + "p"):
                t = text(p)
                for m in NOT_EFFECTIVE.finditer(t):
                    laws_before = re.findall(r"Pub\. L\. (\d+)[\u2013-](\d+)", t[:m.start()])
                    if laws_before:
                        out.add("/us/pl/%s/%s" % laws_before[-1])
    return out


def title_sections(path: Path) -> list[dict]:
    """Each section of one title: identifier, status, heading, the provisions its credit names."""
    out = []
    for _, el in etree.iterparse(str(path), events=("end",), tag=U + "section", huge_tree=True):
        if in_quoted(el):
            continue
        sc = el.find(U + "sourceCredit")
        h = el.find(U + "heading")
        out.append({
            "identifier": el.get("identifier"),
            "status": el.get("status"),
            "heading": text(h) if h is not None else "",
            "credit": [list(k) for k in parse_credit(text(sc))] if sc is not None else [],
        })
    return out
