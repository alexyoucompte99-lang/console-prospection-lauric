#!/usr/bin/env python3
"""Pipeline console prospection Insta Lauric.

Télécharge les 2 Google Sheets (EOD setters + soumissions Tally) dans data/,
puis génère dashboard.html : une copie figée de index.html avec les CSV
inlinés, pour republier l'artifact Claude (qui ne peut pas appeler le réseau).

La page GitHub Pages (index.html) n'a besoin de rien de tout ça : elle lit les
Sheets en direct dans le navigateur. Les CSV de data/ lui servent seulement de
secours si Google est injoignable.

Usage:
  python3 build.py              télécharge + régénère dashboard.html
  python3 build.py --data-only  télécharge seulement (utilisé par GitHub Actions)
  python3 build.py --no-fetch   réutilise les CSV déjà téléchargés (debug)
"""
import csv, io, json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
EOD_URL = ("https://docs.google.com/spreadsheets/d/"
           "1vVzQXjAGp-lzF1LTeDMg281dan3TcPxrksvWvxZQRuU/export?format=csv&gid=123224703")
TALLY_URL = ("https://docs.google.com/spreadsheets/d/"
             "1aMQ_zNQbq2xyntex3V_6GDY5pE9pIaD_v-FTCzJWxes/export?format=csv")
# Portefeuille de leads (deals Lauric). Nécessite le partage « tous ceux qui ont
# le lien » ; tant qu'il est privé, Google renvoie du HTML et on garde la copie.
PF_URL = ("https://docs.google.com/spreadsheets/d/"
          "1RdQsQu6FytcHQkWXqXNYTJOi1rhgwJyBE7PJgPtB09c/export?format=csv&gid=0")

# Notification téléphone (app ntfy) quand un nouveau scan Tally est rempli :
# on compare les Submission ID du CSV fraîchement téléchargé avec la copie
# précédente et on publie un message par nouveau scan sur ce topic.
NTFY_TOPIC = "scan-dirigeant-lauric-d7k4q2"

# Notification Telegram (Alex) quand une idée est envoyée depuis la boîte à
# idées de l'onglet Script setting : elle arrive dans le Sheet EOD avec le
# setter « Boîte à idées », on diffe les lignes à chaque run.
# Secrets GitHub : TG_TOKEN (bot) et TG_CHAT (chat_id).
IDEA_RE = re.compile(r"bo[iî]te\s*[aà]\s*id[ée]es", re.I)
IDEA_NOTE_COLS = (5, 6, 12)

# Soumissions partielles du scan Tally (jamais poussées vers le Sheet par Tally,
# seule l'API les expose). Clé : secret GitHub TALLY_API_KEY, ou fichier local.
TALLY_FORM_ID = "zxvka0"
TALLY_KEY_FILE = HERE.parent / "tally-lead-magnet-anais" / "tally-api-key.txt"

# Calls Calendly de Lauric (onglets « Calls à venir » et « Calls à remplir »).
# Jeton : secret GitHub CALENDLY_TOKEN, ou fichier local gitignoré. Le jeton ne
# doit JAMAIS apparaître dans la page ni dans le repo (public) : seul le CSV
# data/calendly.csv, écrit ici, est exposé.
CAL_KEY_FILE = HERE / "calendly-token.txt"

COL_DATE, COL_SETTER = 1, 2
COL_MSG_NEW, COL_MSG_OLD, COL_MSG_OTHER, COL_RELANCE = 3, 4, 5, 7
COL_SUBS, COL_MSG_LIKE, COL_MSG_COM, COL_SCAN_OK, COL_SCAN_FILLED = 13, 15, 16, 17, 18


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def num(v: str) -> int:
    m = re.search(r"\d+", v or "")
    return int(m.group()) if m else 0


def parse_date(v: str):
    v = (v or "").strip().split(" ")[0]
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    return None


def tally_key() -> str:
    k = os.environ.get("TALLY_API_KEY", "").strip()
    if not k and TALLY_KEY_FILE.exists():
        k = TALLY_KEY_FILE.read_text().strip()
    return k


