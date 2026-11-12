"""Write the tables: analysis/uncodified/tN.md, tN.csv and tN.json."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

from . import laws
from .analyze import RELEASE_POINT, cite, in_title, law_sort
from .citations import parse_note_citation, unbracket

ROOT = Path(__file__).resolve().parents[2]
UNCOD = ("set out", "described", "amends a note", "amendment not effective", "not in the Code")
CODIFIED = ("enacts", "enacts other", "amends title", "amends other titles")


def law_label(law: str) -> str:
    m = re.fullmatch(r"/us/pl/(\d+)/(\d+)", law)
    if m:
        return f"Pub. L. {m[1]}-{m[2]}"
    m = re.fullmatch(r"/us/act/(\d{4})-(\d\d)-(\d\d)/ch(\d+)", law)
    if m:
        return f"Act of {m[1]}-{m[2]}-{m[3]}, ch. {m[4]}"
    return law


CODE_NAMES: dict[str, str] = {}


def code_names(idx: dict) -> dict[str, str]:
    """A law's short title from the Code: the note that sets out its section 1, "This Act may
    be cited as the ‘…’"."""
    out = {}
    for n in idx["notes"]:
        if n["topic"] not in ("shortTitle", "shortTitleOfAmendment"):
            continue
        m = re.match(r"\W*(?:That )?this Act[^‘“]{0,80}?may be cited as (?:the )?[‘“](.+?)[’”](?=[.,;]?(?:[”’\]]|\s*$|\s+(?:or|and)\b))", unbracket(n["text"]), re.I)
        if not m:
            continue
        for k in n["keys"]:
            if k[2] == "1" and k[1] is None:
                out.setdefault(k[0], m[1].strip().rstrip(","))
    return out


def law_name(law: str) -> str:
    if law in CODE_NAMES:
        return CODE_NAMES[law]
    d = laws.load(laws.toc_path(law)) or laws.load(laws.unit_path(law)) or {}
    info = d.get("law") or {}
    st = info.get("short_titles") or []
    if st:
        for x in st[:1] if len(st) == 1 else []:
            name = x if isinstance(x, str) else (x.get("title") or x.get("text") or "")
            if re.fullmatch(r"[^”“\"]{5,120}\bAct(?: of \d{4})?", name.strip()):
                return name.strip()
    t = info.get("official_title") or ""
    return (t[:90] + "…") if len(t) > 90 else t


def sec_label(r: dict) -> str:
    ident = r["identifier"][len(r["law"]):] if r["identifier"].startswith(r["law"]) else r["identifier"]
    parts = []
    for seg in ident.strip("/").split("/"):
        m = re.fullmatch(r"([a-z]+)(.+)", seg)
        if not m:
            continue
        lvl, num = m.groups()
        parts.append({"d": "div. ", "t": "title ", "st": "subtitle ", "s": "§ "}.get(lvl, lvl + " ") + num)
    return ", ".join(p for p in parts if not p.startswith("subtitle"))


def where(r: dict) -> str:
    bits = []
    notes = r["notes"]
    if len(notes) > 6:  # the notes in other titles of a section set out in many places
        notes = notes[:6]
    for n in notes:
        lab = f"{n['cite']} note ({n['heading']})" if n["heading"] else f"{n['cite']} note"
        if n["mode"] == "set out":
            bits.append(f"set out as {lab}")
        else:
            bits.append(f"described in {lab}" + (f", {n['ended']}" if n["ended"] else ""))
    am = list(dict.fromkeys(f"{n['cite']} note ({n['heading']})" for n in r["amends_notes"]))
    if am:
        more = f" and {len(am) - 3} more notes" if len(am) > 3 else ""
        bits.append("amends the provisions set out as " + "; ".join(am[:3]) + more)
    if r["code_in_title"]:
        bits.append("also amends " + short_list(r["code_in_title"]))
    if r["code_other"]:
        bits.append("also amends " + short_list(r["code_other"]))
    if len(r["notes"]) > 6:
        bits.append(f"and {len(r['notes']) - 6} more notes")
    if r.get("not_effective") and not r["code_in_title"] and not r["code_other"]:
        bits.append("amended " + short_list(r["not_effective"]) + ", an amendment the Code's notes say did not take effect")
    if not bits:
        t = (r.get("text") or "").strip()
        bits.append("not in the Code" + (f": “{trim(t, 110)}”" if t else ""))
    return "; ".join(dict.fromkeys(bits))


