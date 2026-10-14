#!/usr/bin/env python3
"""Generate the translated pages of the site from wwwroot/index.html.

index.html (English) is the single source. Each i18n/<lang>.json maps an exact
English fragment of index.html to its translation; this script writes
wwwroot/<lang>.html with every fragment replaced.

It also writes, for every language, the SEO block of the page head (between
<!-- i18n:seo --> and <!-- /i18n:seo -->, in index.html too): canonical address,
alternate languages (hreflang), Open Graph address and locale, and the ProfilePage
JSON-LD; and wwwroot/sitemap.xml, with every page and its alternates.

The last-updated date (footer, JSON-LD dateModified, sitemap lastmod) becomes
today's date only when the content changes: index.html or a translation file.
tools/last_updated.json keeps the date with a fingerprint of that content, so
re-running the script on unchanged content (as the deploy workflow does) leaves
every page as it is.

It fails, and writes nothing, when:
  - a fragment listed in a translation file is no longer in index.html
    (the English text changed: update the key and the translations);
  - the translation files do not all have the same set of keys.

Usage (from the repository root):  python3 tools/build_i18n.py
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "wwwroot" / "index.html"
I18N = ROOT / "i18n"
LANGS = ["it", "es", "de", "fr"]
SITE = "https://www.boschin.it"   # GitHub Pages custom domain
SITEMAP = ROOT / "wwwroot" / "sitemap.xml"
STATE = ROOT / "tools" / "last_updated.json"
UPDATED = re.compile(r'(<span class="footer-updated">[^<]*<time datetime=")[^"]*(">)[^<]*(</time>)')
EN_DATE = {"format": "{d} {month} {y}",
           "months": ["January", "February", "March", "April", "May", "June", "July",
                      "August", "September", "October", "November", "December"]}
SEO = re.compile(r"(<!-- i18n:seo[^>]*-->).*?(\n\s*<!-- /i18n:seo -->)", re.S)

REDIRECT = re.compile(r"\n\s*<!-- i18n:redirect -->.*?<!-- /i18n:redirect -->", re.S)


def load(lang):
    data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
    return data["locale"], data["date"], data["strings"]


def url(lang):
    """Public address of the page of a language: the English one is the site root."""
    return f"{SITE}/" if lang == "en" else f"{SITE}/{lang}.html"


def seo_block(lang, locales, updated):
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
        "dateModified": updated.isoformat(),
        "mainEntity": {"@id": f"{SITE}/#person"},
    }
    lines.append(f'<script type="application/ld+json">{json.dumps(data)}</script>')
    return "\n" + "\n".join(f"  {line}" for line in lines)


def with_seo(page, lang, locales, updated):
    page, n = SEO.subn(lambda m: m.group(1) + seo_block(lang, locales, updated) + m.group(2), page, count=1)
    if not n:
        raise SystemExit("index.html: the <!-- i18n:seo --> block is missing")
    return page


def sitemap(locales, updated):
    """Every page, with the addresses of its other languages (xhtml:link)."""
    alternates = "".join(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{escape(url(lang))}"/>\n'
                         for lang in locales)
    lastmod = f"    <lastmod>{updated.isoformat()}</lastmod>\n"
    pages = "".join(f"  <url>\n    <loc>{escape(url(lang))}</loc>\n{lastmod}{alternates}  </url>\n"
                    for lang in locales)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            f"{pages}</urlset>\n")


def with_updated(page, updated, fmt):
    """The footer date, in the language's own format."""
    text = fmt["format"].format(d=updated.day, month=fmt["months"][updated.month - 1], y=updated.year)
    page, n = UPDATED.subn(lambda m: m.group(1) + updated.isoformat() + m.group(2) + text + m.group(3),
                           page, count=1)
    if not n:
        raise SystemExit('index.html: the <span class="footer-updated"> date is missing')
    return page


def last_updated(source):
    """Today when index.html or a translation changed since the last run, else the stored date.

    The fingerprint leaves out what this script writes itself (SEO block, footer date),
    so only a change of content moves the date."""
    content = UPDATED.sub("", SEO.sub("", source))
    digest = hashlib.sha256(content.encode("utf-8"))
    for lang in LANGS:
        digest.update((I18N / f"{lang}.json").read_bytes())
    fingerprint = digest.hexdigest()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if state.get("fingerprint") == fingerprint:
        return date.fromisoformat(state["date"])
    today = date.today()
    STATE.write_text(json.dumps({"date": today.isoformat(), "fingerprint": fingerprint}, indent=2) + "\n",
                     encoding="utf-8")
    print(f"content changed: last updated {today.isoformat()}")
    return today


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
    reference = set(loaded[LANGS[0]][2])
    for lang, (_, _, strings) in loaded.items():
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

    updated = last_updated(source)
    locales = {"en": "en_GB", **{lang: locale for lang, (locale, _, _) in loaded.items()}}
    source = with_updated(with_seo(source, "en", locales, updated), updated, EN_DATE)
    if source != SOURCE.read_text(encoding="utf-8"):
        SOURCE.write_text(source, encoding="utf-8")
        print(f"updated the SEO block and date of {SOURCE.relative_to(ROOT)}")
    for lang, (locale, fmt, strings) in loaded.items():
        out = ROOT / "wwwroot" / f"{lang}.html"
        page = with_seo(localize(source, lang, locale, strings), lang, locales, updated)
        out.write_text(with_updated(page, updated, fmt), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({len(strings)} strings)")
    SITEMAP.write_text(sitemap(locales, updated), encoding="utf-8")
    print(f"wrote {SITEMAP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
