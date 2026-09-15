#!/usr/bin/env python3
"""Ajoute (ou remplace) le relevé du jour du tableau de bord professionnel Instagram
dans data/contenu-insta.csv, lu par l'onglet Contenu et l'entonnoir de la Vue d'ensemble.
Source : https://www.instagram.com/accounts/insights/?timeframe=30 (et ?timeframe=7), texte de <main>.
Usage : python3 releve_contenu.py <texte_30j.txt> [--sept <texte_7j.txt>] [jj/mm/aaaa]
   ou : python3 releve_contenu.py --vues N --spectateurs N --interactions N --comptes N --visites N --liens N --followers N [--date jj/mm/aaaa]
Colonnes 7 j et détails (part des non-followers, part des Reels, meilleurs contenus) ajoutées le 15/09/2026 :
les anciennes lignes gardent ces cases vides."""
import csv, sys, os, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "data", "contenu-insta.csv")
COLS = ["Date", "Vues 30j", "Spectateurs 30j", "Interactions 30j", "Comptes ayant interagi 30j",
        "Visites profil 30j", "Liens externes 30j", "Followers",
        "Vues 7j", "Spectateurs 7j", "Interactions 7j", "Comptes ayant interagi 7j", "Visites profil 7j", "Liens externes 7j",
        "Non-followers vues 30j", "Reels vues 30j", "Top vues 30j", "Top vues 7j"]
num = lambda s: int(re.sub(r"[^\d]", "", s)) if s and re.search(r"\d", s) else ""
MOIS = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8, "aout": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "déc": 12, "dec": 12}
args = sys.argv[1:]
d = datetime.date.today().strftime("%d/%m/%Y")
if "--date" in args:
    i = args.index("--date"); d = args[i + 1]; del args[i:i + 2]
sept = ""
if "--sept" in args:
    i = args.index("--sept"); sept = args[i + 1]; del args[i:i + 2]


def parse(t):
    def after(label, nth=1):
        m = list(re.finditer(r"^" + label + r"\s*\n([\d\s  ]+)\s*$", t, re.M))
        return num(m[nth - 1].group(1)) if len(m) >= nth else ""
    r = {"vues": after("Vues"), "spect": after(r"Spectateur\(ice\)s"), "inter": after("Interactions"),
         "comptes": after("Comptes ayant interagi"), "visites": after("Visites du profil"),
         "liens": after("Appuis sur des liens externes"), "followers": after("Followers")}
    if r["followers"] == "":
        m = re.search(r"\n([\d\s  ]+)\nTotal des followers", t); r["followers"] = num(m.group(1)) if m else ""
    # part des non-followers dans les vues (premier bloc « Followers x % / Non-followers y % »)
    m = re.search(r"^Vues\n[\d\s  ]+\nVues\nFollowers\n[\d,]+%\nNon-followers\n([\d,]+)%", t, re.M)
    r["nonf"] = m.group(1).replace(",", ".") if m else ""
    # répartition par type de contenu : Reels, Stories, Publications puis les 3 pourcentages
    m = re.search(r"Reels\nStories\nPublications\n([\d,]+)%", t)
    r["reels"] = m.group(1).replace(",", ".") if m else ""
    # meilleurs contenus d'après les vues : couples « 36,9 k » / « 25 août »
    top = []
    m = re.search(r"Meilleur contenu d’après les vues\nVoir tout\n(.*?)\nInteractions\n", t, re.S)
    if m:
        lines = [x.strip() for x in m.group(1).split("\n") if x.strip()]
        for v, dd in zip(lines[0::2], lines[1::2]):
            n = re.match(r"([\d\s  ]+(?:,\d+)?)\s*(k|M)?$", v)
            dm = re.match(r"(\d{1,2})\s+(\S+)", dd)
            if not n or not dm: continue
            val = float(re.sub(r"[\s  ]", "", n.group(1)).replace(",", "."))
            val = int(round(val * (1000 if n.group(2) == "k" else 1_000_000 if n.group(2) == "M" else 1)))
            mo = MOIS.get(dm.group(2).lower().rstrip("."), 0)
            if mo: top.append("%d@%02d/%02d" % (val, int(dm.group(1)), mo))
    r["top"] = " ".join(top)
    return r


if args and not args[0].startswith("--"):
    t = open(args[0], encoding="utf-8").read()
    if len(args) > 1: d = args[1]
    a = parse(t)
    b = parse(open(sept, encoding="utf-8").read()) if sept else {}
    row = {"Vues 30j": a["vues"], "Spectateurs 30j": a["spect"], "Interactions 30j": a["inter"],
           "Comptes ayant interagi 30j": a["comptes"], "Visites profil 30j": a["visites"], "Liens externes 30j": a["liens"],
           "Followers": a["followers"] or b.get("followers", ""),
           "Non-followers vues 30j": a["nonf"], "Reels vues 30j": a["reels"], "Top vues 30j": a["top"]}
    if b:
        row.update({"Vues 7j": b["vues"], "Spectateurs 7j": b["spect"], "Interactions 7j": b["inter"],
                    "Comptes ayant interagi 7j": b["comptes"], "Visites profil 7j": b["visites"],
                    "Liens externes 7j": b["liens"] if b["liens"] != "" else (0 if b["vues"] != "" else ""),
                    "Top vues 7j": b["top"]})
else:
    keys = {"--vues": "Vues 30j", "--spectateurs": "Spectateurs 30j", "--interactions": "Interactions 30j",
            "--comptes": "Comptes ayant interagi 30j", "--visites": "Visites profil 30j", "--liens": "Liens externes 30j",
            "--followers": "Followers"}
    row = {}
    for k, v in keys.items():
        if k in args: row[v] = num(args[args.index(k) + 1])
if row.get("Vues 30j", "") == "":
    sys.exit("vues introuvables : rien écrit")
rows = []
if os.path.exists(P):
    with open(P, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
row = {c: row.get(c, "") for c in COLS}
rows = [r for r in rows if r["Date"] != d] + [dict(row, Date=d)]
rows.sort(key=lambda r: r["Date"][6:] + r["Date"][3:5] + r["Date"][:2])
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore", restval=""); w.writeheader(); w.writerows(rows)
print(d, {k: v for k, v in row.items() if v != ""})
