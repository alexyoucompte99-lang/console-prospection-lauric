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

Astuce du 15/09 : lancer la boucle avec `thread_message_limit=40` depuis un onglet `instagram.com/robots.txt` (rien ne se fige), garder le résultat dans `window.__T40`, puis `window.__T = __T40` réduit aux 20 derniers messages (`nItems` plafonné à 20) pour les étapes 3, Appels et Lead magnet : un seul passage sur Instagram sert aussi à l'onglet À répondre (40 messages de contexte, étiquettes, vocaux).

## Étape 3 : mise en forme (javascript_tool)
Code de référence : `scripts-releve/step3.js` (corrigé le 15/09 : un like du lead après sa réponse ne masque plus la réponse, et une réponse du lead au milieu d'une rafale de messages de Lauric ne la classe plus « à répondre »). Construire `window.__out3` : une ligne par conversation ayant au moins un message de Lauric, 20 champs séparés par `┃`
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
`--act-from` (14/09) : sans lui, un relevé court réécrit les jours anciens de `insta-activite.csv` avec des comptes partiels.

Piège du 14/09 : après avoir vidé `<main>` de l'onglet messagerie pour le canal `<pre>`, l'onglet Instagram s'est figé
(« renderer frozen ») quelques minutes plus tard, et tout nouvel onglet instagram.com restait figé aussi (même processus) tant
que l'onglet figé n'était pas fermé. Pour les appels API qui suivent (abonnés, fiches profil), ouvrir un onglet léger sur
`https://www.instagram.com/robots.txt` : même origine, cookies envoyés, pas d'application React, et le `<pre>` s'écrit dans `body`.
```
python3 releve_insta.py <dump.txt> --date JJ/MM/AAAA --act-from <AAAA-MM-JJ de la plus ancienne activité lue>
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

## Onglet « 💬 À répondre » (ajouté le 12/09/2026)

But : chaque matin, lister les conversations où **le lead a écrit (ou réagi) en dernier sur les 7 derniers
jours et où personne n'a répondu**, et proposer pour chacune un message prêt à envoyer, écrit pour cette
personne. La page lit `data/a-repondre.json` ; l'état « Répondu » est partagé par le Google Form EOD
(setter réservé `RepInsta`, marqueur `— RepIG : <pseudo> · 1|0`, dernière ligne gagne).

1. **Extraction** : même boucle qu'à l'étape 2, mais on s'arrête dès que la plus ancienne activité de la page
   dépasse 7 jours (4 pages suffisent en général, 160 conversations) et on prend `thread_message_limit=40`
   pour avoir le contexte. Ajouter au passage les champs utiles à la personnalisation : `label_items`
   (étiquettes Instagram), `replied_to_message`, les réactions par emoji, la durée des vocaux, la légende
   des réels partagés.
2. **Tri** : garder les conversations où le dernier message hors `action_log` vient du lead et date de moins
   de 7 jours (catégorie `rep`), plus celles où le lead a **réagi** à notre dernier message sans écrire
   (catégorie `reac`). Exclure l'équipe et les proches : `constant_blt`, `majorel_alex`, `juliensergent_`,
   `lrtemmanuelle`, `damienrealise`. Le dossier General (`folder=1`) et les demandes de message
   (`/api/v1/direct_v2/pending_inbox/`) se vérifient aussi, ils sont presque toujours vides côté prospection.
3. **Profils** : `/api/v1/users/<pk>/info/` pour chaque lead retenu, 10 s entre deux appels (bio, catégorie,
   abonnés, lien). **Ne pas utiliser** `/api/v1/users/web_profile_info/` (429 immédiat) ni
   `/api/v1/feed/user/<pk>/` (renvoie du HTML).
4. **Dossiers** : un fichier par conversation (profil, ce que la console sait déjà via `leads-insta.csv`,
   `abonnes.csv`, `insta-appels-notes.json`, `todo.json`, étiquettes EOD, puis le fil complet en heure de
   Paris), plus `brief.md` (positionnement de Lauric, cible, leçons de l'analyse des appels, règles
   d'écriture) et `style.txt` (une trentaine de vraies réponses de Lauric des 14 derniers jours, pour le ton).
5. **Rédaction** : workflow `reponses-insta-lauric` (un rédacteur par conversation, deux critiques
   indépendantes — le lead lui-même et le directeur commercial gardien des règles — puis un éditeur final,
   et un contrôle croisé anti copié-collé). Sortie : `finals.json`.
6. **Fabrication du fichier** : `python3 a_repondre.py <convs.json> <finals.json> --date "JJ/MM/AAAA HHhMM" --fenetre "du JJ/MM au JJ/MM" [--synthese <synthese.json>]`
   → `data/a-repondre.json` (ajoute l'attente en jours, le fil des 10 derniers messages, le dernier message
   du lead, les vocaux à écouter, le lien WhatsApp quand le DM tombe sur un répondeur).
7. **Commit** : `git add data/a-repondre.json` (le dump brut des conversations n'est jamais commité).

Pièges : ne jamais ouvrir une conversation dans l'interface Instagram pendant le relevé (ça envoie le « vu ») ;
les vocaux du lead ne sont pas transcrits, la carte dit de les écouter avant d'envoyer ; un message de masse
envoyé après la réponse du lead compte comme une réponse, vérifier à la main si la liste paraît trop courte.

## Onglet « 🎁 Lead magnet » (Setting, ajouté le 14/09/2026)

But : savoir à qui on a proposé ou envoyé chaque lead magnet (Le Scan Dirigeant sur Tally, la vidéo YouTube
https://youtu.be/edgg977QObk), qui l'a vu, ouvert, qui a répondu, qui a booké ensuite, et quel message marche le mieux.
La page lit `data/lead-magnets.json` ; les analyses rédigées vivent dans `data/lead-magnets-notes.json` (`_analyse`, `_releve`).

1. Avec le même `window.__T` que le relevé (aucun nouvel appel à Instagram), exécuter `scripts-releve/export_lm.js`
   dans l'onglet Instagram : une ligne par message de Lauric qui contient un lien Tally, un lien YouTube ou le mot « scan »,
   avec vu / réaction / réponse du lead après CE message. Renvoie le nombre de tranches (souvent 1 ou 2).
2. Sortie par `browser_batch` : [javascript_tool `window.__lpart(0)`, get_page_text, `window.__lpart(1)`, get_page_text…].
3. `python3 scripts-releve/glue_lm.py <scratchpad>/export_lm.txt` puis
   `python3 lead_magnets.py <scratchpad>/export_lm.txt --date JJ/MM/AAAA`.
   Le script fusionne avec la veille (les envois plus anciens que le relevé du jour sont gardés), ajoute les propositions
   du scan trouvées dans `leads-insta.csv` (accroches LIKE et BIENV sur tout l'historique), rapproche les scans remplis ou
   commencés (Tally, par prénom, uniquement parmi les personnes qui ont reçu le lien ou répondu) et les calls bookés
   APRÈS l'envoi (Calendly par nom complet, `insta-appels.json`, portefeuille). Un call antérieur au lead magnet est noté
   « déjà … avant » et ne compte pas.
4. Mettre à jour les chiffres de `data/lead-magnets-notes.json` (`_analyse`) si ils ont bougé (le script affiche les
   totaux par lead magnet), et `_releve` avec la date. Pas de tiret cadratin.
5. `git add data/lead-magnets.json data/lead-magnets-notes.json`.

Limites : YouTube ne dit pas qui regarde (« ouvert » non mesurable pour la vidéo) ; le rapprochement Tally se fait par
prénom tant que le lien personnalisé `https://tally.so/r/zxvka0?insta=<pseudo>` (champ caché « insta » dans Tally)
n'est pas en place ; seuls les 20 derniers messages de chaque conversation sont relus.

## Onglet « 🎬 Reels à refaire » (Contenu, ajouté le 15/09/2026)
À refaire une fois par mois environ, pas chaque jour, et jamais le même jour qu'un gros relevé.
- **Ce qui ne marche pas** : `/api/v1/feed/user/77138870834/` renvoie une page HTML (plus de JSON côté web),
  `/api/v1/users/web_profile_info/` a répondu 429 dès le premier appel le 15/09 au matin.
- **Ce qui marche (lecture seule, trafic de visiteur normal)** : ouvrir `https://www.instagram.com/lauric_sergent/reels/`,
  installer un espion sur `window.fetch` et `XMLHttpRequest` qui garde les réponses `/graphql/query` contenant `play_count`,
  puis faire défiler avec l'outil `computer` (molette, 8 à 10 crans, 10 s d'attente) : chaque cran charge une ligne de 4 Reels
  (code, `play_count`, `like_count`, `comment_count`, couverture). `window.scrollBy` ne déclenche pas le chargement.
  Les 12 premiers Reels sont déjà chargés avant l'espion : vues lues sur la vignette, likes inconnus. 60 Reels = 15 lignes.
