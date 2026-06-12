# CLAUDE.md

Guidance for AI assistants (Claude Code) working in this repository.

## What this is

A [Quarto](https://quarto.org/) website + book for an IB DP Music course ("IB Music"). It publishes:

- A **website** (`_quarto.yml`, project type `website`) — home page, curriculum map, presentations listing, resources listing, glossary.
- A **Course Book** (`book/_quarto.yml`, project type `book`, nested inside `book/`) — a PDF + HTML companion organized by IB assessment component, built to `_book/`.

Content is mostly `.qmd` (Quarto Markdown) files — prose, checklists, rubrics, and guidance for students/teachers, not application code. There is no app server, package manager, or test suite.

## Repository layout

```
_quarto.yml              Top-level website config (navbar, sidebar, theme)
index.qmd                 Website home page
curriculum-map.qmd        Two-year scope-and-sequence overview
presentations.qmd         Listing page for presentations/ (dir not currently populated)
resources.qmd             Listing page for resources/
styles.css                Site-wide CSS
presentation-nav.html     Injected nav fragment (include-after-body)

book/                     Quarto "book" sub-project
  _quarto.yml             Book config (chapters, PDF output -> ../_book)
  index.qmd               Book preface
  *-guide.qmd, *-checklist.qmd, *-criterion-guidance.qmd,
  *-common-mistakes.qmd, *-tasks.qmd
                           Per-component guidance, organized by prefix:
                             exploring-*  = Exploring Music in Context
                             ewm-*        = Experimenting with Music
                             presenting-* = Presenting Music
                             cmm-*        = Contemporary Music Maker (HL)
  *_files/                Quarto-generated supporting assets (do not hand-edit)

resources/                Reference materials (rubrics, subject guide, glossary page)
  glossary.qmd            Interactive glossary page (generated content + custom JS/CSS)
  _All DP Music Rubrics.md
  rubricTerms.pdf, rubrics.qmd, subject-guide.qmd, assessment-guidance.qmd

pdfs/                      Source PDFs (IB subject guide, subject reports, additional guidance)

_extensions/debruine/glossary/  Quarto extension providing the {{< glossary-... >}} shortcode

music-dictionary.org       SOURCE OF TRUTH for glossary terms (Org-mode)
generate-glossary.py        Generates glossary.yml and resources/glossary.qmd FROM music-dictionary.org
glossary.yml                GENERATED — Quarto glossary shortcode definitions (one-line defs)
fix-blank-lines.py           Pre-render hook (see below)

_book/                      Build output of book/ (PDF + HTML) — generated
_site/                       Build output of website — generated
```

## Key workflows

### Editing the glossary

The glossary has a **single source of truth**: `music-dictionary.org`. Never hand-edit `glossary.yml` or `resources/glossary.qmd` directly — both are generated.

1. Edit terms/definitions in `music-dictionary.org`.
2. Regenerate from the repo root:
   ```
   python3 generate-glossary.py
   ```
   This rewrites `glossary.yml` (used by the `{{< glossary ... >}}` shortcode via the `_extensions/debruine/glossary` extension) and `resources/glossary.qmd` (the interactive glossary page).
3. `generate-glossary.py` is excluded from Quarto's render via `.quartoignore`.

Note `CORE_SLUGS` / `EXPERT_SLUGS` / `CAT_LABEL` in `generate-glossary.py` control importance tiers and category labels — update these sets if you add new terms that should be tagged as core/expert vocabulary or need a new category.

### Pre-render hook: `fix-blank-lines.py`

Configured as `project.pre-render` in `_quarto.yml`. It runs automatically before every Quarto render and inserts a blank line before list items that immediately follow a prose paragraph (Pandoc requires this or the list gets merged into the paragraph). It skips YAML front matter and fenced code blocks. You normally don't need to run this manually, but be aware it will rewrite `.qmd` files in place during a render — don't be surprised by working-tree diffs after a build.

### Building the site

```
quarto render            # builds website -> _site/ and book -> _book/ (per book/_quarto.yml output-dir)
quarto preview            # live preview
```

The book sub-project (`book/_quarto.yml`) renders to PDF (`scrbook` documentclass via LaTeX) — building it requires a working TeX installation (e.g., TinyTeX).

## Conventions

- **Naming by component prefix**: files under `book/` use a consistent prefix per IB component (`exploring-`, `ewm-`, `presenting-`, `cmm-`) and a consistent suffix per document type (`-guide`, `-checklist`, `-criterion-guidance`, `-common-mistakes`, `-tasks`). When adding new component material, follow this pattern and add the new file to the relevant `chapters:`/`contents:` list in `book/_quarto.yml` and/or `_quarto.yml` sidebar.
- **`*_files/` directories**: Quarto auto-generated support assets for a corresponding `.qmd`. Don't hand-edit; they regenerate on render.
- **Generated vs. source files**: `glossary.yml`, `resources/glossary.qmd`, `_book/`, `_site/` are build artifacts — edit their sources (`music-dictionary.org`, `generate-glossary.py`, the `.qmd` files) instead.
- **Glossary shortcode**: inline glossary popups use `{{< glossary "slug" "display text" >}}` (provided by `_extensions/debruine/glossary`), backed by `glossary.yml`.
- Prose in `.qmd` files is written for students, teachers, and parents (course guidance, rubrics, checklists). Keep tone clear and instructional, matching the existing voice — match the style of the file you're editing.

## Things to be careful about

- Don't commit changes to `_site/` or `_book/` casually — they're build output and large (the book includes a rendered PDF). Check `git status` before committing after a render.
- When regenerating the glossary, review the diff in `resources/glossary.qmd` and `glossary.yml` — `generate-glossary.py` does HTML/category formatting that can change broadly if `CAT_LABEL`/slug logic changes.
- The `presentations.qmd` and `resources.qmd` pages are Quarto `listing` pages that scan their respective directories (`presentations/`, `resources/`) for content with categories/date front matter — new files dropped into those directories will automatically appear in the listings if they have appropriate metadata.
