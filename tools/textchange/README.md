# Text change ranking (`tools/textchange`)

Ranks the sections of one or more Code titles by how many words of their statutory text changed
across the release points held by the US Code mirror (`aih/uscode-redesign`, deployed at
`uscode.linkedlegislation.org`), and writes a word-level redline for every change.

Python 3.11 or later with `lxml`; network access to `uscode.linkedlegislation.org`.

## Running it

```
python3 -m tools.textchange.fetch 11 24      # about 25 minutes cold; cached under data/textchange/
python3 -m tools.textchange.analyze 11 24    # seconds; writes analysis/textchange/*.tsv, *.json
python3 -m tools.textchange.render           # writes analysis/textchange/index.html
```

`fetch` caches every API response under `data/textchange/cache/` (gitignored), so a rerun fetches
only what is new. Delete the cache to pick up release points published since the last run.
Any title the mirror holds can be passed (`python3 -m tools.textchange.fetch 5 41`); `render`
draws whatever `analyze` last wrote.

## Steps

1. **Sections.** `fetch` walks the title's table of contents (`GET /api/v1/us/usc/t{N}` and each
   chapter and subchapter below it) and lists every section. A row whose identifier names a range
   of sections (`/us/usc/t24/s7...12`) is a repealed or omitted block with no text of its own and
   is skipped; title 24 has 40 of them.
2. **Version groups.** For each section, `GET /api/v1/sections/{identifier}/versions` returns the
   section's version groups in order. Each carries uscode-redesign's change classification
   (ADR-0074): `initial`, `text` (the reading text changed), `notes` (only the notes changed) or
   `structure` (only the XML or metadata changed), and the Public Laws the classification tables
   attribute the change to.
3. **Text versions.** For the `initial` group and every `text` group, `fetch` takes the section's
   XML at the group's first release point (`GET /api/v1/us/usc/t{N}/s{n}?release=…`). `notes` and
   `structure` groups have the same reading text as the group before them and are not fetched.
4. **Reading text.** `analyze.reading_lines` reduces the XML to one line per provision: the
   section's and each level's number, heading, chapeau, content and continuation. It leaves out
   notes, the source credit, any table of contents, and footnote markers (`ref class="footnoteRef"`
   and a `sup` holding only a footnote number).
5. **Per change.** Each consecutive pair of text versions is compared word by word
   (`difflib.SequenceMatcher`, no autojunk). The change's **churn** is words inserted plus words
   deleted. A change is **editorial** when the two texts are identical once OLRC's
   "of this section", "of this title", "of this chapter" (and subchapter, part, subtitle,
   subpart) are removed from both.
6. **Per section.** **Substantive churn** is the sum of churn over the section's changes that are
   not editorial. The ranking is by substantive churn, then total churn, then number of changes.
   **Net churn** compares the first text held with the latest; it is lower than substantive churn
   where text was added and later taken out again (a temporary provision that expired).
7. **Redline.** Each change is aligned line by line, then word by word inside the lines that
   differ. Unchanged runs of more than six lines keep two lines of context either side.

## Outputs (`analysis/textchange/`, regenerated, not edited)

| File | Contents |
|---|---|
| `top.tsv` | The ranked sections with any substantive change, up to 50 |
| `sections.tsv` | Every section analyzed, with its counts, in ranking order |
| `transitions.tsv` | Every text change: release points, date, words inserted and deleted, editorial flag, attributed laws |
| `summary.json` | Counts per title |
| `redlines.json` | Everything `render` draws, including each change's redline |
| `index.html` | The ranked list and the redlines, one page, no network access needed but its fonts |

## Limitations

- The mirror's history starts at release point 113-21 (2013-07-18). A change enacted before then
  is not seen; for title 11 that includes the Bankruptcy Abuse Prevention and Consumer Protection
  Act of 2005 (Pub. L. 109-8). A section that first appears after 113-21 (title 11's subchapter V
  of chapter 11, §§ 1181 to 1195, and § 1232) is counted from its first text, so its enactment is
  not a change.
- A release point is a snapshot, so two laws that reach the Code between the same two release
  points are one change, attributed to both.
- A change with no attributed law is usually one no Public Law in the window made: the expiry of a
  temporary provision (the CARES Act and Consolidated Appropriations Act, 2021 amendments to title
  11) or an editorial change by OLRC (the 2014 removal of "of this section" in title 24).
- Thirteen title 11 changes the mirror classifies as `text` have no word churn: they add a footnote
  ("So in original"), or change only a footnote marker or an attribute.
- The editorial test recognizes only the "of this …" phrases. A change that also updates a
  citation's form (title 16 → title 54) counts as substantive.
