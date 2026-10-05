"""Live numbers and lists for the profile, read from their own sources.

Every source can fail on a given day (a rate limit, a bot wall, a site being
down), and a profile that shows a zero or a broken list is worse than one that
is a day old. So each reading is cached in assets/data.json and a failed fetch
falls back to the last good value instead of writing anything new. The date
each source last answered is kept beside it, and a source that has been silent
for several days is reported as a workflow warning rather than left to go
stale unnoticed.

Standard library only: this runs on a bare GitHub Actions runner.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import urllib.request
from email.utils import parsedate_to_datetime

LOGIN = 'PranayMahendrakar'
PODCAST_PLAYLIST = 'PLx4PeJLyygtDmw071GgDqDcUwGK87mMFW'      # The Founder Mindset Operating System
SITE = 'https://pranaymahendrakar.com'
RESEARCH = 'https://research.pranaymahendrakar.com'
STALE_AFTER_DAYS = 3

# The sites sit behind a CDN that challenges requests carrying only bare
# script headers; a normal Accept and Accept-Language pair is let through.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
    'Accept': 'application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# What ends up inside a Markdown link in README.md has to be exactly what it
# claims to be; a feed value that is not is treated as a failed read.
SITE_URL = re.compile(r'^https://(?:research\.)?pranaymahendrakar\.com/[A-Za-z0-9._~%/-]*$')
DOI_URL = re.compile(r'^https://doi\.org/10\.[0-9]{4,9}/[A-Za-z0-9._-]+$')
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
COLOUR = re.compile(r'^#[0-9A-Fa-f]{3,8}$')


def fetch(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 40) -> str:
    request = urllib.request.Request(url, data=data, headers={**HEADERS, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


def _text(xml: str, tag: str) -> str:
    """First <tag> in a feed item, CDATA and entities removed."""
    m = re.search(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), xml, re.S)
    if not m:
        return ''
    value = re.sub(r'^<!\[CDATA\[|\]\]>$', '', m.group(1).strip())
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def _items(feed: str, tag: str) -> list[str]:
    return re.findall(r'<%s\b.*?</%s>' % (tag, tag), feed, re.S)


def _checked(value: str, pattern: re.Pattern, what: str) -> str:
    if not pattern.match(value):
        raise ValueError('unexpected %s: %r' % (what, value[:120]))
    return value


def _title(item: str) -> str:
    title = _text(item, 'title')
    if not title:
        raise ValueError('feed item without a title')
    return title


def _day(item: str) -> str:
    return parsedate_to_datetime(_text(item, 'pubDate')).strftime('%Y-%m-%d')


# --------------------------------------------------------------- sources
def github(token: str) -> dict:
    def gql(query: str, variables: dict) -> dict:
        body = json.dumps({'query': query, 'variables': variables}).encode()
        raw = fetch('https://api.github.com/graphql', body, {
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'Accept': 'application/json'})
        payload = json.loads(raw)
        if payload.get('errors'):
            raise RuntimeError(payload['errors'][0].get('message', 'GraphQL error'))
        return payload['data']

    head = gql('''query($login: String!) { user(login: $login) {
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
        contributionsCollection { contributionCalendar { totalContributions
          weeks { contributionDays { date weekday contributionCount } } } } } }''', {'login': LOGIN})['user']
    calendar = head['contributionsCollection']['contributionCalendar']
    # Seven slots a week, Sunday first; the first and last weeks can be short,
    # and a day outside the window is None rather than a zero.
    weeks = []
    for week in calendar['weeks']:
        row = [None] * 7
        for day in week['contributionDays']:
            row[day['weekday']] = day['contributionCount']
        weeks.append(row)
    first = calendar['weeks'][0]['contributionDays'][0]
    sunday = datetime.date.fromisoformat(first['date']) - datetime.timedelta(days=first['weekday'])

    languages: dict[str, dict] = {}
    stars, cursor = 0, None
    while True:
        page = gql('''query($login: String!, $after: String) { user(login: $login) {
            repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
              pageInfo { hasNextPage endCursor }
              nodes { stargazerCount primaryLanguage { name color } } } } }''',
                   {'login': LOGIN, 'after': cursor})['user']['repositories']
        for node in page['nodes']:
            stars += node['stargazerCount']
            language = node['primaryLanguage']
            if language:
                colour = language['color'] if COLOUR.match(language['color'] or '') else '#8b949e'
                entry = languages.setdefault(language['name'], {'name': language['name'], 'color': colour, 'repos': 0})
                entry['repos'] += 1
        if not page['pageInfo']['hasNextPage']:
            break
        cursor = page['pageInfo']['endCursor']

    ranked = sorted(languages.values(), key=lambda l: (-l['repos'], l['name']))
    top, rest = ranked[:6], ranked[6:]
    if rest:
        top.append({'name': 'Other', 'color': '#8b949e', 'repos': sum(l['repos'] for l in rest)})
    return {
        'repos': head['repositories']['totalCount'],
        'followers': head['followers']['totalCount'],
        'stars': stars,
        'contributions': calendar['totalContributions'],
        'weeks': weeks,
        'first_sunday': sunday.isoformat(),
        'languages': top,
        'with_language': sum(l['repos'] for l in ranked),
    }


def research() -> dict:
    items = _items(fetch(RESEARCH + '/feed.xml'), 'item')
    if not items:
        raise RuntimeError('research feed has no items')
    papers = []
    for item in items[:5]:
        doi = _text(item, 'guid')
        papers.append({'title': _title(item), 'url': _checked(_text(item, 'link'), SITE_URL, 'paper link'),
                       'doi': doi if DOI_URL.match(doi) else '', 'date': _day(item)})
    return {'count': len(items), 'latest': papers}


def blog() -> dict:
    items = _items(fetch(SITE + '/feed.xml'), 'item')
    if not items:
        raise RuntimeError('blog feed has no items')
    return {'latest': [{'title': _title(i), 'url': _checked(_text(i, 'link'), SITE_URL, 'post link'), 'date': _day(i)}
                       for i in items[:5]]}


def podcast() -> dict:
    """The podcast's own playlist, newest first - not everything the channel uploads."""
    entries = _items(fetch('https://www.youtube.com/feeds/videos.xml?playlist_id=' + PODCAST_PLAYLIST), 'entry')
    if not entries:
        raise RuntimeError('podcast playlist feed has no entries')
    episodes = []
    for entry in entries:
        video_id = _checked(_text(entry, 'yt:videoId'), VIDEO_ID, 'video id')
        episodes.append({'title': _title(entry), 'url': 'https://www.youtube.com/watch?v=' + video_id,
                         'date': _checked(_text(entry, 'published')[:10], ISO_DATE, 'episode date')})
    episodes.sort(key=lambda e: (e['date'], e['title']), reverse=True)
    return {'latest': episodes[:4]}


