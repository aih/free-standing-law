"""Rank sections by how much their text changed, and write the redlines.

Reads what `fetch.py` cached under data/textchange/ and writes
analysis/textchange/: `sections.tsv` (every section), `top.tsv` (the ranked
list), `transitions.tsv` (every text change), and `redlines.json`, which
`render.py` turns into the HTML page.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

from lxml import etree

from .fetch import get

OUT = Path("analysis/textchange")
CACHE = Path("data/textchange")

SKIP = {"notes", "note", "sourceCredit", "toc"}
LEVELS = {"subsection", "paragraph", "subparagraph", "clause", "subclause", "item",
          "subitem", "subsubitem"}
BLOCKS = LEVELS | {"chapeau", "content", "continuation", "p", "proviso", "tr", "table"}


def local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def reading_lines(xml: str) -> list[tuple[int, str]]:
    """The section's body text, one (depth, text) line per block.

    Leaves out notes, the source credit and any table of contents, as the
    uscode-redesign plain_text() does (ADR-0069). A level's num and heading
    share its first line.
    """
    root = etree.fromstring(xml.encode("utf-8"))
    lines: list[tuple[int, list[str]]] = [(0, [])]
    head_open = [True]  # the current line holds only a level's num and heading

    def emit(s: str | None) -> None:
        if s:
            lines[-1][1].append(s)

    def newline(d: int) -> None:
        if "".join(lines[-1][1]).strip():
            lines.append((d, []))
        else:
            lines[-1] = (d, lines[-1][1])

    def walk(el, depth: int) -> None:
        name = local(el)
        if name in SKIP or (name == "ref" and "footnoteRef" in (el.get("class") or "")) \
                or (name == "sup" and re.fullmatch(r"[\d*†‡§]+", (el.text or "").strip())):
            emit(el.tail)
            return
        if el is not root and name in BLOCKS:
            if name in LEVELS:
                d = depth + 1
                newline(d)
                head_open[0] = True
            else:
                d = depth
                if not head_open[0]:
                    newline(d)
                else:
                    emit(" ")
                head_open[0] = False
            emit(el.text)
            for ch in el:
                walk(ch, d)
            head_open[0] = False
            lines.append((depth, []))
            emit(el.tail)
            return
        emit(el.text)
        for ch in el:
            walk(ch, depth)
        emit(el.tail)

    walk(root, 0)
    out = []
    for d, parts in lines:
        t = " ".join("".join(parts).split())
        if t:
            out.append((d, t))
    return out


def words(lines: list[tuple[int, str]]) -> list[str]:
    return [w for _, t in lines for w in t.split()]


EDITORIAL = re.compile(r"\s+of this (?:section|title|chapter|subchapter|part|subtitle|subpart)\b")


def editorial_only(a: list[tuple[int, str]], b: list[tuple[int, str]]) -> bool:
    """True when the two texts differ only by OLRC's "of this section/title/…" insertions."""
    norm = lambda ls: "".join(EDITORIAL.sub("", " ".join(t for _, t in ls)).split())
    return norm(a) == norm(b)


def word_diff(a: list[str], b: list[str]) -> tuple[int, int, list]:
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ins = dele = 0
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            dele += i2 - i1
        if tag in ("insert", "replace"):
            ins += j2 - j1
        ops.append((tag, i1, i2, j1, j2))
    return ins, dele, ops


