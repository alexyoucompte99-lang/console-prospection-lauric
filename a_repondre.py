#!/usr/bin/env python3
"""Fabrique data/a-repondre.json (onglet « 💬 À répondre » de la console) à partir de deux fichiers :

  1. le dump des conversations relevées sur Instagram (convs.json produit par le relevé :
     une conversation par entrée, avec profil, items, lastL / lastP, read_state) ;
  2. les réponses rédigées par les agents (finals.json : une entrée par pseudo, champs
     categorie, priorite, cible, resume, attend, objectif, format, reponse, pourquoi,
     vocal, alternatives, si_silence, eviter, chances).

Usage :
    python3 a_repondre.py <convs.json> <finals.json> [--date "12/09/2026 00h40"] [--fenetre "du 05 au 12/09"]

Ne touche à rien d'autre : la page lit le JSON, l'état « répondu » vit dans le Google Form (RepInsta).
"""
import json, sys, datetime as dt

TZ = dt.timezone(dt.timedelta(hours=2))
JOURS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
WHATSAPP = {"linstitut.stquentin": "https://wa.me/33788512302"}
FIL_MAX = 10


def fdate(ts):
    d = dt.datetime.fromtimestamp(ts, TZ)
    return JOURS[d.weekday()] + " " + d.strftime("%d/%m %H:%M")


def texte(i):
    ty, x = i.get("ty"), (i.get("x") or "").strip()
    if ty in ("text", "link"):
        return x
    if ty == "voice_media":
        return "[vocal de %s s]" % i.get("d", "?")
    if ty in ("clip", "media_share"):
        return "[partage d'un post de @%s%s]" % (i.get("own", "?"), (" : " + x[:120]) if x else "")
    if ty == "reel_share":
        return "[réponse à une story%s]" % ((" : " + x) if x else "")
    if ty == "story_share":
        return "[partage d'une story de @%s]" % i.get("own", "?")
    if ty == "action_log":
        return "(" + x + ")"
    if ty == "placeholder":
        return "[message non affichable]"
    return "[" + str(ty) + "]" + ((" " + x) if x else "")


def profil_court(p):
    bits = []
    if p.get("cat"):
        bits.append(p["cat"])
    if p.get("fol") is not None:
        bits.append("%s abonnés" % p["fol"])
    if p.get("med"):
        bits.append("%s publications" % p["med"])
    bits.append("compte privé" if p.get("pr") else "compte public")
    bio = (p.get("bio") or "").replace("\n", " / ").strip()
    if bio:
        bits.append("bio : " + (bio[:120] + ("…" if len(bio) > 120 else "")))
    return " · ".join(bits)


def main():
    convs = json.load(open(sys.argv[1], encoding="utf-8"))
    finals = json.load(open(sys.argv[2], encoding="utf-8"))
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    now = dt.datetime.now(TZ)
    par_pseudo = {f["pseudo"]: f for f in finals if f.get("pseudo")}
    out = []
    for c in convs:
        f = par_pseudo.get(c["u"])
        if not f:
            print("pas de réponse rédigée pour @" + c["u"])
            continue
        items = c.get("items", [])
        reels = [i for i in items if i.get("ty") != "action_log"]
        last_p = [i for i in reels if i["w"] == "P"]
        ref = last_p[-1]["t"] if last_p else c.get("la")
        # les messages du lead restés sans réponse (après notre dernier message)
        lastL = c.get("lastL") or 0
        pend = [i for i in last_p if i["t"] > lastL]
        vocaux = [i for i in pend if i.get("ty") == "voice_media"]
        entry = {
            "pseudo": c["u"],
            "nom": c.get("n") or c["u"],
            "conv": "https://www.instagram.com/direct/t/%s/" % c["id"],
            "cat": c.get("cat", "rep"),
            "non_lu": c.get("rs") == 1,
            "attente_jours": round((now.timestamp() - ref) / 86400, 2) if ref else None,
            "profil_info": profil_court(c.get("prof") or {}),
            "dernier": {"t": fdate(last_p[-1]["t"]), "x": texte(last_p[-1])} if last_p else None,
            "fil": [{"w": i["w"], "t": fdate(i["t"]), "x": texte(i)} for i in reels[-FIL_MAX:]],
        }
        if vocaux:
            entry["vocaux"] = "%d %s du lead (%s) : à écouter avant de répondre" % (
                len(vocaux), "vocaux" if len(vocaux) > 1 else "vocal",
                " et ".join("%s s" % v.get("d", "?") for v in vocaux))
        if c["u"] in WHATSAPP:
            entry["whatsapp"] = WHATSAPP[c["u"]]
        for k in ("categorie", "priorite", "cible", "resume", "attend", "objectif", "format",
                  "reponse", "pourquoi", "vocal", "alternatives", "si_silence", "eviter", "chances",
                  "quand", "lauric_seul"):
            if f.get(k) not in (None, ""):
                entry[k] = f[k]
        out.append(entry)
    out.sort(key=lambda e: (e.get("priorite", 9), -(e.get("attente_jours") or 0)))
    data = {
        "genere": arg("--date", now.strftime("%d/%m/%Y %Hh%M")),
        "fenetre": arg("--fenetre", "7 derniers jours"),
        "convs": out,
        "synthese": json.load(open(arg("--synthese", ""), encoding="utf-8")) if "--synthese" in sys.argv else [],
        "note": "Analyse faite par Claude sur les conversations relevées par l'API interne d'Instagram (lecture seule, aucun « vu » envoyé). Les messages sont des propositions : Lauric les adapte avant d'envoyer.",
    }
    json.dump(data, open("data/a-repondre.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "conversations écrites dans data/a-repondre.json")


if __name__ == "__main__":
    main()
