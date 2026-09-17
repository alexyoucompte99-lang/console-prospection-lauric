#!/usr/bin/env python3
"""Réactivité de l'équipe sur Instagram → data/reactivite.json + colonnes « Abonne le » / « Premier message le » de data/abonnes.csv

Deux mesures, lues par Setting › ⏱️ Réactivité :
1. Temps de réponse aux leads : chaque fois qu'un lead écrit (un « tour » = ses messages d'affilée), combien de temps
   avant le message suivant de notre côté. Les likes de message ne comptent pas, les messages de pure politesse
   (« merci », « ok », emoji seul, cœur) sont marqués pour être mis à part. Chaud / pas chaud se décide dans la page
   (étiquettes EOD, scan, call, vente, prospects chauds d'À répondre, appels, étiquettes Instagram).
2. Délai de premier contact des nouveaux abonnés : heure exacte de l'abonnement (notifications Instagram, ~5 jours
   d'historique : relever au moins tous les 4 jours) et heure du premier message envoyé.

Entrées : l'export R (scripts-releve/export_reac.js recollé par glue_text.py --prefix R) et les abonnements lus dans
les notifications (lignes « timestamp┃pk┃pseudo »).
Usage : python3 reactivite.py <reac.txt> --notif <follows.txt> --date "17/09/2026 16h45"
Les tours déjà connus des conversations non relues sont conservés (fusion par pseudo) : le relevé du jour ne relit
que les conversations récentes.
"""
import csv, json, re, sys, datetime, pathlib, unicodedata

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "data" / "reactivite.json"
ABO = ROOT / "data" / "abonnes.csv"
TZ = datetime.timezone(datetime.timedelta(hours=2))
EXC = {"constant_blt", "majorel_alex", "juliensergent_", "lrtemmanuelle", "damienrealise"}

# messages de politesse qui ne demandent pas de réponse : au moins un mot de clôture (merci, ok, bonne soirée…),
# rien d'autre que des mots de remplissage, pas de point d'interrogation. « Oui », « Bonjour », « Avec plaisir »
# restent des messages à traiter (souvent une acceptation ou une ouverture).
CLOSE = set("""merci mercii merciii ok okay oki okk dac d'accord parfait nickel cordialement bisous bises bientôt bientot
pareillement idem remercie thanks top super génial genial cool reçu recu""".split())
FILL = set("""beaucoup bcp infiniment a à toi vous ça ca marche de journée journee soirée soiree semaine weekend week-end week
end nuit continuation lauric trop bien et encore grave vraiment également egalement tout pareil pour le la ta votre ton
message retour je te bonjour bonsoir hello salut coucou oui yes ty thank you mdr haha ahah hihi lol aussi accord d
bonne bon belle""".split()) | CLOSE
NON_MERCI = re.compile(r"\b(non merci|pas int[ée]ress[ée]e?|pas pour moi)\b", re.I)


def is_poli(ty, x):
    """Message qui ne demande pas de réponse : cœur, GIF, emoji seul, merci / ok / bonne soirée, refus poli."""
    if ty in ("h", "g"):
        return True
    if ty != "t" or not x or "?" in x:
        return False          # vocal, réel, story, lien, photo, texte long (non exporté) ou question : à traiter
    if NON_MERCI.search(x):
        return True
    s = "".join(ch if unicodedata.category(ch)[0] in "LNZ" or ch in "'’-" else " " for ch in x).lower().replace("’", "'")
    words = [w.strip("'-") for w in s.split() if w.strip("'-")]
    if not words:
        return any(unicodedata.category(ch) == "So" for ch in x)      # emoji seul
    return all(w in FILL for w in words) and any(w in CLOSE for w in words)


def parse(path):
    convs = []
    for line in open(path, encoding="utf-8").read().split("\n"):
        if not line.startswith("R┃"):
            continue
        _, u, lb, n_items, seen, items = line.split("┃", 5)
        its = []
        for it in items.split(";"):
            if not it:
                continue
            w, t, ty, x = (it.split(",", 3) + ["", "", "", ""])[:4]
            if w not in ("L", "P") or not t.isdigit():
                continue
            its.append((w, int(t), ty, x))
        its.sort(key=lambda i: i[1])
        convs.append({"u": u, "lb": lb, "n": int(n_items or 0), "seen": int(seen or 0), "items": its})
    return convs


