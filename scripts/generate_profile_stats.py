#!/usr/bin/env python3
"""GitHub profile statistics: public repositories and per-language repository prevalence."""
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get('PROFILE_USERNAME', 'Hyouem')
TOKEN = os.environ.get('GH_TOKEN', '')
OUT = Path('assets/stats')
HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'Hyouem-profile-statistics',
    'X-GitHub-Api-Version': '2022-11-28',
}
if TOKEN:
    HEADERS['Authorization'] = f'Bearer {TOKEN}'


def request(path):
    url = path if path.startswith('https://') else 'https://api.github.com/' + path.lstrip('/')
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def owned_public_repositories():
    found = []
    page = 1
    while True:
        items = request(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(items, list):
            raise RuntimeError(f'Invalid repository response on page {page}')
        found.extend(items)
        if len(items) < 100:
            break
        page += 1
    return found


def label(x, y, value, size=13, color='#e2e8f0', weight=400):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}">{escape(str(value))}</text>')


def svg(body, width=460, height=250):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="13" '
            f'fill="#15131f" stroke="#3c354e" />'
            '<g font-family="Segoe UI,Arial,sans-serif">' + body + '</g></svg>')


def generate():
    profile = request(f'users/{USER}')
    expected = profile.get('public_repos')
    if not isinstance(expected, int):
        raise RuntimeError('The GitHub API did not provide public_repos')
    repos = owned_public_repositories()
    names = [r.get('full_name') for r in repos]
    if len(repos) != expected or len(set(names)) != len(repos):
        raise RuntimeError(f'Incomplete GitHub API inventory: fetched {len(repos)}, profile reports {expected}')
    if any(r.get('private') or r.get('owner', {}).get('login', '').lower() != USER.lower() for r in repos):
        raise RuntimeError('Unexpected private or foreign repository in public inventory')

    prevalence = Counter()
    stars = 0
    with_code = 0
    for repo in repos:
        stars += repo.get('stargazers_count', 0)
        languages = request(repo['languages_url'])
        if not isinstance(languages, dict):
            raise RuntimeError(f'Invalid language payload for {repo["full_name"]}')
        present = [name for name, count in languages.items() if isinstance(count, (int, float)) and count > 0]
        if present:
            with_code += 1
        prevalence.update(set(present))

    count = len(repos)
    out = label(24, 40, 'GitHub • Repositórios públicos', 19, '#ff399c', 700)
    out += label(24, 95, count, 34, '#fff', 700)
    out += label(105, 95, 'repositórios públicos', 14)
    out += label(24, 145, stars, 30, '#fff', 700)
    out += label(105, 145, 'estrelas recebidas', 14)
    out += label(24, 191, f'{with_code} projetos com código detectado', 13, '#73e4e4', 600)
    out += label(24, 218, f'{len(prevalence)} linguagens identificadas', 12, '#b9adc6')

    ranked = sorted(prevalence.items(), key=lambda pair: (-pair[1], pair[0].casefold()))
    top = ranked[:8]
    if 'Java' in prevalence and not any(name == 'Java' for name, _ in top):
        top = ranked[:7] + [('Java', prevalence['Java'])]
    # No fabricated Java figure if Java is absent. Still show 0 accurately.
    if 'Java' not in prevalence and not any(name == 'Java' for name, _ in top):
        top = ranked[:7] + [('Java', 0)]
    colors = ['#f7d046','#3b82f6','#ec4899','#2dd4bf','#a78bfa','#f97316','#8dd84b','#94a3b8']
    body = label(24, 35, 'Linguagens • Presença nos projetos', 18, '#ff399c', 700)
    body += label(24, 57, f'% dos {count} repositórios que contêm cada linguagem', 11, '#c9c0d3')
    body += label(24, 72, 'Um projeto pode conter várias linguagens', 10, '#b9adc6')
    for index, (language, occurrences) in enumerate(top):
        col, row = divmod(index, 4)
        x, y = 24 + col * 216, 108 + row * 30
        body += f'<circle cx="{x+5}" cy="{y-4}" r="5" fill="{colors[index]}"/>'
        percent = 100 * occurrences / count if count else 0.0
        body += label(x + 16, y, f'{language[:12]} {percent:.1f}% ({occurrences})', 12, '#e6e1eb', 600)
    if not count:
        body += label(24, 155, 'Nenhum repositório público identificado', 12)
    body += label(24, 238, f'Base: {count} repositórios públicos • dados do GitHub', 11, '#b9adc6')

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'overview.svg').write_text(svg(out), encoding='utf-8')
    (OUT / 'languages.svg').write_text(svg(body), encoding='utf-8')
    print(f'VALIDATED: {count} / {expected} public repositories; {with_code} with language data; Java in {prevalence.get("Java", 0)}')


if __name__ == '__main__':
    generate()
