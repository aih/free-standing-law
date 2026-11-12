# Provisions of a title's source laws that are not in the title (`tools/uncodified`)

For one title of the Code: every section of the laws that went into the title, and for each
section where it is now. The tables answer which parts of those laws are not in the text of the
title (short titles, purposes, findings, effective dates, savings and transition provisions,
studies, and the like), and where each one is: set out as a statutory note, described in a note,
in the text of another title, or nowhere in the Code.

Python 3.11 or later with `lxml`; network access to `uscode.house.gov` and
`statutes.linkedlegislation.org`. Commands are run from the repository root.

## Running it

```
python3 -m tools.uncodified fetch-code     # release point 119-138, 109 MB, into data/uscode/xml/
python3 -m tools.uncodified index          # about 20 seconds; data/uncodified/index-119-138.pickle
python3 -m tools.uncodified fetch 11       # the statutes API responses title 11 needs; one a second
python3 -m tools.uncodified run 11         # analysis/uncodified/t11.md, .csv, .json
python3 -m unittest discover -s tools/uncodified/tests -t .
```

`fetch` saves each response under `data/uncodified/statutes-api/` (gitignored) and fetches only
what is not saved. With `STATUTES_API_TOKEN` set it sends the token and paces at 0.12 seconds;
without one, at one a second. Title 11 cold is about 600 requests. A request that fails is
appended to `data/uncodified/unavailable.tsv` and is tried again on the next run.

For a title with a draft bill in aih/codification-bills, `run` reads `drafts/tN/bill.toml` from
the checkout named by `CODIFICATION_BILLS`, or from `../codification-bills` beside this one.

## Sources

| Source | What it gives | Where |
|---|---|---|
| OLRC's USLM for every title at release point 119-138 | Source credits (which provisions of which laws a section's text came from) and statutory notes (which provisions are set out or described under a section) | `data/uscode/xml/usc*.xml`, from `xml_uscAll@119-138.zip` |
| The statutes API's table of contents of each law | Every section of the law at the Act's own level, with its heading and the title or division it is in | `GET /api/v1/laws/{congress}/{number}`; an Act cited by date and chapter is resolved first through `GET /api/v1/us/act/{date}/ch{n}` |
| The statutes API's text of a section | The first words of a section that the Code does not hold | `GET /api/v1/us/pl/…/s{n}` |
| The draft bill, where there is one | The draft's disposition of each former section and statutory note | aih/codification-bills `drafts/tN/bill.toml` |

## Steps

1. **Index the Code** (`index`). One pass over every title reads:
   - every section's source credit, parsed into provisions keyed by law, division and section
     number (`Pub. L. 98–353, title III, §§ 304, 363(b)` names sections 304 and 363 of Pub. L.
     98-353; `June 15, 1943, ch. 125, § 3` names section 3 of that Act);
   - every statutory note whose text begins with a citation of law followed by "provided
     that:" (the note **sets out** the provision) or by ", which provided …" (the note
     **describes** it, and usually says it was repealed or has expired). The citation before
     "as amended by" names the provision; the provisions after it are recorded as having
     amended a provision set out as a note. Notes that cite an Executive order, a
     proclamation or a reorganization plan are left out;
   - every paragraph of an amendments note that says an amendment "did not become effective"
     (or "did not take effect", "never took effect"), and the last law it names before saying so.
2. **Scope the laws.** The laws in scope are those the title's source credits name and those
   whose provisions a statutory note in the title sets out or describes. For each law the
   sections examined are:
   - every section, for the Act that enacted the title (a section that encloses it: section
     101 of Pub. L. 95-598 encloses title 11), for a law whose short title is set out as a note
     in the title, for a law of 10 sections or fewer, and for a law of more than 10 sections a
     quarter or more of which the title's credits or notes name; appropriations Acts are
     excepted from the last two;
   - otherwise the sections the title names, and every section of a title (or division) of
     the law a quarter or more of whose sections the title names. The rest of an omnibus,
     appropriations or authorization Act is out of scope.

   The enacting Act, a law whose short title is filed in the title, and a law of more than 10
   sections a quarter of which the title names are the title's **primary** laws.
