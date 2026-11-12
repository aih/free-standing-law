"""The sections of a source law, from the statutes API, read from `data/uncodified/statutes-api/`.

A law's table of contents is `GET /api/v1/laws/{congress}/{number}` (saved as
`data/uncodified/statutes-api/laws/{c}/{n}.json`); a law cited by date and chapter is first resolved
through `GET /api/v1/us/act/{date}/ch{n}` (saved under its identifier), which names the public
law it is an alias of, if any, and lists its children. One section's text is
`GET /api/v1{identifier}`. Nothing here fetches; `fetch.py` does.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://statutes.linkedlegislation.org/api/v1"
CACHE = ROOT / "data/uncodified/statutes-api"


def unit_path(identifier: str) -> Path:
    return CACHE / (identifier.lstrip("/") + ".json")


def toc_path(law: str) -> Path | None:
    m = re.fullmatch(r"/us/pl/(\d+)/(\d+)", law)
    return CACHE / f"laws/{m[1]}/{m[2]}.json" if m else None


def request_line(path: Path, url: str, note: str = "") -> tuple[Path, str]:
    """A response to fetch: where it is cached, and its URL."""
    return (path, url)


def load(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def resolve(law: str) -> str | None:
    """The public law a `/us/act/…` identifier is an alias of, from its saved unit JSON; the
    identifier itself for a public law, or for an Act the API serves under its chapter."""
    if law.startswith("/us/pl/"):
        return law
    d = load(unit_path(law))
    if not d:
        return None
    return (d.get("law") or {}).get("identifier") or d.get("served_identifier")


def act_sections(law: str) -> list[dict] | None:
    """Every section of a law at the Act's own level, in reading order: identifier, num,
    heading, container (the title or division holding it), and `encloses` (a structural
    unit a section contains: section 101 of Pub. L. 95-598 contains title 11). Sections
    inside another section (an enacted title, quoted text) are not the Act's sections."""
    served = resolve(law)
    if served is None:
        return None
    toc = None
    d = load(toc_path(served))
    if d and d.get("toc"):
        toc = d["toc"]
    else:
        u = load(unit_path(served)) or load(unit_path(law))
        if u and u.get("children"):
            toc = u["children"]
    if toc is None:
        return None
    out, by_id = [], {}
    for e in toc:
        ident = e["identifier"]
        rest = ident[len(served):].strip("/").split("/") if ident.startswith(served) else []
        segs = [s for s in rest if s]
        s_idx = [i for i, s in enumerate(segs) if re.fullmatch(r"s\d.*|s[A-Z].*", s)]
        if e.get("is_section") and len(s_idx) == 1 and s_idx[0] == len(segs) - 1:
            cont = served + "".join("/" + s for s in segs[:-1])
            row = {"identifier": ident, "num": e.get("num"), "heading": e.get("heading"),
                   "container": cont, "encloses": []}
            out.append(row)
            by_id[ident] = row
        elif s_idx and not e.get("is_section"):
            owner = served + "".join("/" + s for s in segs[: s_idx[0] + 1])
            if owner in by_id and e.get("level") == "title" and len(segs) == s_idx[0] + 2:
                by_id[owner]["encloses"].append(f"{e.get('level')} {e.get('num')}")
    return out


def containers(law: str) -> dict[str, dict]:
    """The structural units above sections (titles, divisions, subtitles), by identifier."""
    served = resolve(law)
    d = load(toc_path(served)) if served else None
    out = {}
    for e in (d or {}).get("toc") or []:
        if not e.get("is_section"):
            out[e["identifier"]] = e
    return out


def section_text(identifier: str) -> str | None:
    d = load(unit_path(identifier))
    if not d:
        return None
    t = d.get("text") or ""
    return " ".join(t.split()) or None


def is_appropriations(law: str) -> bool:
    d = load(toc_path(law)) or load(unit_path(law)) or {}
    t = ((d.get("law") or {}).get("official_title") or "").lower()
    return bool(re.match(r"(?:an act )?making (?:an |\w+ )?appropriations?\b", t)) or "appropriation act" in t
