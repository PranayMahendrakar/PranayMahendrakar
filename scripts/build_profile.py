#!/usr/bin/env python3
"""Rebuild the profile: read the live numbers, redraw the images, refresh the marked parts of README.md.

Run by .github/workflows/refresh-profile.yml once a day, and by hand with
    GITHUB_TOKEN=$(gh auth token) python scripts/build_profile.py
Nothing here needs more than the Python standard library.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, 'assets')
RAW = 'https://raw.githubusercontent.com/PranayMahendrakar/PranayMahendrakar/main/assets/'
sys.path.insert(0, HERE)

import profile_data  # noqa: E402
import profile_svg  # noqa: E402
from profile_svg import number  # noqa: E402


def write(name: str, svg: str) -> None:
    xml.dom.minidom.parseString(svg.encode('utf-8'))     # never publish an image a browser cannot parse
    with open(os.path.join(ASSETS, name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(svg)


def tiles(data: dict) -> list[tuple[str, str, str, str, str, str]]:
    """slug, label, value, caption, accent, link - the six figures at the top of the page."""
    gh, lc = data['github'], data['leetcode']
    return [
        ('papers', 'Research papers', number(data['research']['count']), 'open access, each with a DOI', 'accent1',
         'https://research.pranaymahendrakar.com/'),
        ('repos', 'Public repositories', number(gh['repos']), 'on GitHub', 'accent3',
         'https://github.com/PranayMahendrakar?tab=repositories'),
        ('leetcode', 'LeetCode solved', number(lc['solved']),
         f'{number(lc["easy"])} easy / {number(lc["medium"])} medium / {number(lc["hard"])} hard', 'accent2',
         'https://leetcode.com/u/PranayMahendrakar/'),
        ('contributions', 'Contributions', number(gh['contributions']), 'on GitHub in the last 12 months', 'accent2',
         'https://github.com/PranayMahendrakar'),
        ('packages', 'PyPI packages', number(data['packages']['count']), 'open-source Python packages', 'accent1',
         'https://pypi.org/user/pranaymahendrakar/'),
        # not read from anywhere: the three titles are listed further down the page
        ('books', 'Books', '3', 'on artificial intelligence, with ISBNs', 'accent3', 'https://pranaymahendrakar.com/about'),
    ]


def images(data: dict) -> None:
    with open(os.path.join(ASSETS, 'tokens.json'), encoding='utf-8') as handle:
        themes = json.load(handle)
    gh = data['github']
    for mode, theme in themes.items():
        write(f'banner-{mode}.svg', profile_svg.banner(theme))
        write(f'skyline-{mode}.svg', profile_svg.skyline(theme, gh['weeks'], gh['contributions'], gh['first_sunday']))
        write(f'languages-{mode}.svg', profile_svg.languages(theme, gh['languages'], gh['with_language']))
        for slug, label, value, caption, accent, _link in tiles(data):
            write(f'tile-{slug}-{mode}.svg', profile_svg.tile(theme, label, value, caption, accent))


def md(text: str) -> str:
    """A feed title made safe to sit inside a Markdown link."""
    return re.sub(r'([\\\[\]<>|`*_~])', r'\\\1', text.replace('&', '&amp;'))


def attr(text: str) -> str:
    return text.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def short(title: str, limit: int = 110) -> str:
    """Paper titles here run to three clauses; a list wants the main title, and the link has the rest."""
    if len(title) <= limit:
        return title
    head = re.split(r'(?<=\?) |: ', title, maxsplit=1)[0]
    return head if 20 <= len(head) <= limit else title[:limit].rsplit(' ', 1)[0] + '…'


def picture(name: str, alt: str, width: str) -> str:
    """Dark and light versions of one image, chosen by the visitor's theme. The numbers go in the alt
    text as well, because an image shown through <img> gives a screen reader nothing else."""
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="{RAW}{name}-light.svg">'
            f'<img src="{RAW}{name}-dark.svg" width="{width}" alt="{attr(alt)}"></picture>')


def blocks(data: dict) -> dict[str, str]:
    gh = data['github']
    tile_row = '<p align="center">\n' + '\n'.join(
        f'  <a href="{link}">' + picture(f'tile-{slug}', f'{label}: {value} ({caption})', '32%') + '</a>'
        for slug, label, value, caption, _accent, link in tiles(data)) + '\n</p>'
    language_text = ', '.join(f'{lang["name"]} {number(lang["repos"])}' for lang in gh['languages'])
    charts = (picture('skyline', f'{number(gh["contributions"])} GitHub contributions in the last 12 months, drawn as a city: '
                                 'one block per day, taller on busier days', '100%')
              + '\n\n'
              + picture('languages', f'Primary language of {number(gh["with_language"])} public repositories: {language_text}', '100%'))
    papers = '\n'.join(
        f'- [{md(short(p["title"]))}]({p["url"]})' + (f' &mdash; [DOI]({p["doi"]})' if p['doi'] else '') + f' <sub>{p["date"]}</sub>'
        for p in data['research']['latest'])
    posts = '\n'.join(f'- [{md(p["title"])}]({p["url"]}) <sub>{p["date"]}</sub>' for p in data['blog']['latest'])
    episodes = '\n'.join(f'- [{md(v["title"])}]({v["url"]}) <sub>{v["date"]}</sub>' for v in data['podcast']['latest'])
    return {'TILES': tile_row, 'CHARTS': charts, 'PAPERS': papers, 'POSTS': posts, 'VIDEOS': episodes,
            'PAPER-COUNT': number(data['research']['count'])}


def readme(parts: dict[str, str]) -> None:
    path = os.path.join(ROOT, 'README.md')
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    for name, body in parts.items():
        start, end = f'<!-- {name}:START -->', f'<!-- {name}:END -->'
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
            raise SystemExit(f'README.md must contain exactly one {name} START/END pair, in that order')
        if '<!--' in body:
            raise SystemExit(f'refusing to write a comment marker into the {name} block')
        inner = body if name.endswith('COUNT') else '\n' + body + '\n'
        text = text[:text.index(start) + len(start)] + inner + text[text.index(end):]
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def main() -> None:
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''
    data = profile_data.collect(os.path.join(ASSETS, 'data.json'), token)
    images(data)
    readme(blocks(data))
    print('profile rebuilt', flush=True)


if __name__ == '__main__':
    main()