3. **Fetch the laws** (`fetch`): the tables of contents, then the text of each section found
   nowhere in the Code.
4. **Dispose of each section** (`run`). A section can have more than one of:

   | Disposition | Meaning |
   |---|---|
   | `enacts` | The section encloses the title (it is the enacting section of a positive law title) |
   | `amends title` | A source credit in the title names the section |
   | `amends other titles` | A source credit in another title names it |
   | `set out` | A statutory note sets out its text |
   | `described` | A statutory note describes it (usually a provision since repealed or expired) |
   | `amends a note` | It amended a provision that is set out as a note |
   | `amendment not effective` | It amended a Code section, and that section's amendments note says the amendment did not take effect |
   | `not in the Code` | None of these |

   A section is **not in the text of any title** when it is `set out`, `described`, `amends a
   note`, `amendment not effective` or `not in the Code`; it is *partly* so when it also amends
   the text of a title (a section that amends title 11 in its subsection (a) and sets an
   effective date in (b)). Each such section gets a **kind** from its heading, then the
   headings of the notes that set it out, then the first words of its text (`KINDS` in
   `analyze.py`: short title, table of contents, findings, purposes, sense of Congress,
   effective date, study, savings and transition, construction, severability, termination,
   budgetary effects, repeal, appropriations and fees, definitions, rules, programs,
   judgeships and courts, amendment, other).

   The Markdown lists every such section of a primary law. Of another law it lists a section
   set out or described in the title or that amends a note in the title, and a section the
   Code does not hold that the title names or that sits in a title of the law the title
   mostly names.
5. **Join the draft.** For a title with a draft bill, each note and each section in the title is
   matched to the draft's disposition table.

## Outputs (`analysis/uncodified/`, regenerated, not edited)

| File | Contents |
|---|---|
| `tN.md` | The laws with counts; the kinds of provision not in the text of any title; each such section by law, with where it is; the statutory notes in the title that set out or describe law |
| `tN.csv` | Every section examined, one row each |
| `tN.json` | The same rows with the note texts, and every statutory note in the title |

## Modules

| Module | Does |
|---|---|
| `citations.py` | Parses source credits and note citations into (law, division, section) keys |
| `codeindex.py` | One pass over every title: source credits, statutory notes that set out or describe law, amendments that did not take effect |
| `laws.py` | A law's sections from the statutes API's saved table of contents |
| `fetch.py` | Downloads the release point and the statutes API responses |
| `analyze.py` | Scope (which laws, which sections), disposition of each section, its kind |
| `report.py` | The JSON, CSV and Markdown tables; the draft bill's dispositions |

## Limitations

- The Code is the index. A provision that the Code neither credits nor sets out is `not in
  the Code`, which covers an amendment to a law the Code does not classify (an amendment of
  the Bankruptcy Act of 1898 after 1978, of the Bankruptcy Rules, of the Federal Rules of
  Evidence), an amendment that never took effect and that no amendments note mentions, a
  provision executed and dropped without a note, and a provision the Code omits. The first
  words of the section's text, in the tables, tell these apart; the tool does not.
- A note that sets out only part of a section (subsection (e) of section 102 of Pub. L.
  109-8) is matched to the whole section. A source credit names sections, and a section whose
  subsections went to different places has each place listed.
- The statutes API's tables of contents come from GPO's conversion of the printed volumes,
  and some sections are missing from them (95-598 § 212; 98-353 §§ 429, 435, 453; sections a
  later law added to an Act). A section the Code names that the table of contents lacks is
  added and marked †, without its title or division. Laws enacted by reference (Pub. L.
  106-398, 106-554, 99-500) are keyed by the enacting section; the API has no table of
  contents for Pub. L. 99-500.
- The kind is a reading of headings and first words; a section can be more than one kind.
- The classification tables at uscode.house.gov (104th Congress on), which the US Code mirror
  serves at `/api/v1/classifications/pl/{c}/{n}`, give the same placements for later laws and
  are not used, so that one method covers laws of every date.
