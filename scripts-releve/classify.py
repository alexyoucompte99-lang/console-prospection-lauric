#!/usr/bin/env python3
"""INFOS lines (pk|u|n|bio|cat|biz|pro|posts|fol|fing|priv|url|city) → JSON pour add_anciens.py"""
import sys,json,re
PRO=re.compile(r"dirigeant|fondat|ceo|gérant|gerant|coach|consult|entrepren|entreprise|boutique|agence|sas\b|sarl|auto.?entrepreneur|artisan|freelance|formatri|formateur|expert|cabinet|directeur|directrice|manager|business|marketing|immobilier|restaurant|salon|société|societe|pdg|president|présidente|commerce|studio|atelier|ingénieur|ingenieur|écrivain|auteur|artiste|coaching|thérap|therap|naturo|reiki|nutrition|photograph|vidéaste|monteur|musique|music|ecole|école|formation",re.I)
def prenom(n):
    w=(n or '').split()
    if w and re.match(r"^[A-Za-zÀ-ÿ'’-]{2,}$",w[0]) and w[0].lower() not in ('mr','mrs','the','chef','coach','dr','le','la','notes','mc'): return w[0][0].upper()+w[0][1:].lower()
    return ''
def nb(x):
    try: return int(x)
    except: return 0
out=[]
for l in open(sys.argv[1],encoding='utf-8').read().split('\n'):
    f=l.split('|')
    if len(f)<13: continue
    pk,u,n,bio,cat,biz,pro,posts,fol,fing,priv,url,city=f[:13]
    bio=bio.replace('⏎',' ').strip(); posts,fol,fing,priv=nb(posts),nb(fol),nb(fing),nb(priv)
    p=prenom(n); hello=('Hello '+p+' !') if p else 'Hello !'
    desc=[]
    desc.append(('Compte privé' if priv else 'Compte public')+f' : {posts} publication{"s" if posts>1 else ""}, {fol} abonnés, suit {fing} comptes.')
    if bio: desc.append('Bio : « '+bio[:140]+' ».')
    if cat: desc.append('Catégorie : '+cat+'.')
    if url: desc.append('Lien : '+url)
    if city: desc.append('Ville : '+city)
    profil=' '.join(desc)
    mass = fing>=3000 and fol<fing/4
    m = PRO.search(bio or '') or PRO.search(n or '')
    propro = bool(cat) or bool(biz=='1') or bool(m)
    if mass and not propro: cible='❌ Probable compte de masse (suit '+str(fing)+' comptes)'
    elif propro: cible='✅ Potentiel ('+(cat or (m.group(0).lower() if m else 'compte pro'))+')'
    elif priv and posts<=3 and not bio: cible='❓ À qualifier (compte privé, rien de visible)'
    elif posts==0 and not bio: cible='❓ À qualifier (profil vide)'
    else: cible='❓ À qualifier (profil perso, pas d\'info pro)'
    intro=hello+' Je me permets de t\'écrire, tu suis mon compte depuis un moment et je ne t\'ai jamais dit bonjour, c\'est réparé 😊\n\n'
    if mass and not propro:
        msg=''
    elif cat or m:
        elem=cat.lower() if cat else m.group(0).lower()
        msg=intro+f"Je suis passé sur ton profil et j'ai vu que tu étais dans l'univers {elem}, c'est un domaine où on porte souvent tout sur ses épaules.\n\nJe suis curieux : tu es à ton compte ou tu diriges une équipe ?"
    elif priv:
        msg=intro+"Ton compte est privé donc je n'ai rien pu voir de ton activité, et j'aime bien savoir qui se cache derrière les personnes qui me suivent.\n\nTu es à ton compte ou tu diriges une équipe ?"
    elif posts==0:
        msg=intro+"Ton profil ne dit pas grand chose sur toi, et comme je parle surtout aux dirigeants ici, je suis curieux de savoir ce qui t'a parlé dans mon contenu.\n\nTu es à ton compte ou tu diriges une équipe ?"
    else:
        msg=intro+"J'ai jeté un œil à tes publications, sympa ! Je n'ai pas vu de trace de ton activité pro par contre, et comme je parle surtout aux dirigeants ici, je suis curieux.\n\nTu es à ton compte ou tu diriges une équipe ?"
    out.append({'pseudo':u,'nom':n or u,'pk':pk,'prive':priv,'profil':profil,'cible':cible,'message':msg})
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
import collections; print(len(out),collections.Counter(o['cible'][:12] for o in out))
