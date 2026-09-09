#!/usr/bin/env python3
"""Conversations où un appel a été proposé → data/insta-appels.json (sous-onglet « Appels proposés » de l'onglet Datas).

Entrée : le dump complet des conversations (JSON produit par scripts-releve/extract.js, relayé via window.name,
voir RELEVE-INSTA.md « Export complet ») : liste de {id,u,n,rs,seen,la,items:[{w,t,ty,x,re}],nItems}.
Usage : python3 appels_insta.py dump.json [--date 09/09/2026]
Les notes manuelles (récap, cible, verdict) sont lues dans data/insta-appels-notes.json (clé = pseudo) et fusionnées.
"""
import json, sys, re, csv, datetime, pathlib, unicodedata

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "data" / "insta-appels.json"
NOTES = ROOT / "data" / "insta-appels-notes.json"
LEADS = ROOT / "data" / "leads-insta.csv"
CAL = ROOT / "data" / "calendly.csv"
TZ = datetime.timezone(datetime.timedelta(hours=2))
EXC = {"constant_blt", "majorel_alex", "juliensergent_", "lrtemmanuelle", "damienrealise"}

PROP = re.compile(r"\b(appel|call|visio|cr[ée]neau|rdv|rendez[- ]vous|calendly|zoom|google ?meet|t[ée]l[ée]phone|on s'appelle|t'appeler|vous appeler|de vive voix|1 ?h d'accompagnement)\b", re.I)
DISPO = re.compile(r"dispo", re.I)
POS = re.compile(r"\b(oui|ok|okay|d'accord|parfait|avec plaisir|[çc]a marche|volontiers|top|super|carr[ée]ment|pourquoi pas|je suis dispo|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|\d{1,2} ?h(\d{2})?)\b", re.I)
NEG = re.compile(r"(pas maintenant|pas le temps|non merci|pas int[ée]ress|pas besoin|plus tard|pas pour le moment|je passe|pas dispo|pas possible|apr[èe]s la rentr[ée]e|reviens vers toi|je te redis|pas de suite|d[ée]j[àa] accompagn|je ne suis pas|c'est gentil mais)", re.I)

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower().strip()
def dt(ts):
    return datetime.datetime.fromtimestamp(int(ts), TZ).strftime("%d/%m/%Y %H:%M") if ts else ""

def main():
    src = sys.argv[1]
    releve = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.date.today().strftime("%d/%m/%Y")
    T = json.load(open(src, encoding="utf-8"))
    leads = {r["Pseudo"]: r for r in csv.DictReader(open(LEADS, encoding="utf-8"))} if LEADS.exists() else {}
    notes = json.load(open(NOTES, encoding="utf-8")) if NOTES.exists() else {}
    cal = list(csv.DictReader(open(CAL, encoding="utf-8"))) if CAL.exists() else []
    calNames = {}
    for c in cal:
        n = fold(c.get("Invite", ""))
        if n: calNames.setdefault(n, []).append(c)
    calFirst = {}
    for n, cs in calNames.items():
        calFirst.setdefault(n.split()[0], []).extend(cs)
    out = []
    for t in T:
        u = t.get("u") or ""
        if not u or u in EXC: continue
        items = sorted(t.get("items") or [], key=lambda i: i["t"])
        L = [i for i in items if i["w"] == "L"]
        if not L: continue
        props = [i for i in L if i.get("x") and (PROP.search(i["x"]) or (DISPO.search(i["x"]) and "?" in i["x"]))]
        n = notes.get(u) or {}
        if n.get("force") and not props:
            props = [i for i in L if i.get("x")][-1:]
        if n.get("propose"):   # sous-chaîne du message à considérer comme la proposition
            sel = [i for i in L if i.get("x") and n["propose"] in i["x"]]
            if sel: props = sel + [i for i in props if i["t"] > sel[0]["t"]]
        if not props or n.get("exclude"): continue
        p0 = props[0]; tp = p0["t"]
        Pbefore = [i for i in items if i["w"] == "P" and i["t"] < tp and i.get("ty") != "action_log"]
        Pafter = [i for i in items if i["w"] == "P" and i["t"] > tp and i.get("ty") != "action_log"]
        txtAfter = " ".join(i.get("x") or "" for i in Pafter)
        nm = fold(t.get("n") or "")
        booked = calNames.get(nm) or (calFirst.get(nm.split()[0]) if nm and len(calFirst.get(nm.split()[0], [])) == 1 else None)
        if booked: issue = "booke"
        elif Pafter:
            pos, neg = bool(POS.search(txtAfter)), bool(NEG.search(txtAfter))
            issue = "reporte" if neg and not pos else "accepte" if pos and not neg else "discussion"
        else:
            issue = "vu" if int(t.get("seen") or 0) >= tp else "nonvu"
        if n.get("issue"): issue = n["issue"]
        lead = leads.get(u) or {}
        complete = int(t.get("nItems") or len(items)) < 20 and items and items[0]["w"] == "L"
        first = {"text": items[0].get("x") or ("[vocal]" if items[0].get("ty") == "voice_media" else "[" + items[0].get("ty", "") + "]"), "t": dt(items[0]["t"])} if complete else \
                {"text": lead.get("Message envoye") or "", "t": lead.get("Date envoi") or "", "partial": True}
        out.append({
            "pseudo": u, "nom": t.get("n") or "", "thread": t.get("id"), "variante": lead.get("Variante") or "",
            "premier": first, "complet": complete, "nItems": int(t.get("nItems") or len(items)),
            "propose": {"text": p0["x"], "t": dt(tp), "ts": tp, "n": len(props), "vocal": any(i.get("ty") == "voice_media" for i in L if abs(i["t"] - tp) < 900)},
            "avant": {"msgsLead": len(Pbefore), "msgsLauric": len([i for i in L if i["t"] < tp]), "jours": round((tp - items[0]["t"]) / 86400, 1)},
            "apres": {"repondu": len(Pafter), "texte": txtAfter[:600], "t": dt(Pafter[0]["t"]) if Pafter else "", "vu": int(t.get("seen") or 0) >= tp},
            "issue": issue, "booked": [{"date": b.get("Debut", "")[:10], "statut": b.get("Statut", "")} for b in (booked or [])],
            "conv": "https://www.instagram.com/direct/t/" + str(t.get("id")) + "/",
            "msgs": [{"w": i["w"], "t": dt(i["t"]), "ty": i.get("ty"), "x": i.get("x") or ""} for i in items],
            "recap": n.get("recap", ""), "cible": n.get("cible", ""), "type": n.get("type", ""), "verdict": n.get("verdict", ""),
        })
    out.sort(key=lambda o: -o["propose"]["ts"])
    json.dump({"releve": releve, "analyse": notes.get("_analyse", []), "convs": out}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    from collections import Counter
    print(len(out), "conversations avec appel proposé ;", dict(Counter(o["issue"] for o in out)))
    for o in out: print(" ", o["pseudo"], "|", o["issue"], "|", o["propose"]["t"], "|", o["propose"]["text"][:70].replace("\n", " "))

if __name__ == "__main__":
    main()