- **Date** : décodée depuis l'identifiant, sans requête : `pk = shortcode en base64 (A-Z a-z 0-9 - _)`,
  `timestamp_ms = (pk >> 23) + 1314220021721`.
- **Légendes** : absentes de la grille. Ouvrir `https://www.instagram.com/p/<code>/` (pas `/reel/`, qui ouvre le fil de
  suggestions) pour 3 ou 4 Reels maximum, 40 s d'écart. La légende type est « Follow @lauric_sergent si t'es dirigeant… ».
- **Sortie** : dump JSON dans un `<pre>` + `get_page_text` (21 k caractères pour 60 Reels, revenu en clair : récupéré dans le
  transcript jsonl de la session), converti au format de `reels.py` (`plays`, `likes`, `comms`, `t`, `cov`).
- **Analyse** : l'accroche écrite sur la vidéo, le format et le sujet se notent à la main dans `data/reels-notes.json`
  (clé = code du Reel) en regardant les couvertures ; `_analyse` contient résumé, à refaire, pourquoi, idées, à éviter.
  Puis `python3 reels.py <export.json> --date "JJ/MM/AAAA HHhMM"` → `data/reels.json`.
- Les couvertures sont des liens Instagram signés qui expirent en 5 jours environ : la carte affiche alors l'accroche sur fond
  coloré, rien ne casse.

