# Relevé nocturne des nouveaux abonnés (tâche « releve-abonnes-lauric », 4 h)

But : chaque nuit, lister les nouveaux abonnés du compte Instagram de Lauric (@lauric_sergent),
vérifier dans la messagerie qui a déjà été contacté (message envoyé, date, lien de la conv),
préparer un premier message personnalisé pour ceux qui ne l'ont pas été, et réécrire
`data/abonnes.csv`. La page GitHub Pages lit ce fichier (onglet « Nouveaux abonnés »).

## Fichier de sortie : data/abonnes.csv

Colonnes (en-tête exact, ordre exact) :
`Pseudo,Nom,Detecte,Profil,Cible,Message propose,Contacte,Date contact,Message envoye,Statut,Conv,Releve,Type`

- Pseudo : identifiant Insta sans @. Clé unique : ne jamais dupliquer une ligne.
- Nom : nom affiché (sinon le pseudo).
- Detecte : date jj/mm/aaaa du relevé où le follower est apparu la première fois (ne jamais la modifier ensuite).
- Profil : 1 à 2 phrases d'analyse du profil (bio, publications, pro/perso, taille du compte).
- Cible : `✅ Potentiel (…)`, `❓ À qualifier (…)` ou `❌ Hors cible (…)` avec la raison courte.
- Message propose : premier message perso dans l'esprit du script setting (voir plus bas). Vide si Contacte = oui.
- Contacte : `oui` / `non`.
- Date contact : jj/mm/aaaa du message envoyé par Lauric (lue dans la conv), sinon vide.
- Message envoye : texte exact du dernier message envoyé par Lauric (« Vocal » si c'est un vocal), sinon vide.
- Statut : `envoye` (pas vu), `vu`, `reagi` (❤️), `repondu`, sinon vide.
- Conv : URL `https://www.instagram.com/direct/t/<id>/` si connue, sinon vide.
- Releve : jj/mm/aaaa du dernier passage qui a vérifié cette ligne.

Les anciennes lignes sont CONSERVÉES et mises à jour (Contacte / Date / Message / Statut / Conv / Releve).
Une ligne passée à `oui` ne repasse jamais à `non`. Écrire le CSV avec le module `csv` de Python
(quoting minimal, UTF-8, retours à la ligne dans les champs entre guillemets), jamais à la main.

## Méthode API (préférée depuis le 07/09, lecture seule, bien plus fiable que le scroll)

La modale « Followers » reste souvent bloquée sur un spinner et la liste de la messagerie charge par paquets.
Depuis un onglet instagram.com connecté (compte lauric_sergent), `javascript_tool` peut appeler l'API interne
en GET avec `credentials:'include'` et les en-têtes `x-ig-app-id: 936619743392459`, `x-requested-with: XMLHttpRequest` :

- Followers (les plus récents en premier, 50 par page, `next_max_id` pour la suite) :
  `/api/v1/friendships/77138870834/followers/?count=50&search_surface=follow_list_page` → `users[]` (pk, username, full_name, is_private).
- Fiche d'un profil (bio, compteurs, catégorie) : `/api/v1/users/<pk>/info/` → `user`. Attendre 3 à 4 s entre deux appels
  (`web_profile_info` répond 429, ne pas l'utiliser ; `feed/user` renvoie du HTML, ouvrir le profil dans l'onglet et lire
  les `alt` des images de `main` pour avoir les légendes).
- Messagerie SANS envoyer de « vu » : `/api/v1/direct_v2/inbox/?folder=&limit=45&thread_message_limit=10` → `inbox.threads[]` :
  `thread_id` (URL de conv = `https://www.instagram.com/direct/t/<thread_id>/`), `users[0].username`, `items[]` (user_id 77138870834 = Lauric,
  `text`, `item_type` text/voice_media, `timestamp` en µs), `read_state` ≠ 0 = réponse non lue, `last_seen_at[<pk du lead>]` = ce que le lead a vu.
  Un GET sur l'inbox ne marque rien comme lu : on peut lire la réponse du lead sans ouvrir la conv.
  Piège : la sortie de javascript_tool masque les longs identifiants dans un objet JSON (« BLOCKED ») ; les renvoyer dans une chaîne jointe par « | ».

Si l'API répond en HTML ou 4xx, revenir à la méthode visuelle ci-dessous.


## Prudence (ajouté le 07/09/2026 au soir)
Le 07/09, une lecture de 189 abonnés en 8 pages (7 s entre pages) a fait passer Instagram de 1 s à 50 s de réponse par page :
signal de limitation douce. Règles depuis :
- pause complète le 08/09/2026 ;
- puis **4 pages maximum par nuit**, **12 s entre deux appels** à la liste des abonnés, 4 s entre deux fiches de profil, 15 profils max ;
- si une réponse dépasse 20 s ou renvoie 429 : arrêter, noter « ralentissement Instagram » dans data/abonnes.log, reprendre la nuit suivante ;
- un abonné dont le pseudo figure déjà dans data/leads-insta.csv a déjà une conversation : ne pas le retraiter.
- Relevé rétroactif du 08/09 (session Alex) : 16 pages à 15 s (la liste renvoie ~24 abonnés par page malgré `count=50`),
  384 abonnés lus, latence 0,3 à 0,8 s, aucun ralentissement ; 49 fiches `/users/<pk>/info/` à 5 s d'écart (1 à 10 s de latence).
  Les anciens abonnés jamais contactés sont ajoutés avec la colonne `Type=ancien` : la page les range dans une section
  repliable « Anciens abonnés jamais contactés » et ne les compte pas dans « À contacter ». Le relevé nocturne laisse `Type` vide.

## Étape 1 : nouveaux abonnés (Chrome d'Alex, compte lauric_sergent connecté)

Outils : `mcp__claude-in-chrome__*` chargés en UN SEUL appel ToolSearch
(tabs_context_mcp, tabs_create_mcp, navigate, read_page, find, get_page_text, computer, javascript_tool, tabs_close_mcp).
Créer un NOUVEL onglet, ne toucher à aucun autre onglet, le fermer à la fin.

1. Ouvrir `https://www.instagram.com/lauric_sergent/followers/` (modale « Abonnés », les plus récents en haut).
   Si la page demande une connexion ou affiche un checkpoint : écrire « chrome/insta indisponible » dans
   `data/abonnes.log` et s'arrêter, sans boucler, sans notifier.
2. Lire la liste du haut vers le bas (read_page ou get_page_text) et s'arrêter dès qu'on retombe sur
   3 pseudos consécutifs déjà présents dans data/abonnes.csv (ou après 40 pseudos max). Les pseudos
   inconnus = nouveaux abonnés des dernières 24 h environ (Instagram ne donne pas la date de follow).
   Attendre 5 à 6 s après chaque scroll : la liste charge lentement.
3. Pour chaque nouveau : ouvrir `https://www.instagram.com/<pseudo>/`, lire nom, bio, nombre de
   publications/abonnés/abonnements, type de compte, quelques légendes. Noter Profil + Cible.
   Naviguer lentement (3 à 5 s entre deux pages), max ~30 profils par passage.

## Étape 2 : qui a déjà été contacté (messagerie, SANS envoyer de « vu »)

RÈGLE ABSOLUE : ne JAMAIS ouvrir une conversation qui contient une réponse non lue
(ligne en gras / texte « Unread » dans la liste). Ouvrir une conv non lue envoie le « vu » au lead.

PIÈGE vérifié le 05/09 : le champ « Rechercher » de la messagerie ne liste QUE des comptes (« Plus de comptes »),
il ne fait PAS remonter les conversations existantes. Ne pas s'en servir pour décider « contacté ou pas ».

Méthode qui marche : parcourir la liste de la boîte Primary elle-même.
1. Ouvrir `https://www.instagram.com/direct/inbox/` (onglet Primary ; General = perso, on n'y va pas).
2. Lire la liste du haut vers le bas par captures (zoom sur la colonne de gauche, x 70-480) en scrollant
   par 3 crans avec la souris sur la liste, 4 à 7 s d'attente à chaque fois : la liste charge par paquets
   lents et reste parfois bloquée sur un squelette gris (réessayer un scroll après 7 s). Lire jusqu'à ce que
   les horodatages dépassent 3 j : un nouvel abonné contacté a forcément une conv plus récente que ça.
   Les entrées se lisent : nom affiché, extrait (« Vous: … » = notre dernier message, sinon c'est le lead
   qui a parlé en dernier), horodatage. Une conv non lue est en gras avec un point bleu.
3. Croiser par NOM AFFICHÉ (le pseudo n'apparaît pas dans la liste) avec les abonnés à vérifier. Trois cas :
   - Absent de la liste : Contacte = non.
   - Présent avec extrait « Vous: … » : Contacte = oui. La conv peut être ouverte sans risque (dernier message
     = le nôtre) : cliquer l'entrée (find « conversation list item <Nom> » puis left_click sur le ref), attendre
     5 s, lire le texte après le dernier « Voir profil » dans main.innerText : horodatage (« Ven 22:45 » =
     jour de la semaine + heure, à convertir en date), texte exact, « Vu : il y a … » sous le message
     (→ Statut vu) ou ❤️ (→ reagi), sinon envoye. Conv = location.href (`/direct/t/<id>/`).
     Les emojis manquent dans main.innerText : reprendre le texte depuis l'extrait de la liste ou une capture.
   - Présent en gras / point bleu (réponse non lue) : Contacte = oui, Statut = repondu, Date contact = horodatage,
     Message envoye = « (réponse non lue, conv non ouverte) », Conv vide. NE PAS OUVRIR.

Exclure des relevés : CON$TANT (@constant_blt, setter), « Utilisateur Instagram » (comptes supprimés),
Alexandre Majorel (épinglé).

## Étape 3 : message personnalisé (pour les Contacte = non)

Esprit du script setting de la console (onglet Script setting) :
- Commencer par « Hello <Prénom> ! » et remercier pour l'abonnement.
- Au moins UN élément vu sur le profil (« J'ai vu que… »), jamais deux messages identiques.
- Finir par une seule question ouverte du type « tu es à ton compte ou tu diriges une équipe ? ».
- Profil muet ou privé : dire honnêtement qu'on n'a rien pu voir et poser la question.
- Ton chaleureux, tutoiement, 3 à 5 lignes, emojis avec parcimonie, JAMAIS de tiret cadratin (—).
- Pas de lien, pas de lead magnet dans le premier message.

## Étape 4 : écrire, vérifier, pousser

1. Réécrire `data/abonnes.csv` (Python + module csv). Vérifier : en-tête exact, aucun pseudo en double,
   toutes les anciennes lignes présentes, Releve = date du jour sur les lignes vérifiées.
2. Ajouter une ligne à `data/abonnes.log` : `<date heure> · <n> nouveaux · <n> non contactés · <n> contactés vérifiés`.
3. `git add data/abonnes.csv data/abonnes.log && git commit -m "Relevé abonnés du <date>" && git pull --rebase && git push`
   (JAMAIS de stash ; si le rebase échoue, `git rebase --abort`, noter l'erreur dans le log et s'arrêter).
4. Fermer l'onglet Chrome créé. Ne pas republier l'artifact claude.ai.

Si Chrome, la session Insta ou GitHub sont indisponibles : logger et s'arrêter proprement. Ne jamais
envoyer de message Instagram, ne jamais liker, ne jamais suivre/se désabonner : lecture seule.

## Relevé du total d'abonnés (tâche « releve-total-abonnes-lauric », 18 h)

But : chaque soir à 18 h, lire le compteur d'abonnés affiché sur le profil @lauric_sergent et l'ajouter
à `data/abonnes_total.csv` (colonnes `Date,Abonne scrappe`, une ligne par jour, jj/mm/aaaa). La page trace
la courbe en haut de l'onglet « Nouveaux abonnés » (KPIs : dernier relevé, delta veille, 7 j, 30 j).

1. Chrome d'Alex (outils mcp__claude-in-chrome__*, un seul ToolSearch), NOUVEL onglet sur
   `https://www.instagram.com/lauric_sergent/`, attendre 5 s.
2. Lire le nombre : `javascript_tool` → `document.querySelector('main').innerText.match(/([\d\s  ]+)\s*followers|abonnés/i)`,
   ou en secours l'API `/api/v1/users/77138870834/info/` (en-tête `x-ig-app-id: 936619743392459`) → `user.follower_count`.
   Sur le HTML, le nombre est arrondi au-delà de 10 000 (« 12,3 k ») : préférer l'API dans ce cas.
3. `python3 releve_total.py <nombre>` (remplace la ligne du jour si elle existe).
4. `git checkout -- data/eod.csv data/.rappel-calls` (copies auto modifiées par les runs locaux) puis
   `git add data/abonnes_total.csv && git commit -m "Abonnés du <date> : <n>" && git pull --rebase && git push` (jamais de stash).
5. Fermer l'onglet. Si Chrome / Insta indisponible : ajouter « <date> · total indisponible » à `data/abonnes.log` et s'arrêter.
