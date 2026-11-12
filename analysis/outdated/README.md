# Outdated, inapplicable and wrong provisions

Per-title tables of provisions that are outdated, no longer applicable or wrong, at release point
119-138, with the evidence for each. Method and categories: [`tools/outdated/README.md`](../../tools/outdated/README.md).

| Title | Table | Rendered | Outdated | Not applicable | Wrong | Checked |
|---|---|---|---:|---:|---:|---:|
| 11 Bankruptcy (positive law) | `tables/t11.tsv`, `tables/t11-dollar-amounts.tsv` | [tables/t11.md](tables/t11.md) | 2 | 7 | 7 | 7 |
| 24 Hospitals and Asylums (draft bill in aih/codification-bills, `drafts/t24/`) | `tables/t24.tsv` | [tables/t24.md](tables/t24.md) | 11 | 12 | 8 | 8 |

```
bash tools/outdated/fetch_uscode.sh 119-138
python3 tools/outdated/scan.py 11 && python3 tools/outdated/report.py 11
python3 tools/outdated/scan.py 24 && python3 tools/outdated/report.py 24
```

## Title 24

Eleven provisions describe institutions that have closed, moved or changed hands:

| Former section | Draft | Institution | What happened |
|---|---|---|---|
| 18, 20 | 302, 304 | Army and Navy General Hospital, Hot Springs, Ark. | Conveyed to Arkansas by Pub. L. 86-323 (73 Stat. 594); deeded Apr. 1, 1960 |
| 19 | 303 | Fort Bayard tuberculosis hospital, N.M. | Veterans Bureau/VA 1922-1965, then the State of New Mexico |
| 301, 302 | 306, 307 | Gorgas Hospital, Canal Zone | Canal Zone ended Oct. 1, 1979; U.S. service ended Oct. 1, 1997 |
| 13 | 301 | Marine hospitals | Public Health Service hospitals closed or transferred by Oct. 31, 1981 (42 U.S.C. 248b) |
| 14 (asylum clause), 17 | 101, 111 | Naval Asylum | Moved to Gulfport in 1976; now Armed Forces Retirement Home-Gulfport (24 U.S.C. 411(c)(2)) |
| 225d(c)(1) | 705 | D.C. General Hospital; D.C. Department of Human Services | Hospital closed 2001; mental health now the Department of Behavioral Health (D.C. Law 20-61) |
| 152 | 502 | Battle Mountain Sanitarium | Still VA-operated, as the Hot Springs campus of VA Black Hills; the name is the only outdated part |

Most of the Saint Elizabeths Hospital chapter (former 24 U.S.C. 225-225h, draft chapter 7)
is spent: plans, transfers and appropriations dated 1985 to 1993. The draft carries every row
above forward. Of the 31 findings, 23 already carry a question or correction in the draft (some
through the chapter-wide question t24-q-0008), and 8 are not raised by the draft: 24 U.S.C. 13
("marine hospitals"), the Naval Asylum clauses of §§ 14 and 17, the Battle Mountain Sanitarium
name in § 152, the 1902 claims and lieu selection in § 153, the abolished and renamed
committees in §§ 225b, 225c and 225f, the fiscal 1992-1993 report in § 225h(c), and "legally
adjudged insane" in § 321(d)(2).

## Title 11

Title 11 is positive law, so a finding here is a candidate for a technical corrections bill,
not a codification disposition. Groups:

- References to repealed or redesignated law: FDICIA § 409 in §§ 103(e), 109(b)(2), 109(d)
  and 781(3) (repealed 2010, which leaves subchapter V of chapter 7 with no possible debtor);
  § 103(e) for (f) in §§ 901(b), 902 and 943(b)(1); § 1202(c) in § 1226(b)(2); 42 U.S.C. 2751
  in § 541(b)(3); § 1182(1) in § 104.
- Spent provisions: § 362(b)(12) and (13) (petitions filed on or before Dec. 31, 1989); the
  Bankruptcy Act alternatives in §§ 524(b)(1)(A), 727(a)(8) and (9) (six- and eight-year
  windows that no Bankruptcy Act case can meet); the 1994 phase-in in § 330(b)(2); the
  Resolution Trust Corporation in § 101(21B)(C).
- Printed dollar amounts: 40 amounts in 11 sections differ from the amounts in force since
  Apr. 1, 2025 (`tables/t11-dollar-amounts.tsv`).
- Nine misprints OLRC footnotes as "So in original".

## Outside sources

Facts not stated in an enacted law:

| Row | Source |
|---|---|
| t24-o-01, o-02 | Encyclopedia of Arkansas, "Army and Navy Hospital" (encyclopediaofarkansas.net); NPS, nps.gov/places/army-and-navy-hospital.htm |
| t24-o-03 | National Register of Historic Places nomination 02000726, Fort Bayard Historic District (npgallery.nps.gov/NRHP/GetAsset/NRHP/02000726_text) |
| t24-o-04, o-05 | Hektoen International, "Gorgas Hospital, Ancon, Panama" (hekint.org/2017/02/24/gorgas-hospital-ancon-panama/) |
| t24-o-06 | National Library of Medicine, "Images from the History of the Public Health Service" (nlm.nih.gov/exhibition/phs_history/seamen.html) |
| t24-o-07, o-08 | Armed Forces Retirement Home, "AFRH-Gulfport history" (afrh.gov/locations/afrh-g-history) |
| t24-o-09 | Sen. John Thune, release of June 27, 2022 (AIR Commission); VA Black Hills Health Care System record of decision, Jan. 3, 2017 (achp.gov) |
| t24-o-10, n-05 | D.C. Code § 7-1141.02 (Department of Behavioral Health Establishment Act of 2013, D.C. Law 20-61); "District of Columbia General Hospital" (Wikipedia) |
| t11-n-06 | Conrail's division between CSX and Norfolk Southern (1999) |

Retrieved 2026-11-12. Pub. L. 86-323 (73 Stat. 594) is
https://www.govinfo.gov/content/pkg/STATUTE-73/pdf/STATUTE-73-Pg594.pdf.
