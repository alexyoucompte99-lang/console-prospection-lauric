#!/usr/bin/env python3
"""Onglet « 🎁 Lead magnet » : qui a reçu quel lead magnet, qui l'a ouvert, qui a répondu, qui a booké.

Sources :
  - export du relevé Insta (scripts-releve/export_lm.js, lignes ┃) : chaque message de Lauric qui propose
    ou envoie un lead magnet dans les 20 derniers messages des conversations relues, avec vu / réaction / réponse
  - data/leads-insta.csv : les accroches qui proposent le scan (templates LIKE et BIENV) sur tout l'historique
  - data/tally.csv + tally-dates.csv + partielles.csv : scan rempli ou commencé (rapproché par prénom)
  - data/calendly.csv, data/insta-appels.json, data/portefeuille.csv : call booké, appel accepté, client
  - data/lead-magnets.json de la veille : les envois déjà connus sont gardés (le relevé du jour ne relit que le récent)

Usage : python3 lead_magnets.py [export_lm.txt] --date JJ/MM/AAAA
Les analyses rédigées à la main vivent dans data/lead-magnets-notes.json (_analyse, _messages).
"""
import csv, json, re, sys, unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
PARIS = timezone(timedelta(hours=2))

LMS = [
    {"id": "scan", "nom": "Le Scan Dirigeant", "support": "Formulaire Tally, 9 questions, résultat envoyé en vocal par Lauric",
     "url": "https://tally.so/r/zxvka0"},
    {"id": "yt", "nom": "Vidéo YouTube « Dirigeant : comment arrêter de s'épuiser sans ralentir son entreprise ! »",
     "support": "Vidéo sur la chaîne YouTube de Lauric", "url": "https://youtu.be/edgg977QObk", "youtube_id": "edgg977QObk"},
]
TPL_LABELS = {
    "LIKE": "Message aux likers : « merci pour ton like… je propose un scan »",
    "BIENV": "Ancien script abonnés : « Bienvenue sur mon compte, j'offre un scan »",
    "RESS": "Partage de la vidéo : « je te partage une ressource 100 % maison »",
    "RELSCAN": "Relance : « as-tu jeté un œil au scan ? »",
    "PERSO": "Message personnalisé (écrit à la main)",
}
TPL_RE = [("LIKE", r"merci pour ton like sur mon post"), ("BIENV", r"bienvenue sur mon compte"),
          ("RESS", r"ressource 100\s*% maison"), ("RELSCAN", r"(jet[ée]|regard[ée]) un (œ|oe)il au scan|as-tu (fait|rempli) (le|ton) scan")]


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).split()


def kind_of(x):
    if re.search(r"tally\.so", x, re.I): return "scan", "lien"
    if re.search(r"youtu\.?be", x, re.I): return "yt", "lien"
    if not re.search(r"\bscan\b", x, re.I): return None, None
    if re.search(r"(bien )?re[çc]u (ton|votre) scan|l'analyse|mon analyse|r[ée]sultat|synth[èe]se", x, re.I): return "scan", "suivi"
    if re.search(r"(jet(é|e|er)|regard[ée]r?) un (œ|oe)il au scan|as-tu (fait|rempli|pu faire)", x, re.I): return "scan", "relance"
    if re.search(r"^\s*(voici|le voici)", x, re.I): return "scan", "lien"
    return "scan", "offre"


def exemple_of(tpl):
    return "scan" if tpl in ("LIKE", "BIENV") else ""


def tpl_of(x):
    for k, r in TPL_RE:
        if re.search(r, x, re.I): return k
    return "PERSO"


def fr_to_iso(s):
    """'11/09/2026 20:14' ou '11/09/2026' -> '2026-09-11T20:14'"""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2}))?", (s or "").strip())
    if not m: return ""
    return f"{m[3]}-{m[2]}-{m[1]}" + (f"T{m[4]}:{m[5]}" if m[4] else "")


def ts_to_iso(ts):
    return datetime.fromtimestamp(int(ts), PARIS).strftime("%Y-%m-%dT%H:%M") if ts and int(ts) > 0 else ""


def read_csv(p):
    try:
        return list(csv.DictReader(open(p, encoding="utf-8")))
    except FileNotFoundError:
        return []