def trim(t: str, n: int) -> str:
    t = re.sub(r"^(?:SEC\.|Sec\.|§)\s*\S+\s*", "", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"


def short_list(ids: list[str], n: int = 4) -> str:
    cites = [cite(i) for i in ids]
    by_title = defaultdict(list)
    for c in cites:
        t, _, s = c.partition(" U.S.C. ")
        by_title[t].append(s)
    out = []
    for t, ss in list(by_title.items())[:n]:
        more = f" and {len(ss) - n} more" if len(ss) > n else ""
        out.append(f"{t} U.S.C. {', '.join(ss[:n])}{more}")
    if len(by_title) > n:
        out.append(f"sections in {len(by_title) - n} more titles")
    return "; ".join(out)


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def draft_dispositions(title: str) -> dict:
    """From aih/codification-bills' drafts/tN/bill.toml, when there is one: the draft's disposition of each former
    Code section (by identifier) and of each statutory note (by provision key)."""
    base = Path(os.environ.get("CODIFICATION_BILLS") or ROOT.parent / "codification-bills")
    p = base / f"drafts/t{title}/bill.toml"
    if not p.exists():
        return {}
    d = tomllib.loads(p.read_text(encoding="utf-8"))
    secs, notes = {}, {}
    for row in d.get("disposition", []):
        former, disp = row["former"], row["disposition"]
        m = re.search(r"note \((.*)\)$", former)
        if m:
            for k in parse_note_citation(m[1].replace("-", "\u2013") + " provided:"):
                notes.setdefault((k[0], k[2]), []).append((m[1], disp))
            continue
        for cov in row.get("covers", []):
            for ident in cov.split():
                secs[ident] = disp
    return {"sections": secs, "notes": notes, "path": f"aih/codification-bills drafts/t{title}/bill.toml"}


DATE_RE = r"(?:Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\.? \d{1,2}, \d{4}"


def provision(citation: str) -> str:
    """A note's citation without its date and Statutes at Large page: `Pub. L. 98–621, § 1`,
    `Act July 1, 1898, ch. 546`."""
    c = re.split(r",? \d+ Stat\.", citation)[0]
    c = re.split(r",? as (?:amended|added)\b", c)[0]
    if c.startswith("Pub. L."):
        c = re.split(rf",? {DATE_RE}", c)[0]
    return c.strip(" ,")


def listed(r: dict, title: str) -> bool:
    """Whether an uncodified section belongs in the tables. All of a primary law's (the
    enacting Act, a law filed with the title, a law mostly about the title); of another
    law, a section the Code does not hold at all that the title names or that sits in a
    title of the law mostly about this one, and a section set out or described in the
    title, or that amends a provision set out in it."""
    if r["primary"]:
        return True
    if "not in the Code" in r["disposition"] or "amendment not effective" in r["disposition"]:
        return r["named_in_title"] or r["in_full_container"]
    return (any(in_title(n["where"], title) for n in r["notes"])
            or any(in_title(n["where"], title) for n in r["amends_notes"]))


def note_disp(entries: list | None) -> str | None:
    """One disposition, or each with the provision it covers when the draft splits a note."""
    if not entries:
        return None
    if len({d for _, d in entries}) == 1:
        return entries[0][1]
    return "; ".join(f"{re.sub(r'^Pub. L. [^,]+, (?:div. [A-Z]+, )?(?:title [IVXL]+, )?', '', f)}: {d}" for f, d in entries)


def write(title: str, sc: dict, res: dict, idx: dict) -> int:
    rows = res["rows"]
    CODE_NAMES.update(code_names(idx))
    draft = draft_dispositions(title)
    for r in rows:
        r["uncodified"] = any(x in r["disposition"] for x in UNCOD)
        r["listed"] = r["uncodified"] and listed(r, title)
        r["partly"] = r["uncodified"] and any(x in r["disposition"] for x in CODIFIED)
        if draft:
            dd = [draft["sections"].get(c) for c in r["code_in_title"]]
            dn = [note_disp(draft["notes"].get((r["law"], r["num"])) or draft["notes"].get((r["cited_as"], r["num"])))
                  for n in r["notes"] if in_title(n["where"], title)]
            r["draft"] = "; ".join(dict.fromkeys(x for x in dd + dn if x)) or None
    tnotes = [n for n in idx["notes"] if in_title(n["where"], title)]
    for n in tnotes:
        n["draft"] = None
        if draft:
            for k in n["keys"]:
                n["draft"] = n["draft"] or note_disp(draft["notes"].get((k[0], k[2])))
    by_law = defaultdict(list)
    for r in rows:
        by_law[r["law"]].append(r)
    laws_sorted = sorted(by_law, key=law_sort)

    out_json = ROOT / f"analysis/uncodified/t{title}.json"
    out_md = ROOT / f"analysis/uncodified/t{title}.md"
    out_csv = ROOT / f"analysis/uncodified/t{title}.csv"
    for p in (out_json, out_md, out_csv):
        p.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({
        "title": title, "release_point": RELEASE_POINT,
        "laws": [{"law": l, "name": law_name(l), "scope": by_law[l][0]["scope"]} for l in laws_sorted],
        "missing_laws": res["missing_laws"],
        "rows": rows,
        "title_notes": tnotes,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    cols = ["law", "name", "section", "identifier", "heading", "kind", "disposition", "uncodified", "listed",
            "where", "code_in_title", "code_other", "scope", "missing_from_toc"] + (["draft"] if draft else [])
    w.writerow(cols)
    names = {l: law_name(l) for l in laws_sorted}
    for l in laws_sorted:
        for r in by_law[l]:
            vals = [law_label(l), names[l], sec_label(r), r["identifier"], r["heading"] or "", r["kind"],
                    "; ".join(r["disposition"]), "partly" if r["partly"] else ("yes" if r["uncodified"] else "no"),
                    "yes" if r["listed"] else "no",
                    where(r), " ".join(cite(c) for c in r["code_in_title"]),
                    " ".join(cite(c) for c in r["code_other"]), r["scope"], "yes" if r["missing_from_toc"] else ""]
            if draft:
                vals.append(r.get("draft") or "")
            w.writerow(vals)
    out_csv.write_text(buf.getvalue(), encoding="utf-8")

    md = []
    md.append(f"# Provisions of the laws in title {title} that are not in the title\n")
    md.append(f"Generated by `python3 -m tools.uncodified run {title}` from the Code at release point "
              f"{RELEASE_POINT} and the statutes API's tables of contents. Do not edit by hand; the method "
              f"is `tools/uncodified/README.md`. Every row is in `t{title}.csv`, and with the note texts in "
              f"`t{title}.json`.\n")
    md.append("## Laws\n")
    md.append("Scope `whole`: every section of the law; `part`: the sections the title's credits or notes "
              "name and the titles of the law mostly made of them. Counts are of the law's sections; a "
              "section is counted in each column that applies.\n")
    md.append(f"| Law | Name | Scope | Sections | In title {title} | In other titles | Set out as a note | Described in a note | Amends a note | Amendment not effective | Not in the Code |")
    md.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    tot = Counter()
    for l in laws_sorted:
        rs = by_law[l]
        c = Counter()
        for r in rs:
            c["n"] += 1
            if "enacts" in r["disposition"] or "amends title" in r["disposition"]:
                c["in"] += 1
            if "amends other titles" in r["disposition"] or "enacts other" in r["disposition"]:
                c["other"] += 1
            for k in ("set out", "described", "amends a note", "amendment not effective", "not in the Code"):
                if k in r["disposition"]:
                    c[k] += 1
        tot.update(c)
        md.append(f"| {law_label(l)} | {esc(names[l])} | {rs[0]['scope']} | {c['n']} | {c['in']} | {c['other']} | "
                  f"{c['set out']} | {c['described']} | {c['amends a note']} | {c['amendment not effective']} | {c['not in the Code']} |")
    md.append(f"| **Total** | | | {tot['n']} | {tot['in']} | {tot['other']} | {tot['set out']} | "
              f"{tot['described']} | {tot['amends a note']} | {tot['amendment not effective']} | {tot['not in the Code']} |")
    if res["missing_laws"]:
        md.append("\nNo table of contents on the statutes API for: " + ", ".join(law_label(l) for l in res["missing_laws"]) + ".")
    md.append("")

    unc = [r for r in rows if r["listed"]]
    md.append("## Kinds of provision not in the text of any title\n")
    md.append("The kind is read from the section's heading, the headings of the notes that set it out, "
              "and the first words of its text (`tools/uncodified/analyze.py`, `KINDS`).\n")
    kinds = Counter(r["kind"] for r in unc)
    md.append("| Kind | Sections | Set out or described in a note | Not in the Code |")
    md.append("|---|---:|---:|---:|")
    for k, n in kinds.most_common():
        a = sum(1 for r in unc if r["kind"] == k and ("set out" in r["disposition"] or "described" in r["disposition"]))
        b = sum(1 for r in unc if r["kind"] == k and "not in the Code" in r["disposition"])
        md.append(f"| {k} | {n} | {a} | {b} |")
    md.append("")

    md.append("## Sections not in the text of any title, by law\n")
    md.append("A section that also amends the Code (part of it is executed, part set out) is marked *partly*.\n")
    for l in laws_sorted:
        rs = [r for r in by_law[l] if r["listed"]]
        if not rs:
            continue
        md.append(f"### {law_label(l)}{' — ' + esc(names[l]) if names[l] else ''}\n")
        head = "| Section | Heading | Kind | Where it is |" + (" Draft |" if draft else "")
        md.append(head)
        md.append("|---|---|---|---|" + ("---|" if draft else ""))
        for r in rs:
            h = r["heading"] or ""
            if not h and r["notes"]:
                h = r["notes"][0]["heading"]
            lab = sec_label(r) + (" *partly*" if r["partly"] else "") + (" †" if r["missing_from_toc"] else "")
            line = f"| {esc(lab)} | {esc(h.capitalize() if h.isupper() else h)} | {r['kind']} | {esc(where(r))} |"
            if draft:
                line += f" {esc(r.get('draft') or '')} |"
            md.append(line)
        md.append("")
    if any(r["missing_from_toc"] for r in rows):
        md.append("† Not in the statutes API's table of contents for the law; named in the Code's credits or "
                  "notes (a section a later law added, or one lost in the conversion of the printed volume).\n")

    md.append(f"## Statutory notes in title {title} that set out or describe law\n")
    md.append(f"{len(tnotes)} notes, in the order of the title.\n")
    md.append("| Under | Note | Provision | Kind | Form |" + (" Draft |" if draft else ""))
    md.append("|---|---|---|---|---|" + ("---|" if draft else ""))
    from .analyze import kind as kind_of
    for n in tnotes:
        k = kind_of({"heading": "", "notes": [n], "text": n["text"]})
        form = n["mode"] + (f", {n['ended']}" if n["ended"] else "") + (", as amended" if n["amended"] else "")
        prov = provision(n["citation"])
        line = f"| {cite(n['where'])} | {esc(n['heading'])} | {esc(prov)} | {k} | {form} |"
        if draft:
            line += f" {esc(n.get('draft') or '')} |"
        md.append(line)
    md.append("")
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"{out_md.relative_to(ROOT)}: {len(rows)} sections of {len(laws_sorted)} laws, {len(unc)} not in the text of any title; "
          f"{len(tnotes)} statutory notes in the title")
    return 0
