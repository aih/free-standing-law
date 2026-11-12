"""Citations of enacted law in OLRC's USLM: source credits and statutory notes.

A provision is keyed as (law, div, sec): `law` is `/us/pl/{congress}/{number}` or
`/us/act/{date}/ch{n}` (or `R.S.` for the Revised Statutes), `div` the division letter when the
law has divisions (numbering restarts in each), `sec` the section number. Titles and
subsections are dropped from the key: section numbers are unique inside a division.
"""
from __future__ import annotations

import re

MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "June": 6, "July": 7, "Aug": 8,
          "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12}
MONTH = r"(?:Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\.?"
DATE = rf"{MONTH} \d{{1,2}}, \d{{4}}"
DASH = "–"


def squash(s: str) -> str:
    return " ".join(s.replace("\u00ad", "").split())


def iso(date: str) -> str:
    m = re.match(r"(\w+)\.? (\d{1,2}), (\d{4})", date)
    return f"{m[3]}-{MONTHS[m[1]]:02d}-{int(m[2]):02d}"


def key_of(identifier: str) -> tuple[str, str | None, str | None] | None:
    """`/us/pl/109/8/tI/s102/e` → ('/us/pl/109/8', None, '102');
    `/us/pl/105/277/dI/tVI/s603` → ('/us/pl/105/277', 'I', '603');
    `/us/act/1943-06-15/ch125/s3` → ('/us/act/1943-06-15/ch125', None, '3')."""
    m = re.match(r"(/us/pl/\d+/\d+|/us/act/\d{4}-\d\d-\d\d/ch\d+)(/.*)?$", identifier or "")
    if not m:
        return None
    law, rest = m[1], m[2] or ""
    div = sec = None
    for part in rest.strip("/").split("/"):
        if not part:
            continue
        if re.fullmatch(r"d[A-Z]+", part):
            div = part[1:]
        elif re.fullmatch(r"s\d+[A-Za-z0-9]*(?:[-–]\d+)?", part) and sec is None:
            sec = part[1:]
            break
    return (law, div, sec)


_SECNUM = r"\d+[A-Za-z]{0,3}(?:[-–]\d+)?"


def _sections(rest: str, law: str) -> list[tuple[str, str | None, str | None]]:
    """The provisions of one law named in a credit chunk's tail (`title III, §§ 304, 363(b)`)."""
    out: list[tuple[str, str | None, str | None]] = []
    div = None
    for tok in [t.strip() for t in rest.split(",")]:
        if not tok:
            continue
        d = re.match(r"div\. ([A-Z]+)\b", tok)
        if d:
            div = d[1]
            continue
        s = re.match(rf"§§? ?({_SECNUM})", tok)
        if s:
            out.extend((law, div, n) for n in expand(s[1]))
            continue
        s2 = re.match(rf"({_SECNUM})(?:\(|$)", tok)
        if s2 and out:
            out.extend((law, div, n) for n in expand(s2[1]))
    return out or [(law, div, None)]


def expand(num: str) -> list[str]:
    """`551–553` → ['551', '552', '553']; anything else as is."""
    m = re.fullmatch(r"(\d+)[-–](\d+)", num)
    if m and int(m[2]) > int(m[1]) and int(m[2]) - int(m[1]) < 60:
        return [str(n) for n in range(int(m[1]), int(m[2]) + 1)]
    return [num]


def unbracket(text: str) -> str:
    """Drop bracketed insertions, nested ones included."""
    prev = None
    while prev != text:
        prev, text = text, re.sub(r"\[[^\[\]]*\]", "", text)
    return text


def parse_credit(text: str) -> list[tuple[str, str | None, str | None]]:
    """Every provision a source credit names, in order.

    `(Pub. L. 98–353, title III, §§ 304, 363(b), July 10, 1984, 98 Stat. 352, 363)` →
    [('/us/pl/98/353', None, '304'), ('/us/pl/98/353', None, '363')];
    `(June 15, 1943, ch. 125, § 3, 57 Stat. 153)` → [('/us/act/1943-06-15/ch125', None, '3')];
    `(R.S. § 4813; …)` → [('R.S.', None, '4813'), …]."""
    out: list[tuple[str, str | None, str | None]] = []
    # a bracketed citation is the section of an Act enacted by reference
    # (`Pub. L. 106–554, § 1(a)(5) [title X, § 1001]`); the key is the enacting section
    text = unbracket(text)
    for chunk in squash(text).strip("() .").split(";"):
        chunk = chunk.strip()
        m = re.search(r"Pub\. L\. (\d+)[–-](\d+)\s*,?(.*)", chunk)
        if m:
            law = f"/us/pl/{m[1]}/{m[2]}"
            out.extend(_sections(re.split(DATE, m[3])[0], law))
            continue
        m = re.search(rf"(?:Act )?({DATE}),? ch\. (\d+)\s*,?(.*)", chunk)
        if m:
            law = f"/us/act/{iso(m[1])}/ch{m[2]}"
            out.extend(_sections(re.split(r"\d+ Stat\.", m[3])[0], law))
            continue
        m = re.search(r"R\.S\. §§? ?([\d, –-]+)", chunk)
        if m:
            out.extend(("R.S.", None, n.strip()) for n in m[1].split(",") if n.strip())
    return out


def parse_note_citation(text: str) -> list[tuple[str, str | None, str | None]]:
    """The provisions a statutory note sets out, from the words before "provided":
    `Pub. L. 98–353, title III, §§ 551–553, July 10, 1984, …, provided that:`."""
    head = unbracket(re.split(r"\bprovided(?: that)?:", text)[0])
    # `§ 552, formerly § 553`: the section as enacted (the statutes API's numbering) is the former one
    head = re.sub(r"§ ?([\w()]+), formerly §+ ?([\w()]+)", r"§ \2", head)
    head = re.split(r",? as (?:amended|added|renumbered)\b", head)[0]
    m = re.search(r"(?:Section|Sections|§§?) ?([\d\w()–-]+(?:, [\d\w()]+)*) of Pub\. L\. (\d+)[–-](\d+)", head)
    if m:
        law = f"/us/pl/{m[2]}/{m[3]}"
        nums = [re.match(_SECNUM, n.strip()) for n in m[1].split(",")]
        return [(law, None, x) for n in nums if n for x in expand(n[0])]
    keys = parse_credit(head)
    if len(keys) == 1 and keys[0][2] is None:
        # a whole title of a law: `Pub. L. 103–394, title VI, Oct. 22, 1994, …, established …`
        t = re.match(r"Pub\. L\. \d+[\u2013-]\d+, (?:div\. ([A-Z]+), )?title ([IVXLC]+)\b(?!,? §)", head)
        if t:
            return [(keys[0][0], t[1], f"title:{t[2]}")]
    return keys
