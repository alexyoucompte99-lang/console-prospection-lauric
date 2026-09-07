#!/usr/bin/env python3
"""Relevé des conversations Instagram → data/leads-insta.csv + data/insta-activite.csv

Entrée : un fichier texte produit par le script JS du runbook RELEVE-INSTA.md (une conversation par ligne,
champs séparés par ┃, retours à la ligne encodés ⏎), plus les lignes ACT┃date┃accroches┃suivi┃vocaux.
Usage : python3 releve_insta.py dump.txt [--date 07/09/2026]
Les lignes existantes du CSV sont conservées (Prio, Raison, Message rédigés à la main) et mises à jour
avec les nouveaux statuts ; les conversations inconnues sont ajoutées.
"""
import csv, sys, re, datetime, collections, pathlib

ROOT = pathlib.Path(__file__).parent
CSV = ROOT / "data" / "leads-insta.csv"
ACT = ROOT / "data" / "insta-activite.csv"
FIELDS = ["Pseudo","Nom","Statut","Variante","Premier contact","Dernier message","Detail","Releve","Prio","Raison","Message",
          "Message envoye","Date envoi","Date vu","Dernier message Lauric","Date dernier Lauric","Reponse lead","Date reponse","Conv","Action"]
TZ = datetime.timezone(datetime.timedelta(hours=2))
C0 = 1787781600  # 27/08/2026 : début de la campagne A/B

def dt(ts):
    ts = int(ts or 0); return datetime.datetime.fromtimestamp(ts, TZ).strftime("%d/%m/%Y %H:%M") if ts else ""
def day(ts):
    ts = int(ts or 0); return datetime.datetime.fromtimestamp(ts, TZ).strftime("%d/%m/%Y") if ts else ""
TEMPLATES = {
    "{BIENV}": "Bienvenue sur mon compte {N}! 🙂\nJ’offre à tous mes abonnés qui sont dirigeants un scan qui peut leur permettre de prendre du recul et de grandement diminuer leur charge mentale.\n\nÇa prend quelques minutes et ça a énormément aidé de gros entrepreneurs, dis-moi si tu es curieux de voir ça ?\n\n(Pour gagner du temps, like ce message et je te l’envoie)",
    "{LIKE}": "Hello {N}, merci pour ton like sur mon post. 🙂\n\nJe propose aux dirigeants qui s’intéressent à ce sujet un scan qui peut leur permettre de prendre du recul et de grandement diminuer leur charge mentale.\n\nÇa prend quelques minutes et ça a énormément aidé de gros entrepreneurs, dis-moi si tu es curieux de voir ça ?",
    "{RELB}": "Bonsoir {N}! J’espère que tu vas bien.\n\nJe me demandais simplement si tu avais bien reçu mon message.\n\nBonne soirée!😀",
    "{RELQ}": "Hello {N}, tu vas bien ?\n\nTu es toi même entrepreneur ?😊",
    "{A}": "Hello {N} !\nBienvenue et merci de me suivre 🙏\n\nTu l’as sûrement vu, ici je parle aux dirigeants principalement 😊\n\nJ’ai dirigé pendant 10 ans je connais par cœur les défis :\nTout porter sur ses épaules.\nLe stress du chiffre.\nRecruter, motiver ses employés.\nPrendre une tonne de décisions.\nEtc.\n\n✅ Depuis de nombreuses années j’applique une méthode que j’ai apprise auprès des plus grands dirigeants !\n👉 + d’engagement\n👉 + de business\nC’est dingue la différence.\n\nEt puis la cerise sur le gâteau : beaucoup moins de charge mentale pour le dirigeant 😎\n\nUne question importante :\nTu es dirigeant d’une boîte ?",
    "{B}": "Hello {N} ! Merci beaucoup pour ton abonnement, ça fait super plaisir de te voir ici ! 😁\n\n[personnalisation]\n\nJ’aime bien savoir qui se cache derrière les nouveaux profils, alors je te laisse un petit vocal pour me présenter rapidement !",
}
_NAME = ""
def txt(s):
    s = (s or "")
    if s in TEMPLATES: s = TEMPLATES[s].replace("{N}", _NAME).replace(" !", " !").replace("  ", " ")
    return s.replace("⏎", "\n").strip()

