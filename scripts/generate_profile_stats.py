import json, os, urllib.request
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.getenv('PROFILE_USERNAME', 'Hyouem')
HEADERS = {'Accept':'application/vnd.github+json','User-Agent':'profile-stats','X-GitHub-Api-Version':'2022-11-28'}
if os.getenv('GH_TOKEN'):
    HEADERS['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']

def api(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS),timeout=40) as response:
        return json.load(response)

def repositories():
    result=[]; page=1
    while True:
        batch=api(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch,list): raise RuntimeError('Invalid repositories response')
        result.extend(r for r in batch if not r.get('private'))
        if len(batch)<100: return result
        page+=1

def t(x,y,s,size=14,color='#e2e8f0',weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(s))}</text>'

def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" width="460" height="235" viewBox="0 0 460 235"><rect x="1" y="1" width="458" height="233" rx="13" fill="#15131f" stroke="#3c354e"/><g font-family="Segoe UI,Arial,sans-serif">'+body+'</g></svg>'

def main():
    repos=repositories()
    bytes_by_lang=defaultdict(int)
    for r in repos:
        langs=api(r['languages_url'])
        if not isinstance(langs,dict): raise RuntimeError(f'Invalid languages response for {r["name"]}')
        for lang,amount in langs.items():
            if isinstance(amount,int) and amount>0: bytes_by_lang[lang]+=amount
    ranked=sorted(bytes_by_lang.items(),key=lambda x:(-x[1],x[0]))
    total=sum(bytes_by_lang.values())
    stars=sum(r.get('stargazers_count',0) for r in repos)
    n=len(repos)
    overview=t(24,42,'GitHub • Repositórios públicos',19,'#ff399c',700)
    overview+=t(24,95,n,36,'#ffffff',700)+t(105,95,'repositórios públicos',15)
    overview+=t(24,148,stars,30,'#ffffff',700)+t(105,148,'estrelas recebidas',15)
    overview+=t(24,191,f'{len(ranked)} linguagens identificadas',14,'#73e4e4')
    overview+=t(24,214,'Inclui forks, arquivados e demais projetos',11,'#b9adc6')
    body=t(24,36,'Linguagens • Código publicado',19,'#ff399c',700)
    body+=t(24,58,'% de bytes classificados pelo GitHub Linguist',11,'#c9c0d3')
    top=ranked[:7]; remaining=sum(q for _,q in ranked[7:])
    if remaining: top.append(('Outras',remaining))
    colors=['#f7d046','#3b82f6','#ec4899','#2dd4bf','#a78bfa','#f97316','#8dd84b','#94a3b8']
    if total:
        x=24.
        for i,(_,amount) in enumerate(top):
            w=412*amount/total
            body+=f'<rect x="{x:.2f}" y="75" width="{w:.2f}" height="14" fill="{colors[i]}"/>'
            x+=w
        for i,(name,amount) in enumerate(top):
            cx=24+(i//4)*214; cy=111+(i%4)*27
            body+=f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{colors[i]}"/>'
            body+=t(cx+16,cy,f'{name[:13]} {amount/total*100:.1f}%',12,'#e6e1eb',600)
    else: body+=t(24,120,'Nenhum código de linguagem encontrado',13)
    body+=t(24,222,f'{n} repositórios públicos analisados',11,'#b9adc6')
    out=Path('assets/stats'); out.mkdir(parents=True,exist_ok=True)
    (out/'overview.svg').write_text(svg(overview),encoding='utf-8')
    (out/'languages.svg').write_text(svg(body),encoding='utf-8')
    print(f'Public repositories={n}; languages={len(ranked)}; bytes={total}')

if __name__=='__main__': main()
