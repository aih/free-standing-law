"""Downloads: OLRC's release point of the whole Code, and the statutes API's responses.

The Code is `xml_uscAll@119-138.zip` from uscode.house.gov, saved under `data/uscode/` and
unzipped into `data/uscode/xml/`. Each statutes API response is saved as JSON at the path
`laws.py` reads it from, under `data/uncodified/statutes-api/`; a saved response is not fetched
again. Requests are paced at one a second, or at `--api-delay` with a token
(`STATUTES_API_TOKEN`, sent as `Authorization: Bearer`). A request that fails is listed in
`data/uncodified/unavailable.tsv` and is tried again on the next run.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .laws import ROOT

UA = "free-standing-law-uncodified/1.0"
CODE_URL = "https://uscode.house.gov/download/releasepoints/us/pl/119/138/xml_uscAll@119-138.zip"
CODE_ZIP = ROOT / "data/uscode/xml_uscAll@119-138.zip"
CODE_XML = ROOT / "data/uscode/xml"
UNAVAILABLE = ROOT / "data/uncodified/unavailable.tsv"


def code() -> Path:
    if not CODE_ZIP.exists():
        CODE_ZIP.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(CODE_URL, headers={"User-Agent": UA})
        tmp = CODE_ZIP.with_suffix(".part")
        with urllib.request.urlopen(req, timeout=600) as r, tmp.open("wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        tmp.rename(CODE_ZIP)
    with zipfile.ZipFile(CODE_ZIP) as z:
        z.extractall(CODE_XML)
    return CODE_XML


def responses(items: list[tuple[Path, str]], delay: float | None = None) -> tuple[int, int]:
    """Fetch each (path, url) not yet saved. Returns (fetched, failed)."""
    token = os.environ.get("STATUTES_API_TOKEN")
    if delay is None:
        delay = 0.12 if token else 1.0
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    fetched, failed = 0, []
    for path, url in dict.fromkeys(items):
        if path.exists():
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                data = json.loads(r.read())
        except (urllib.error.URLError, ValueError, TimeoutError) as e:
            failed.append(f"{url}\t{getattr(e, 'code', '') or type(e).__name__}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            fetched += 1
        time.sleep(delay)
    if failed:
        UNAVAILABLE.parent.mkdir(parents=True, exist_ok=True)
        with UNAVAILABLE.open("a", encoding="utf-8") as f:
            f.write("".join(ln + "\n" for ln in failed))
    return fetched, len(failed)
