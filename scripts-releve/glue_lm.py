#!/usr/bin/env python3
"""Recolle les tranches L<k> de l'export lead magnet (window.__lpart, scripts-releve/export_lm.js) → export_lm.txt.
Usage : python3 scripts-releve/glue_lm.py <out.txt> [--hours 3]
Même principe que glue_json.py : cherche dans les tool-results récents, recolle par ancre dans le recouvrement."""
import json, sys, glob, os, re, time
out = sys.argv[1]
hours = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 3
lim = time.time() - hours * 3600
files = sorted([p for p in glob.glob(os.path.expanduser('~/.claude/projects/*/*/tool-results/*')) if os.path.getmtime(p) >= lim], key=os.path.getmtime)
parts = {}
for p in files:
    try: t = ''.join(x.get('text', '') for x in json.load(open(p, encoding='utf-8')))
    except Exception: t = open(p, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'(?:^|\n)L(\d+)\n', t):
        body = t[m.end():]; j = body.find('\nENDLPART')
        if j >= 0: parts[int(m.group(1))] = body[:j]
if not parts: sys.exit('aucune tranche L trouvée')
ks = sorted(parts); missing = [k for k in range(ks[-1] + 1) if k not in parts]
if missing: sys.exit('tranches manquantes : ' + str(missing))
lines = parts[ks[0]].split('\n')
for k in ks[1:]:
    nxt = parts[k].split('\n')
    anchor = nxt[1] if len(nxt) > 1 else ''
    if anchor not in lines: sys.exit(f'ancre introuvable pour la tranche {k}')
    lines = lines[:lines.index(anchor)] + nxt[1:]
lines = [l for l in lines if l and l != 'ENDLM']
open(out, 'w', encoding='utf-8').write('\n'.join(lines))
print(len(ks), 'tranches,', len(lines) - 1, 'envois →', out, '| fin OK' if any('ENDLM' in parts[k] for k in ks) else '| ENDLM ABSENT')
