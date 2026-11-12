# Outdated, inapplicable and wrong provisions (`tools/outdated`)

How this repository finds the provisions of one title of the Code that are outdated, no longer
applicable or wrong, and records each one with its evidence. The method runs on any title in
OLRC's release-point USLM; titles 11 and 24 at release point 119-138 are the first two runs
(`analysis/outdated/tables/`).

## Categories

| Category | Meaning | Examples |
|---|---|---|
| Outdated | The text describes facts that no longer hold: an institution closed or transferred, a body abolished or renamed, a place that no longer exists, an obsolete term | 24 U.S.C. 18 (a hospital conveyed to Arkansas in 1960); 11 U.S.C. 101(21B)(C) (the Resolution Trust Corporation) |
| Not applicable | The provision is spent: a deadline, an appropriation, a report, a transition or a condition that has run or can no longer occur | 24 U.S.C. 225g(a) (appropriations for fiscal years 1988 to 1991); 11 U.S.C. 362(b)(12), (13) (petitions filed on or before Dec. 31, 1989) |
| Wrong | The text is in error: a reference to a provision repealed, transferred or redesignated, a misprint, a misplaced or duplicated designation | 11 U.S.C. 901(b) (cites § 103(e), redesignated (f)); 24 U.S.C. 421(b)(1) (cites 5 U.S.C. 5532, repealed) |
| Checked | A signal the scanner raised that review found is not a finding, with the reason | 11 U.S.C. 1110(d) (equipment placed in service before 1994 is still flying) |

Confidence is high when the text and an enacted law or an official record settle the question,
medium when an outside source settles the facts but whether the provision still has a use
needs the agency, and low when the finding is a matter of wording.

## Steps

1. **Release point.** `bash tools/outdated/fetch_uscode.sh 119-138` downloads OLRC's XML for every
   title at the release point, checks its sha256 where one is recorded, and unzips it into
   `data/uscode/xml/` (gitignored).
2. **Scan.** `python3 tools/outdated/scan.py N` reads `data/uscode/xml/uscNN.xml` and writes
   `analysis/outdated/candidates/tN.json`: every signal in the statutory text of the sections in
   force (notes and source credits are read only for the two note signals). The signals:
   - `footnote`: an OLRC footnote in the text ("So in original", "See References in Text note",
     "See Adjustment of Dollar Amounts notes"), with the words before the mark;
   - `dead-ref`: a link to a Code section that is repealed, omitted, transferred or reserved,
     or that has no identifier, at the release point (an index of every section in every title,
     cached in `data/uscode/xml/.section-status.json`);
   - `rit-note`: a References in Text note saying the provision referred to was repealed,
     omitted, terminated, abolished, renamed, redesignated or transferred;
   - `status-note`: a note headed Change of Name, Transfer of Functions, Abolition,
     Termination, Expiration, Sunset, Reorganization Plan or Savings Provision;
   - `term`: a match from `tools/outdated/terms.tsv` (bodies abolished or renamed, former
     places, obsolete terms; each row gives the reason). The list grows with each title;
   - `date`: a year before the release point's, in a phrase that sets a time ("not later than",
     "before", "fiscal year", "beginning", "until" …);
   - `dup-num`: two sibling units with the same designation.
3. **Read the whole title.** The scanner finds text that names a dated thing; it cannot see a
   provision about an institution that has closed when the text names nothing dated (24 U.S.C.
   13, "marine hospitals"). Read every section in force and add those.
4. **Establish the facts.** For each candidate, in this order:
   - the Code's own notes and the enacted law (the References in Text note, the amendment notes,
     the Statutes at Large page of a later law that repealed, conveyed or abolished, cited by its
     govinfo URL);
   - the law that replaced a body or program (a reorganization plan, a transfer statute, an
     Act that restated it);
   - for facts outside the law (a hospital closed, a facility renamed), an official or
     institutional source: the agency, the National Park Service, the National Register, a State
     encyclopedia. Record the source in the row.
   A finding that turns on whether anyone still uses the provision (an open claim, a pending
   Bankruptcy Act case) is medium confidence, and the row names the agency that can confirm it.
5. **Record.** One row per finding in `analysis/outdated/tables/tN.tsv`: id (`tN-o-`, `-n-`, `-w-`, `-c-`
   for the category), the section, the units, category, confidence, finding, evidence and
   recommendation. For a title with a draft bill, two more columns: the draft section and how
   the draft treats the provision (restated unchanged, restated with a question, corrected,
   omitted, repealed), read from the draft (for title 24, `drafts/t24/title.toml` and its markers in aih/codification-bills). Every signal the
   scanner raised must be accounted for by a row: a finding, or a `checked` row saying why it is
   not one.
6. **Check and render.** `python3 tools/outdated/report.py N` checks that every unit a row
   names is an identifier in the title's USLM and that every signal is accounted for, and
   writes `analysis/outdated/tables/tN.md`. It exits 1 on a failure.

## Recommendations

The recommendation column uses the dispositions of a codification bill (aih/codification-bills, `docs/methodology.md`
section 5): repeal as obsolete, omit as executed or superseded, substitute a current reference
with a revision note, correct a misprint. A finding in a positive law title (title 11) is a
candidate for a technical corrections bill. A finding that changes who or what the law reaches
(striking an exception, replacing a reference to a repealed authority with a current one) is a
policy question, and the row says so.

## Limitations

- The scanner reads the text of the sections in force. Statutory notes that are law (a
  provision set out as a note) are scanned only through the section they sit under.
- `date` and `term` are word rules; most of what they raise in a long title is not a finding
  (title 11: 9 date and 21 term signals, 2 findings among the dates).
- Facts about institutions come from secondary sources where no enacted law states them (the
  closing of Gorgas Hospital, the current name of the Battle Mountain campus). Each such row
  names its source.
- Whether a spent-looking provision still has a use (a claim accrued before 1987, a Bankruptcy
  Act case still open) needs the agency; those rows are medium confidence.
