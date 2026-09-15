#!/usr/bin/env python3
"""Onglet Contenu › « 🎬 Reels » : quels Reels de Lauric marchent le mieux, lesquels refaire et pourquoi.

Source : export du relevé des publications (scripts-releve/reels.js, tranches R<k> recollées par
scripts-releve/glue_json.py <out.json> --prefix R) : une ligne par publication avec vues, likes,
commentaires, durée, légende, couverture.
L'analyse rédigée (pourquoi, à refaire, à éviter, idées) vit dans data/reels-notes.json : ce script ne
l'écrase jamais, il la recopie dans data/reels.json avec les chiffres du jour.

Usage : python3 reels.py <export.json> --date "JJ/MM/AAAA HHhMM"
"""
import json, re, statistics, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
DATA = HERE / "data"
PARIS = ZoneInfo("Europe/Paris")
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
TROP_RECENT = 3   # jours : un Reel plus jeune n'a pas fini de tourner, il ne compte pas dans les médianes

CTA_RE = [
    ("commente", re.compile(r"comment(e|ez|aire)[^\n]{0,40}?[«\"“']\s*([A-Za-zÀ-ÿ0-9]{2,20})\s*[»\"”']", re.I)),
    ("commente", re.compile(r"comment(e|ez)\s+([A-ZÀ-Ý0-9]{2,20})\b")),
    ("message", re.compile(r"(envoie|écris|ecris)[-\s]?(moi)?[^\n]{0,20}(message|dm|mp)|en (dm|mp)\b", re.I)),
    ("lien", re.compile(r"lien (en|dans (la|ma)) bio|link in bio", re.I)),
    ("enregistre", re.compile(r"enregistre", re.I)),
    ("partage", re.compile(r"partage[sz]?\b[^\n]{0,30}(à|a|avec)", re.I)),
    ("abonne", re.compile(r"abonne[-\s]?toi|suis[-\s]moi|follow", re.I)),
]


def hook_of(cap):
    for line in (cap or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:220]
    return ""


def cta_of(cap):
    for kind, rx in CTA_RE:
        m = rx.search(cap or "")
        if m:
            mot = m.group(2).upper() if kind == "commente" and m.lastindex and m.lastindex >= 2 else ""
            return kind, mot
    return "", ""


