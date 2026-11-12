"""Fetch every section's version history and the XML of each text version.

Reads the uscode-redesign API (ADR-0074's change rows) and caches every response
under data/textchange/cache/, so a rerun fetches nothing it already has.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://uscode.linkedlegislation.org/api/v1"
CACHE = Path("data/textchange/cache")
UA = "free-standing-law-textchange/1.0"
DELAY = 0.25


def get(path: str, params: dict | None = None) -> dict | None:
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    key = (path + q).strip("/").replace("/", "_").replace("?", "__").replace("&", "_").replace("=", "-")
    key = urllib.parse.quote(key, safe="_-.")
    f = CACHE / f"{key}.json"
    if f.exists():
        data = json.loads(f.read_text())
        return None if data == {"__404__": True} else data
    url = API + urllib.parse.quote(path, safe="/") + q
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                data = {"__404__": True}
                break
            if e.code in (429, 502, 503, 504):
                time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                continue
            raise
    else:
        raise RuntimeError(f"gave up on {url}")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data))
    time.sleep(DELAY)
    return None if data == {"__404__": True} else data


def walk(identifier: str, out: list[dict]) -> None:
    node = get("/us/usc" + identifier.removeprefix("/us/usc"))
    if node is None:
        return
    for s in node.get("sections") or []:
        out.append(s)
    for c in node.get("children") or []:
        if not c.get("is_section"):
            walk(c["identifier"], out)


def sections_of(title: str) -> list[dict]:
    out: list[dict] = []
    walk(f"/us/usc/t{title}", out)
    seen, uniq = set(), []
    for s in out:
        if s["identifier"] not in seen:
            seen.add(s["identifier"])
            uniq.append(s)
    return uniq


def main(titles: list[str]) -> None:
    for t in titles:
        secs = sections_of(t)
        print(f"title {t}: {len(secs)} sections", file=sys.stderr)
        index = []
        for i, s in enumerate(secs):
            ident = s["identifier"]
            if " " in ident or "..." in ident:
                index.append({**s, "skipped": "range identifier"})
                continue
            v = get(f"/sections{ident}/versions")
            if v is None:
                index.append({**s, "skipped": "no versions"})
                continue
            for g in v["versions"]:
                if g["change_kind"] in ("initial", "text"):
                    get("/us/usc" + ident.removeprefix("/us/usc"), {"release": g["releases"][0]})
            index.append(s)
            if i % 25 == 0:
                print(f"  {i}/{len(secs)} {ident}", file=sys.stderr)
        p = CACHE.parent / f"t{t}-sections.json"
        p.write_text(json.dumps(index, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["11", "24"])
