"""Build the static site in _site/ from the committed analysis.

Every Markdown file the site publishes is rendered to HTML at the same path with `.html` in
place of `.md`; data files (CSV, TSV, JSON) and the text change viewer are copied unchanged.
Citations in the rendered text are linked:

  N U.S.C. M, N U.S.C. ch. M, title N note   -> uscode.linkedlegislation.org/us/usc/...
  Pub. L. X-Y, Pub. L. X-Y, § N              -> statutes.linkedlegislation.org/us/pl/...
  V Stat. P                                  -> statutes.linkedlegislation.org/us/stat/...
  Act of <date>, ch. N                       -> statutes.linkedlegislation.org/us/act/...
  a bare https:// URL                        -> itself
  `path` naming a published file             -> that file's page

In the per-law tables of analysis/uncodified/, the first column's `§ N` is linked to section N
of the law named by the table's heading.

    python3 -m tools.site.build [--out _site]
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path

import markdown

USC = "https://uscode.linkedlegislation.org"
STAT = "https://statutes.linkedlegislation.org"
REPO = "https://github.com/aih/free-standing-law"

# What the site publishes, in index order. Entries whose file does not exist are left out.
SECTIONS = [
    ("Text change", "How the text of each section of titles 11 and 24 changed across the release points of the US Code since July 2013, ranked by words changed, with a word-level redline of every change.", [
        ("analysis/textchange/index.html", "Ranking and redline viewer"),
        ("tools/textchange/README.md", "Method"),
        ("analysis/textchange/top.tsv", "top.tsv"),
        ("analysis/textchange/sections.tsv", "sections.tsv"),
        ("analysis/textchange/transitions.tsv", "transitions.tsv"),
        ("analysis/textchange/summary.json", "summary.json"),
    ]),
    ("Uncodified provisions", "Every section of the laws that went into titles 11 and 24, and where each section is now: the title, another title, a statutory note, or nowhere in the Code.", [
        ("docs/uncodified.md", "Findings"),
        ("analysis/uncodified/t11.md", "Title 11 table"),
        ("analysis/uncodified/t24.md", "Title 24 table"),
        ("tools/uncodified/README.md", "Method"),
        ("analysis/uncodified/t11.csv", "t11.csv"),
        ("analysis/uncodified/t11.json", "t11.json"),
        ("analysis/uncodified/t24.csv", "t24.csv"),
        ("analysis/uncodified/t24.json", "t24.json"),
    ]),
    ("Outdated provisions", "Provisions of titles 11 and 24 that are outdated, no longer applicable or wrong, with the evidence for each.", [
        ("analysis/outdated/README.md", "Summary"),
        ("analysis/outdated/tables/t11.md", "Title 11 table"),
        ("analysis/outdated/tables/t24.md", "Title 24 table"),
        ("tools/outdated/README.md", "Method"),
        ("analysis/outdated/tables/t11.tsv", "t11.tsv"),
        ("analysis/outdated/tables/t11-dollar-amounts.tsv", "t11-dollar-amounts.tsv"),
        ("analysis/outdated/tables/t24.tsv", "t24.tsv"),
        ("analysis/outdated/candidates/t11.json", "candidates/t11.json"),
        ("analysis/outdated/candidates/t24.json", "candidates/t24.json"),
    ]),
    ("About", "The repository's README: contents, requirements and build log.", [
        ("README.md", "README"),
    ]),
]

DATA_SUFFIXES = {".csv", ".tsv", ".json"}

# ---------------------------------------------------------------- citations

DASH = "[-–]"
SEC = r"\d+[A-Za-z]*(?:[-–]\d+[A-Za-z]*)?"
SUB = r"(?:\([0-9A-Za-z]{1,6}\))*"
MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}

CITE = re.compile(
    r"(?P<usc>(?P<ut>\d+[a-z]?) U\.S\.C\. (?P<usec>" + SEC + r")(?P<usub>" + SUB + r")(?: to (?P<uto>" + SEC + r")(?P<unote> note)?)?)"
    r"|(?P<tnote>\b[Tt]itle (?P<tn>\d+[a-z]?) note\b)"
    r"|(?P<pl>(?:Pub\. ?L\.|Public Law|P\.L\.) (?P<pc>\d+)" + DASH + r"(?P<pn>\d+)(?:(?:,| ) ?§ (?P<ps>\d+[A-Za-z]*))?)"
    r"|(?P<stat>\b(?P<sv>\d+) Stat\. (?P<sp>\d+)\b(?![A-Za-z]))"
    r"|(?P<act>Act of (?P<am>[A-Z][a-z]+)\.? (?P<ad>\d{1,2}), (?P<ay>\d{4}), ch\. (?P<ach>\d+))"
    r"|(?P<url>https?://[^\s<>()\"']+[^\s<>()\"'.,;:])"
)


def usc_section(sec: str) -> str:
    """`1087-3` is section 1087–3; `321–329` and `225–225h` are ranges, of which the first."""
    a, sep, b = (re.split(r"([-–])", sec, maxsplit=1) + ["", ""])[:3]
    if not sep:
        return sec
    if int(re.match(r"\d+", b)[0]) >= int(re.match(r"\d+", a)[0]):
        return a
    return f"{a}–{b}"


def cite_href(m: re.Match) -> str | None:
    if m["usc"]:
        t = m["ut"]
        if m["uto"] and m["unote"] and not m["usub"]:
            return f"{USC}/us/usc/t{t}/s{m['usec']}...{m['uto']}"
        path = f"/us/usc/t{t}/s{usc_section(m['usec'])}"
        for p in re.findall(r"\(([0-9A-Za-z]+)\)", m["usub"] or ""):
            path += f"/{p}"
        return USC + path
    if m["tnote"]:
        return f"{USC}/us/usc/t{m['tn']}"
    if m["pl"]:
        path = f"/us/pl/{m['pc']}/{m['pn']}"
        if m["ps"]:
            path += f"/s{m['ps']}"
        return STAT + path
    if m["stat"]:
        return f"{STAT}/us/stat/{m['sv']}/{m['sp']}"
    if m["act"]:
        mon = MONTHS.get(m["am"][:3].lower())
        if not mon:
            return None
        return f"{STAT}/us/act/{m['ay']}-{mon:02d}-{int(m['ad']):02d}/ch{m['ach']}"
    if m["url"]:
        return html.unescape(m["url"])
    return None


def link_text(text: str) -> str:
    """Link the citations in an HTML text run (no tags inside)."""
    def sub(m: re.Match) -> str:
        href = cite_href(m)
        if not href:
            return m[0]
        cls = "url" if m["url"] else "cite"
        return f'<a class="{cls}" href="{html.escape(href)}">{m[0]}</a>'
    return CITE.sub(sub, text)


SECTION_CELL = re.compile(r"(§ (\d+[A-Za-z]*))")
LAW_HEADING = re.compile(r"Pub\. L\. (\d+)" + DASH + r"(\d+)")
TOKEN = re.compile(r"(<[^>]+>)")


def link_html(body: str, page: Path, published: set[str]) -> str:
    """Walk the rendered HTML and link citations in text outside <a>, <code> and <pre>."""
    out: list[str] = []
    skip = 0            # depth inside a, pre
    in_code = False
    code_buf: list[str] = []
    law: tuple[str, str] | None = None   # from the last h2/h3 naming a Pub. L.
    heading: list[str] | None = None
    cell = 0            # td index within the current row
    for tok in TOKEN.split(body):
        if not tok:
            continue
        if tok.startswith("<"):
            name = re.match(r"</?([a-zA-Z0-9]+)", tok)
            tag = name[1].lower() if name else ""
            closing = tok.startswith("</")
            if in_code and not (tag == "code" and closing):
                code_buf.append(tok)
                continue
            if tag in ("a", "pre"):
                skip += -1 if closing else 1
            elif tag == "code" and skip == 0:
                if not closing:
                    in_code, code_buf = True, []
                    continue
                in_code = False
                out.append(code_link("".join(code_buf), page, published))
                continue
            elif tag in ("h2", "h3"):
                if closing and heading is not None:
                    hm = LAW_HEADING.match(re.sub(r"<[^>]+>", "", "".join(heading)))
                    law = (hm[1], hm[2]) if hm else None
                    heading = None
                elif not closing:
                    heading = []
            elif tag == "tr" and not closing:
                cell = 0
            elif tag == "td" and not closing:
                cell += 1
            out.append(tok)
            continue
        if in_code:
            code_buf.append(tok)
            continue
        if heading is not None:
            heading.append(tok)
        if skip:
            out.append(tok)
        elif law and cell == 1 and is_uncodified(page) and SECTION_CELL.search(tok):
            c, n = law
            out.append(SECTION_CELL.sub(
                lambda m: f'<a class="cite" href="{STAT}/us/pl/{c}/{n}/s{m[2]}">{m[1]}</a>', tok))
        else:
            out.append(link_text(tok))
    return "".join(out)


def is_uncodified(page: Path) -> bool:
    return page.parts[:2] == ("analysis", "uncodified")


def code_link(inner: str, page: Path, published: set[str]) -> str:
    """`analysis/uncodified/t11.md` or `t24.md` beside the page -> a link to that file's page."""
    text = html.unescape(inner)
    target = resolve(text, page, published)
    if target:
        return f'<a href="{html.escape(rel(page, target))}"><code>{inner}</code></a>'
    return f"<code>{inner}</code>"


