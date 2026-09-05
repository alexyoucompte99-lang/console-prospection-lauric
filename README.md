# Console Prospection Insta · Lauric

Console de suivi du setting Instagram de Lauric : entonnoir (messages, nouveaux abonnés, scans acceptés, scans remplis) avec sélecteur Hier / 3 / 7 / 30 jours, chiffres clés avec delta vs 7 jours précédents et cumul du mois, tuiles « Messages par catégorie », vue par setter, messages par jour, alerte si l'EOD n'est plus rempli. Instagram uniquement, LinkedIn exclu.

6 onglets : Vue d'ensemble (avec panneau « EOD non faits » par setter actif), EOD (formulaire + pilotage + derniers reports), Scans Tally (remplis + partiels, boutons WhatsApp), **Calls** (fusion le 04/09 : vues À venir / À remplir / Remplis / À relancer par pills ; à venir = RDV Calendly futurs avec message WhatsApp de confirmation pré-call + lien visio ; à relancer = calls follow-up ou pas de vente avec message WhatsApp de relance ; à remplir = RDV Calendly passés avec suivi fait/no-show/annulé + issue + note, rempli par Lauric depuis la page via des lignes « CallSuivi » du Google Form, la dernière ligne par call gagne), **Ventes** (suivi des calls de vente : à venir / en cours / conclues / perdus + CA signé approximatif, croisement des colonnes de suivi du Sheet Tally et du Sheet « portefeuille des leads », bouton « Voir toutes les infos du call » par carte, **modification directe de chaque deal par Lauric** et ajout d'un deal à la main), **Script setting** (process étiquette leads chauds, vivier d'URLs cliquables vers Insta, A/B testing des messages A Constant / B Cynthia avec résultats EOD par variante, tracking abonnés + scans (saisie directe du total d'abonnés par Lauric), propositions IA, boîte à idées).

Le Google Form EOD sert aussi de base d'écriture pour la console (le front GitHub Pages ne peut pas écrire dans un Sheet) : `postEodRow(setter, notes, date)` poste une ligne technique avec un setter réservé — `Boîte à idées`, `Doublon` (mise de côté d'un deal dans l'onglet Ventes, marqueur `— Doublon : <clé> · <nom>`, retour avec `— Doublon annulé : <clé>`, la dernière ligne gagne), `Vente` (modification d'un deal depuis l'onglet Ventes, voir plus bas), `Tracking` (saisie directe de Lauric dans l'onglet Script setting) et `CallSuivi` (suivi d'un call Calendly depuis l'onglet Calls à remplir : `— Call : <uuid> · <nom>` + `— CallStatut : fait|noshow|annule` + `— CallIssue` + `— CallNote`). Ces 5 setters sont exclus de toutes les stats par `isTestRow`.

