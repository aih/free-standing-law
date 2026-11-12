"""Check every citation link in a built site against the two APIs it points at.

A link https://uscode.linkedlegislation.org/us/usc/... is checked as GET /api/v1/us/usc/...,
and likewise for statutes.linkedlegislation.org; a 200 is a pass. Other hosts are not checked.

    python3 -m tools.site.check_links [_site]
"""
from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

HOSTS = ("https://uscode.linkedlegislation.org", "https://statutes.linkedlegislation.org")


def status(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "free-standing-law-linkcheck", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    pages: dict[str, set[str]] = defaultdict(set)
    for f in root.rglob("*.html"):
        for href in re.findall(r'class="cite" href="([^"]+)"', f.read_text()):
            href = href.replace("&amp;", "&")
            if href.startswith(HOSTS):
                pages[href].add(str(f.relative_to(root)))
    bad = 0
    for href in sorted(pages):
        host, path = re.match(r"(https://[^/]+)(/.*)", href).groups()
        code = status(host + "/api/v1" + urllib.parse.quote(path))
        if code != 200:
            bad += 1
            print(f"{code}\t{href}\t{', '.join(sorted(pages[href]))}")
        time.sleep(0.2)
    print(f"{len(pages)} links checked, {bad} not found", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