def resolve(text: str, page: Path, published: set[str]) -> str | None:
    if not re.fullmatch(r"[\w./-]+\.(md|csv|tsv|json|html)", text):
        return None
    for cand in (text, str((page.parent / text)), str(Path("analysis/outdated") / text)):
        norm = str(Path(cand)).replace("\\", "/")
        norm = re.sub(r"[^/]+/\.\./", "", norm)
        if norm in published:
            return norm
    return None


def rel(page: Path, target: str) -> str:
    out = Path(target).with_suffix(".html") if target.endswith(".md") else Path(target)
    up = "../" * (len(page.parts) - 1)
    return up + str(out)


def rewrite_md_links(body: str, page: Path, published: set[str]) -> str:
    """Markdown links between published .md files point at their .html pages; others at GitHub."""
    def sub(m: re.Match) -> str:
        href = html.unescape(m[1])
        if re.match(r"[a-z]+:|#", href):
            return m[0]
        path, _, frag = href.partition("#")
        target = re.sub(r"[^/]+/\.\./", "", str(page.parent / path)).lstrip("./")
        while "/../" in "/" + target:
            target = re.sub(r"(^|/)[^/]+/\.\./", r"\1", target)
        if target in published:
            new = rel(page, target) + (f"#{frag}" if frag else "")
        else:
            new = f"{REPO}/blob/main/{target}" + (f"#{frag}" if frag else "")
        return f'href="{html.escape(new)}"'
    return re.sub(r'href="([^"]+)"', sub, body)


