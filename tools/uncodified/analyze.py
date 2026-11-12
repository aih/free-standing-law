"""Which sections of a title's source laws are not in the title, and where each one is.

Scope (`scope`): the laws named in the source credits of the title's sections, and the laws
whose provisions are set out or described in a statutory note of the title. For each law the
sections examined are:

- all of them, for the Act that enacted the title (a section that encloses the title), for a
  law whose short title is set out as a note in the title (the Act is filed with the title),
  for a law of 10 sections or fewer, and for a law a quarter or more of whose sections the
  title's credits or notes name;
- otherwise the sections the title's credits or notes name, and every section of a title (or
  division) of the law a quarter or more of whose sections they name: the other sections of
  an omnibus Act, an appropriations Act or an authorization Act are out of scope.

Disposition (`dispose`), from the Code at the release point (`codeindex`): each section is
`enacts` (it encloses the title), `amends title N` / `amends other titles` (a section credit
names it), `set out` / `described` (a statutory note sets out its text, or describes it,
usually because it was repealed or has expired), `amends a note` (it amended a provision set
out as a note), or `not in the Code` (none of these). A section can have several.
"""
from __future__ import annotations

import pickle
import re
from collections import defaultdict
from pathlib import Path

from . import codeindex, laws
from .citations import key_of, parse_credit

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "data/uncodified/index-119-138.pickle"
RELEASE_POINT = "119-138"
SMALL = 10
SHARE = 0.25


def code_index(rebuild: bool = False) -> dict:
    if INDEX.exists() and not rebuild:
        return pickle.loads(INDEX.read_bytes())
    d = codeindex.build()
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_bytes(pickle.dumps(d))
    return d


def in_title(where: str, title: str) -> bool:
    t = f"/us/usc/t{title}"
    return where == t or where.startswith(t + "/")


def amended_by(note: dict) -> list[tuple]:
    m = re.search(r"\bas (?:amended|added) by (.*)$", note["citation"])
    return parse_credit(m[1]) if m else []


def title_of(where: str) -> str:
    m = re.match(r"/us/usc/t(\w+)", where)
    return m[1] if m else "?"


def cite(where: str) -> str:
    """`/us/usc/t28/s2075` → `28 U.S.C. 2075`; `/us/usc/t28/ptI/ch6` → `28 U.S.C. ch. 6`."""
    m = re.match(r"/us/usc/t(\w+)(?:/(.*))?$", where)
    if not m:
        return where
    t, rest = m[1], m[2] or ""
    s = re.search(r"(?:^|/)s([^/]+)", rest)
    if s:
        return f"{t} U.S.C. {s[1].replace('...', ' to ')}"
    parts = [p for p in rest.split("/") if p]
    if parts:
        last = parts[-1]
        lab = {"ch": "ch.", "sch": "subch.", "pt": "pt.", "st": "subtitle"}
        mm = re.match(r"(sch|ch|pt|st)(.+)", last)
        if mm:
            return f"{t} U.S.C. {lab[mm[1]]} {mm[2]}"
    return f"title {t}"


def scope(title: str, idx: dict) -> dict:
    """The laws in scope, with the keys the title's credits and notes name."""
    tsec = codeindex.title_sections(codeindex.ROOT / "data/uscode/xml" / codeindex_file(title))
    named: dict[str, set] = defaultdict(set)
    whole: set[str] = set()
    for s in tsec:
        for law, div, sec in s["credit"]:
            if law != "R.S." and not (sec or "").startswith("title:"):
                named[law].add((div, sec))
    for n in idx["notes"]:
        if not in_title(n["where"], title):
            continue
        for law, div, sec in n["keys"]:
            if law == "R.S.":
                continue
            if (sec or "").startswith("title:"):
                named[law].add((div, None))
                continue
            named[law].add((div, sec))
            if (n["topic"] in ("shortTitle", "shortTitleOfAmendment") and sec == "1" and div is None
                    and re.match(r"\W*(?:That )?this Act\b", n["text"], re.I)):
                whole.add(law)
    return {"title": title, "sections": tsec, "named": named, "whole": whole}


def codeindex_file(title: str) -> str:
    m = re.fullmatch(r"(\d+)([aA]?)", title)
    n, app = m.groups()
    d = codeindex.ROOT / "data/uscode/xml"
    for cand in (f"usc{int(n):02d}{app.lower()}.xml", f"usc{int(n):02d}{app.upper()}.xml"):
        if (d / cand).exists():
            return cand
    raise FileNotFoundError(f"usc{int(n):02d}{app}.xml (python3 -m tools.uncodified fetch-code)")


