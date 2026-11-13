#!/usr/bin/env python3
"""Generate Hyouem profile cards from verified public GitHub inventory.

Primary language = largest positive byte count in each repository's GitHub
languages endpoint (tie broken alphabetically). Repos without language bytes
are included in overview but excluded from language denominator.
"""
import json
import os
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen
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
    with urlopen(Request(url, headers=HEADERS), timeout=40) as response:
        return json.load(response)


def owned_public_repositories():
    results = []
    page = 1
    while True:
        batch = request(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError(f'Invalid GitHub repository response at page {page}')
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def primary_language(languages):
    """Deterministic primary language from GitHub Linguist language bytes."""
    if not isinstance(languages, dict):
        raise RuntimeError('Invalid languages response')
    valid = [(language, amount) for language, amount in languages.items()
             if isinstance(language, str) and isinstance(amount, int)
             and not isinstance(amount, bool) and amount > 0]
    return sorted(valid, key=lambda item: (-item[1], item[0].casefold()))[0][0] if valid else None


def label(x, y, content, size=13, color='#e2e8f0', weight=400, anchor=None):
    attr = f' x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}"'
    if anchor:
        attr += f' text-anchor="{anchor}"'
    return f'<text{attr}>{escape(str(content))}</text>'


def svg(body, width=460, height=250):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="14" '
            f'fill="#15131f" stroke="#3c354e"/>'
            '<g font-family="Segoe UI,Arial,sans-serif">' + body + '</g></svg>')


def overview(total, with_code, stars, languages):
    body = label(24, 39, 'GitHub • Estatísticas', 19, '#ff399c', 700)
    body += label(24, 96, total, 36, '#ffffff', 700)
    body += label(105, 96, 'repositórios públicos', 14)
    body += label(24, 150, with_code, 30, '#ffffff', 700)
    body += label(105, 150, 'com linguagem detectada', 14)
    body += label(24, 198, f'{stars} estrelas recebidas', 14, '#73e4e4', 600)
    body += label(24, 224, f'{languages} linguagens identificadas', 12, '#b9adc6')
    return svg(body)


LANGUAGE_COLORS = {
    'Java': '#f97362', 'TypeScript': '#3b82f6', 'Python': '#f7c95c',
    'HTML': '#e47543', 'JavaScript': '#e8df6c', 'CSS': '#a78bfa',
    'Rust': '#dd9566', 'C#': '#7cc47c', 'Go': '#5bc7d8',
}


def languages_card(counts, denominator):
    body = label(24, 36, 'Linguagens • Principais por projeto', 18, '#ff399c', 700)
    body += label(24, 58, 'Cada projeto conta para uma linguagem principal', 11, '#c9c0d3')
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    visible = ranked[:6]
    others = sum(amount for _, amount in ranked[6:])
    if others:
        visible.append(('Outras', others))
    if not denominator:
        body += label(24, 125, 'Nenhuma linguagem principal encontrada', 13)
    else:
        y = 83
        for name, amount in visible:
            pct = 100 * amount / denominator
            color = LANGUAGE_COLORS.get(name, '#54c5bb' if name != 'Outras' else '#94a3b8')
            body += label(24, y + 12, name[:19], 12, '#e6e1eb', 600)
            body += label(436, y + 12, f'{pct:.1f}% ({amount})', 12, '#e6e1eb', 600, 'end')
            body += f'<rect x="166" y="{y+3}" width="153" height="9" rx="4" fill="#373244"/>'
            body += f'<rect x="166" y="{y+3}" width="{153*pct/100:.2f}" height="9" rx="4" fill="{color}"/>'
            y += 22
    body += label(24, 242, f'Base: {denominator} repositórios com linguagem detectada', 10, '#b9adc6')
    return svg(body)


STACK = [
    ('Java', 'Linguagem'), ('Spring Boot', 'Backend'),
    ('PostgreSQL', 'Banco de dados'), ('JUnit', 'Testes'),
    ('Docker', 'Infraestrutura'), ('GitHub Actions', 'CI/CD'),
]


def stack_card():
    """Curated professional stack, not inferred skills or fake expertise scores."""
    width, height = 940, 132
    body = label(24, 35, 'Stack • Desenvolvimento Backend', 20, '#ff399c', 700)
    body += label(24, 55, 'Tecnologias de atuação • seleção profissional', 11, '#b9adc6')
    for i, (name, category) in enumerate(STACK):
        x = 24 + i * 153
        body += f'<rect x="{x}" y="69" width="143" height="46" rx="8" fill="#221f2d" stroke="#3c354e"/>'
        body += label(x + 11, 87, name, 12, '#ffffff', 650)
        body += label(x + 11, 103, category, 9, '#b9adc6')
    return svg(body, width, height)


def generate():
    profile = request(f'users/{USER}')
    expected = profile.get('public_repos')
    if not isinstance(expected, int) or isinstance(expected, bool):
        raise RuntimeError('GitHub public_repos count is invalid')
    repos = owned_public_repositories()
    names = [r['full_name'] for r in repos]
    if len(repos) != expected or len(set(names)) != expected:
        raise RuntimeError(f'Incomplete inventory: {len(repos)} retrieved vs {expected} published')
    if any(r.get('private') or r.get('owner', {}).get('login', '').casefold() != USER.casefold() for r in repos):
        raise RuntimeError('Found private or foreign repository in public inventory')

    primary = Counter()
    all_languages = set()
    stars = 0
    for repo in repos:
        stars += repo.get('stargazers_count', 0)
        data = request(repo['languages_url'])
        selected = primary_language(data)
        if selected:
            primary[selected] += 1
        all_languages.update(k for k, v in data.items() if isinstance(v, int) and not isinstance(v, bool) and v > 0)

    denominator = sum(primary.values())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'overview.svg').write_text(overview(len(repos), denominator, stars, len(all_languages)), encoding='utf-8')
    (OUT / 'languages.svg').write_text(languages_card(primary, denominator), encoding='utf-8')
    (OUT / 'stack.svg').write_text(stack_card(), encoding='utf-8')
    print(f'VALIDATED: {len(repos)} public repos, {denominator} with language; primary distribution: {dict(primary)}')


if __name__ == '__main__':
    generate()
