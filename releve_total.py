#!/usr/bin/env python3
"""Ajoute (ou remplace) le relevé du jour dans data/abonnes_total.csv.
Usage : python3 releve_total.py <nombre d'abonnés> [jj/mm/aaaa]"""
import csv, sys, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "data", "abonnes_total.csv")
n = int(str(sys.argv[1]).replace(" ", "").replace(" ", "").replace(",", ""))
d = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime("%d/%m/%Y")
rows = []
if os.path.exists(P):
    with open(P, encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)][1:]
rows = [r for r in rows if r and r[0] != d] + [[d, str(n)]]
rows.sort(key=lambda r: r[0][6:] + r[0][3:5] + r[0][:2])
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["Date", "Abonne scrappe"]); w.writerows(rows)
print(f"{d} : {n} abonnés ({len(rows)} relevés)")