def law_request_lines(sc: dict) -> list[tuple]:
    out = []
    for law in sorted(sc["named"]):
        if law.startswith("/us/act/"):
            p = laws.unit_path(law)
            if not p.exists():
                out.append(laws.request_line(p, laws.API + law, f"statutes API law, uncodified provisions of title {sc['title']}"))
                continue
        served = laws.resolve(law)
        tp = laws.toc_path(served) if served else None
        if tp is not None and not tp.exists():
            m = re.fullmatch(r"/us/pl/(\d+)/(\d+)", served)
            out.append(laws.request_line(tp, f"{laws.API}/laws/{m[1]}/{m[2]}",
                                         f"statutes API table of contents, uncodified provisions of title {sc['title']}"))
        if served and not served.startswith("/us/pl/"):
            p = laws.unit_path(served)
            if not p.exists():
                out.append(laws.request_line(p, laws.API + served, f"statutes API law, uncodified provisions of title {sc['title']}"))
    return out


def dispose(sc: dict, idx: dict) -> dict:
    title = sc["title"]
    notes_by_key: dict[tuple, list] = defaultdict(list)
    amends_note: dict[tuple, list] = defaultdict(list)
    for n in idx["notes"]:
        for k in n["keys"]:
            notes_by_key[(k[0], k[1], k[2])].append(n)
        for k in amended_by(n):
            amends_note[k].append(n)
    credits = idx["credits"]
    known: dict[str, set] = defaultdict(set)  # every (div, sec) of a law the Code names anywhere
    for k in list(credits) + list(notes_by_key):
        if k[2] is not None and not k[2].startswith("title:"):
            known[k[0]].add((k[1], k[2]))
    rows, missing_laws = [], []
    for law in sorted(sc["named"], key=law_sort):
        secs = laws.act_sections(law)
        served = laws.resolve(law) or law
        if secs is None:
            missing_laws.append(law)
            continue
        named = sc["named"][law]
        enacting = any(s["encloses"] and any(e == f"title {title}" for e in s["encloses"]) for s in secs)
        # a section named by its number alone in the Code (no division) matches in any division
        def hit(sec_row):
            k = key_of(sec_row["identifier"]) or (served, None, sec_row["num"])
            return k
        named_ids = set()
        if len(secs) == 1 and (None, None) in named:
            named_ids.add(secs[0]["identifier"])  # an Act credited without a section number
        for s in secs:
            k = hit(s)
            if (k[1], k[2]) in named or (None, k[2]) in named:
                named_ids.add(s["identifier"])
        small = len(secs) <= SMALL and not laws.is_appropriations(served)
        whole = (enacting or law in sc["whole"] or served in sc["whole"] or small
                 or (len(named_ids) >= SHARE * len(secs) and not laws.is_appropriations(served)))
        by_cont: dict[str, list] = defaultdict(list)
        for s in secs:
            by_cont[s["container"]].append(s["identifier"] in named_ids)
        full = {c for c, v in by_cont.items() if c != served and sum(v) >= SHARE * len(v)}
        have = {(hit(s)[1], hit(s)[2]) for s in secs} | {(None, hit(s)[2]) for s in secs}
        extra = sorted(known[law] | known[served], key=lambda k: (k[0] or "", natural(k[1])))
        for div, sec in extra:
            if (div, sec) in have or (None, sec) in have:
                continue
            if (div, sec) not in named and (not whole or len(secs) <= SMALL):
                continue
            ident = served + (f"/d{div}" if div else "") + f"/s{sec}"
            secs.append({"identifier": ident, "num": sec, "heading": None, "container": "",
                         "encloses": [], "missing_from_toc": True})
            if (div, sec) in named:
                named_ids.add(ident)
        primary = (enacting or law in sc["whole"] or served in sc["whole"]
                   or (len(secs) > SMALL and len(named_ids) >= SHARE * len(secs)
                       and not laws.is_appropriations(served)))
        for s in secs:
            if not whole and s["identifier"] not in named_ids and s["container"] not in full:
                continue
            k = hit(s)
            keys = {(law, k[1], k[2]), (served, k[1], k[2])}
            if k[1] is not None:
                pass
            if len(secs) == 1:
                keys |= {(law, None, None), (served, None, None)}
            code = sorted({c for kk in keys for c in credits.get(kk, ())}, key=sec_sort)
            void = sorted({c for kk in keys for c in idx.get("not_effective", {}).get(kk, ())}, key=sec_sort)
            in_t = [c for c in code if in_title(c, title)]
            other = [c for c in code if not in_title(c, title)]
            nts = [n for kk in keys for n in notes_by_key.get(kk, [])]
            tm = re.search(r"/t([IVXLC]+)$", s["container"] or "")
            if tm:  # a note on the whole title of the law the section is in
                nts += [n for n in notes_by_key.get((law, k[1], f"title:{tm[1]}"), [])
                        + notes_by_key.get((served, k[1], f"title:{tm[1]}"), []) if n not in nts]
            nts = list({id(n): n for n in nts}.values())
            amn = list({id(n): n for kk in keys for n in amends_note.get(kk, [])}.values())
            disp = []
            if any(e == f"title {title}" for e in s["encloses"]):
                disp.append("enacts")
            elif s["encloses"]:
                disp.append("enacts other")
            if in_t:
                disp.append("amends title")
            if other:
                disp.append("amends other titles")
            if any(n["mode"] == "set out" for n in nts):
                disp.append("set out")
            if any(n["mode"] == "described" for n in nts):
                disp.append("described")
            if amn:
                disp.append("amends a note")
            if void and not code:
                disp.append("amendment not effective")
            if not disp:
                disp.append("not in the Code")
            heading = s["heading"]
            text = None
            if "not in the Code" in disp or not heading:
                text = laws.section_text(s["identifier"])
            rows.append({
                "law": served,
                "cited_as": law,
                "identifier": s["identifier"],
                "num": s["num"],
                "container": s["container"],
                "heading": heading,
                "encloses": s["encloses"],
                "named_in_title": s["identifier"] in named_ids,
                "missing_from_toc": bool(s.get("missing_from_toc")),
                "scope": "whole" if whole else "part",
                "primary": primary,
                "in_full_container": s["container"] in full,
                "disposition": disp,
                "code_in_title": in_t,
                "code_other": other,
                "not_effective": void,
                "notes": [{"where": n["where"], "cite": cite(n["where"]), "heading": n["heading"],
                           "topic": n["topic"], "mode": n["mode"], "ended": n["ended"],
                           "citation": n["citation"], "amended": n["amended"]} for n in nts],
                "amends_notes": [{"where": n["where"], "cite": cite(n["where"]), "heading": n["heading"],
                                  "citation": n["citation"][:200]} for n in amn],
                "text": text[:600] if text else None,
                "kind": None,
            })
    for r in rows:
        r["kind"] = kind(r)
    return {"rows": rows, "missing_laws": missing_laws}