Marqueurs stockés dans le champ notes du Google Form EOD et reparsés par la page : `— Détail console : …`, `— Abonnés total : N`, `— Étiquette drapeau : N`, `— Étiquette URL : <url>` (une ligne par URL, champ répétable du form console). Les marqueurs `— Impressions : N` et `— ManyChat Clarté : N` ne sont plus produits (champs retirés le 01/09 à la demande d'Alex) mais restent nettoyés à l'affichage s'ils traînent dans d'anciennes lignes. Les idées de la boîte à idées passent par le même Google Form avec le setter `Boîte à idées` (exclu de toutes les stats par `isTestRow`/`isIdeaRow`).

La console est installable sur téléphone (PWA : manifest + service worker + icônes) : le process à envoyer à Lauric est dans `INSTALLATION-TEL.md`. Une notification ntfy (topic `scan-dirigeant-lauric-d7k4q2`) part à chaque nouveau scan Tally rempli, détecté par le job GitHub qui tourne toutes les 15 min entre ~7h et ~22h Paris. Le même job envoie un message Telegram à Alex à chaque nouvelle idée déposée dans la boîte à idées (diff des lignes `Boîte à idées` du Sheet EOD, secrets repo `TG_TOKEN` / `TG_CHAT`, fonction `notify_new_ideas` de build.py). Le message contient un lien `#script` : la page ouvre directement l'onglet visé (`#eod`, `#tally`, `#ventes`, `#script`).

## Où ça vit

| | |
|---|---|
| **Page live (à partager)** | https://alexyoucompte99-lang.github.io/console-prospection-lauric/ |
| **Artifact Claude (copie figée)** | https://claude.ai/code/artifact/80404996-d93b-4883-8258-e895c32ce168 |
| **Repo** | https://github.com/alexyoucompte99-lang/console-prospection-lauric |

La page live n'a pas besoin d'être régénérée : elle lit les Google Sheets **en direct dans le navigateur**, à chaque ouverture, au retour sur l'onglet (si la dernière lecture date de plus de 5 min), toutes les 10 min tant que l'onglet est visible, et sur clic du bouton **Actualiser**. Le petit badge en haut à droite dit d'où viennent les chiffres et de quand ils datent.

## Ajouts du 04/09

- **Cockpit** en haut de la Vue d'ensemble : calls du jour, à remplir, ventes du mois, € encaissés — tuiles cliquables vers l'onglet concerné.
- **Funnel complet** « Du message à la vente · 30 jours » sous l'entonnoir (messages → scans acceptés → calls faits → ventes).
- **Récap par mois** dans Ventes (calls, faits, no-show, show-up %, ventes, CA depuis la propo des calls).
- **Versements** sur les ventes : payé en 1x/2x/3x + versements reçus (marqueur `— Versements : <clé> · r/t`), CA encaissé au prorata.
- **Recherche par prénom** sous les onglets, filtre toutes les cartes.
- **Dates relatives** (« hier », « dans 3 j ») sur les cartes calls et deals.
- **Rappel « Calls du jour »** : notif ntfy vers 7h Paris (jeton `data/.rappel-calls` commité pour ne l'envoyer qu'une fois par jour).
- Les anciens liens `#cav` / `#car` redirigent vers `#calls` (TAB_ALIAS).

## Calendly

Les RDV de Lauric viennent de l'API Calendly (`fetch_calendly` dans build.py, 90 j passés → 90 j futurs, invités + téléphone extrait des questions). Le jeton (personal access token de lauric.sergent.pro@gmail.com, reçu le 03/09/2026) vit dans le secret GitHub `CALENDLY_TOKEN` et localement dans `calendly-token.txt` (gitignoré). **Il ne doit jamais apparaître dans la page ni être commité** : seul `data/calendly.csv` est public, comme les autres CSV.

## Sources

Google Sheets publics, export CSV direct par URL (pas besoin du MCP Drive) :

- EOD setters : `1vVzQXjAGp-lzF1LTeDMg281dan3TcPxrksvWvxZQRuU`, onglet gid `123224703` (« Réponses au formulaire 1 »)
- Soumissions Tally (scans remplis) : `1aMQ_zNQbq2xyntex3V_6GDY5pE9pIaD_v-FTCzJWxes` (colonnes de suivi vente ajoutées à la main par Lauric : source, Call R1 fait ?, R2 ?, Issue (vente), Dans la cible ; les lignes de stats en bas du Sheet n'ont pas de Submission ID et sont ignorées)
- Portefeuille des leads : `1RdQsQu6FytcHQkWXqXNYTJOi1rhgwJyBE7PJgPtB09c` — **encore privé** : tant qu'il n'est pas partagé « tous ceux qui ont le lien : lecteur », la page et l'Action utilisent la copie `data/portefeuille.csv` (figée au 31/08/2026). Dès que le partage est activé, tout se met à jour tout seul.

Google renvoie bien les en-têtes CORS sur `export?format=csv`, y compris sur la redirection : le `fetch` depuis GitHub Pages passe.

## Fichiers

- `index.html` — toute la console (parsing CSV, agrégation, rendu). Seul fichier à modifier.
- `data/eod.csv`, `data/tally.csv` — copie de secours, utilisée seulement si Google est injoignable. Rafraîchie par GitHub Actions.
- `build.py` — télécharge les CSV et génère `dashboard.html` (copie figée d'`index.html` avec les CSV inlinés) pour l'artifact Claude, qui ne peut pas appeler le réseau.
- `.github/workflows/refresh.yml` — cron 6 h et 11 h UTC, commit `data/` si ça a bougé.

`dashboard.html` est généré, il n'est pas versionné.

## Republier l'artifact Claude

```bash
python3 build.py
```

Puis outil Artifact avec `file_path` = chemin absolu de `dashboard.html`, `url` = l'artifact ci-dessus (URL stable, toujours republier dessus), `favicon` = 🎯.

Options : `--data-only` (télécharge seulement, utilisé par l'Action), `--no-fetch` (réutilise les CSV locaux, debug).

## Pièges connus

- Valeurs sales dans l'EOD : « 25/30 », « 40 (messages) », « P », textes libres. On prend le premier nombre trouvé, sinon 0. Les cellules texte sans chiffre (« Pas de likes ni commentaires ») comptent 0, c'est voulu.
- Colonnes du form longtemps vides : likes (15) et commentaires (16) ont commencé à se remplir en août 2026, scans acceptés (17) démarre à peine, scans remplis (18) toujours vide. Tant qu'une colonne n'a jamais reçu de valeur, la page affiche « pas encore reporté » au lieu de faux zéros, et bascule toute seule dès qu'elle se remplit.
- Le Tally n'a pas de colonne date : il sert de compteur total (+ prénoms), pas de données par jour.
- Les fenêtres 3 / 7 / 30 j se terminent au dernier jour reporté (hier en général, aujourd'hui si l'EOD du jour est déjà là). La ligne sous l'entonnoir dit combien de jours de la fenêtre ont vraiment un EOD.
- Plusieurs lignes EOD par date (plusieurs setters, corrections) : elles s'additionnent.
- Catégories du graphe : Abonnés = colonnes nouveaux + anciens ; Relances = colonne 7 ; Autres = colonne 5 (like/commentaire/story en texte libre au début du form).
- Les colonnes de l'EOD sont repérées par **index**, pas par nom. Si une question est insérée dans le formulaire, tout décale : ajuster `COL` dans `index.html` et les constantes de `build.py`.
- Setter Cynthia : le formulaire EOD de la console lui affiche 3 questions que les autres setters n'ont pas — « Nombre total d'abonnés du compte (relevé en fin de journée) », « Nombre de personnes sur Insta qui ont l'étiquette drapeau » et « URL des personnes mises en étiquette ». Elles partent dans le champ notes du Google Form sous la forme `— Abonnés total : N`, `— Étiquette drapeau : N`, `— Étiquette URL : <url>`, relues et affichées dans les derniers EOD (👥 / 🚩 / 🏷️).
- Abonnés : plus personne ne saisit un gain. Cynthia relève le **total** du compte chaque soir, la console calcule le gain (total du jour − dernier total connu, jamais négatif) et n'envoie que ce gain dans la colonne « abonnés gagnés » du Sheet, pour ne pas casser l'entonnoir historique. Le total brut alimente la tuile « abonnés au total · dernier relevé » (onglet Script setting).
- « Leads ayant rempli le scan » n'est plus demandé dans le formulaire (l'info remonte toute seule de Tally) : la colonne du Sheet reçoit toujours 0, elle est requise côté Google Form.
- Onglet Ventes, modifications de Lauric : chaque carte a un bouton « ✏️ Modifier » (statut forcé, date du prochain call, proposition d'offre, note) et l'onglet a un bloc « ➕ Ajouter un deal » pour un lead absent des deux Sheets. Un enregistrement = une ligne du Google Form avec le setter `Vente`, qui porte tout l'état du deal : `— Vente : <clé> · <nom>` puis `— Statut : auto|avenir|encours|gagne|perdu`, `— Date : aaaa-mm-jj`, `— Offre : …`, `— Note : …`. La dernière ligne gagne, `— Vente annulée : <clé>` rend la main aux Sheets (et supprime un deal ajouté à la main). Statut `auto` = on reclasse normalement, avec l'offre modifiée si elle l'a été. Une clé inconnue des deux Sheets = un deal ajouté à la main (`man|…`), affiché avec le badge « ✍️ Ajouté à la main ». Le tout compte dans les compteurs et dans le CA. Rien n'est écrit dans les Sheets : la console garde la version de Lauric par-dessus. Piège : dans les regex de `parseDealEdits`, l'espace après le `:` doit être `[^\S\n]*` et jamais `\s*`, sinon un champ vide avale la ligne suivante.
- Onglet Ventes : le classement gagné / perdu / à venir / en cours se fait sur du texte libre (regex dans `classifyDeal`), avant les modifications de Lauric qui passent devant. « client », « vente » (aussi en colonne R1) ou « audit » = gagné ; « non », « KO », « aucune réponse », « trop cher » = perdu ; une date jj/mm future dans R1 / R2 / Propo = à venir ; le reste = en cours. Le CA additionne le premier montant ≥ 100 des issues gagnées (après avoir retiré « / N mois »).

## Prévisualisation locale

Serveur `lauric-dashboard` dans `/Users/alex/Alex/.claude/launch.json` (port 8752), page `index.html`.

## Nouveaux abonnés : relevé nocturne (05/09/2026)

L'onglet « 🆕 Nouveaux abonnés » lit `data/abonnes.csv`. Ce fichier est réécrit chaque nuit vers 4 h
par la tâche planifiée Claude `releve-abonnes-lauric` (app Claude Desktop d'Alex, Chrome d'Alex avec
le compte lauric_sergent), qui suit le runbook `RELEVE-ABONNES.md` : nouveaux followers, vérification
« contacté ou pas » dans la messagerie (sans ouvrir les convs non lues), message perso pour les autres,
commit + push. Pré-requis côté Mac : branché, en veille (pas éteint), app Claude et Chrome ouverts,
réveil auto `pmset repeat wakeorpoweron MTWRFSU 03:55:00`, agent launchd
`com.alex.caffeinate-releve-4h` (caffeinate 3h56 → 5h26) pour empêcher la veille pendant le relevé.
Journal : `data/abonnes.log`.