def fetch_partials(key: str) -> str:
    """CSV des soumissions partielles du form Tally, une ligne par prospect en cours."""
    subs, questions, page = [], [], 1
    while page <= 20:
        url = (f"https://api.tally.so/forms/{TALLY_FORM_ID}/submissions"
               f"?filter=partial&limit=500&page={page}")
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.load(r)
        if page == 1:
            questions = body.get("questions") or []
        subs += body.get("submissions") or []
        if not body.get("hasMore"):
            break
        page += 1

    by_title = {}
    for q in questions:
        t = (q.get("title") or "").strip().lower()
        if t.startswith("votre prénom"):
            by_title.setdefault("prenom", set()).add(q["id"])
        elif t.startswith("votre numéro whatsapp"):
            by_title.setdefault("wa", set()).add(q["id"])
        elif t.startswith("avant de commencer"):
            by_title.setdefault("profil", set()).add(q["id"])
        elif re.match(r"q\d", t):
            by_title.setdefault("questions", set()).add(q["id"])
    nb_q = len(by_title.get("questions", ())) or 9

    # Réponses détaillées : les Q1..Q9 + « Votre résultat arrive... », une colonne
    # par question (intitulé complet en en-tête, la page les affiche au clic).
    detail_qs = [q for q in questions
                 if q["id"] in by_title.get("questions", ())
                 or (q.get("title") or "").strip().lower().startswith("votre résultat arrive")]

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Submission ID", "Derniere activite", "Prenom", "WhatsApp",
                "Profil", "Score", "Questions repondues", "Questions total"]
               + [q.get("title") or "" for q in detail_qs])
    for s in subs:
        row = {"prenom": "", "wa": "", "profil": "", "score": "", "answered": 0}
        answers = {}
        last = s.get("updatedAt") or s.get("submittedAt") or s.get("createdAt") or ""
        for r in s.get("responses") or []:
            a = r.get("answer")
            qid = r.get("questionId")
            if isinstance(a, dict) and "score" in a:
                row["score"] = a["score"]
                continue
            if isinstance(a, list):
                a = ", ".join(str(x) for x in a)
            a = "" if a is None else str(a).strip()
            if not a:
                continue
            answers[qid] = a
            if qid in by_title.get("prenom", ()):
                row["prenom"] = a
            elif qid in by_title.get("wa", ()):
                row["wa"] = a
            elif qid in by_title.get("profil", ()):
                row["profil"] = a
            elif qid in by_title.get("questions", ()):
                row["answered"] += 1
        w.writerow([s.get("id", ""), last, row["prenom"], row["wa"],
                    row["profil"], row["score"], row["answered"], nb_q]
                   + [answers.get(q["id"], "") for q in detail_qs])
    return out.getvalue()


def calendly_token() -> str:
    k = os.environ.get("CALENDLY_TOKEN", "").strip()
    if not k and CAL_KEY_FILE.exists():
        k = CAL_KEY_FILE.read_text().strip()
    return k