def natural(n: str):
    m = re.match(r"(\d+)(.*)", n or "")
    return (int(m[1]), m[2]) if m else (0, n or "")


def law_sort(law: str):
    m = re.match(r"/us/pl/(\d+)/(\d+)", law)
    if m:
        return (1, int(m[1]), int(m[2]), "")
    m = re.match(r"/us/act/(\S+)", law)
    return (0, 0, 0, m[1] if m else law)


def sec_sort(ident: str):
    m = re.match(r"/us/usc/t(\d+)(\w*)/s(\d+)(.*)", ident)
    return (int(m[1]), m[2], int(m[3]), m[4]) if m else (999, ident, 0, "")


KINDS = [
    ("Short title", r"short title|may be cited as"),
    ("Table of contents, references", r"table of contents|references? to (?:title|the) .{0,40}code|^references\b"),
    ("Findings", r"\bfindings\b"),
    ("Purposes", r"\bpurposes?\b(?! of (?:this|the|such|paragraph|subsection|section|determining|title))"),
    ("Sense of Congress", r"sense of (?:the )?(?:congress|senate|house)"),
    ("Effective date, application", r"effective date|take effect|become effective|effective dates|application of amendments|applicability|retroactive|apply (?:only )?(?:to|with respect to) (?:any )?cases?"),
    ("Study, report", r"\bstudy\b|\breport\b|\bsurvey\b|general accounting office|comptroller general|\bgao\b"),
    ("Savings, transition", r"saving|transition|pending (?:cases|proceedings)|continuation of|continue in effect"),
    ("Construction", r"construction|nothing in this|shall not be construed|interpretation|limitation of (?:information|implied)"),
    ("Severability", r"separability|severability"),
    ("Budgetary effects", r"budgetary effects"),
    ("Termination, sunset", r"\btermination|sunset|expir"),
    ("Repeal", r"\brepeal"),
    ("Appropriations, fees", r"authoriz\w+ (?:of )?appropriat|authorized to be appropriated|appropriated|\bfees?\b"),
    ("Definitions", r"definition|the term .{1,40} means"),
    ("Rules, regulations", r"\brules?\b|regulation|rulemaking"),
    ("Program, pilot, training", r"program|pilot|training|education|demonstration"),
    ("Judgeships, courts", r"judgeship|bankruptcy judges?|court|referee|trustee"),
    ("Amendment", r"\bamended\b|\bamendments?\b|\bstriking\b|\binserting\b"),
]


def kind(r: dict) -> str:
    """A label for what a section is: the first rule that matches its heading, else the
    headings of the notes that set it out, else the first words of its text."""
    if "enacts" in r.get("disposition", []):
        return "Enacts the title"
    sources = [r.get("heading") or "", " ".join(n["heading"] for n in r["notes"]), (r.get("text") or "")[:300]]
    for i, hay in enumerate(sources):
        if i == 2:
            head = re.sub(r"^[A-Z0-9 ;,.’'“”-]{6,}\. ", "", hay[:300])[:250]  # drop a capitalized heading
            if re.search(r"\b(?:is|are) (?:hereby )?amended\b|\bis amended by\b", head):
                return "Amendment"
            if re.search(r"\b(?:is|are) (?:hereby )?repealed\b", head):
                return "Repeal"
        hay = hay.lower()
        if not hay.strip():
            continue
        for label, pat in KINDS:
            if re.search(pat, hay):
                return label
    return "Other"
