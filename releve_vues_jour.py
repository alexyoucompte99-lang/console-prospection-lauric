#!/usr/bin/env python3
"""Fusionne les vues par jour du compte dans data/vues-jour.csv (lu par Contenu › Audience, section « Vues par jour »).
Source : tableau de bord professionnel Instagram interrogé jour par jour (requête GraphQL de la page insights rejouée
avec currentPeriodStart/currentPeriodEnd = une seule journée, voir RELEVE-ABONNES.md).
Entrée : un fichier texte, une ligne par jour « AAAA-MM-JJ,vues,spectateurs,comptes touchés » (ordre libre).
Usage : python3 releve_vues_jour.py <fichier.txt> [--date JJ/MM/AAAA]"""
import csv, sys, re, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "vues-jour.csv"
FIELDS = ["Date", "Vues", "Spectateurs", "Comptes touches", "Releve"]
args = sys.argv[1:]
today = args[args.index("--date") + 1] if "--date" in args else datetime.date.today().strftime("%d/%m/%Y")
rows = {}
if OUT.exists():
    rows = {r["Date"]: r for r in csv.DictReader(open(OUT, encoding="utf-8"))}
new = 0
for line in open(args[0], encoding="utf-8"):
    m = re.match(r"\s*(\d{4}-\d\d-\d\d),(\d*),(\d*),(\d*)", line)
    if not m or m.group(2) == "": continue
    d = m.group(1)
    if d not in rows: new += 1
    rows[d] = {"Date": d, "Vues": m.group(2), "Spectateurs": m.group(3), "Comptes touches": m.group(4), "Releve": today}
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
    for d in sorted(rows): w.writerow(rows[d])
print(len(rows), "jours dans", OUT.name, "·", new, "nouveaux ·", min(rows), "→", max(rows))
