"""Live numbers and lists for the profile, read from their own sources.

Every source can fail on a given day (a rate limit, a bot wall, a site being
down), and a profile that shows a zero or a broken list is worse than one that
is a day old. So each reading is cached in assets/data.json and a failed fetch
falls back to the last good value instead of writing anything new.

Standard library only: this runs on a bare GitHub Actions runner.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from email.utils import parsedate_to_datetime

LOGIN = 'PranayMahendrakar'
YOUTUBE_CHANNEL = 'UCB2AeFEc6VXJAaXckP1XmqA'
SITE = 'https://pranaymahendrakar.com'
RESEARCH = 'https://research.pranaymahendrakar.com'

# The sites sit behind a CDN that challenges requests carrying only bare
# script headers; a normal Accept and Accept-Language pair is let through.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36',
    'Accept': 'application/rss+xml,application/xml,text/html;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


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
    return re.sub(r'\s+', ' ', html.unescape(html.unescape(value))).strip()


def _items(feed: str, tag: str) -> list[str]:
    return re.findall(r'<%s\b.*?</%s>' % (tag, tag), feed, re.S)


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
          weeks { contributionDays { date contributionCount } } } } } }''', {'login': LOGIN})['user']
    calendar = head['contributionsCollection']['contributionCalendar']
    weeks = [[day['contributionCount'] for day in week['contributionDays']] for week in calendar['weeks']]

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
                entry = languages.setdefault(language['name'], {'name': language['name'], 'color': language['color'] or '#8b949e', 'repos': 0})
                entry['repos'] += 1
        if not page['pageInfo']['hasNextPage']:
            break
        cursor = page['pageInfo']['endCursor']

    return {
        'repos': head['repositories']['totalCount'],
        'followers': head['followers']['totalCount'],
        'stars': stars,
        'contributions': calendar['totalContributions'],
        'weeks': weeks,
        'last_day': calendar['weeks'][-1]['contributionDays'][-1]['date'],
        'languages': sorted(languages.values(), key=lambda l: -l['repos'])[:8],
    }


def research() -> dict:
    items = _items(fetch(RESEARCH + '/feed.xml'), 'item')
    if not items:
        raise RuntimeError('research feed has no items')
    papers = []
    for item in items[:5]:
        doi = _text(item, 'guid')
        papers.append({'title': _text(item, 'title'), 'url': _text(item, 'link'),
                       'doi': doi if doi.startswith('https://doi.org/') else '',
                       'date': parsedate_to_datetime(_text(item, 'pubDate')).strftime('%Y-%m-%d')})
    return {'count': len(items), 'latest': papers}


def blog() -> dict:
    items = _items(fetch(SITE + '/feed.xml'), 'item')
    if not items:
        raise RuntimeError('blog feed has no items')
    return {'latest': [{'title': _text(i, 'title'), 'url': _text(i, 'link'),
                        'date': parsedate_to_datetime(_text(i, 'pubDate')).strftime('%Y-%m-%d')} for i in items[:5]]}


def youtube() -> dict:
    entries = _items(fetch('https://www.youtube.com/feeds/videos.xml?channel_id=' + YOUTUBE_CHANNEL), 'entry')
    if not entries:
        raise RuntimeError('YouTube feed has no entries')
    videos = []
    for entry in entries[:4]:
        video_id = _text(entry, 'yt:videoId')
        videos.append({'title': _text(entry, 'title'), 'url': 'https://www.youtube.com/watch?v=' + video_id,
                       'date': _text(entry, 'published')[:10]})
    return {'latest': videos}


def leetcode() -> dict:
    query = ('query($u: String!) { matchedUser(username: $u) { submitStatsGlobal { acSubmissionNum '
             '{ difficulty count } } } }')
    raw = fetch('https://leetcode.com/graphql', json.dumps({'query': query, 'variables': {'u': LOGIN}}).encode(),
                {'Content-Type': 'application/json', 'Accept': 'application/json',
                 'Referer': 'https://leetcode.com/u/%s/' % LOGIN})
    counts = {row['difficulty']: row['count']
              for row in json.loads(raw)['data']['matchedUser']['submitStatsGlobal']['acSubmissionNum']}
    if not counts.get('All'):
        raise RuntimeError('LeetCode returned no solved count')
    return {'solved': counts['All'], 'easy': counts.get('Easy', 0), 'medium': counts.get('Medium', 0),
            'hard': counts.get('Hard', 0)}


def pypi() -> dict:
    """Counted from the site's own llms.txt, which lists what pypi.org shows for the account."""
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

    sources = {'github': (lambda: github(token)) if token else None, 'research': research, 'blog': blog,
               'youtube': youtube, 'leetcode': leetcode, 'pypi': pypi}
    for name, read in sources.items():
        if read is None:
            print('skip  %-9s (no token)' % name)
            continue
        try:
            data[name] = read()
            print('ok    %s' % name)
        except Exception as error:  # noqa: BLE001 - any failure means "keep yesterday's value"
            state = 'kept the cached value' if name in data else 'NO cached value yet'
            print('FAIL  %-9s %s: %s (%s)' % (name, type(error).__name__, error, state))

    missing = [name for name in sources if name not in data]
    if missing:
        raise SystemExit('No data at all for: ' + ', '.join(missing))

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False, sort_keys=True)
        handle.write('\n')
    return data
