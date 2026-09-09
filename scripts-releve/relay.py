#!/usr/bin/env python3
"""Relais local pour sortir un gros texte de Chrome : la page servie lit window.name et le POSTe sur /save.
Usage : python3 scripts-releve/relay.py  (port 8765, Ctrl-C pour arrêter). Fichier écrit : relay-HHMMSS.txt (dossier courant).
Côté Chrome : window.name = JSON.stringify(window.__T); location.href = 'http://127.0.0.1:8765/'"""
import http.server, time, os
PAGE = b"""<!doctype html><meta charset=utf-8><title>relais</title><pre id=s>...</pre><script>
const d=window.name||''; document.getElementById('s').textContent='len '+d.length;
fetch('/save',{method:'POST',body:d}).then(r=>r.text()).then(t=>{document.getElementById('s').textContent='saved '+t; window.name='';});
</script>"""
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(PAGE)
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); body = self.rfile.read(n)
        name = os.path.abspath('relay-' + time.strftime('%H%M%S') + '.txt'); open(name, 'wb').write(body)
        self.send_response(200); self.end_headers(); self.wfile.write((name + ' ' + str(n)).encode())
print("relais sur http://127.0.0.1:8765/")
http.server.HTTPServer(('127.0.0.1', 8765), H).serve_forever()
