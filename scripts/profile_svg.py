"""The profile's generated images: stat tiles, the contribution skyline and the language bar.

GitHub shows README images through an <img> tag, so each one is a single
self-contained SVG: no scripts, no web fonts, no outside files. Animation is
CSS inside the SVG and stops under prefers-reduced-motion. Colours and type
come from assets/tokens.json so every image matches the banner.
"""
from __future__ import annotations

import datetime
import re
from xml.sax.saxutils import escape

NS = 'http://www.w3.org/2000/svg'


def number(n: int) -> str:
    return f'{n:,}'


def _rgb(colour: str) -> tuple[int, int, int]:
    colour = colour.lstrip('#')
    if len(colour) == 3:
        colour = ''.join(c * 2 for c in colour)
    return int(colour[0:2], 16), int(colour[2:4], 16), int(colour[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """Colour a moved a fraction t of the way towards colour b."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return '#%02x%02x%02x' % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t))


def _open(width: int, height: int, title: str, desc: str, theme: dict, style: str = '') -> list[str]:
    reduced = '@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}'
    return [
        f'<svg xmlns="{NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="t d" font-family="{escape(theme["fontSans"], {chr(34): "&quot;"})}">',
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>',
        f'<style>{style}{reduced}</style>',
    ]


# ----------------------------------------------------------------- banner
NAME = 'Pranay Mahendrakar'
HEADLINE = 'AI Specialist and LLM Engineer  |  Managing Director, SonyTech  |  Author'
PLACE = 'BENGALURU, INDIA'
MOTTO = 'Where code meets consciousness'
FIELDS = ['Large language models', 'Natural language processing', 'Computer vision', 'Retrieval-augmented generation']
QUOT = {'"': '&quot;'}


def banner(theme: dict) -> str:
    """The header: his name over a slow aurora, beside a small network whose signals keep moving."""
    width, height = 1280, 360
    sans, mono = escape(theme['fontSans'], QUOT), escape(theme['fontMono'], QUOT)
    style = (
        '.a{animation:drift 26s ease-in-out infinite alternate}'
        '.b{animation:drift 34s ease-in-out -9s infinite alternate-reverse}'
        '.c{animation:drift 30s ease-in-out -17s infinite alternate}'
        '@keyframes drift{from{transform:translate(-46px,-14px)}to{transform:translate(58px,22px)}}'
        '.led{animation:led 2.4s ease-in-out infinite}@keyframes led{0%,100%{opacity:1}50%{opacity:.35}}'
        '.scan{animation:scan 11s linear infinite}@keyframes scan{from{transform:translateY(-40px)}to{transform:translateY(400px)}}'
        '.f{animation:lit 12s ease-in-out infinite}.f2{animation-delay:3s}.f3{animation-delay:6s}.f4{animation-delay:9s}'
        f'@keyframes lit{{0%,30%,100%{{fill:{theme["muted"]}}}8%,20%{{fill:{theme["text"]}}}}}'
        '.n{animation:node 6s ease-in-out infinite}@keyframes node{0%,100%{opacity:.55}50%{opacity:1}}')
    out = _open(width, height, f'{NAME} - AI Specialist and LLM Engineer, Managing Director of SonyTech, Author',
                f'Profile banner for {NAME}, based in Bengaluru, India. Fields: {", ".join(FIELDS)}.', theme, style)
    out.append(
        '<defs>'
        f'<clipPath id="frame"><rect width="{width}" height="{height}" rx="{theme["radius"]}"/></clipPath>'
        '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter>'
        f'<linearGradient id="ink" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{theme["accent1"]}"/>'
        f'<stop offset=".55" stop-color="{theme["accent3"]}"/><stop offset="1" stop-color="{theme["accent2"]}"/></linearGradient>'
        f'<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{theme["accent2"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{theme["accent2"]}" stop-opacity="{theme["beam"]}"/>'
        f'<stop offset="1" stop-color="{theme["accent2"]}" stop-opacity="0"/></linearGradient>'
        '<pattern id="mesh" width="40" height="40" patternUnits="userSpaceOnUse">'
        f'<path d="M40 0H0V40" fill="none" stroke="{theme["text"]}" stroke-opacity="{theme["mesh"]}"/></pattern>'
        '</defs>')
    out.append(f'<g clip-path="url(#frame)"><rect width="{width}" height="{height}" fill="{theme["bg"]}"/>')
    out.append(f'<g filter="url(#blur)" opacity="{theme["glow"]}">'
               f'<ellipse class="a" cx="250" cy="70" rx="330" ry="150" fill="{theme["accent1"]}"/>'
               f'<ellipse class="b" cx="1010" cy="330" rx="360" ry="150" fill="{theme["accent2"]}"/>'
               f'<ellipse class="c" cx="760" cy="20" rx="260" ry="120" fill="{theme["accent3"]}"/></g>')
    out.append(f'<rect width="{width}" height="{height}" fill="url(#mesh)"/>')
    out.append(f'<rect class="scan" x="0" y="0" width="{width}" height="2" fill="url(#beam)"/>')

    # a small network on the right; signals travel along three of its routes
    nodes = [(968, 150), (1030, 116), (1100, 158), (1172, 124), (1226, 190), (1140, 226), (1052, 204), (992, 258), (1200, 280)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6), (6, 0), (6, 7), (5, 8), (4, 8), (1, 6)]
    lines = ''.join(f'<path d="M{nodes[p][0]} {nodes[p][1]}L{nodes[q][0]} {nodes[q][1]}"/>' for p, q in edges)
    out.append(f'<g fill="none" stroke="{theme["text"]}" stroke-opacity="{theme["wire"]}" stroke-width="1.2">{lines}</g>')
    for k, (route, colour, seconds) in enumerate((((0, 1, 2, 3, 4), 'accent2', 7), ((7, 6, 5, 8), 'accent3', 6), ((1, 6, 0), 'accent1', 5))):
        path = 'M' + 'L'.join(f'{nodes[i][0]} {nodes[i][1]}' for i in route)
        out.append(f'<circle r="4" fill="{theme[colour]}"><animateMotion dur="{seconds}s" begin="{k * 1.3}s" '
                   f'repeatCount="indefinite" path="{path}"/></circle>')
    dots = ''.join(f'<circle class="n" style="animation-delay:{-i * .7:.1f}s" cx="{x}" cy="{y}" r="{5 if i % 3 else 7}"/>'
                   for i, (x, y) in enumerate(nodes))
    out.append(f'<g fill="{theme["node"]}" stroke="{theme["accent1"]}" stroke-width="1.5">{dots}</g>')

    # corner marks, as on pranaymahendrakar.com
    out.append(f'<g fill="none" stroke="{theme["accent1"]}" stroke-width="2"><path d="M36 60V36H60"/>'
               f'<path d="M{width - 36} {height - 60}V{height - 36}H{width - 60}"/></g>')

    out.append(f'<circle class="led" cx="72" cy="84" r="6" fill="{theme["accent2"]}"/>')
    out.append(f'<text x="90" y="90" font-family="{mono}" font-size="18" letter-spacing="3" fill="{theme["muted"]}">{PLACE}</text>')
    out.append(f'<text x="{width - 64}" y="90" text-anchor="end" font-family="{mono}" font-size="17" font-style="italic" '
               f'fill="{theme["muted"]}">{escape(MOTTO)}</text>')
    first, last = NAME.split(' ')
    out.append(f'<text x="62" y="190" font-family="{sans}" font-size="86" font-weight="800" letter-spacing="-1.5" '
               f'fill="{theme["text"]}">{first} <tspan fill="url(#ink)">{last}</tspan></text>')
    out.append(f'<text x="66" y="240" font-family="{sans}" font-size="25" fill="{theme["text"]}" fill-opacity=".88">{escape(HEADLINE)}</text>')
    out.append('<rect x="66" y="266" width="120" height="3" rx="1.5" fill="url(#ink)"/>')
    x, parts = 66.0, []
    for i, field in enumerate(FIELDS):
        parts.append(f'<text class="f f{i + 1}" x="{x:.0f}" y="312" fill="{theme["muted"]}">{escape(field)}</text>')
        x += len(field) * 10.85 + 14
        if i < len(FIELDS) - 1:
            parts.append(f'<circle cx="{x:.0f}" cy="306" r="2.5" fill="{theme["accent1"]}"/>')
            x += 16
    out.append(f'<g font-family="{mono}" font-size="18">{"".join(parts)}</g>')
    out.append(f'</g><rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="{theme["radius"]}" fill="none" stroke="{theme["border"]}"/>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


# ------------------------------------------------------------------ tiles
def tile(theme: dict, label: str, value: str, caption: str, accent: str = 'accent1') -> str:
    """One number: a small label, the figure, and a line saying what it counts."""
    width, height = 400, 180
    sans, mono = escape(theme['fontSans'], QUOT), escape(theme['fontMono'], QUOT)
    other = 'accent2' if accent != 'accent2' else 'accent1'
    style = ('.bar{animation:fill 1.6s cubic-bezier(.16,1,.3,1) both;transform-origin:28px 0}'
             '@keyframes fill{from{transform:scaleX(.08)}to{transform:none}}'
             '.halo{animation:halo 7s ease-in-out infinite}@keyframes halo{0%,100%{opacity:.55}50%{opacity:1}}')
    out = _open(width, height, f'{label}: {value}', f'{value} {label.lower()}, {caption}', theme, style)
    out.append(
        '<defs>'
        f'<clipPath id="frame"><rect width="{width}" height="{height}" rx="{theme["radius"]}"/></clipPath>'
        '<filter id="blur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="34"/></filter>'
        f'<linearGradient id="ink" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{theme[accent]}"/>'
        f'<stop offset="1" stop-color="{theme[other]}"/></linearGradient>'
        '</defs>')
    out.append(f'<g clip-path="url(#frame)"><rect width="{width}" height="{height}" fill="{theme["bg"]}"/>'
               f'<g opacity="{theme["glow"]}"><circle class="halo" cx="352" cy="24" r="70" fill="{theme[accent]}" filter="url(#blur)"/></g></g>')
    out.append(f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="{theme["radius"]}" fill="none" stroke="{theme["border"]}"/>')
    out.append(f'<text id="label" x="28" y="46" font-family="{mono}" font-size="17" letter-spacing="1.6" fill="{theme["muted"]}">{escape(label.upper())}</text>')
    out.append(f'<text id="value" x="26" y="114" font-family="{sans}" font-size="{66 if len(value) <= 5 else 56}" font-weight="800" '
               f'letter-spacing="-1" fill="url(#ink)">{escape(value)}</text>')
    out.append(f'<text id="caption" x="28" y="146" font-family="{sans}" font-size="17" fill="{theme["text"]}" fill-opacity=".82">{escape(caption)}</text>')
    out.append(f'<rect x="28" y="160" width="344" height="3" rx="1.5" fill="{theme["panel_solid"]}"/>'
               f'<rect class="bar" x="28" y="160" width="344" height="3" rx="1.5" fill="url(#ink)"/>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- skyline
def skyline(theme: dict, weeks: list[list[int]], total: int, last_day: str) -> str:
    """A year of contributions as an isometric city: one block per day, height by count."""
    width, height = 1280, 592
    a, b = 19.0, 6.4                      # half-width and half-depth of one grid step on screen
    origin_x, origin_y = 236.0, 178.0
    rise = 124.0
    days = [c for week in weeks for c in week]
    busy = sorted(c for c in days if c)
    # One freak day would flatten the rest of the year, so heights are scaled to the
    # 97th percentile and anything above it simply reaches the top.
    peak = (busy[min(len(busy) - 1, int(len(busy) * .97))] if busy else 0) or 1
    ramp = [theme['panel_solid'], mix(theme['panel_solid'], theme['accent1'], .5),
            mix(theme['panel_solid'], theme['accent1'], .78), theme['accent1'],
            mix(theme['accent1'], theme['accent2'], .55)]
    streak = longest = 0
    for c in days:
        streak = streak + 1 if c else 0
        longest = max(longest, streak)

    def project(u: float, v: float, lift: float = 0.0) -> str:
        return f'{origin_x + (u - v) * a:.1f},{origin_y + (u + v) * b - lift:.1f}'

    end = datetime.date.fromisoformat(last_day)
    first_of_last_week = end - datetime.timedelta(days=len(weeks[-1]) - 1)
    best = (0, 0, 0)                       # count, week, day

    style = ('.w{animation:up .7s cubic-bezier(.16,1,.3,1) both}'
             '@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}'
             '.pin{animation:pulse 3.2s ease-in-out infinite}'
             '@keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}')
    out = _open(width, height, f'{number(total)} contributions in the last 12 months',
                'An isometric chart of daily GitHub contributions over the past year; taller blocks are busier days.',
                theme, style)
    out.append(f'<rect width="{width}" height="{height}" rx="{theme["radius"]}" fill="{theme["bg"]}"/>')
    out.append(f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="{theme["radius"]}" fill="none" stroke="{theme["border"]}"/>')

    for i, week in enumerate(weeks):
        cells = []
        for j, count in enumerate(week):
            u0, u1, v0, v1 = i + .08, i + .92, j + .08, j + .92
            if count > best[0]:
                best = (count, i, j)
            if count == 0:
                cells.append(f'<path d="M{project(u0, v0)}L{project(u1, v0)}L{project(u1, v1)}L{project(u0, v1)}Z" '
                             f'fill="{ramp[0]}"/>')
                continue
            share = min(1.0, count / peak)
            level = min(4, 1 + int(3.999 * share ** 0.6))
            lift = 5 + rise * share ** 0.6
            top = ramp[level]
            cells.append(
                f'<path d="M{project(u0, v1, lift)}L{project(u1, v1, lift)}L{project(u1, v1)}L{project(u0, v1)}Z" fill="{mix(top, theme["shade"], .5)}"/>'
                f'<path d="M{project(u1, v0, lift)}L{project(u1, v1, lift)}L{project(u1, v1)}L{project(u1, v0)}Z" fill="{mix(top, theme["shade"], .28)}"/>'
                f'<path d="M{project(u0, v0, lift)}L{project(u1, v0, lift)}L{project(u1, v1, lift)}L{project(u0, v1, lift)}Z" fill="{top}"/>')
        out.append(f'<g class="w" style="animation-delay:{i * 0.018:.3f}s">{"".join(cells)}</g>')

    # month names along the near edge
    months, previous = [], None
    for i in range(len(weeks)):
        start = first_of_last_week - datetime.timedelta(weeks=len(weeks) - 1 - i)
        if start.month != previous and i < len(weeks) - 2:
            previous = start.month
            x, y = project(i + .5, 8.4).split(',')
            months.append(f'<text x="{x}" y="{y}" text-anchor="middle">{start.strftime("%b")}</text>')
    out.append(f'<g font-size="17" fill="{theme["muted"]}" font-family="{escape(theme["fontMono"], {chr(34): "&quot;"})}">{"".join(months)}</g>')

    # the busiest day gets a marker
    count, i, j = best
    if count:
        lift = 5 + rise
        x, y = (float(p) for p in project(i + .5, j + .5, lift).split(','))
        when = (first_of_last_week - datetime.timedelta(weeks=len(weeks) - 1 - i) + datetime.timedelta(days=j))
        anchor, dx = ('end', -12) if x > width - 260 else ('start', 12)
        out.append(f'<g class="pin"><line x1="{x:.1f}" y1="{y - 4:.1f}" x2="{x:.1f}" y2="{y - 44:.1f}" stroke="{theme["accent2"]}" stroke-width="2"/>'
                   f'<circle cx="{x:.1f}" cy="{y - 48:.1f}" r="5" fill="{theme["accent2"]}"/></g>'
                   f'<text x="{x + dx:.1f}" y="{y - 43:.1f}" text-anchor="{anchor}" font-size="18" fill="{theme["text"]}">'
                   f'{number(count)} on {when.strftime("%d %b %Y").lstrip("0")}</text>')

    out.append(f'<text x="64" y="84" font-size="52" font-weight="700" fill="{theme["text"]}">{number(total)}</text>')
    out.append(f'<text x="66" y="116" font-size="20" fill="{theme["muted"]}">contributions in the last 12 months</text>')
    for row, (value, label) in enumerate(((number(len(busy)), ' active days'), (number(longest), '-day longest streak'))):
        out.append(f'<text x="1216" y="{74 + row * 36}" text-anchor="end" font-size="20" fill="{theme["muted"]}">'
                   f'<tspan font-size="26" font-weight="700" fill="{theme["text"]}">{value}</tspan>{label}</text>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


# -------------------------------------------------------------- languages
def languages(theme: dict, langs: list[dict], repos: int) -> str:
    width, height = 1280, 190
    total = sum(lang['repos'] for lang in langs) or 1
    bar_x, bar_y, bar_w, bar_h = 64, 84, width - 128, 20
    style = ('.seg{animation:grow 1.1s cubic-bezier(.16,1,.3,1) both;transform-origin:64px 0}'
             '@keyframes grow{from{transform:scaleX(0)}to{transform:none}}')
    out = _open(width, height, 'Primary language of public repositories',
                ', '.join(f'{lang["name"]} {number(lang["repos"])}' for lang in langs), theme, style)
    out.append(f'<rect width="{width}" height="{height}" rx="{theme["radius"]}" fill="{theme["bg"]}"/>')
    out.append(f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="{theme["radius"]}" fill="none" stroke="{theme["border"]}"/>')
    out.append(f'<text x="64" y="54" font-size="20" fill="{theme["muted"]}">Primary language across '
               f'<tspan fill="{theme["text"]}" font-weight="700">{number(repos)}</tspan> public repositories</text>')
    out.append(f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}"/></clipPath>')
    out.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}" fill="{theme["panel_solid"]}"/>')

    # every language gets at least a visible sliver, the rest share what is left
    floor = 7.0
    spare = bar_w - floor * len(langs)
    x = float(bar_x)
    segments = []
    for lang in langs:
        w = floor + spare * lang['repos'] / total
        segments.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{w + .6:.1f}" height="{bar_h}" fill="{lang["color"]}"/>')
        x += w
    out.append(f'<g clip-path="url(#bar)"><g class="seg">{"".join(segments)}</g></g>')

    lx, ly = 64.0, 150.0
    for lang in langs:
        label = f'{lang["name"]} '
        out.append(f'<circle cx="{lx + 7:.1f}" cy="{ly - 6:.1f}" r="7" fill="{lang["color"]}"/>'
                   f'<text x="{lx + 22:.1f}" y="{ly}" font-size="18" fill="{theme["text"]}">{escape(label)}'
                   f'<tspan fill="{theme["muted"]}">{number(lang["repos"])}</tspan></text>')
        lx += 22 + (len(label) + len(number(lang['repos']))) * 10.4 + 30
    out.append('</svg>')
    return '\n'.join(out) + '\n'
