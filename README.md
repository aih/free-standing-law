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
| `tools/outdated/` | Finds provisions of a title that are outdated, no longer applicable or wrong: a scanner over OLRC's release-point USLM, a checker that renders the reviewed tables, and the method (`tools/outdated/README.md`) |
| `analysis/outdated/` | Titles 11 and 24 at release point 119-138: `candidates/` (scanner output), `tables/t11.tsv`, `t24.tsv`, `t11-dollar-amounts.tsv` (reviewed) and `tables/t11.md`, `t24.md` (rendered); summary in `analysis/outdated/README.md` |

Files under `analysis/` are generated; regenerate them rather than editing them. The exception is `analysis/outdated/tables/*.tsv`, which are reviewed by hand and checked by `tools/outdated/report.py`. `data/` holds
caches and downloads and is not committed.

Python 3.11 or later with `lxml`. Commands are run from the repository root.

## Build log

### 2026-11-12: outdated, inapplicable and wrong provisions in titles 11 and 24

Moved here from aih/codification-bills (PR 30, closed unmerged). `tools/outdated/scan.py` lists
signals in the statutory text of the sections in force at release point 119-138 (OLRC footnotes,
links to repealed or missing sections anywhere in the Code, References in Text notes, Change of
Name and Termination notes, a term list, past dates, duplicate designations). Each signal was
reviewed, and the facts were checked against the enacted law and outside sources, into
`analysis/outdated/tables/`. Title 24: 31 findings (11 outdated, 12 not applicable, 8 wrong) and
8 checked signals, with the treatment in the codification-bills draft of each; 8 findings are not
raised by the draft. Title 11: 16 findings (2 outdated, 7 not applicable, 7 wrong) and 7 checked
signals; 40 printed dollar amounts differ from those in force since Apr. 1, 2025.

Re-check: `bash tools/outdated/fetch_uscode.sh 119-138`, then for N in 11 and 24,
`python3 tools/outdated/scan.py N && python3 tools/outdated/report.py N` (0 problems); `git
status` should list nothing changed.

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
