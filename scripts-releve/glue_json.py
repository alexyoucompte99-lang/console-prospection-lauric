#!/usr/bin/env python3
"""Recolle les tranches P<k> (47 000 caractères de pas, 49 000 de longueur) sorties par get_page_text → dump.json.
Usage : python3 scripts-releve/glue_json.py <session-id> <out.json>   (cherche dans ~/.claude/projects/-Users-alex-Alex/<session>/tool-results/)
Chaque tranche est `P<k>\n` + texte + `\nENDPART` ; on prend les 47 000 premiers caractères de chaque tranche sauf la dernière."""
import json, sys, glob, os, re
sess, out = sys.argv[1], sys.argv[2]
files = sorted(glob.glob(os.path.expanduser(f'~/.claude/projects/-Users-alex-Alex/{sess}/tool-results/*.txt')), key=os.path.getmtime)
parts = {}
for p in files:
    try: t = ''.join(x.get('text', '') for x in json.load(open(p, encoding='utf-8')))
    except Exception: t = open(p, encoding='utf-8').read()
    for m in re.finditer(r'(?:^|\n)P(\d+)\n', t):
        k = int(m.group(1)); body = t[m.end():]
        j = body.find('\nENDPART')
        if j < 0: print('tranche', k, 'incomplète dans', p); continue
        parts[k] = body[:j]
if not parts: sys.exit('aucune tranche trouvée')
ks = sorted(parts); missing = [k for k in range(ks[-1] + 1) if k not in parts]
if missing: sys.exit('tranches manquantes : ' + str(missing))
# get_page_text altère quelques caractères : on recolle par ancre dans le recouvrement (2 000 caractères), pas par position
txt = parts[ks[0]]
for k in ks[1:]:
    t = parts[k]; anchor = t[200:500]; i = txt.rfind(anchor)
    if i < 0: sys.exit(f'ancre introuvable pour la tranche {k}')
    txt = txt[:i] + t[200:]
convs = []
for line in txt.split('\n'):
    line = line.strip()
    if not line or line in ('ENDDUMP',): continue
    try: convs.append(json.loads(line))
    except Exception as e: print('ligne illisible :', line[:80], e)
json.dump(convs, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
print(len(ks), 'tranches,', len(txt), 'caractères,', len(convs), 'conversations →', out)
