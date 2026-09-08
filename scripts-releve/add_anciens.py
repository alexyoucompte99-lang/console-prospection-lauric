#!/usr/bin/env python3
"""Ajoute des anciens abonnés jamais contactés à data/abonnes.csv (Type=ancien).
Entrée : JSON [{pseudo,nom,prive,pk,bio,cat,posts,followers,following,profil,cible,message}] ; conserve toutes les lignes existantes."""
import csv,sys,json,datetime,pathlib
ROOT=pathlib.Path('/Users/alex/Alex/lauric-dashboard'); CSV=ROOT/'data'/'abonnes.csv'
FIELDS=['Pseudo','Nom','Detecte','Profil','Cible','Message propose','Contacte','Date contact','Message envoye','Statut','Conv','Releve','Type']
today=datetime.date.today().strftime('%d/%m/%Y')
old=list(csv.DictReader(open(CSV,encoding='utf-8')))
for o in old: o.setdefault('Type','')
have={o['Pseudo'] for o in old}
leads={r['Pseudo'] for r in csv.DictReader(open(ROOT/'data'/'leads-insta.csv',encoding='utf-8'))}
new=json.load(open(sys.argv[1]))
added=0
for n in new:
    if n['pseudo'] in have or n['pseudo'] in leads: continue
    old.append({'Pseudo':n['pseudo'],'Nom':n.get('nom') or n['pseudo'],'Detecte':today,'Profil':n.get('profil',''),'Cible':n.get('cible',''),
        'Message propose':n.get('message',''),'Contacte':'non','Date contact':'','Message envoye':'','Statut':'','Conv':'','Releve':today,'Type':'ancien'})
    have.add(n['pseudo']); added+=1
assert len({o['Pseudo'] for o in old})==len(old)
with open(CSV,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(old)
print('ajoutés',added,'total',len(old))