def variant(t):
    t = TEMPLATES.get(t, t)
    if re.search(r"sûrement vu, ici je parle|dirigé pendant 10 ans|cerise sur le gâteau", t, re.I): return "A"
    if re.search(r"Merci beaucoup pour ton abonnement, ça fait super plaisir|se cache derrière les nouveaux profils", t, re.I): return "B"
    if re.search(r"Bienvenue sur mon compte|offre (à|a) tous mes abonnés", t, re.I): return "ancienne"
    if re.search(r"merci pour ton like", t, re.I): return "like"
    if re.search(r"merci pour (le|ton) follow|merci de t.être abonn", t, re.I): return "lauric"
    return "perso"

def prenom(nom):
    w = (nom or "").split()
    if w and re.match(r"^[A-Za-zÀ-ÿ'’-]{2,}$", w[0]) and w[0].lower() not in ("the","mr","mx","mhb","cm","oev","summus","laast","dress","coach","chef","isa","flo","seb","jb","sbca","mces","ne"):
        p = w[0]; return p[0].upper() + p[1:].lower()
    return ""

def main():
    src = sys.argv[1]
    releve = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.date.today().strftime("%d/%m/%Y")
    now = datetime.datetime.now(TZ)
    lines = [l for l in open(src, encoding="utf-8").read().split("\n") if l and l not in ("RICH", "RICH2", "ENDDUMP")]
    rows = [l.split("┃") for l in lines if not l.startswith("ACT")]
    acts = [l.split("┃")[1:] for l in lines if l.startswith("ACT")]
    old = list(csv.DictReader(open(CSV, encoding="utf-8"))) if CSV.exists() else []
    byp = {o["Pseudo"]: o for o in old}
    out = []
    for r in rows:
        if len(r) < 20: continue
        u, nom, accTs, accText, accVoc, seen, lastLts, lastLtext, lastPts, lastPtext, rs, tid, nL, nP, relDays, firstIsAcc, recent, firstAny, nItems, reagi = r[:20]
        if not u: continue
        accTs, seen, lastLts, lastPts, firstAny, nItems = int(accTs), int(seen), int(lastLts), int(lastPts), int(firstAny), int(nItems)
        o = dict(byp.get(u) or {k: "" for k in FIELDS})
        o["Pseudo"] = u; o["Nom"] = o["Nom"] or nom
        global _NAME; _NAME = prenom(nom)
        acc = txt(accText)
        va = o["Variante"] if o["Variante"] and o["Variante"] not in ("historique",) else variant(acc)
        if not o["Variante"] and firstAny < C0 and lastLts >= 1787868000 and lastLts < 1787954400 and not (firstIsAcc == "1" and accTs >= C0): va = "relance2808"
        o["Variante"] = va
        isLike = lastPtext.strip() == "[action_log]"
        replied = lastPts > accTs and not isLike
        st = "repondu" if replied else "reagi" if (reagi == "1" or isLike) else "vu" if seen >= lastLts else "nonvu"
        o["Statut"] = st
        o["Premier contact"] = day(firstAny); o["Dernier message"] = day(max(lastLts, lastPts)); o["Releve"] = releve
        o["Message envoye"] = acc or ("[vocal]" if accVoc == "1" else "")
        o["Date envoi"] = dt(accTs); o["Date vu"] = dt(seen) if seen >= accTs else ""
        o["Dernier message Lauric"] = txt(lastLtext) if lastLts > accTs + 900 else ""; o["Date dernier Lauric"] = dt(lastLts) if lastLts > accTs + 900 else ""
        o["Reponse lead"] = txt(lastPtext) if replied else ""; o["Date reponse"] = dt(lastPts) if replied else ""
        o["Conv"] = "https://www.instagram.com/direct/t/" + tid + "/"
        det = ("Accroche " + va + " le " + day(accTs)) if accTs >= C0 else ("Conversation d'avant le 27/08 (1er contact " + day(firstAny) + ") ; accroche de type « " + va + " » le " + day(accTs))
        if nItems >= 20: det += " ; conversation longue, début non relevé (20 derniers messages seulement)"
        if lastLts > accTs + 900: det += " ; dernier message de notre côté le " + day(lastLts)
        if st == "vu": det += " ; vu le " + day(seen) + " sans réponse"
        if st == "nonvu": det += " ; jamais ouvert"
        if st == "reagi": det += " ; a réagi ❤️ à notre message"
        if replied: det += " ; a répondu le " + day(lastPts) + " : « " + txt(lastPtext)[:120].replace("\n", " ") + " »"
        if rs != "0": det += " ; RÉPONSE NON LUE"
        o["Detail"] = det
        pre = prenom(o["Nom"]); age = (now - datetime.datetime.fromtimestamp(accTs, TZ)).days
        hello = ("Hello " + pre + " !") if pre else "Hello !"
        if o["Prio"]:
            act = "Priorité n°" + o["Prio"] + " : " + o["Raison"]
        elif replied and lastPts > lastLts:
            act = "RÉPONDRE : le lead attend une réponse depuis le " + day(lastPts)
        elif replied and accTs < C0:
            act = "À réactiver : avait répondu le " + day(lastPts) + ", silence depuis le " + day(lastLts)
            if not o["Message"]: o["Message"] = hello + " On avait échangé il y a quelques semaines et je reprends le fil : où en es-tu de ton côté ? Si c'est le bon moment pour parler de ton équipe ou de ta boîte, je suis dispo."
        elif replied:
            act = "Attendre sa réponse (dernier message de notre côté le " + day(lastLts) + ")"
        elif st == "reagi":
            act = "A réagi ❤️ sans répondre : relancer avec une question simple"
            if not o["Message"]: o["Message"] = hello + " Merci pour ton like. Je te posais une question simple : tu es à ton compte ou tu diriges une équipe ?"
        elif va == "like" and st == "nonvu":
            act = "Ne rien faire : personne non abonnée, le message est tombé dans ses Demandes et n'a jamais été ouvert"
        elif st == "vu" and lastLts > accTs + 900:
            act = "Déjà relancé le " + day(lastLts) + " sans réponse : laisser tomber ou dernière relance légère"
        elif st == "vu" and age >= 3:
            act = "Relancer : vu le " + day(seen) + " sans réponse"
            if not o["Message"]: o["Message"] = hello + " Mon message est peut-être passé un peu vite. Je te posais juste une question simple : tu es à ton compte ou tu diriges une équipe ?"
        elif st == "vu":
            act = "Vu le " + day(seen) + " : attendre 48 h avant de relancer"
        elif age >= 4:
            act = "Jamais ouvert depuis " + str(age) + " jours : laisser tomber (compte inactif ou message non délivré)"
        else:
            act = "Pas encore ouvert : attendre"
        o["Action"] = act
        out.append(o); byp.pop(u, None)
    out += list(byp.values())   # conversations non revues cette fois : conservées telles quelles
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out)
    if acts:
        prev = {}
        if ACT.exists():
            for r in csv.DictReader(open(ACT, encoding="utf-8")): prev[r["Date"]] = [r["Accroches"], r["Messages de suivi"], r["Vocaux"]]
        for d, a, s, v in acts: prev[d] = [a, s, v]
        with open(ACT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["Date", "Accroches", "Messages de suivi", "Vocaux", "Releve"])
            for d in sorted(prev): w.writerow([d] + prev[d] + [releve])
    c = collections.Counter(o["Statut"] for o in out)
    print(f"{len(out)} leads ({len(rows)} relevés, {len(byp)} conservés sans mise à jour) · {dict(c)} · {len(acts)} jours d'activité")

if __name__ == "__main__":
    main()
