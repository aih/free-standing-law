"""Write analysis/textchange/index.html from analysis/textchange/redlines.json."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("analysis/textchange")
TEMPLATE = Path(__file__).with_name("template.html")

METHOD = """
<p><b>Source.</b> The US Code mirror at uscode.linkedlegislation.org (aih/uscode-redesign), which
holds every OLRC release point from 113-21 (July 2013). For each section its version history
classifies every version as initial, text, notes-only or structure-only (ADR-0074) and names the
Public Laws the classification tables attribute it to.</p>
<p><b>Text compared.</b> The section's statutory text at the first release point of each text
version: number, heading, chapeau, content and continuation of every level. Notes, the source
credit and footnote markers are left out.</p>
<p><b>Metric.</b> For each change, words inserted plus words deleted (a word-level diff). A
section's score is the sum over its changes, leaving out editorial changes that only add or drop
“of this section”, “of this title” and the like. “Net” compares the first text with the latest; it
is smaller where a temporary provision was added and later expired.</p>
<p><b>Limits.</b> Nothing before July 2013 is seen, so the Bankruptcy Abuse Prevention and
Consumer Protection Act of 2005 is outside the window. Sections first enacted inside the window
(title 11, subchapter V of chapter 11) count from their first text. Two laws reaching the Code
between the same two release points are one change. Repealed ranges of title 24 with no text of
their own are skipped.</p>
<p><b>Rerun.</b> <code>python3 -m tools.textchange.fetch 11 24</code>, then
<code>analyze 11 24</code> and <code>render</code>, in aih/free-standing-law
(<code>tools/textchange/README.md</code>).</p>
"""


def main() -> None:
    data = json.loads((OUT / "redlines.json").read_text())
    for r in data["top"]:
        # the page shows first/last text only through the redlines
        r.pop("first_text", None)
        r.pop("last_text", None)
    data["method_html"] = METHOD
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*DATA*/null", blob)
    (OUT / "index.html").write_text(html)
    print(f"wrote {OUT / 'index.html'} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
