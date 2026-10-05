#!/usr/bin/env python3
"""Rebuild the profile: read the live numbers, redraw the images, refresh the lists in README.md.

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
sys.path.insert(0, HERE)

import profile_data  # noqa: E402
import profile_svg  # noqa: E402
from profile_svg import number  # noqa: E402


def write(name: str, svg: str) -> None:
    xml.dom.minidom.parseString(svg.encode('utf-8'))     # never publish an image a browser cannot parse
    with open(os.path.join(ASSETS, name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(svg)


def images(data: dict) -> None:
    with open(os.path.join(ASSETS, 'tokens.json'), encoding='utf-8') as handle:
        themes = json.load(handle)
    gh, lc = data['github'], data['leetcode']
    tiles = [
        ('papers', 'Research papers', number(data['research']['count']), 'open access, each with a DOI', 'accent1'),
        ('repos', 'Public repositories', number(gh['repos']), 'on GitHub', 'accent3'),
        ('leetcode', 'LeetCode solved', number(lc['solved']),
         f'{number(lc["easy"])} easy / {number(lc["medium"])} medium / {number(lc["hard"])} hard', 'accent2'),
        ('contributions', 'Contributions', number(gh['contributions']), 'on GitHub in the last 12 months', 'accent2'),
        ('pypi', 'PyPI packages', number(data['pypi']['count']), 'open-source Python packages', 'accent1'),
        ('books', 'Books', '3', 'on artificial intelligence, with ISBNs', 'accent3'),
    ]
    for mode, theme in themes.items():
        write(f'banner-{mode}.svg', profile_svg.banner(theme))
        write(f'skyline-{mode}.svg', profile_svg.skyline(theme, gh['weeks'], gh['contributions'], gh['last_day']))
        write(f'languages-{mode}.svg', profile_svg.languages(theme, gh['languages'], gh['repos']))
        for slug, label, value, caption, accent in tiles:
            write(f'tile-{slug}-{mode}.svg', profile_svg.tile(theme, label, value, caption, accent))


def md(text: str) -> str:
    """A feed title made safe to sit inside a Markdown link."""
    return re.sub(r'([\\\[\]<>|`*_])', r'\\\1', text)


def short(title: str, limit: int = 110) -> str:
    """Paper titles here run to three clauses; a list wants the main title, and the link has the rest."""
    if len(title) <= limit:
        return title
    head = title.split(': ', 1)[0]
    return head if 20 <= len(head) <= limit else title[:limit].rsplit(' ', 1)[0] + '…'


def lists(data: dict) -> dict[str, str]:
    papers = '\n'.join(
        f'- [{md(short(p["title"]))}]({p["url"]})' + (f' &mdash; [DOI]({p["doi"]})' if p['doi'] else '') + f' <sub>{p["date"]}</sub>'
        for p in data['research']['latest'])
    posts = '\n'.join(f'- [{md(p["title"])}]({p["url"]}) <sub>{p["date"]}</sub>' for p in data['blog']['latest'])
    videos = '\n'.join(f'- [{md(v["title"])}]({v["url"]}) <sub>{v["date"]}</sub>' for v in data['youtube']['latest'])
    return {'PAPERS': papers, 'POSTS': posts, 'VIDEOS': videos,
            'PAPER-COUNT': number(data['research']['count'])}


def readme(blocks: dict[str, str]) -> None:
    path = os.path.join(ROOT, 'README.md')
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    for name, body in blocks.items():
        inline = '\n' not in body and name.endswith('COUNT')
        pattern = re.compile(r'(<!-- %s:START -->)(.*?)(<!-- %s:END -->)' % (name, name), re.S)
        if not pattern.search(text):
            raise SystemExit('README.md has no %s markers' % name)
        text = pattern.sub(lambda m: m.group(1) + (body if inline else '\n' + body + '\n') + m.group(3), text)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def main() -> None:
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''
    data = profile_data.collect(os.path.join(ASSETS, 'data.json'), token)
    images(data)
    readme(lists(data))
    print('profile rebuilt')


if __name__ == '__main__':
    main()
