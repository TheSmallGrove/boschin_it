#!/usr/bin/env python3
"""Generate the translated pages of the site from wwwroot/index.html.

index.html (English) is the single source. Each i18n/<lang>.json maps an exact
English fragment of index.html to its translation; this script writes
wwwroot/<lang>.html with every fragment replaced.

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

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "wwwroot" / "index.html"
I18N = ROOT / "i18n"
LANGS = ["it", "es", "de", "fr"]

REDIRECT = re.compile(r"\n\s*<!-- i18n:redirect -->.*?<!-- /i18n:redirect -->", re.S)


def load(lang):
    data = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
    return data["locale"], data["strings"]


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
    page = page.replace('content="en_GB"', f'content="{locale}"', 1)
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

    for lang, (locale, strings) in loaded.items():
        out = ROOT / "wwwroot" / f"{lang}.html"
        out.write_text(localize(source, lang, locale, strings), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({len(strings)} strings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