def line_redline(a: list[tuple[int, str]], b: list[tuple[int, str]]) -> list[dict]:
    """Redline of b against a: line-aligned, word-level inside changed lines.

    Each entry is {"d": depth, "s": [[op, text], ...]} with op "=", "+", "-".
    Unchanged runs longer than 6 lines keep 2 lines of context either side and
    collapse the rest into {"gap": n}.
    """
    at = [t for _, t in a]
    bt = [t for _, t in b]
    sm = difflib.SequenceMatcher(None, at, bt, autojunk=False)
    rows: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            block = [{"d": b[j][0], "s": [["=", bt[j]]]} for j in range(j1, j2)]
            if len(block) > 6:
                rows += block[:2] + [{"gap": len(block) - 4}] + block[-2:]
            else:
                rows += block
            continue
        aw = " \n ".join(at[i1:i2]).split(" ")
        bw = " \n ".join(bt[j1:j2]).split(" ")
        segs: list[list[str]] = []
        for t2, x1, x2, y1, y2 in difflib.SequenceMatcher(None, aw, bw, autojunk=False).get_opcodes():
            if t2 == "equal":
                segs.append(["=", " ".join(bw[y1:y2])])
            else:
                if x2 > x1:
                    segs.append(["-", " ".join(aw[x1:x2])])
                if y2 > y1:
                    segs.append(["+", " ".join(bw[y1:y2])])
        depth = b[j1][0] if j2 > j1 else a[i1][0]
        # split back into lines at the "\n" markers
        cur: list[list[str]] = []
        for op, text in segs:
            pieces = text.split("\n")
            for k, piece in enumerate(pieces):
                if k:
                    rows.append({"d": depth, "s": cur})
                    cur = []
                piece = piece.strip()
                if piece:
                    cur.append([op, piece])
        rows.append({"d": depth, "s": cur})
    # first rows of a file may be pure context; trim leading/trailing context to 2 lines
    return [r for r in rows if r.get("gap") or r["s"]]


def lines_of(ident: str, label: str) -> tuple[list[tuple[int, str]], str | None, str | None]:
    sec = get("/us/usc" + ident.removeprefix("/us/usc"), {"release": label})
    if sec is None:
        return [], None, None
    return reading_lines(sec["xml"]), sec.get("status"), sec.get("heading")


def analyze_section(title: str, s: dict) -> dict | None:
    ident = s["identifier"]
    v = get(f"/sections{ident}/versions")
    if v is None:
        return None
    groups = v["versions"]
    text_groups = [g for g in groups if g["change_kind"] in ("initial", "text")]
    versions = []
    for g in text_groups:
        lines, status, heading = lines_of(ident, g["releases"][0])
        versions.append({
            "release": g["first_release"]["label"],
            "date": g["first_release"]["currency_date"],
            "caveat": g["first_release"]["caveat"],
            "kind": g["change_kind"],
            "status": status if status != "None" else None,
            "status_changed": g["status_changed"],
            "attribution": g["attribution"],
            "laws": [f"{l['pl_congress']}-{l['pl_num']}" for l in g["laws"]],
            "lines": lines,
        })
    transitions = []
    for prev, cur in zip(versions, versions[1:]):
        a, b = words(prev["lines"]), words(cur["lines"])
        ins, dele, _ = word_diff(a, b)
        transitions.append({
            "from": prev["release"], "to": cur["release"], "date": cur["date"],
            "inserted": ins, "deleted": dele, "churn": ins + dele,
            "words_before": len(a), "words_after": len(b),
            "status_before": prev["status"], "status_after": cur["status"],
            "attribution": cur["attribution"], "laws": cur["laws"], "caveat": cur["caveat"],
            "editorial": ins + dele > 0 and editorial_only(prev["lines"], cur["lines"]),
            "redline": line_redline(prev["lines"], cur["lines"]),
        })
    first, last = (versions[0], versions[-1]) if versions else (None, None)
    churn = sum(t["churn"] for t in transitions)
    substantive = [t for t in transitions if t["churn"] and not t["editorial"]]
    w0 = len(words(first["lines"])) if first else 0
    w1 = len(words(last["lines"])) if last else 0
    net_ins, net_del, _ = word_diff(words(first["lines"]), words(last["lines"])) if first else (0, 0, [])
    return {
        "title": title,
        "identifier": ident,
        "num": s.get("num"),
        "heading": s.get("heading"),
        "status_now": s.get("status"),
        "first_release": groups[0]["first_release"]["label"],
        "first_date": groups[0]["first_release"]["currency_date"],
        "last_release": groups[-1]["last_release"]["label"],
        "last_seq": groups[-1]["last_release"]["seq"],
        "version_groups": len(groups),
        "text_versions": len(versions),
        "text_changes": len(transitions),
        "churn": churn,
        "substantive_churn": sum(t["churn"] for t in substantive),
        "substantive_changes": len(substantive),
        "editorial_changes": sum(1 for t in transitions if t["editorial"]),
        "inserted": sum(t["inserted"] for t in transitions),
        "deleted": sum(t["deleted"] for t in transitions),
        "net_churn": net_ins + net_del,
        "words_first": w0,
        "words_last": w1,
        "relative_churn": round(churn / max(w0, w1, 1), 4),
        "repeal_in_window": any(t["status_after"] in ("repealed", "omitted", "transferred")
                                and t["status_before"] != t["status_after"] for t in transitions),
        "versions": [{k: x[k] for k in ("release", "date", "kind", "status", "attribution", "laws")}
                     | {"words": len(words(x["lines"]))} for x in versions],
        "first_text": first["lines"] if first else [],
        "last_text": last["lines"] if last else [],
        "transitions": transitions,
        "net_redline": line_redline(first["lines"], last["lines"]) if len(transitions) > 1 else None,
    }


