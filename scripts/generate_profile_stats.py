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
    """Ranked bars scaled to the largest language, with true percentages."""
    width, height = 460, 250
    body = label(16, 28, 'Linguagens principais', 17, '#ff2995', 700)
    body += '<g transform="translate(426 15)" stroke="#ff2995" stroke-width="2" stroke-linecap="round">'
    body += '<path d="M0 13v-4 M5 13V4 M10 13V0"/></g>'
    body += label(16, 48, 'Ranking por linguagem predominante', 10, '#b9adc6')
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    visible = ranked[:6]
    others = sum(amount for _, amount in ranked[6:])
    if not denominator:
        body += label(18, 118, 'Nenhuma linguagem detectada', 13)
    else:
        max_count = visible[0][1] if visible else 1
        for i, (name, amount) in enumerate(visible):
            y = 67 + i * 25
            pct = 100 * amount / denominator
            color = LANGUAGE_COLORS.get(name, '#54c5bb')
            body += label(17, y + 8, f'{i + 1:02d}', 10, '#807891')
            body += label(42, y + 8, name[:15], 11, '#ffffff', 700)
            body += f'<rect x="145" y="{y-2}" width="256" height="11" rx="5.5" fill="#393445"/>'
            fill_width = 256 * amount / max_count
            body += f'<rect x="145" y="{y-2}" width="{fill_width:.2f}" height="11" rx="5.5" fill="{color}"/>'
            body += label(446, y + 8, f'{pct:.1f}%', 11, '#f4f1f8', 650, 'end')
        body += '<path d="M16 224H444" stroke="#363041"/>'
        body += label(16, 242, f'{denominator} projetos classificados • Outras: {100*others/denominator:.1f}%', 9, '#b9adc6')
    return svg(body, width, height)


STACK = [
    ('Java', 'Linguagem'), ('Spring Boot', 'Backend'),
    ('PostgreSQL', 'Banco de dados'), ('JUnit', 'Testes'),
    ('Docker', 'Infraestrutura'), ('GitHub Actions', 'CI/CD'),
]


def stack_card():
    "Self-contained premium SVG with no external assets."
    width, height = 940, 288
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Stack de desenvolvimento backend: Java, Spring Boot, PostgreSQL, JUnit, Docker, GitHub Actions">']
    parts.append('''<defs>
      <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#13101b"/><stop offset="1" stop-color="#080811"/></linearGradient>
      <linearGradient id="pink" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fe479f"/><stop offset="1" stop-color="#a90070"/></linearGradient>
      <linearGradient id="java" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#ffb046"/><stop offset="1" stop-color="#ff4e83"/></linearGradient>
      <linearGradient id="spring" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#7fed13"/><stop offset="1" stop-color="#4b9e2a"/></linearGradient>
      <linearGradient id="postgres" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#31b7ff"/><stop offset="1" stop-color="#2974f8"/></linearGradient>
      <linearGradient id="junit" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#d4f535"/><stop offset="1" stop-color="#78bb33"/></linearGradient>
      <linearGradient id="docker" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#21d7f5"/><stop offset="1" stop-color="#168cff"/></linearGradient>
      <linearGradient id="actions" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#d26aff"/><stop offset="1" stop-color="#8741ed"/></linearGradient>
      <filter id="glow" x="-20%" y="-30%" width="140%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
    </defs>''')
    parts.append('<rect x="10" y="10" width="920" height="264" rx="20" stroke="#ff2399" stroke-opacity=".45" stroke-width="6" fill="none" filter="url(#glow)"/>')
    parts.append('<rect x="10" y="10" width="920" height="264" rx="20" fill="url(#panel)" stroke="#d52c8c" stroke-width="1.4"/>')
    parts.append('<path d="M640 92 C760 90 810 60 930 16 L930 11 L650 11Z" fill="#db197b" opacity=".11"/>')
    parts.append('<rect x="36" y="31" width="57" height="57" rx="12" fill="#201626" stroke="#51304a"/>')
    parts.append('<g font-family="Segoe UI,Arial,sans-serif">')
    parts.append(label(64, 70, '</>', 27, '#ff399c', 750, 'middle'))
    parts.append('<path d="M113 30V90" stroke="#584457"/>')
    parts.append(label(132, 60, 'Stack • Desenvolvimento Backend', 26, '#ff2995', 750))
    parts.append(label(132, 82, 'Tecnologias de atuação • seleção profissional', 13, '#c7bfcf'))
    palette=['java','spring','postgres','junit','docker','actions']
    accent=['#ff7c64','#7ce23b','#39a8ff','#abdb43','#22bcf3','#b05aff']
    # Icons are compact native SVG pictograms, guaranteed to render offline.
    icons=[
      '<g stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"><path d="M-16 10Q0 18 16 10M-14 17Q0 24 14 17M-14 7H13Q12 12 6 14H-7Q-13 11-14 7ZM0-19Q-8-12 1-6Q9 1 0 5M8-18Q1-10 7-7"/></g>',
      '<path d="M-20 7Q-11-19 17-18Q21 8-1 19Q-10 23-20 7ZM-13 13Q0-2 15-10" fill="currentColor" stroke="currentColor" stroke-width="2"/>',
      '<g stroke="currentColor" stroke-width="2.5" fill="none"><ellipse cx="0" cy="-13" rx="17" ry="7"/><path d="M-17-13V15Q0 28 17 15V-13M-17 0Q0 13 17 0"/></g>',
      '<g stroke="currentColor" stroke-width="2.4" stroke-linejoin="round"><path d="M-7-20H8M-4-20V-4L-17 16Q-18 20-12 20H13Q19 20 16 15L4-4V-20" fill="none"/><path d="M-11 12H11L14 18H-14Z" fill="currentColor" stroke="none"/></g>',
      '<g fill="currentColor"><rect x="-20" y="-9" width="9" height="8" rx="1"/><rect x="-9" y="-9" width="9" height="8" rx="1"/><rect x="2" y="-9" width="9" height="8" rx="1"/><rect x="-9" y="-19" width="9" height="8" rx="1"/><rect x="2" y="-19" width="9" height="8" rx="1"/><path d="M-23 2H22Q17 19-1 20Q-19 19-23 2Z"/></g>',
      '<g fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="-15" cy="-15" r="6"/><circle cx="15" cy="-4" r="6"/><circle cx="-6" cy="17" r="6"/><path d="M-11-10L10-6M11 1L-2 13"/></g>'
    ]
    for i,(name, category) in enumerate(STACK):
        x=28+i*148
        parts.append(f'<rect x="{x}" y="115" width="138" height="137" rx="12" fill="#17131f" stroke="#42384b"/>')
        parts.append(f'<rect x="{x+1}" y="115" width="136" height="5" rx="2.5" fill="url(#{palette[i]})"/>')
        parts.append(f'<circle cx="{x+69}" cy="161" r="28" fill="{accent[i]}" fill-opacity=".1"/>')
        parts.append(f'<g transform="translate({x+69} 161)" style="color:{accent[i]}">{icons[i]}</g>')
        parts.append(label(x+69, 208, name, 13 if i!=5 else 11, '#ffffff', 700, 'middle'))
        parts.append(label(x+69, 230, category, 10.5, '#b9adc6', 400, 'middle'))
    parts.append('</g></svg>')
    return ''.join(parts)


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
