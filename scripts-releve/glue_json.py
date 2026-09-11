#!/usr/bin/env python3
"""Recolle les tranches J<k> de l'export complet (window.__jpart, pas de 47 000, longueur 49 000) → dump.json.
Usage : python3 scripts-releve/glue_json.py <out.json> [--prefix J] [--hours 3]
Cherche dans tous les ~/.claude/projects/*/*/tool-results/*.txt modifiés depuis moins de --hours heures (la plus récente
occurrence de chaque tranche gagne). get_page_text altère quelques caractères : on recolle par ancre dans le
recouvrement, jamais par position."""
import json, sys, glob, os, re, time
out = sys.argv[1]
pre = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "J"
hours = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 3
lim = time.time() - hours * 3600
files = sorted([p for p in glob.glob(os.path.expanduser('~/.claude/projects/*/*/tool-results/*.txt')) if os.path.getmtime(p) >= lim], key=os.path.getmtime)
parts = {}
for p in files:
    try: t = ''.join(x.get('text', '') for x in json.load(open(p, encoding='utf-8')))
    except Exception: t = open(p, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'(?:^|\n)' + pre + r'(\d+)\n', t):
        k = int(m.group(1)); body = t[m.end():]
        j = body.find('\nEND' + pre + 'PART')
        if j < 0: continue
        parts[k] = body[:j]
if not parts: sys.exit('aucune tranche ' + pre + ' trouvée')
ks = sorted(parts); missing = [k for k in range(ks[-1] + 1) if k not in parts]
if missing: sys.exit('tranches manquantes : ' + str(missing))
txt = parts[ks[0]]
for k in ks[1:]:
    t = parts[k]; anchor = t[200:500]; i = txt.rfind(anchor)
    if i < 0: sys.exit(f'ancre introuvable pour la tranche {k}')
    txt = txt[:i] + t[200:]
convs, bad = [], 0
for line in txt.split('\n'):
    line = line.strip()
    if not line or line == 'ENDDUMP': continue
    try: convs.append(json.loads(line))
    except Exception as e: bad += 1; print('ligne illisible :', line[:80], e)
json.dump(convs, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
print(len(ks), 'tranches,', len(txt), 'caractères,', len(convs), 'conversations,', bad, 'illisibles →', out, '| fin OK' if 'ENDDUMP' in txt else '| ENDDUMP ABSENT')
