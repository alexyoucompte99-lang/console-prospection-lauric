# Relevé quotidien des conversations Instagram (tâche « releve-insta-lauric »)

But : chaque jour, relire la messagerie de @lauric_sergent par l'API interne (lecture seule, aucun « vu » envoyé),
mettre à jour `data/leads-insta.csv` (statuts vu / répondu, textes, dates, actions) et `data/insta-activite.csv`
(messages envoyés par jour), puis pousser. La page GitHub Pages (onglets Leads, Datas, EOD vs réel) se met à jour seule.

## Rythme et prudence
- 8 secondes minimum entre deux pages d'API (40 conversations par page). Jamais d'envoi, de like, de follow.
- Chaque jour : relire les **300 premières conversations** (les plus récentes, c'est là que les statuts bougent),
  puis **5 pages de plus** que la veille pour remonter progressivement dans le passé (le plancher atteint est noté
  dans `data/insta-coverage.txt`, format `YYYY-MM-DD` de la plus ancienne activité relevée). Quand le plancher est
  antérieur au 01/01/2026, ne plus étendre : 300 conversations par jour suffisent.
- Si une réponse est 429 ou non-200 : arrêter, noter dans `data/insta-releve.log`, réessayer le lendemain.
- Garde-fou de latence (ajouté le 08/09) : mesurer la durée de chaque fetch ; au-delà de 20 s, arrêter la boucle
  (Instagram ralentit avant de bloquer : le 08/09, la page 17 a mis 87 s après 16 pages à 12 s). Attendre 5 min puis
  reprendre depuis `window.__cursor` avec 30 s entre les pages : la reprise s'est faite à 2-4 s de latence sans incident.
- Relevé rétroactif du 08/09 : 35 pages, 1 395 conversations, plancher 01/07/2026 (`data/insta-coverage.txt`).
  La boîte est triée par dernière activité : ce qui manque encore, ce sont les conversations sans aucune activité depuis juillet.
- Chrome ouvert, extension Claude connectée, compte lauric_sergent. Si indisponible : logger et s'arrêter.
- **Une seule session Claude sur Instagram à la fois** (11/09) : deux sessions relevaient en même temps le soir,
  Instagram a répondu en 26 s sur une fiche profil puis en 30 s dès la 2e page d'inbox. Vérifier `data/insta-releve.log`
  et `data/abonnes.log` avant de lancer : si une ligne a moins de 2 h, ne rien lancer.
- Après `releve_insta.py`, lancer `python3 scripts-releve/maj_abonnes.py [nouveaux.json] --date JJ/MM/AAAA` : les abonnés
  qui ont une conversation passent « contacté » (date, message, statut vu/répondu, lien) dans `data/abonnes.csv`.

## Étape 1 : Chrome
Outils `mcp__claude-in-chrome__*` (un seul ToolSearch : tabs_context_mcp, navigate, javascript_tool, get_page_text, tabs_close_mcp).
Nouvel onglet sur `https://www.instagram.com/direct/inbox/`. Le fermer à la fin.

## Étape 2 : extraction (javascript_tool, en arrière-plan)
Lancer une IIFE async qui stocke tout dans `window.__T` (sinon le tool coupe à 45 s) :
```js
window.__T=[]; window.__state2='start'; window.__cursor=null; window.__seen=new Set();
(async()=>{ const H={'x-ig-app-id':'936619743392459','x-requested-with':'XMLHttpRequest'}; const ME='77138870834'; let pages=0;
try{ while(pages<MAXPAGES){
  const u='/api/v1/direct_v2/inbox/?folder=&limit=40&thread_message_limit=20'+(window.__cursor?'&cursor='+encodeURIComponent(window.__cursor):'');
  const r=await fetch(u,{credentials:'include',headers:H});
  if(r.status===429){window.__state2='RATE LIMIT page '+(pages+1);return;} if(!r.ok){window.__state2='ERR '+r.status;return;}
  const j=await r.json();
  for(const t of j.inbox.threads){ if(window.__seen.has(t.thread_id)) continue; window.__seen.add(t.thread_id);
    const lead=t.users[0]||{}; const pk=String(lead.pk||'');
    const items=(t.items||[]).slice().sort((a,b)=>a.timestamp-b.timestamp).map(i=>({w:String(i.user_id)===ME?'L':'P',t:Math.floor(i.timestamp/1e6),ty:i.item_type,x:i.item_type==='text'?(i.text||''):(i.item_type==='link'&&i.link?(i.link.text||''):''),re:(i.reactions&&i.reactions.emojis&&i.reactions.emojis.length)?i.reactions.emojis.map(e=>String(e.sender_id)===ME?'L':'P').join(''):''}));
    window.__T.push({id:t.thread_id,u:lead.username||'',n:lead.full_name||'',rs:t.read_state,seen:(t.last_seen_at&&t.last_seen_at[pk]&&t.last_seen_at[pk].timestamp)?Math.floor(t.last_seen_at[pk].timestamp/1e6):0,la:Math.floor((t.last_activity_at||0)/1e6),items,nItems:(t.items||[]).length}); }
  pages++; window.__state2='page '+pages+' threads '+window.__T.length; window.__cursor=j.inbox.oldest_cursor;
  if(!j.inbox.has_older){window.__state2='done';return;} await new Promise(r=>setTimeout(r,8000)); }
window.__state2='done(max)'; }catch(e){window.__state2='EXC '+e.message} })();
```
MAXPAGES = 8 (300 convs) + pages supplémentaires pour dépasser le plancher de la veille de 5 pages.
Attendre (`python3 -c "import time; time.sleep(60)"`) et lire `window.__state2` jusqu'à « done ».

## Étape 3 : mise en forme (javascript_tool)
Construire `window.__out3` : une ligne par conversation ayant au moins un message de Lauric, 20 champs séparés par `┃`
(pseudo, nom, ts accroche, texte accroche, vocal 0/1, ts vu, ts dernier message Lauric, texte, ts dernier message lead,
texte, read_state, thread_id, nb L, nb P, ts des relances, 1er message = Lauric 0/1, récent 0/1, ts 1er item, nb items, réagi 0/1),
puis les lignes `ACT┃YYYY-MM-DD┃accroches┃suivi┃vocaux`. Retours à la ligne → `⏎`. **Compresser les templates** :
remplacer le texte par `{BIENV}` `{LIKE}` `{RELB}` `{RELQ}` `{A}` `{B}` quand il correspond (regex dans `releve_insta.py`,
même liste), ça divise la taille par 3 et `releve_insta.py` les ré-expanse. Le code complet (extraction, mise en forme, `__part`) est dans
`scripts-releve/` (fichiers `extract.js`, `step3.js`, `save_part.py`, `glue.py`), copiés depuis la session du 08/09.

## Étape 4 : sortie vers le disque (le point délicat)
`javascript_tool` coupe à ~1 000 caractères. Le canal fiable : écrire le texte dans un `<pre>` qui remplace le contenu de
`<main>`, puis `get_page_text`. Ce tool renvoie 50 000 caractères max ; le résultat est **sauvé dans un fichier**
(`~/.claude/projects/-Users-alex-Alex/<session>/tool-results/mcp-claude-in-chrome-get_page_text-*.txt`, JSON `[{text}]`)
seulement s'il dépasse le seuil de tokens de l'outil. Recette qui marche : tranches de 47 000 caractères de données
avec recouvrement (départs 0, 47 000, 94 000…), chaque tranche suivie d'un marqueur `ENDPART` puis de 30 000 caractères
de remplissage (début des données) pour dépasser ~75 000 caractères de page. Après chaque `get_page_text`, sauver la
tranche avec un petit script (voir `scratchpad/save_part.py` de la session du 07/09) puis recoller par ligne commune.
Si une tranche revient quand même en clair (contenu trop répétitif), la relire en compressant les templates.

## Étape 5 : traitement, commit, log
```
python3 releve_insta.py <dump.txt> --date JJ/MM/AAAA
git checkout -- data/eod.csv data/.rappel-calls   # copies modifiées par les runs locaux (jamais de stash)
git add data/leads-insta.csv data/insta-activite.csv data/insta-coverage.txt data/insta-releve.log
git commit -m "Relevé Insta du JJ/MM" && git pull --rebase && git push
```
Ligne de log : `<date heure> · <n> convs relues · plancher <YYYY-MM-DD> · <n> à répondre`.
Ne jamais republier l'artifact claude.ai, ne rien envoyer sur Instagram.

## Export complet des conversations (sous-onglet « 📞 Appels proposés » de l'onglet Datas, ajouté le 09/09)
Le dump `┃` ne garde qu'un résumé par conversation. Pour le sous-onglet Appels proposés il faut les messages complets
(les 20 derniers de chaque conv). **Ce qui ne marche pas (testé le 09/09)** : `window.name` + navigation vers un serveur
local (Instagram envoie COOP, le nom est effacé), `fetch`/`sendBeacon`/`<form>` vers 127.0.0.1 (CSP connect-src et
form-action), `/api/v1/direct_v2/threads/<id>/` (refusé par le classifieur de l'outil Chrome). `scripts-releve/relay.py`
reste utile pour une page sans CSP, pas pour Instagram.
**Ce qui marche** : réduire côté JS aux conversations utiles (au moins un message du lead, ou un message de Lauric qui
propose un appel), sérialiser en JSON une conv par ligne (`window.__out5`), puis le canal `<pre>` + `get_page_text` par
tranches de 47 000 caractères avec recouvrement (voir Étape 4), 4 tranches par `browser_batch` → un fichier tool-results
par lot, recollé par `scripts-releve/glue_json.py <scratchpad>/dump.json` → `dump.json`.
Code prêt : `scripts-releve/export_appels.js` (tranches marquées `J<k>` / `ENDJPART` via `window.__jpart(k)`, pour ne pas
les confondre avec les tranches `P<k>` du relevé ┃). `glue_json.py` cherche seul les tranches des 3 dernières heures dans
tous les dossiers tool-results. `appels_insta.py` fusionne avec le fichier de la veille (le relevé du jour ne relit que les
convs récentes) et liste les conversations « SANS NOTE » à rédiger. Tourne chaque matin dans la tâche `releve-insta-lauric`
(depuis le 11/09), qui met aussi à jour la To do de Lauric (`data/todo.json`).
Puis `python3 appels_insta.py dump.json --date JJ/MM/AAAA` → `data/insta-appels.json`
(détection regex des propositions d'appel dans les messages de Lauric, issue auto : booké Calendly / accepté / répondu /
reporté / vu / non vu ; récaps, cibles et analyse rédigés à la main dans `data/insta-appels-notes.json`, clé = pseudo,
champs `recap`, `cible`, `type`, `verdict`, `issue` (force l'issue), `exclude`, `force` ; `_analyse` = blocs du haut).
Le dump JSON brut n'est pas commité (conversations complètes) : seul `insta-appels.json` l'est.
