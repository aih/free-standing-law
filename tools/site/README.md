# Static site (`tools/site`)

Builds the browsable site at freestand.linkedlegislation.org from the committed analysis. The
site is static: every page is generated from files under `analysis/`, `docs/` and `tools/`, and
nothing is computed or stored when a page is read.

Python 3.11 or later with `markdown` (`pip install markdown==3.7`).

```
python3 -m tools.site.build              # writes _site/ (gitignored)
python3 -m http.server -d _site 8000     # preview at http://localhost:8000/
python3 -m tools.site.check_links _site  # checks every citation link against the two APIs
```

## What the build does

- Renders each Markdown file listed in `SECTIONS` (`build.py`) to HTML at the same path, with
  `.html` in place of `.md`. A file that does not exist is left out, so the list can name analyses
  that are not merged yet.
- Copies the listed CSV, TSV and JSON files, and `analysis/textchange/index.html` (the redline
  viewer, built by `tools/textchange/render.py`), unchanged.
- Writes `index.html`, which lists each analysis with its pages and data files.
- Links citations in the rendered text:

| Text | Link |
|---|---|
| `11 U.S.C. 362(b)(4)` | `https://uscode.linkedlegislation.org/us/usc/t11/s362/b/4` |
| `24 U.S.C. 321–329`, `28 U.S.C. 2075 to 2077` | the first section of the range |
| `24 U.S.C. 271 to 276 note` | `https://uscode.linkedlegislation.org/us/usc/t24/s271...276`, the range OLRC hangs the note on |
| `title 11 note` | `https://uscode.linkedlegislation.org/us/usc/t11` |
| `Pub. L. 98-353`, `Pub. L. 98-353, § 113` | `https://statutes.linkedlegislation.org/us/pl/98/353`, `…/s113` |
| `73 Stat. 594` | `https://statutes.linkedlegislation.org/us/stat/73/594` |
| `Act of May 5, 1950, ch. 169` | `https://statutes.linkedlegislation.org/us/act/1950-05-05/ch169` |
| `§ 201` in the first column of a per-law table in `analysis/uncodified/` | section 201 of the law named by the table's heading |
| a bare `https://` URL | itself |
| `` `t24.md` `` or another code span naming a published file | that file's page |

  Text inside an existing link, a code span or a code block is not linked otherwise. A Markdown
  link to a file the site does not publish points at the file on GitHub.
- In the viewer (`tools/textchange/template.html`), each change's release points link to the
  section at that release point on the US Code mirror, and each attributed law to the law on the
  Statutes at Large site.

Every link is in the citation form each site redirects from (`/us/usc/…`, `/us/pl/…`); a browser
lands on the reader under `/app`.

## Deployment

`.github/workflows/pages.yml` runs the build on every push to `main` (and on demand) and deploys
`_site/` to GitHub Pages. Repository settings it needs, set once:

- Settings → Pages → Build and deployment → Source: **GitHub Actions**.
- Settings → Pages → Custom domain: `freestand.linkedlegislation.org`, then **Enforce HTTPS** once
  the certificate is issued. A workflow deployment ignores a `CNAME` file, so the repository has
  none.
- DNS: a `CNAME` record for `freestand.linkedlegislation.org` pointing at `aih.github.io`.

Pages for a private repository needs a paid GitHub plan; the published site is public either way.

## Limitations

- U.S.C. chapters (`10 U.S.C. ch. 47`) are not linked: the mirror's chapter identifiers carry the
  subtitle and part above the chapter (`/us/usc/t10/stA/ptII/ch47`), which the citation does not give.
- `§§ 985-988`, `R.S. 4813`, `Ex. Ord. No. 10272`, draft section numbers and question ids such as
  `t24-q-0004` are not linked.
- `V Stat. P` is not linked where the page carries a letter (`114 Stat. 2763A-394`); the Statutes
  at Large site does not serve those pages.
- `check_links` reports citations whose target the APIs do not hold, listed with the pages that
  carry them. On 2026-11-12, 27 of 776: sections no longer in the Code (former 11 U.S.C. 68, 15
  U.S.C. 79k, 31 U.S.C. 191, 24 U.S.C. 106 and others, which the mirror serves only at the release
  points that held them) and Pub. L. 99-500, which the Statutes at Large site does not hold.