# ---------------------------------------------------------------- pages

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Free-standing law</title>
<link rel="stylesheet" href="{root}site.css">
</head>
<body>
<header class="bar"><a href="{root}">Free-standing law</a><span>Titles 11 and 24 of the U.S. Code</span></header>
<main>
{nav}
{body}
</main>
<footer>Generated from <a href="{repo}/blob/main/{src}">{src}</a> in <a href="{repo}">aih/free-standing-law</a>.
Citations link to the US Code mirror (uscode.linkedlegislation.org) and the Statutes at Large site (statutes.linkedlegislation.org).</footer>
</body>
</html>
"""

CSS = """
:root { --ink: #1b1b1f; --ink-2: #4a4a55; --rule: #d9d9e0; --sheet: #fff; --bg: #f6f6f3; --link: #2f4fa0; --code: #f0f0ec; }
@media (prefers-color-scheme: dark) { :root { --ink: #e8e8ea; --ink-2: #b0b0ba; --rule: #3a3a44; --sheet: #1c1c21; --bg: #141418; --link: #9bb3f0; --code: #2a2a31; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
a { color: var(--link); }
a.cite { text-decoration-style: dotted; text-underline-offset: 2px; white-space: nowrap; }
a.url { overflow-wrap: anywhere; }
.bar { display: flex; gap: 1rem; align-items: baseline; flex-wrap: wrap; padding: .7rem 1rem; border-bottom: 1px solid var(--rule); background: var(--sheet); }
.bar a { font-weight: 600; text-decoration: none; color: var(--ink); }
.bar span { color: var(--ink-2); font-size: .9rem; }
main { max-width: 72rem; margin: 0 auto; padding: 1rem; }
nav.crumbs { font-size: .9rem; color: var(--ink-2); margin-bottom: .5rem; }
h1 { font-size: 1.6rem; line-height: 1.25; }
h2 { font-size: 1.25rem; margin-top: 2rem; }
h3 { font-size: 1.05rem; margin-top: 1.5rem; }
code { font: .88em ui-monospace, "SFMono-Regular", Menlo, monospace; background: var(--code); padding: 0 .25em; border-radius: 3px; }
pre { background: var(--code); padding: .75rem; overflow-x: auto; }
pre code { background: none; padding: 0; }
.table { overflow-x: auto; margin: 1rem 0; }
table { border-collapse: collapse; font-size: .88rem; background: var(--sheet); }
th, td { border: 1px solid var(--rule); padding: .35rem .5rem; vertical-align: top; text-align: left; }
th { position: sticky; top: 0; background: var(--sheet); }
td[style*="right"], th[style*="right"] { font-variant-numeric: tabular-nums; }
.card { background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px; padding: 1rem 1.25rem; margin: 1rem 0; }
.card h2 { margin-top: 0; }
.card ul { padding-left: 1.2rem; margin: .5rem 0 0; }
.card .data { color: var(--ink-2); font-size: .9rem; }
footer { max-width: 72rem; margin: 2rem auto; padding: 0 1rem; color: var(--ink-2); font-size: .85rem; }
"""


def render_md(src: Path, page: Path, published: set[str]) -> tuple[str, str]:
    text = src.read_text()
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"],
                             extension_configs={"toc": {"permalink": False}})
    body = rewrite_md_links(body, page, published)
    body = link_html(body, page, published)
    body = re.sub(r"(<table>.*?</table>)", r'<div class="table">\1</div>', body, flags=re.S)
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    title = re.sub(r"<[^>]+>", "", m[1]) if m else page.stem
    return title, body


def index_body(published: set[str]) -> str:
    parts = ["<h1>Free-standing law: titles 11 and 24 of the U.S. Code</h1>",
             "<p>A proof-of-concept review of single titles of the U.S. Code: how the text of each "
             "section has changed, which provisions of the enacting laws were never codified, and "
             "which provisions are outdated, no longer applicable or wrong. Title 11 (Bankruptcy) is "
             "positive law; title 24 (Hospitals and Asylums) is the subject of a draft codification "
             "bill in aih/codification-bills.</p>"]
    for name, blurb, entries in SECTIONS:
        present = [(p, label) for p, label in entries if p in published]
        if not present:
            continue
        pages = [(p, l) for p, l in present if Path(p).suffix not in DATA_SUFFIXES]
        data = [(p, l) for p, l in present if Path(p).suffix in DATA_SUFFIXES]
        items = "".join(f'<li><a href="{rel(Path("index.html"), p)}">{html.escape(l)}</a></li>' for p, l in pages)
        dl = ""
        if data:
            dl = '<p class="data">Data: ' + ", ".join(
                f'<a href="{p}">{html.escape(l)}</a>' for p, l in data) + "</p>"
        parts.append(f'<section class="card"><h2>{html.escape(name)}</h2><p>{html.escape(blurb)}</p><ul>{items}</ul>{dl}</section>')
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_site")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    published = {p for _, _, entries in SECTIONS for p, _ in entries if Path(p).exists()}
    for p in sorted(published):
        src, page = Path(p), Path(p)
        dest = out / page
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".md":
            title, body = render_md(src, page, published)
            root = "../" * (len(page.parts) - 1)
            crumbs = f'<nav class="crumbs"><a href="{root}">All analyses</a></nav>'
            (out / page.with_suffix(".html")).write_text(PAGE.format(
                title=html.escape(title), root=root, nav=crumbs, body=body, repo=REPO, src=p))
        else:
            shutil.copyfile(src, dest)
    (out / "index.html").write_text(PAGE.format(
        title="Titles 11 and 24", root="", nav="", body=index_body(published), repo=REPO, src="tools/site/build.py"))
    (out / "site.css").write_text(CSS.lstrip())
    (out / ".nojekyll").write_text("")
    n = sum(1 for _ in out.rglob("*") if _.is_file())
    print(f"wrote {n} files to {out}/ ({len(published)} sources)")


if __name__ == "__main__":
    main()