def kind_of(p):
    if p.get("pt") == "clips":
        return "reel"
    return {1: "photo", 2: "vidéo", 8: "carrousel"}.get(p.get("mt"), "autre")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = json.load(open(sys.argv[1], encoding="utf-8"))
    stamp = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.now(PARIS).strftime("%d/%m/%Y %Hh%M")
    now = datetime.now(PARIS)
    notes_path = DATA / "reels-notes.json"
    notes = json.load(open(notes_path, encoding="utf-8")) if notes_path.exists() else {}

    items = []
    for p in src:
        if not p.get("code"):
            continue
        d = datetime.fromtimestamp(p["t"], timezone.utc).astimezone(PARIS)
        vues = next((p[k] for k in ("plays", "igp", "views") if isinstance(p.get(k), int) and p[k] > 0), None)
        likes = p["likes"] if isinstance(p.get("likes"), int) else None   # absent quand la grille n'a pas été captée
        comms = p["comms"] if isinstance(p.get("comms"), int) else None
        share = p.get("share") if isinstance(p.get("share"), int) else None
        cta, mot = cta_of(p.get("cap"))
        cap = p.get("cap") or ""
        note = notes.get(p["code"]) or {}
        it = {
            "code": p["code"], "url": ("https://www.instagram.com/reel/" if kind_of(p) == "reel" else "https://www.instagram.com/p/") + p["code"] + "/",
            "type": kind_of(p), "date": d.strftime("%Y-%m-%d"), "heure": d.strftime("%H:%M"), "jour": JOURS[d.weekday()],
            "age": (now - d).days, "vues": vues, "likes": likes, "comms": comms, "partages": share,
            "enreg": p.get("save") if isinstance(p.get("save"), int) else None,
            "duree": round(p["dur"]) if isinstance(p.get("dur"), (int, float)) else None,
            "eng": round(100 * (likes + (comms or 0) + (share or 0)) / vues, 2) if vues and likes is not None else None,
            "comm_1k": round(1000 * comms / vues, 1) if vues and comms is not None else None,
            # sur un Reel, l'accroche qui compte est celle écrite sur la vidéo (notée à la main), pas la 1re ligne de la légende
            "accroche": note.get("accroche") or hook_of(cap), "legende": cap, "longueur": len(cap), "hashtags": len(re.findall(r"#\w", cap)),
            "format": note.get("format", ""), "sujet": note.get("sujet", ""),
            "cta": cta or note.get("cta", ""), "mot": mot or note.get("mot", ""),
            "cover": p.get("cov") or "", "audio": p.get("audio") or "", "collab": p.get("collab") or [],
        }
        items.append(it)

    reels = [x for x in items if x["type"] == "reel" and x["vues"]]
    base = [x for x in reels if x["age"] >= TROP_RECENT]
    med = statistics.median([x["vues"] for x in base]) if base else None
    for x in items:
        x["x_med"] = round(x["vues"] / med, 2) if med and x["vues"] else None
        x["recent"] = x["age"] < TROP_RECENT

    # facteurs : le quart du haut comparé au reste (tendances, petits échantillons)
    facteurs = {}
    if len(base) >= 8:
        srt = sorted(base, key=lambda x: -x["vues"])
        q = max(2, len(srt) // 4)
        top, rest = srt[:q], srt[q:]
        def med_of(l, k):
            v = [x[k] for x in l if x[k] is not None]
            return statistics.median(v) if v else None
        def pct(l, f):
            return round(100 * sum(1 for x in l if f(x)) / len(l)) if l else None
        def pct_a(l, f):   # accroches : notées à la main, on ne compte que les Reels qui en ont une
            l = [x for x in l if x["accroche"]]
            return round(100 * sum(1 for x in l if f(x)) / len(l)) if l else None
        # légendes lues pour moins de la moitié des Reels (relevé par la grille du profil) : pas de stats de légende
        has_cap = sum(1 for x in base if x["legende"]) >= len(base) / 2
        if not has_cap:
            def pct(l, f, _pct=pct):
                return None
        facteurs = {
            "n_top": len(top), "n_reste": len(rest), "seuil_top": top[-1]["vues"],
            "duree": [med_of(top, "duree"), med_of(rest, "duree")],
            "eng": [med_of(top, "eng"), med_of(rest, "eng")],
            "comm_1k": [med_of(top, "comm_1k"), med_of(rest, "comm_1k")],
            "longueur": [med_of(top, "longueur"), med_of(rest, "longueur")] if has_cap else None,
            "avec_cta": [pct(top, lambda x: x["cta"]), pct(rest, lambda x: x["cta"])],
            "cta_commente": [pct(top, lambda x: x["cta"] == "commente"), pct(rest, lambda x: x["cta"] == "commente")],
            "accroche_question": [pct_a(top, lambda x: "?" in x["accroche"]), pct_a(rest, lambda x: "?" in x["accroche"])],
            "accroche_chiffre": [pct_a(top, lambda x: bool(re.search(r"\d", x["accroche"]))), pct_a(rest, lambda x: bool(re.search(r"\d", x["accroche"])))],
            "collab": [pct(top, lambda x: x["collab"]), pct(rest, lambda x: x["collab"])],
            "jours_top": [x["jour"] for x in top],
        }
    # vues médianes par sujet et par format (notés à la main dans reels-notes.json)
    for key in ("sujet", "format"):
        groups = {}
        for x in base:
            if x[key]:
                groups.setdefault(x[key], []).append(x["vues"])
        facteurs["par_" + key] = sorted(
            [{"nom": k, "n": len(v), "mediane": statistics.median(v), "max": max(v), "au_dessus_2000": sum(1 for n in v if n >= 2000)}
             for k, v in groups.items()], key=lambda g: -g["mediane"])

    out = {
        "releve": stamp,
        "periode": {"du": min((x["date"] for x in items), default=""), "au": max((x["date"] for x in items), default="")},
        "stats": {
            "n_publications": len(items), "n_reels": len(reels), "n_autres": len(items) - len(reels),
            "mediane_vues": med, "moyenne_vues": round(statistics.mean([x["vues"] for x in base])) if base else None,
            "top_vues": max((x["vues"] for x in reels), default=None),
            "eng_median": statistics.median([x["eng"] for x in base if x["eng"] is not None]) if base else None,
            "x2": sum(1 for x in base if x["x_med"] and x["x_med"] >= 2),
        },
        "facteurs": facteurs,
        "analyse": notes.get("_analyse") or {},
        "publications": sorted(items, key=lambda x: x["date"] + x["heure"], reverse=True),
    }
    (DATA / "reels.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    s = out["stats"]
    print(f"{s['n_publications']} publications dont {s['n_reels']} Reels · médiane {s['mediane_vues']} vues · "
          f"top {s['top_vues']} · {s['x2']} Reels à 2× la médiane ou plus · du {out['periode']['du']} au {out['periode']['au']}")
    if facteurs:
        print("facteurs (top / reste) :", json.dumps({k: v for k, v in facteurs.items() if k != "jours_top"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
