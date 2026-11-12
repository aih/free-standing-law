# free-standing-law

Analysis of single titles of the U.S. Code, and the tools that produce it, toward a repeatable
method for reviewing a title: what of the enacting laws was not codified, what is outdated, and
how the text of each section has changed.

## Contents

| Path | What it is |
|---|---|
| `tools/textchange/` | Ranks a title's sections by how many words of their text changed across the US Code mirror's release points, and writes a redline for each change (`tools/textchange/README.md`) |
| `analysis/textchange/` | That ranking for titles 11 and 24: `top.tsv`, `sections.tsv`, `transitions.tsv`, `summary.json`, `redlines.json`, `index.html` |
| `tools/uncodified/` | For one title, every section of the laws that went into it and where each section is now: the title, another title, a statutory note, or nowhere in the Code (`tools/uncodified/README.md`) |
| `analysis/uncodified/` | Those tables for titles 11 and 24: `tN.md`, `tN.csv`, `tN.json` |
| `docs/uncodified.md` | Findings from those tables, written by hand: Pub. L. 95-598's free-standing provisions and their relation to title 11, the pattern in later amending Acts, title 24 and its draft bill |

Files under `analysis/` are generated; regenerate them rather than editing them. `data/` holds
caches and downloads and is not committed.

Python 3.11 or later with `lxml`. Commands are run from the repository root.

## Build log

### 2026-11-12: provisions of the source laws not in titles 11 and 24

Moved here from aih/codification-bills, where it was built and not committed. `tools/uncodified/`
indexes every title's source credits and statutory notes at release point 119-138, reads each
source law's table of contents from the statutes API (`statutes.linkedlegislation.org`), and
disposes of each section. Title 11: 869 sections of 83 laws, 262 not in the text of any title.
Title 24: 185 sections of 61 laws, 44 not in the text of any title, joined to the draft bill's
dispositions in aih/codification-bills `drafts/t24/bill.toml`. Findings in `docs/uncodified.md`.

Re-check: `python3 -m tools.uncodified fetch-code && python3 -m tools.uncodified index &&
python3 -m tools.uncodified fetch 11 && python3 -m tools.uncodified run 11` (and 24, with
aih/codification-bills checked out beside this repository); with the same release point and
statutes API the outputs do not change. `python3 -m unittest discover -s tools/uncodified/tests -t .`
runs 11 tests.

### 2026-11-12: text change ranking for titles 11 and 24

Moved here from aih/codification-bills (PR 29, closed unmerged). `tools/textchange/` reads each
section's version history and text versions from the US Code mirror's API
(`uscode.linkedlegislation.org`, aih/uscode-redesign), diffs consecutive text versions word by
word, and ranks sections by words inserted plus deleted. Window: release points 113-21
(2013-07-18) to 119-121. 48 sections had a substantive text change: 35 in title 11 (5,103 words),
13 in title 24 (1,378 words).

Re-check: `python3 -m tools.textchange.fetch 11 24 && python3 -m tools.textchange.analyze 11 24
&& python3 -m tools.textchange.render`; with an unchanged mirror the outputs do not change.