def tours_of(c):
    """Tours du lead : messages du lead d'affilée (likes ignorés), avec l'heure du premier et la réponse suivante."""
    items = [i for i in c["items"] if i[2] != "a"]          # un like de message n'est ni un message ni une réponse
    out, cur = [], None
    for k, (w, t, ty, x) in enumerate(items):
        if w == "P":
            if cur is None:
                cur = {"t": t, "tys": set(), "poli": True, "n": 0, "first": k == 0}
            cur["tys"].add(ty); cur["n"] += 1
            cur["poli"] = cur["poli"] and is_poli(ty, x)
        elif cur is not None:
            cur["r"] = t; out.append(cur); cur = None
    if cur is not None:
        cur["r"] = 0; out.append(cur)
    # conversation tronquée (40 derniers messages) qui commence par le lead : le début réel du tour est inconnu
    if c["n"] >= 40 and out and out[0]["first"]:
        out = out[1:]
    return out


def fmt(ts):
    return datetime.datetime.fromtimestamp(ts, TZ).strftime("%d/%m/%Y %H:%M") if ts else ""


def main():
    src = sys.argv[1]
    stamp = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.datetime.now(TZ).strftime("%d/%m/%Y %Hh%M")
    notif = sys.argv[sys.argv.index("--notif") + 1] if "--notif" in sys.argv else ""
    convs = [c for c in parse(src) if c["u"] not in EXC]

    # 1) tours de réponse, fusionnés avec le fichier précédent
    prev = json.load(open(OUT, encoding="utf-8")) if OUT.exists() else {}
    seen_now = {c["u"] for c in convs}
    tours = [t for t in prev.get("tours", []) if t[0] not in seen_now]
    labels = {k: v for k, v in prev.get("labels", {}).items() if k not in seen_now}
    for c in convs:
        for t in tours_of(c):
            kind = "".join(sorted(t["tys"]))
            tours.append([c["u"], t["t"], t["r"], t["n"], kind, 1 if t["poli"] else 0])
        lb = ",".join(l.split("/")[0] for l in c["lb"].split(",") if l and not l.startswith("Réactif"))
        if lb:
            labels[c["u"]] = lb
    tours.sort(key=lambda t: t[1])
    lastact = sorted(max((i[1] for i in c["items"]), default=0) for c in convs)
    couvert = datetime.datetime.fromtimestamp(lastact[0], TZ).strftime("%Y-%m-%d") if lastact else ""
    couvert = min(couvert, prev.get("couvert_depuis") or couvert) if couvert else prev.get("couvert_depuis", "")

    # 2) abonnements (notifications) → abonnes.csv : heure d'abonnement + premier message de notre côté
    follows = {}
    if notif:
        for line in open(notif, encoding="utf-8").read().split("\n"):
            p = line.strip().split("┃")
            if len(p) >= 3 and p[0].isdigit():
                follows[p[2]] = int(p[0])
    by_u = {c["u"]: c for c in convs}
    rows = list(csv.DictReader(open(ABO, encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else []
    for col in ("Abonne le", "Premier message le"):
        if col not in fields:
            fields.append(col)
    n_follow, n_first, missing = 0, 0, []
    have = {r["Pseudo"] for r in rows}
    for u in follows:
        if u not in have:
            missing.append(u)
    for r in rows:
        r.setdefault("Abonne le", ""); r.setdefault("Premier message le", "")
        u = r["Pseudo"]
        if u in follows and not r["Abonne le"]:
            r["Abonne le"] = fmt(follows[u]); n_follow += 1
        c = by_u.get(u)
        if c:
            ls = [i[1] for i in c["items"] if i[0] == "L"]
            if ls:
                first = fmt(min(ls))
                # on garde la plus ancienne heure connue (un relevé plus court ne doit pas la déplacer)
                if not r["Premier message le"] or _ts(first) < _ts(r["Premier message le"]):
                    r["Premier message le"] = first; n_first += 1
    with open(ABO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    m = re.match(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2})h(\d{2})", stamp)
    ts = int(datetime.datetime(int(m[3]), int(m[2]), int(m[1]), int(m[4]), int(m[5]), tzinfo=TZ).timestamp()) if m else int(datetime.datetime.now(TZ).timestamp())
    json.dump({"genere": stamp, "ts": ts, "couvert_depuis": couvert, "tours": tours, "labels": labels},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    rep = sum(1 for t in tours if t[2]); poli = sum(1 for t in tours if t[5])
    print(f"{len(convs)} convs · {len(tours)} tours ({rep} avec réponse, {poli} de politesse) · couvert depuis {couvert} · "
          f"{len(labels)} étiquettes · abonnés : {n_follow} heures d'abonnement ajoutées, {n_first} premiers messages datés"
          + (f" · absents d'abonnes.csv : {', '.join(missing)}" if missing else ""))


def _ts(s):
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y %H:%M").replace(tzinfo=TZ).timestamp()
    except ValueError:
        return 9e12


if __name__ == "__main__":
    main()
