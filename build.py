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
import csv, io, json, re, sys, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
EOD_URL = ("https://docs.google.com/spreadsheets/d/"
           "1vVzQXjAGp-lzF1LTeDMg281dan3TcPxrksvWvxZQRuU/export?format=csv&gid=123224703")
TALLY_URL = ("https://docs.google.com/spreadsheets/d/"
             "1aMQ_zNQbq2xyntex3V_6GDY5pE9pIaD_v-FTCzJWxes/export?format=csv")

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

    if "--no-fetch" not in sys.argv:
        eod_file.write_text(fetch(EOD_URL), encoding="utf-8")
        tally_file.write_text(fetch(TALLY_URL), encoding="utf-8")

    eod_text = eod_file.read_text(encoding="utf-8")
    tally_text = tally_file.read_text(encoding="utf-8")
    recap(eod_text, tally_text)

    if "--data-only" in sys.argv:
        return

    page = (HERE / "index.html").read_text(encoding="utf-8")
    snapshot = ("{generated:" + js_string(datetime.now().strftime("%d/%m/%Y %H:%M"))
                + ",eod:" + js_string(eod_text)
                + ",tally:" + js_string(tally_text) + "}")
    out = page.replace("/*__SNAPSHOT__*/null", snapshot, 1)
    if out == page:
        raise SystemExit("marqueur /*__SNAPSHOT__*/null introuvable dans index.html")
    (HERE / "dashboard.html").write_text(out, encoding="utf-8")
    print(f"dashboard.html régénéré ({len(out) // 1024} Ko)")


if __name__ == "__main__":
    main()