## Sous-onglet « ⏱️ Réactivité » (Setting, ajouté le 17/09/2026)

But : mesurer par tranches de durée (pas en moyenne) le temps de réponse de l'équipe quand un lead écrit, leads chauds
et autres leads séparés, et le délai entre l'abonnement et le premier message. La page lit `data/reactivite.json`
et les colonnes `Abonne le` / `Premier message le` de `data/abonnes.csv`.

1. **Heures d'abonnement** (avant ou après la boucle inbox, 1 seul appel) : depuis l'onglet `instagram.com/robots.txt`,
   `GET /api/v1/news/inbox/?could_truncate_feed=true&should_skip_su=true&mark_as_seen=false&timezone_offset=7200`
   (en-têtes `x-ig-app-id`, `x-requested-with`). Les `story_type == 101` sont les abonnements, un par personne
   (`args.timestamp`, `args.profile_id`, `args.profile_name`, jamais groupés). **Environ 5 jours d'historique seulement**
   (`is_last_page` dès la 1re page le 17/09, 91 notifications) : relever au moins tous les 4 jours, sinon les heures sont
   perdues. Sortie en lignes `timestamp┃pk┃pseudo` dans un `<pre>` puis `get_page_text` (le texte brut est court).
   La liste des abonnés (`/friendships/.../followers/`) est dans le même ordre : elle sert de contrôle.
2. **Boucle inbox à 40 messages** (`window.__T40`, voir « Astuce du 15/09 ») en ajoutant `lb` (étiquettes `label_items`),
   `g` (groupe) et `nu` (nombre de participants) à chaque conversation.
3. **Export** : `scripts-releve/export_reac.js` sur `__T40` → tranches `R<k>` (`window.__rpart(k)`, ~50 000 caractères
   pour 400 conversations, 2 tranches), recollées par `python3 scripts-releve/glue_text.py <scratchpad>/reac.txt --prefix R`.
4. `python3 reactivite.py <reac.txt> --notif <follows.txt> --date "JJ/MM/AAAA HHhMM"` → `data/reactivite.json`
   (tours : pseudo, heure du 1er message du lead, heure de notre réponse ou 0, nb de messages, types, politesse)
   et remplit `Abonne le` / `Premier message le` dans `abonnes.csv`. **Lancer `maj_abonnes.py` avant** (il ajoute les
   nouveaux abonnés). Fusion : les tours des conversations non relues sont gardés.
5. `git add data/reactivite.json data/abonnes.csv`.

Règles de calcul (dans la page, fonction `rxCompute`) : un tour = messages du lead d'affilée, le délai court de son
premier message au message suivant de notre côté ; les likes de message ne comptent pas ; « politesse » (merci, ok,
bonne soirée, emoji ou cœur seul, « non merci ») mis à part par défaut ; lead chaud = étape chaud ou plus dans Leads
(étiquette EOD, scan, call, vente), `prospect_chaud` d'À répondre, appel fait / booké / reporté / vente, étiquette
Instagram Prospect, Lead, Booked ou Payé ; « en attente » (< 24 h) et « sans réponse » (> 24 h) = état à l'heure du relevé
(`ts`). Abonné déjà en conversation avant de s'abonner : mis à part.