def leetcode() -> dict:
    query = ('query($u: String!) { matchedUser(username: $u) { submitStatsGlobal { acSubmissionNum '
             '{ difficulty count } } } }')
    raw = fetch('https://leetcode.com/graphql', json.dumps({'query': query, 'variables': {'u': LOGIN}}).encode(),
                {'Content-Type': 'application/json', 'Accept': 'application/json',
                 'Referer': 'https://leetcode.com/u/%s/' % LOGIN})
    counts = {row['difficulty']: int(row['count'])
              for row in json.loads(raw)['data']['matchedUser']['submitStatsGlobal']['acSubmissionNum']}
    if not counts.get('All'):
        raise RuntimeError('LeetCode returned no solved count')
    return {'solved': counts['All'], 'easy': counts.get('Easy', 0), 'medium': counts.get('Medium', 0),
            'hard': counts.get('Hard', 0)}


def packages() -> dict:
    """The package list published on pranaymahendrakar.com/llms.txt (which that site reads from PyPI)."""
    text = fetch(SITE + '/llms.txt', headers={'Accept': 'text/plain,*/*;q=0.8'})
    section = text.split('## Open-source packages', 1)[1].split('\n## ', 1)[0]
    count = len([line for line in section.split('\n') if line.startswith('- ')])
    if not count:
        raise RuntimeError('no packages listed in llms.txt')
    return {'count': count}


# ----------------------------------------------------------------- cache
def collect(cache_path: str, token: str) -> dict:
    """Read every source; where one fails, keep what the cache already holds."""
    try:
        with open(cache_path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        data = {}

    today = datetime.datetime.now(datetime.timezone.utc).date()
    answered = data.setdefault('answered', {})
    sources = {'github': (lambda: github(token)) if token else None, 'research': research, 'blog': blog,
               'podcast': podcast, 'leetcode': leetcode, 'packages': packages}
    for name, read in sources.items():
        if read is None:
            print('skip  %-9s (no token)' % name, flush=True)
            continue
        try:
            data[name] = read()
            answered[name] = today.isoformat()
            print('ok    %s' % name, flush=True)
        except Exception as error:  # noqa: BLE001 - any failure means "keep the last good value"
            state = 'kept the value from %s' % answered.get(name, '?') if name in data else 'NO cached value yet'
            print('FAIL  %-9s %s: %s (%s)' % (name, type(error).__name__, error, state), flush=True)

    missing = [name for name in sources if name not in data]
    if missing:
        raise SystemExit('No data at all for: ' + ', '.join(missing))

    for name in sources:
        last = answered.get(name)
        age = (today - datetime.date.fromisoformat(last)).days if last else None
        if age is None or age >= STALE_AFTER_DAYS:
            # shown as a warning on the workflow run, and GitHub mails it to the owner
            print('::warning title=Profile data is stale::%s has not answered since %s' % (name, last or 'ever'), flush=True)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False, sort_keys=True)
        handle.write('\n')
    return data
