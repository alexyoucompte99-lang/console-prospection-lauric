#!/usr/bin/env python3
"""Met à jour data/abonnes.csv après un relevé de la messagerie (leads-insta.csv déjà réécrit par releve_insta.py).

1. Chaque abonné présent dans leads-insta.csv (conversation avec au moins un message de notre côté) passe Contacte=oui
   avec la date et le texte du premier message envoyé, le statut (envoye / vu / reagi / repondu) et le lien de la conv.
   Une ligne à « oui » ne repasse jamais à « non ».
2. Ajoute les nouveaux abonnés d'un JSON optionnel : [{pseudo, nom, profil, cible, message}] (Detecte = date du relevé).
Usage : python3 scripts-releve/maj_abonnes.py [nouveaux.json] --date JJ/MM/AAAA
"""
import csv, sys, json, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "abonnes.csv"
LEADS = ROOT / "data" / "leads-insta.csv"
FIELDS = ["Pseudo","Nom","Detecte","Profil","Cible","Message propose","Contacte","Date contact","Message envoye","Statut","Conv","Releve","Type"]
STATUT = {"nonvu": "envoye", "vu": "vu", "reagi": "reagi", "repondu": "repondu"}
args = [a for a in sys.argv[1:]]
today = args[args.index("--date") + 1] if "--date" in args else datetime.date.today().strftime("%d/%m/%Y")
src = next((a for a in args if a.endswith(".json")), None)

rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
for r in rows: r.setdefault("Type", "")
leads = {l["Pseudo"]: l for l in csv.DictReader(open(LEADS, encoding="utf-8"))}
have = {r["Pseudo"] for r in rows}
added = 0
if src:
    for n in json.load(open(src, encoding="utf-8")):
        if n["pseudo"] in have: continue
        rows.append({"Pseudo": n["pseudo"], "Nom": n.get("nom") or n["pseudo"], "Detecte": today, "Profil": n.get("profil", ""),
                     "Cible": n.get("cible", ""), "Message propose": n.get("message", ""), "Contacte": "non", "Date contact": "",
                     "Message envoye": "", "Statut": "", "Conv": "", "Releve": today, "Type": n.get("type", "")})
        have.add(n["pseudo"]); added += 1
newly, changed = 0, 0
for r in rows:
    l = leads.get(r["Pseudo"])
    if not l: continue
    before = (r["Contacte"], r["Statut"], r["Conv"])
    if r["Contacte"] != "oui": newly += 1
    r["Contacte"] = "oui"
    r["Date contact"] = (l.get("Date envoi") or "")[:10] or r["Date contact"]
    r["Message envoye"] = l.get("Message envoye") or r["Message envoye"] or "[vocal]"
    r["Statut"] = STATUT.get(l.get("Statut", ""), r["Statut"])
    r["Conv"] = l.get("Conv") or r["Conv"]
    r["Message propose"] = ""
    r["Releve"] = l.get("Releve") or today
    if (r["Contacte"], r["Statut"], r["Conv"]) != before: changed += 1
assert len({r["Pseudo"] for r in rows}) == len(rows), "pseudo en double"
with open(CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
todo = [r["Pseudo"] for r in rows if r["Contacte"] != "oui" and r["Type"] != "ancien"]
print(f"{len(rows)} abonnés · {added} ajoutés · {newly} passés à contacté · {changed} lignes modifiées · à contacter : {len(todo)} ({', '.join(todo[:12])}{'…' if len(todo) > 12 else ''})")
