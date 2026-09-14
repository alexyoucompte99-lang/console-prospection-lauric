#!/usr/bin/env python3
"""Ajoute (ou remplace) le relevé du jour du tableau de bord professionnel Instagram (30 derniers jours)
dans data/contenu-insta.csv, lu par l'onglet Contenu et l'entonnoir de la Vue d'ensemble.
Source : https://www.instagram.com/accounts/insights/?timeframe=30 (texte de <main>).
Usage : python3 releve_contenu.py <texte_de_la_page.txt> [jj/mm/aaaa]
   ou : python3 releve_contenu.py --vues N --spectateurs N --interactions N --comptes N --visites N --liens N --followers N [--date jj/mm/aaaa]"""
import csv, sys, os, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "data", "contenu-insta.csv")
COLS = ["Date", "Vues 30j", "Spectateurs 30j", "Interactions 30j", "Comptes ayant interagi 30j",
        "Visites profil 30j", "Liens externes 30j", "Followers"]
num = lambda s: int(re.sub(r"[^\d]", "", s)) if s and re.search(r"\d", s) else ""
args = sys.argv[1:]
d = datetime.date.today().strftime("%d/%m/%Y")
if "--date" in args:
    i = args.index("--date"); d = args[i + 1]; del args[i:i + 2]
if args and not args[0].startswith("--"):
    t = open(args[0], encoding="utf-8").read()
    if len(args) > 1: d = args[1]
    def after(label, nth=1):
        m = list(re.finditer(r"^" + label + r"\s*\n([\d\s  ]+)\s*$", t, re.M))
        return num(m[nth - 1].group(1)) if len(m) >= nth else ""
    row = {"Vues 30j": after("Vues"), "Spectateurs 30j": after(r"Spectateur\(ice\)s"),
           "Interactions 30j": after("Interactions"), "Comptes ayant interagi 30j": after("Comptes ayant interagi"),
           "Visites profil 30j": after("Visites du profil"), "Liens externes 30j": after("Appuis sur des liens externes"),
           "Followers": after("Followers")}
    if row["Followers"] == "":
        m = re.search(r"\n([\d\s  ]+)\nTotal des followers", t); row["Followers"] = num(m.group(1)) if m else ""
else:
    keys = {"--vues": "Vues 30j", "--spectateurs": "Spectateurs 30j", "--interactions": "Interactions 30j",
            "--comptes": "Comptes ayant interagi 30j", "--visites": "Visites profil 30j", "--liens": "Liens externes 30j",
            "--followers": "Followers"}
    row = {v: "" for v in keys.values()}
    for k, v in keys.items():
        if k in args: row[v] = num(args[args.index(k) + 1])
if row["Vues 30j"] == "":
    sys.exit("vues introuvables : rien écrit")
rows = []
if os.path.exists(P):
    with open(P, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
rows = [r for r in rows if r["Date"] != d] + [dict(row, Date=d)]
rows.sort(key=lambda r: r["Date"][6:] + r["Date"][3:5] + r["Date"][:2])
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
print(d, {k: v for k, v in row.items()})
