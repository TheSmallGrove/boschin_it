# boschin.it

Personal CV website of Andrea Boschin — a static site, no build tooling required to serve it.

| Path | Content |
|---|---|
| `wwwroot/` | The site: `index.html` (English) and the generated `it.html`, `es.html`, `de.html`, `fr.html` and `sitemap.xml`; `robots.txt` |
| `wwwroot/assets/` | Stylesheet, script and images |
| `wwwroot/assets/files/` | Downloadable CV (PDF). Its path is encoded in `site.js` (`CV`), never written in the HTML: when the PDF changes, re-encode the new path |
| `i18n/` | Translations: one JSON per language, mapping exact English fragments of `index.html` to the translated text |
| `tools/build_i18n.py` | Generates the translated pages from `index.html` and `i18n/*.json` |
| `docs/` | Source documents (the CV files with personal data are git-ignored) |

## Translations

`wwwroot/index.html` is the only page edited by hand. After changing it:

```
python3 tools/build_i18n.py
```

The script stops without writing anything when an English fragment listed in `i18n/*.json`
is no longer found in `index.html`, or when the language files do not share the same keys:
update the key and its translations, then run it again. Never edit `it.html`, `es.html`,
`de.html` or `fr.html` directly — they are overwritten on every run.

The script also writes the head tags that differ by language — canonical address, `hreflang`
alternates, Open Graph address and locale, `ProfilePage` JSON-LD — between
`<!-- i18n:seo -->` and `<!-- /i18n:seo -->` of every page, `index.html` included, and
`wwwroot/sitemap.xml`. Adding a language to `LANGS` updates all of them.

## SEO

- `index.html` holds the title, description, Open Graph preview (the portrait) and the `Person`
  JSON-LD (job title, MVP award, PSM I credential, LinkedIn); the translations replace the
  English fragments listed in `i18n/*.json`.
- Every page points to its own address (`canonical`) and to the other languages (`hreflang`);
  the English page is the site root, `https://www.boschin.it/` (the domain is `SITE` in the script).
- `wwwroot/robots.txt` allows everything except `/assets/files/` (the CV) and names the sitemap.

`index.html` redirects first-time visitors to their browser language; the choice made in the
language menu is remembered and wins over the browser setting.

## Deploy

Pushing changes to the workflow requires a credential with the `workflow` scope
(`gh auth refresh -s workflow` when git authenticates through `gh`).

`.github/workflows/pages.yml` publishes `wwwroot/` to GitHub Pages on every push to `main`
(or by hand, from the Actions tab). It first re-runs `tools/build_i18n.py` and fails if the
translated pages in the commit are out of date.

One-time setup: in the repository settings, **Pages → Build and deployment → Source** must be
set to **GitHub Actions**.
