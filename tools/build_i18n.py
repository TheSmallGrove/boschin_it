#!/usr/bin/env python3
"""Generate the translated pages of the site from wwwroot/index.html.

index.html (English) is the single source. Each i18n/<lang>.json maps an exact
English fragment of index.html to its translation; this script writes
wwwroot/<lang>.html with every fragment replaced.

It also writes, for every language, the SEO block of the page head (between
<!-- i18n:seo --> and <!-- /i18n:seo -->, in index.html too): canonical address,
alternate languages (hreflang), Open Graph address and locale, and the ProfilePage
JSON-LD; and wwwroot/sitemap.xml, with every page and its alternates.

It fails, and writes nothing, when:
  - a fragment listed in a translation file is no longer in index.html
    (the English text changed: update the key and the translations);
  - the translation files do not all have the same set of keys.

Usage (from the repository root):  python3 tools/build_i18n.py
"""
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "wwwroot" / "index.html"
I18N = ROOT / "i18n"
LANGS = ["it", "es", "de", "fr"]
SITE = "https://www.boschin.it"   # GitHub Pages custom domain
SITEMAP = ROOT / "wwwroot" / "sitemap.xml"
SEO = re.compile(r"(<!-- i18n:seo[^>]*-->).*?(\n\s*<!-- /i18n:seo -->)", re.S)

REDIRECT = re.compile(r"\n\s*<!-- i18n:redirect -->.*?<!-- /i18n:redirect -->", re.S)


def load(lang):
    data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
    return data["locale"], data["strings"]


def url(lang):
    """Public address of the page of a language: the English one is the site root."""
    return f"{SITE}/" if lang == "en" else f"{SITE}/{lang}.html"


def seo_block(lang, locales):
    """Head tags that differ for each language, from the list of all of them."""
    lines = [f'<link rel="canonical" href="{url(lang)}">']
    lines += [f'<link rel="alternate" hreflang="{other}" href="{url(other)}">' for other in locales]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url("en")}">')
    lines.append(f'<meta property="og:url" content="{url(lang)}">')
    lines.append(f'<meta property="og:locale" content="{locales[lang]}">')
    lines += [f'<meta property="og:locale:alternate" content="{loc}">' for other, loc in locales.items() if other != lang]
    data = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "@id": f"{url(lang)}#page",
        "url": url(lang),
        "inLanguage": lang,
        "mainEntity": {"@id": f"{SITE}/#person"},
    }
    lines.append(f'<script type="application/ld+json">{json.dumps(data)}</script>')
    return "\n" + "\n".join(f"  {line}" for line in lines)


def with_seo(page, lang, locales):
    page, n = SEO.subn(lambda m: m.group(1) + seo_block(lang, locales) + m.group(2), page, count=1)
    if not n:
        raise SystemExit("index.html: the <!-- i18n:seo --> block is missing")
    return page


def sitemap(locales):
    """Every page, with the addresses of its other languages (xhtml:link)."""
    alternates = "".join(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{escape(url(lang))}"/>\n'
                         for lang in locales)
    pages = "".join(f"  <url>\n    <loc>{escape(url(lang))}</loc>\n{alternates}  </url>\n" for lang in locales)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            f"{pages}</urlset>\n")


def localize(source, lang, locale, strings):
    page = REDIRECT.sub("", source, count=1)

    # Two passes through placeholders, so a translation that happens to contain
    # another English key is never translated twice.
    tokens = {}
    for i, key in enumerate(sorted(strings, key=len, reverse=True)):
        token = f"\x00{i}\x00"
        page = page.replace(key, token)
        tokens[token] = strings[key]
    for token, value in tokens.items():
        page = page.replace(token, value)

    page = page.replace('<html lang="en">', f'<html lang="{lang}">', 1)
    page = page.replace('<span class="lang-code">EN</span>',
                        f'<span class="lang-code">{lang.upper()}</span>', 1)
    page = page.replace(' data-lang="en" aria-current="page">', ' data-lang="en">', 1)
    page = page.replace(f' data-lang="{lang}">', f' data-lang="{lang}" aria-current="page">', 1)
    return page


def main():
    source = SOURCE.read_text(encoding="utf-8")
    loaded = {lang: load(lang) for lang in LANGS}

    errors = []
    reference = set(loaded[LANGS[0]][1])
    for lang, (_, strings) in loaded.items():
        keys = set(strings)
        for key in sorted(reference - keys):
            errors.append(f"{lang}: missing key {key[:70]!r}")
        for key in sorted(keys - reference):
            errors.append(f"{lang}: extra key {key[:70]!r}")
        for key in strings:
            if key not in source:
                errors.append(f"{lang}: key not found in index.html {key[:70]!r}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    locales = {"en": "en_GB", **{lang: locale for lang, (locale, _) in loaded.items()}}
    source = with_seo(source, "en", locales)
    if source != SOURCE.read_text(encoding="utf-8"):
        SOURCE.write_text(source, encoding="utf-8")
        print(f"updated the SEO block of {SOURCE.relative_to(ROOT)}")
    for lang, (locale, strings) in loaded.items():
        out = ROOT / "wwwroot" / f"{lang}.html"
        out.write_text(with_seo(localize(source, lang, locale, strings), lang, locales), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({len(strings)} strings)")
    SITEMAP.write_text(sitemap(locales), encoding="utf-8")
    print(f"wrote {SITEMAP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