def fetch_calendly(token: str) -> str:
    """CSV des RDV Calendly de Lauric (90 j passés -> 90 j futurs), un par ligne."""
    from datetime import timedelta, timezone

    def api(url):
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token, "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    me = api("https://api.calendly.com/users/me")["resource"]["uri"]
    now = datetime.now(timezone.utc)
    qs = urllib.parse.urlencode({
        "user": me, "count": 100, "sort": "start_time:desc",
        "min_start_time": (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_start_time": (now + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    events, url = [], "https://api.calendly.com/scheduled_events?" + qs
    while url:
        body = api(url)
        events += body.get("collection") or []
        url = (body.get("pagination") or {}).get("next_page")

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["UUID", "Debut", "Evenement", "Statut", "Invite", "Email",
                "Telephone", "Reponses", "Lien visio"])
    for e in events:
        uuid = e["uri"].rsplit("/", 1)[-1]
        inv = {}
        try:
            coll = api(e["uri"] + "/invitees").get("collection") or []
            inv = coll[0] if coll else {}
        except Exception as exc:
            print("invitee KO", uuid, exc)
        phone = inv.get("text_reminder_number") or ""
        qa_parts = []
        for q in inv.get("questions_and_answers") or []:
            ans = (q.get("answer") or "").strip()
            if not ans:
                continue
            if not phone and re.search(r"t[ée]l[ée]phone|phone|whatsapp|num[ée]ro",
                                       q.get("question") or "", re.I):
                phone = ans
            else:
                qa_parts.append(((q.get("question") or "").strip() + " : " + ans))
        loc = e.get("location") or {}
        w.writerow([uuid, e.get("start_time", ""), (e.get("name") or "").strip(),
                    e.get("status", ""), inv.get("name", ""), inv.get("email", ""),
                    phone, " | ".join(qa_parts), loc.get("join_url") or ""])
    return out.getvalue()


def notify_new_tally(old_text: str, new_text: str) -> None:
    """Publie une notif ntfy pour chaque scan présent dans new_text mais pas old_text."""
    def rows(text):
        r = list(csv.reader(io.StringIO(text)))
        return (r[0] if r else []), r[1:]
    _, old_rows = rows(old_text)
    header, new_rows = rows(new_text)
    if not header or not old_rows:   # première exécution : pas de référence, pas de spam
        return
    idx = {(c or "").strip().lower(): i for i, c in enumerate(header)}
    def col(row, name):
        i = next((v for k, v in idx.items() if k.startswith(name)), None)
        return (row[i].strip() if i is not None and i < len(row) else "")
    seen = {r[0] for r in old_rows if r}
    fresh = [r for r in new_rows if r and r[0] not in seen]
    for r in fresh[:10]:
        prenom = col(r, "votre prénom") or "Sans prénom"
        profil = col(r, "avant de commencer")
        score = col(r, "score")
        body = prenom
        if profil:
            body += " · " + profil
        if score:
            body += " · score " + score
        try:
            req = urllib.request.Request(
                "https://ntfy.sh/" + NTFY_TOPIC,
                data=body.encode("utf-8"),
                headers={"Title": "Nouveau Scan Dirigeant rempli",
                         "Tags": "dart", "User-Agent": "Mozilla/5.0"})
            urllib.request.urlopen(req, timeout=30).read()
            print("notif ntfy envoyée :", body)
        except Exception as e:   # la notif ne doit jamais faire échouer le job
            print("notif ntfy échouée :", e)


def send_telegram(text: str) -> None:
    """Envoie un message sur le Telegram d'Alex. N'échoue jamais le job."""
    token = os.environ.get("TG_TOKEN", "").strip()
    chat = os.environ.get("TG_CHAT", "").strip()
    if not token or not chat:
        print("TG_TOKEN/TG_CHAT absents : notif Telegram ignorée")
        return
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        urllib.request.urlopen(req, timeout=30).read()
        print("notif Telegram envoyée")
    except Exception as e:
        print("notif Telegram échouée :", e)


def idea_rows(text: str):
    """Lignes « Boîte à idées » du CSV EOD, sous forme (clé, date, texte)."""
    out = []
    for r in list(csv.reader(io.StringIO(text)))[1:]:
        if len(r) <= COL_SETTER or not IDEA_RE.search(r[COL_SETTER] or ""):
            continue
        note = "\n".join((r[i] or "").strip() for i in IDEA_NOTE_COLS
                          if i < len(r) and (r[i] or "").strip())
        if not note:
            continue
        out.append(((r[0] or "").strip() + "|" + note, (r[COL_DATE] or "").strip(), note))
    return out


def notify_new_ideas(old_text: str, new_text: str) -> None:
    """Un message Telegram par nouvelle idée déposée dans la boîte à idées."""
    if not old_text.strip():        # première exécution : pas de référence
        return
    seen = {k for k, _, _ in idea_rows(old_text)}
    fresh = [i for i in idea_rows(new_text) if i[0] not in seen]
    for _, date, note in fresh[:10]:
        send_telegram("💡 Nouvelle idée dans la console Lauric"
                      + (f" ({date})" if date else "") + "\n\n" + note
                      + "\n\nhttps://alexyoucompte99-lang.github.io/console-prospection-lauric/#script")


def js_string(s: str) -> str:
    """JSON sûr à l'intérieur d'un <script> (pas de </script> ni de <!-- qui s'échappe)."""
    return json.dumps(s, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028")


def recap(eod_text: str, tally_text: str) -> None:
    rows = list(csv.reader(io.StringIO(eod_text)))[1:]
    days = {}
    for r in rows:
        if len(r) < 8:
            continue
        d = parse_date(r[COL_DATE]) or parse_date(r[0])
        if not d:
            continue
        g = lambda i: num(r[i]) if i < len(r) else 0
        day = days.setdefault(d, dict(msg=0, subs=0, like=0, com=0, scan_ok=0, scan_filled=0))
        day["msg"] += (g(COL_MSG_NEW) + g(COL_MSG_OLD) + g(COL_MSG_OTHER)
                       + g(COL_RELANCE) + g(COL_MSG_LIKE) + g(COL_MSG_COM))
        day["subs"] += g(COL_SUBS)
        day["like"] += g(COL_MSG_LIKE)
        day["com"] += g(COL_MSG_COM)
        day["scan_ok"] += g(COL_SCAN_OK)
        day["scan_filled"] += g(COL_SCAN_FILLED)
    if not days:
        print("aucun jour trouvé dans l'EOD, vérifier la source")
        return
    ordered = sorted(days.items())
    tally_n = max(0, len(list(csv.reader(io.StringIO(tally_text)))) - 1)
    print(f"{len(ordered)} jours, du {ordered[0][0]} au {ordered[-1][0]}")
    print(f"messages totaux: {sum(d['msg'] for _, d in ordered)}, "
          f"likes: {sum(d['like'] for _, d in ordered)}, "
          f"commentaires: {sum(d['com'] for _, d in ordered)}, "
          f"scans acceptés: {sum(d['scan_ok'] for _, d in ordered)}, "
          f"scans remplis EOD: {sum(d['scan_filled'] for _, d in ordered)}, "
          f"tally: {tally_n}")
    for d, v in ordered[-10:]:
        print(d, "msg:", v["msg"], "abo:", v["subs"], "scanOk:", v["scan_ok"])


def main():
    DATA.mkdir(exist_ok=True)
    eod_file, tally_file = DATA / "eod.csv", DATA / "tally.csv"
    partials_file, pf_file = DATA / "partielles.csv", DATA / "portefeuille.csv"

    if "--no-fetch" not in sys.argv:
        old_eod = eod_file.read_text(encoding="utf-8") if eod_file.exists() else ""
        new_eod = fetch(EOD_URL)
        notify_new_ideas(old_eod, new_eod)
        eod_file.write_text(new_eod, encoding="utf-8")
        old_tally = tally_file.read_text(encoding="utf-8") if tally_file.exists() else ""
        new_tally = fetch(TALLY_URL)
        notify_new_tally(old_tally, new_tally)
        tally_file.write_text(new_tally, encoding="utf-8")
        try:
            pf_text = fetch(PF_URL)
            if pf_text.lstrip().startswith("<"):
                raise ValueError("le Sheet portefeuille est privé (HTML reçu)")
            pf_file.write_text(pf_text, encoding="utf-8")
        except Exception as e:
            print("portefeuille non rafraîchi :", e)
        key = tally_key()
        if key:
            partials_file.write_text(fetch_partials(key), encoding="utf-8")
        else:
            print("TALLY_API_KEY absent : partielles non rafraîchies")
        cal = calendly_token()
        if cal:
            try:
                (DATA / "calendly.csv").write_text(fetch_calendly(cal), encoding="utf-8")
            except Exception as e:
                print("calendly non rafraîchi :", e)
        else:
            print("CALENDLY_TOKEN absent : calls non rafraîchis")

    eod_text = eod_file.read_text(encoding="utf-8")
    tally_text = tally_file.read_text(encoding="utf-8")
    partials_text = partials_file.read_text(encoding="utf-8") if partials_file.exists() else ""
    pf_text = pf_file.read_text(encoding="utf-8") if pf_file.exists() else ""
    cal_file = DATA / "calendly.csv"
    cal_text = cal_file.read_text(encoding="utf-8") if cal_file.exists() else ""
    print(f"partielles: {max(0, len(partials_text.splitlines()) - 1)}, "
          f"calls calendly: {max(0, len(cal_text.splitlines()) - 1)}")
    recap(eod_text, tally_text)

    if "--data-only" in sys.argv:
        return

    page = (HERE / "index.html").read_text(encoding="utf-8")
    snapshot = ("{generated:" + js_string(datetime.now().strftime("%d/%m/%Y %H:%M"))
                + ",eod:" + js_string(eod_text)
                + ",tally:" + js_string(tally_text)
                + ",partials:" + js_string(partials_text)
                + ",pf:" + js_string(pf_text)
                + ",cal:" + js_string(cal_text) + "}")
    out = page.replace("/*__SNAPSHOT__*/null", snapshot, 1)
    if out == page:
        raise SystemExit("marqueur /*__SNAPSHOT__*/null introuvable dans index.html")
    (HERE / "dashboard.html").write_text(out, encoding="utf-8")
    print(f"dashboard.html régénéré ({len(out) // 1024} Ko)")


if __name__ == "__main__":
    main()
