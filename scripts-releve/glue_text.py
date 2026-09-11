#!/usr/bin/env python3
"""Recolle les tranches P<k> du relevé ┃ (window.__part) → dump.txt, par ancre dans le recouvrement.
Usage : python3 scripts-releve/glue_text.py <out.txt> [--prefix P] [--hours 3]"""
import json, sys, glob, os, re, time
out = sys.argv[1]
pre = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "P"
hours = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 3
lim = time.time() - hours * 3600
files = sorted([p for p in glob.glob(os.path.expanduser('~/.claude/projects/*/*/tool-results/*.txt')) if os.path.getmtime(p) >= lim], key=os.path.getmtime)
parts = {}
for p in files:
    try: t = ''.join(x.get('text', '') for x in json.load(open(p, encoding='utf-8')))
    except Exception: t = open(p, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'(?:^|\n)' + pre + r'(\d+)\n', t):
        k = int(m.group(1)); body = t[m.end():]
        j = min([x for x in (body.find('\nEND' + pre + 'PART'), body.find('\nENDPART')) if x >= 0] or [-1])
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
open(out, 'w', encoding='utf-8').write(txt)
print(len(ks), 'tranches,', len(txt), 'caractères,', txt.count('\n') + 1, 'lignes →', out, '| fin OK' if 'ENDDUMP' in txt else '| ENDDUMP ABSENT')