def tsv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(c, "")) if not isinstance(r.get(c), list)
                              else ",".join(map(str, r[c])) for c in cols) + "\n")


def main(titles: list[str], top_n: int = 50) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for t in titles:
        for s in json.loads((CACHE / f"t{t}-sections.json").read_text()):
            if s.get("skipped"):
                continue
            r = analyze_section(t, s)
            if r:
                results.append(r)
    cols = ["title", "identifier", "num", "heading", "status_now", "first_release",
            "text_versions", "text_changes", "substantive_changes", "editorial_changes",
            "substantive_churn", "churn", "inserted", "deleted", "net_churn",
            "words_first", "words_last", "relative_churn", "repeal_in_window"]
    results.sort(key=lambda r: (-r["substantive_churn"], -r["churn"], -r["text_changes"], r["identifier"]))
    tsv(OUT / "sections.tsv", results, cols)
    changed = [r for r in results if r["substantive_churn"] > 0]
    top = changed[:top_n]
    for i, r in enumerate(top, 1):
        r["rank"] = i
    tsv(OUT / "top.tsv", top, ["rank"] + cols)
    trows = [{"identifier": r["identifier"], **{k: v for k, v in t.items() if k != "redline"}}
             for r in results for t in r["transitions"]]
    tsv(OUT / "transitions.tsv", trows,
        ["identifier", "from", "to", "date", "inserted", "deleted", "churn", "editorial", "words_before",
         "words_after", "status_before", "status_after", "attribution", "laws"])
    # release-point axis for the overview
    releases = sorted({(t["date"], t["to"]) for r in results for t in r["transitions"]})
    summary = {}
    for t in titles:
        rs = [r for r in results if r["title"] == t]
        summary[t] = {
            "sections": len(rs),
            "sections_with_text_change": sum(1 for r in rs if r["churn"] > 0),
            "text_changes": sum(r["text_changes"] for r in rs),
            "churn_words": sum(r["churn"] for r in rs),
            "substantive_churn_words": sum(r["substantive_churn"] for r in rs),
            "sections_with_substantive_change": sum(1 for r in rs if r["substantive_churn"] > 0),
            "editorial_only_changes": sum(r["editorial_changes"] for r in rs),
            "zero_word_text_changes": sum(1 for r2 in rs for t in r2["transitions"] if t["churn"] == 0),
            "first_release": min((r["first_release"] for r in rs), default=None),
        }
    payload = {
        "method": "substantive churn = words inserted + words deleted, summed over every "
                  "consecutive pair of text versions (uscode-redesign change_kind initial/text) of "
                  "the section's reading text (notes, source credit and footnote markers excluded), "
                  "leaving out changes that only add or drop \"of this section/title/...\"",
        "summary": summary,
        "window": {
            "from": min(results, key=lambda r: r["first_date"])["first_release"],
            "to": max(results, key=lambda r: r["last_seq"])["last_release"],
        },
        "releases": [{"date": d, "label": l} for d, l in releases],
        "top": [{k: v for k, v in r.items()} for r in top],
        "all": [{k: r[k] for k in cols} | {"changes": [[t["to"], t["churn"]] for t in r["transitions"]]}
                for r in results if r["churn"] > 0],
    }
    (OUT / "redlines.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["11", "24"])
