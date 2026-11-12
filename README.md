# free-standing-law

Analysis of single titles of the U.S. Code, and the tools that produce it, toward a repeatable
method for reviewing a title: what of the enacting laws was not codified, what is outdated, and
how the text of each section has changed.

## Contents

| Path | What it is |
|---|---|
| `tools/textchange/` | Ranks a title's sections by how many words of their text changed across the US Code mirror's release points, and writes a redline for each change (`tools/textchange/README.md`) |
| `analysis/textchange/` | That ranking for titles 11 and 24: `top.tsv`, `sections.tsv`, `transitions.tsv`, `summary.json`, `redlines.json`, `index.html` |

Files under `analysis/` are generated; regenerate them rather than editing them. `data/` holds
caches and downloads and is not committed.

Python 3.11 or later with `lxml`. Commands are run from the repository root.

## Build log

### 2026-11-12: text change ranking for titles 11 and 24

Moved here from aih/codification-bills (PR 29, closed unmerged). `tools/textchange/` reads each
section's version history and text versions from the US Code mirror's API
(`uscode.linkedlegislation.org`, aih/uscode-redesign), diffs consecutive text versions word by
word, and ranks sections by words inserted plus deleted. Window: release points 113-21
(2013-07-18) to 119-121. 48 sections had a substantive text change: 35 in title 11 (5,103 words),
13 in title 24 (1,378 words).

Re-check: `python3 -m tools.textchange.fetch 11 24 && python3 -m tools.textchange.analyze 11 24
&& python3 -m tools.textchange.render`; with an unchanged mirror the outputs do not change.
