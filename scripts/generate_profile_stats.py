#!/usr/bin/env python3
"""Generate self-hosted GitHub profile cards from public owned repositories."""
import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.getenv('PROFILE_USERNAME', 'Hyouem')
TOKEN = os.getenv('GH_TOKEN', '')
OUT = Path('assets/stats')
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {'Accept':'application/vnd.github+json','User-Agent':'profile-stats-generator','X-GitHub-Api-Version':'2022-11-28'}
if TOKEN: HEADERS['Authorization'] = f'Bearer {TOKEN}'

def request(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=35) as response:
        return json.load(response)

def repos():
    page = 1
    while True:
        data = request(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(data,list): raise RuntimeError(f'Unexpected GitHub response: {data}')
        yield from data
        if len(data) < 100: return
        page += 1

# Deliberate definition: active, original PUBLIC repos owned by the user;
# exclude archive-only mirrors and the profile README repository.
all_repos = list(repos())
selected = [r for r in all_repos if not r.get('fork') and not r.get('archived')
            and not r['name'].lower().startswith('arquivo-')
            and r['name'].lower() != USER.lower()]
lang_bytes = defaultdict(int)
for r in selected:
    for language, count in request(r['languages_url']).items():
        lang_bytes[language] += count

total = sum(lang_bytes.values())
ranked = sorted(lang_bytes.items(), key=lambda x: (-x[1],x[0]))
# Show 7 largest, combine others. Percentages are bytes of GitHub Linguist-detected code.
top = ranked[:7]
others = sum(v for _,v in ranked[7:])
if others: top.append(('Outras', others))
colors = ['#f7d046','#3b82f6','#ec4899','#2dd4bf','#a78bfa','#f97316','#8dd84b','#94a3b8']
updated = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')

def txt(x,y,content,size=14,color='#e2e8f0',weight=400,anchor=None):
    attrs = f' x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}"'
    if anchor: attrs += f' text-anchor="{anchor}"'
    return f'<text{attrs}>{escape(str(content))}</text>'

def svg(body,w=460,h=250):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="13" fill="#15131f" stroke="#3c354e"/>'
            '<g font-family="Segoe UI,Arial,sans-serif">'+body+'</g></svg>')

stars = sum(r.get('stargazers_count',0) for r in selected)
body = txt(24,42,'GitHub • Projetos públicos',20,'#ff399c',700)
body += txt(24,90,f'{len(all_repos)}',32,'#fff',700)+txt(88,90,'repositórios públicos',15)
body += txt(24,139,str(stars),32,'#fff',700)+txt(88,139,'estrelas nos elegíveis',15)
body += txt(24,177,f'{len(ranked)} linguagens detectadas',14,'#73e4e4')
body += txt(24,210,f'{len(selected)} elegíveis no gráfico de linguagens',12,'#b9adc6')
body += txt(24,231,f'Atualizado: {updated}',11,'#b9adc6')
(OUT/'overview.svg').write_text(svg(body),encoding='utf-8')

body = txt(24,36,'Linguagens • Código publicado',19,'#ff399c',700)
body += txt(24,58,'% dos bytes detectados pelo GitHub Linguist',11,'#c9c0d3')
x=24
if total:
    for i,(name,amount) in enumerate(top):
        width = 412*amount/total
        body += f'<rect x="{x:.2f}" y="75" width="{width:.2f}" height="14" fill="{colors[i]}"/>'
        x+=width
    for i,(name,amount) in enumerate(top):
        cx=24+(i//4)*214
        cy=113+(i%4)*29
        body+=f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{colors[i]}"/>'
        body+=txt(cx+16,cy,f'{name[:14]} {amount/total*100:.1f}%',12,'#e6e1eb',600)
else:
    body += txt(24,120,'Nenhum código encontrado nos repositórios elegíveis.',13)
body += txt(24,238,f'{len(selected)} repositórios • {updated}',11,'#b9adc6')
(OUT/'languages.svg').write_text(svg(body),encoding='utf-8')
print(f'Generated cards from {len(selected)} repositories and {len(ranked)} languages.')