def main():
    args = [a for a in sys.argv[1:]]
    date = datetime.now(PARIS).strftime("%d/%m/%Y")
    if "--date" in args:
        i = args.index("--date"); date = args[i + 1]; del args[i:i + 2]
    export = args[0] if args else None

    envois = {}   # clé -> envoi

    def put(e, force=False):
        k = "|".join([e["pseudo"], e["lm"], e["etape"], e["tpl"], e["date"][:10]])
        if force or k not in envois: envois[k] = e

    # 0) fichier de la veille : on garde tout ce qui a déjà été vu
    old = DATA / "lead-magnets.json"
    if old.exists():
        for p in json.load(open(old, encoding="utf-8")).get("personnes", []):
            for etape in ("offre", "lien"):
                sl = p.get(etape)
                if sl:
                    put({"pseudo": p["pseudo"], "nom": p["nom"], "conv": p["conv"], "lm": p["lm"], "etape": etape,
                         "tpl": sl["tpl"], "date": sl["date"], "texte": sl["texte"] or exemple_of(sl["tpl"]),
                         "vu": sl["vu"], "reac": False, "rep": sl["rep"], "repDate": sl["repDate"], "repTxt": sl["repTxt"],
                         "premier": False, "src": "veille"})
            for k in range(p.get("relances", 0)):   # relances : on ne garde que le nombre
                put({"pseudo": p["pseudo"], "nom": p["nom"], "conv": p["conv"], "lm": p["lm"], "etape": "relance",
                     "tpl": "RELSCAN" if p["lm"] == "scan" else "PERSO", "date": p["premier"][:10] + "#%d" % k, "texte": "",
                     "vu": False, "reac": False, "rep": False, "repDate": "", "repTxt": "", "premier": False, "src": "veille"})

    # 1) accroches de leads-insta.csv qui proposent le scan (tout l'historique relevé)
    for r in read_csv(DATA / "leads-insta.csv"):
        ps = (r.get("Pseudo") or "").strip()
        if not ps: continue
        st = (r.get("Statut") or "").strip()
        for champ, champ_date in (("Message envoye", "Date envoi"), ("Dernier message Lauric", "Date dernier Lauric")):
            x = r.get(champ) or ""
            lm, etape = kind_of(x)
            if not lm: continue
            d = fr_to_iso(r.get(champ_date)) or fr_to_iso(r.get("Premier contact"))
            if not d: continue
            drep = fr_to_iso(r.get("Date reponse"))
            rep = st == "repondu" and drep and drep[:10] >= d[:10]
            put({"pseudo": ps, "nom": r.get("Nom") or ps, "conv": r.get("Conv") or "", "lm": lm, "etape": etape,
                 "tpl": tpl_of(x), "date": d, "texte": x[:400],
                 "vu": st in ("vu", "reagi", "repondu") if champ == "Message envoye" else bool(rep),
                 "reac": st == "reagi" and champ == "Message envoye", "rep": bool(rep),
                 "repDate": drep if rep else "", "repTxt": (r.get("Reponse lead") or "")[:300] if rep else "",
                 "premier": champ == "Message envoye", "src": "accroche"})

    # 2) export du relevé du jour : plus précis (vu / réaction / réponse après CE message), il écrase
    if export:
        lines = open(export, encoding="utf-8").read().splitlines()
        for ln in lines:
            p = ln.split("┃")
            if len(p) < 13 or p[0] == "PSEUDO": continue
            ps, nom, thread, kind, tpl, ts, vu, reac, repts, reptxt, texte, premier, _ = p[:13]
            lm, etape = kind_of(texte.replace("⏎", "\n"))
            if not lm: continue
            put({"pseudo": ps, "nom": nom or ps, "conv": "https://www.instagram.com/direct/t/" + thread + "/",
                 "lm": lm, "etape": etape, "tpl": tpl, "date": ts_to_iso(ts), "texte": texte.replace("⏎", "\n"),
                 "vu": vu == "1", "reac": reac == "1", "rep": int(repts or 0) > 0, "repDate": ts_to_iso(repts),
                 "repTxt": reptxt.replace("⏎", "\n"), "premier": premier == "1", "src": "releve"}, force=True)

    # 2b) « Voici le scan » juste avant / après le lien = même envoi : on garde le lien, texte complété
    ev = sorted(envois.values(), key=lambda e: (e["pseudo"], e["date"]))
    for i, e in enumerate(ev):
        if e["lm"] != "scan" or e["etape"] != "lien": continue
        for o in ev[max(0, i - 2):i + 3]:
            if o is e or o["pseudo"] != e["pseudo"] or o["etape"] not in ("lien", "offre") or o["lm"] != "scan": continue
            if abs(minutes(o["date"]) - minutes(e["date"])) <= 15 and len(o["texte"]) < 200 and not re.search(r"tally\.so", o["texte"]):
                if o["etape"] == "offre" and o["tpl"] in ("LIKE", "BIENV"): continue
                e["texte"] = (o["texte"] + "\n" + e["texte"]) if o["date"] <= e["date"] else (e["texte"] + "\n" + o["texte"])
                e["rep"] = e["rep"] or o["rep"]; e["repTxt"] = e["repTxt"] or o["repTxt"]; e["repDate"] = e["repDate"] or o["repDate"]
                o["_drop"] = True
    envois = {k: e for k, e in envois.items() if not e.pop("_drop", False)}
    envois = {k: e for k, e in envois.items() if e["etape"] != "suivi"}

    # 3) par personne et par lead magnet : proposé, lien envoyé, relances, vu, répondu
    pers = {}
    for e in sorted(envois.values(), key=lambda e: e["date"]):
        p = pers.setdefault((e["pseudo"], e["lm"]), {"pseudo": e["pseudo"], "nom": e["nom"], "conv": e["conv"], "lm": e["lm"],
                                                     "premier": e["date"], "offre": None, "lien": None, "relances": 0,
                                                     "vu": False, "rep": False, "repDate": "", "repTxt": ""})
        if e["conv"] and not p["conv"]: p["conv"] = e["conv"]
        slot = {"date": e["date"], "tpl": e["tpl"], "texte": e["texte"], "vu": e["vu"], "rep": e["rep"], "repTxt": e["repTxt"], "repDate": e["repDate"]}
        if e["etape"] == "offre" and not p["offre"]: p["offre"] = slot
        elif e["etape"] == "lien" and not p["lien"]: p["lien"] = slot
        elif e["etape"] == "relance": p["relances"] += 1
        p["vu"] = p["vu"] or e["vu"]
        if e["rep"] and not p["rep"]:
            p["rep"], p["repDate"], p["repTxt"] = True, e["repDate"], e["repTxt"]

    # 4) ouvert : scan rempli (Tally) ou commencé (partiel), rapproché par prénom parmi les personnes
    #    qui ont vraiment pu l'ouvrir (lien envoyé, ou proposition à laquelle elles ont répondu)
    tdates = {r["Submission ID"]: r["Soumis le"] for r in read_csv(DATA / "tally-dates.csv")}
    scans = []
    for r in read_csv(DATA / "tally.csv"):
        pre = (r.get("Votre prénom") or "").strip()
        if pre and re.match(r"^[A-Za-z0-9_-]{5,}$", r.get("Submission ID") or ""):
            scans.append({"pre": pre, "etat": "rempli", "date": (tdates.get(r["Submission ID"]) or "")[:10],
                          "source": (r.get("source") or "").strip()})
    for r in read_csv(DATA / "partielles.csv"):
        pre = (r.get("Prenom") or "").strip()
        if pre: scans.append({"pre": pre, "etat": "commencé", "date": (r.get("Derniere activite") or "")[:10], "source": ""})
    ouvrables = [p for p in pers.values() if p["lm"] == "scan" and (p["lien"] or p["rep"])]
    for s in scans:
        fn = (norm(s["pre"]) or [""])[0]
        if not fn: continue
        full = set(norm(s["source"])) - {"instagram", "facebook", "tiktok"}
        cands = [p for p in ouvrables if (norm(p["nom"]) or [""])[0] == fn and (not s["date"] or s["date"] >= p["premier"][:10])]
        if len(full) >= 2:
            cands = [p for p in cands if full <= set(norm(p["nom"])) | {fn}] or cands
        if len(cands) != 1: continue
        p = cands[0]
        if p.get("ouvert") != "rempli":
            p["ouvert"], p["ouvertDate"] = s["etat"], s["date"]

    # 5) booké APRÈS le lead magnet : RDV Calendly (nom complet), appel accepté ou fait (onglet Appels proposés),
    #    fiche du portefeuille (1er contact après l'envoi) ; « déjà client / pipeline » si c'était avant
    cal = [(set(norm(r.get("Invite"))), (r.get("Debut") or "")[:10]) for r in read_csv(DATA / "calendly.csv") if r.get("Statut") == "active"]
    appels = {c["pseudo"]: c for c in json.load(open(DATA / "insta-appels.json", encoding="utf-8")).get("convs", [])} \
        if (DATA / "insta-appels.json").exists() else {}
    pf_rows = []
    try:
        rows = list(csv.reader(open(DATA / "portefeuille.csv", encoding="utf-8")))
        hi = next(i for i, r in enumerate(rows) if "NOM" in [c.strip() for c in r])
        h = [c.strip() for c in rows[hi]]
        inom, iiss, i1 = h.index("NOM"), h.index("Issue"), h.index("1er contact")
        pf_rows = [(set(norm(r[inom])), r[iiss], fr_to_iso(r[i1] if re.search(r"\d{4}", r[i1]) else r[i1] + "/2026")) for r in rows[hi + 1:] if len(r) > iiss and r[inom].strip()]
    except (StopIteration, FileNotFoundError, ValueError):
        pass
    for p in pers.values():
        toks = set(norm(p["nom"]))
        d0 = p["premier"][:10]
        best = None
        a = appels.get(p["pseudo"])
        if a and a.get("issue") in ("vente", "fait", "booke", "accepte"):
            m = re.match(r"(\d{2})/(\d{2})(?:/(\d{4}))?", (a.get("propose") or {}).get("t", ""))
            da = f"{m[3] or '2026'}-{m[2]}-{m[1]}" if m else ""
            best = ({"vente": "vente", "fait": "call fait", "booke": "call booké", "accepte": "appel accepté"}[a["issue"]], da)
        if len(toks) >= 2:
            for ctoks, d in cal:
                if len(ctoks & toks) >= 2 and (not best or best[0] == "appel accepté"):
                    best = ("call booké", d)
            for ptoks, issue, d in pf_rows:
                if len(ptoks & toks) >= 2:
                    if re.search(r"client", issue, re.I): best = ("vente", d)
                    elif not best: best = ("dans le pipeline", d)
        if not best: continue
        if best[1] and best[1] < d0:
            p["avant"] = best[0]          # déjà booké / client avant ce lead magnet : pas compté
        else:
            p["booke"], p["bookeDate"] = best

    out_pers = sorted(pers.values(), key=lambda p: p["premier"], reverse=True)
    for p in out_pers:   # page légère : le texte des messages types n'est gardé qu'une fois (exemples)
        for k in ("offre", "lien"):
            if p[k] and p[k]["tpl"] in ("LIKE", "BIENV", "RESS"): p[k]["texte"] = ""
            if p[k]: p[k]["repTxt"] = p[k]["repTxt"][:240]
        p["repTxt"] = p["repTxt"][:240]
    exemples = json.load(open(old, encoding="utf-8")).get("exemples", {}) if old.exists() else {}
    for e in sorted(envois.values(), key=lambda e: e["date"], reverse=True):
        if e["tpl"] in ("LIKE", "BIENV", "RESS") and len(e["texte"]) > 60 and (e["tpl"] not in exemples or len(exemples[e["tpl"]]) < 60):
            exemples[e["tpl"]] = re.sub(r"^(Hello|Bienvenue sur mon compte)\s+[^,!\s]+\s*", r"\1 [Prénom]", e["texte"])
    notes = {}
    if (DATA / "lead-magnets-notes.json").exists():
        notes = json.load(open(DATA / "lead-magnets-notes.json", encoding="utf-8"))
    res = {"genere": date, "releve": notes.get("_releve", ""), "lms": LMS, "templates": TPL_LABELS,
           "analyse": notes.get("_analyse", []), "exemples": exemples, "personnes": out_pers}
    json.dump(res, open(DATA / "lead-magnets.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for lm in ("scan", "yt"):
        P = [p for p in out_pers if p["lm"] == lm]
        c = lambda f: sum(1 for p in P if f(p))
        print(lm, "personnes", len(P), "proposé", c(lambda p: p["offre"]), "lien", c(lambda p: p["lien"]), "vu", c(lambda p: p["vu"]),
              "répondu", c(lambda p: p["rep"]), "ouvert", c(lambda p: p.get("ouvert")), "booké", c(lambda p: p.get("booke")))


def minutes(iso):
    try:
        return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").timestamp() / 60
    except ValueError:
        return datetime.strptime(iso[:10], "%Y-%m-%d").timestamp() / 60


if __name__ == "__main__":
    main()
