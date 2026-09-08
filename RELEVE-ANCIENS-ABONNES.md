# Relevé des anciens abonnés (tâche « anciens-abonnes-lauric », demandée par Alex le 08/09/2026)

But : remonter la liste des abonnés de @lauric_sergent au-delà des 384 plus récents (déjà relevés le 08/09),
trouver ceux qui n'ont JAMAIS eu de conversation, et les ajouter à `data/abonnes.csv` avec `Type=ancien`
(section « 🗂️ Anciens abonnés jamais contactés » de la console). Compte à 2 566 abonnés : ~2 180 restent à passer,
en PLUSIEURS sessions. Lecture seule : jamais d'envoi, de like, de follow, jamais ouvrir une conversation.

## Rythme imposé par Alex (anti-ban)
- **20 secondes minimum entre deux pages** de la liste des abonnés (≈ 24 abonnés par page malgré `count=50`).
- Garde-fou : mesurer la latence de chaque fetch ; si > 20 s ou statut 429 / non-200 → arrêter la boucle, noter
  « ralentissement Instagram » dans `data/abonnes.log`, et reprendre à la session suivante (le lendemain).
- **40 pages maximum par session** (≈ 950 abonnés, ~14 min), puis s'arrêter même si tout va bien.
- Fiches profil `/api/v1/users/<pk>/info/` : 6 s entre deux appels, 40 fiches max par session (les inconnus au-delà
  sont ajoutés avec Profil « non consulté, à qualifier à la session suivante » et sans message).
- Aucun autre appel Instagram dans la même session (ne pas relire la messagerie ce jour-là).

## Reprise entre sessions : data/abonnes-cursor.json
`{"max_id": "<next_max_id>", "position": <n abonnés déjà lus>, "date": "jj/mm/aaaa"}`.
- Au démarrage, si le fichier existe : appeler la liste avec `&max_id=<max_id>` ; si la réponse est vide ou en erreur,
  repartir du début (max_id absent) : les premières pages ne coûtent que du temps, les pseudos déjà connus sont ignorés.
- À la fin de chaque session (ou à l'arrêt par le garde-fou) : écrire le `next_max_id` courant et la position.
- Quand `next_max_id` est absent de la réponse : fin de la liste, noter « liste complète » dans le log et supprimer le fichier.

## Étapes
1. Chrome d'Alex (outils `mcp__claude-in-chrome__*`, un seul ToolSearch : tabs_context_mcp, tabs_create_mcp, navigate,
   javascript_tool, get_page_text, tabs_close_mcp). Nouvel onglet sur `https://www.instagram.com/lauric_sergent/`,
   vérifier `document.cookie` contient `ds_user_id=77138870834`. Sinon : log « chrome/insta indisponible », stop.
2. Lancer `scripts-releve/followers.js` adapté : `window.__FMAX=40`, délai 20000 ms, `window.__fmax` initialisé depuis
   le cursor. Attendre par tranches (`python3 -c "import time; time.sleep(120)"`) en lisant `window.__fstate`.
3. Dump : `window.__dump('FOLLOWERS\n'+window.__F.map(x=>[x.pk,x.u,x.n,x.p,x.v].join('|')).join('\n')+'\nENDF')`
   puis `get_page_text` ; le sauver dans le scratchpad (si le résultat revient en clair, le récupérer dans le
   transcript jsonl de la session : tool_result contenant `FOLLOWERS\n`). Noter aussi `window.__fmax`.
4. Croiser avec `data/leads-insta.csv` (Pseudo) et `data/abonnes.csv` (Pseudo) → inconnus = jamais contactés.
   Exclure constant_blt, majorel_alex, juliensergent_, lrtemmanuelle, damienrealise.
5. Fiches profil des inconnus (6 s d'écart, 40 max), dump `INFOS` au même format que le 08/09
   (`pk|u|n|bio|cat|biz|pro|posts|fol|fing|priv|url|city`), puis `python3 scripts-releve/classify.py infos.txt anciens.json`.
   Relire les ✅ Potentiel et écrire à la main leur message (1 élément vu sur le profil, une seule question,
   pas de tiret cadratin, pas de lien). Les ❌ comptes de masse n'ont pas de message.
6. `python3 scripts-releve/add_anciens.py anciens.json` (ajoute uniquement les pseudos inconnus, Type=ancien).
7. Écrire `data/abonnes-cursor.json`, une ligne dans `data/abonnes.log`
   (`<date heure> · anciens abonnés : pages X-Y (positions A-B) · n inconnus ajoutés · latence min-max · cursor sauvé`).
8. `git checkout -- data/eod.csv data/.rappel-calls` puis
   `git add data/abonnes.csv data/abonnes.log data/abonnes-cursor.json && git commit -m "Anciens abonnés : session du <date>" && git pull --rebase && git push`
   (jamais de stash). Fermer l'onglet Chrome. Ne pas republier l'artifact.
9. Si la liste n'est pas finie : la tâche planifiée se relance le jour suivant à la même heure.
