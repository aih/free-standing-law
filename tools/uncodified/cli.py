"""python3 -m tools.uncodified {fetch-code,index,fetch,run} … (README.md)."""
from __future__ import annotations

import argparse

from . import analyze, fetch, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.uncodified")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-code", help="download and unzip release point 119-138 into data/uscode/xml/")
    sub.add_parser("index", help="index the Code's source credits and statutory notes (data/uncodified/)")
    f = sub.add_parser("fetch", help="fetch the statutes API responses the title needs")
    f.add_argument("title")
    f.add_argument("--api-delay", type=float, default=None)
    g = sub.add_parser("run", help="write analysis/uncodified/tN.md, .csv, .json")
    g.add_argument("title")
    a = ap.parse_args(argv)
    if a.cmd == "fetch-code":
        print(fetch.code())
        return 0
    if a.cmd == "index":
        d = analyze.code_index(rebuild=True)
        print(f"{len(d['credits'])} credited provisions, {len(d['notes'])} statutory notes")
        return 0
    idx = analyze.code_index()
    sc = analyze.scope(a.title, idx)
    if a.cmd == "fetch":
        # the Acts cited by chapter resolve first; then the tables of contents; then the text
        # of the sections the Code does not hold
        for _ in range(2):
            n, bad = fetch.responses(analyze.law_request_lines(sc), a.api_delay)
            print(f"laws: {n} fetched, {bad} failed")
        res = analyze.dispose(sc, idx)
        texts = [analyze.laws.request_line(analyze.laws.unit_path(r["identifier"]),
                                           analyze.laws.API + r["identifier"])
                 for r in res["rows"]
                 if ("not in the Code" in r["disposition"] or not r["heading"]) and r["text"] is None]
        n, bad = fetch.responses(texts, a.api_delay)
        print(f"section texts: {n} fetched, {bad} failed")
        return 0
    res = analyze.dispose(sc, idx)
    return report.write(a.title, sc, res, idx)
